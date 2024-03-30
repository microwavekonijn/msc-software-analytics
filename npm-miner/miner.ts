import * as dotenv from 'dotenv';
import {MongoClient} from 'mongodb';
import {Npm} from './utils/npm';
import {Utils} from './utils/utils';
import {load} from 'all-package-names';
import {retryWrapper} from './utils/retry';

dotenv.config();

const debug = (process.env.DEBUG?.toLowerCase().trim() == 'true') ? console.log : () => null;

(async function () {
  const {packageNames} = await load();
  console.log('Loaded dataset');

  const mongodb = new MongoClient(process.env.MONGODB_URL);

  await mongodb.connect();
  console.log('Connected to Mongo');

  const db = mongodb.db(process.env.MONGODB_DATABASE);
  const collection = db.collection('npm');

  const getPackage = retryWrapper(Npm.getPackage);
  const getDownloads = retryWrapper(Npm.getDownloads);

  const LAST_YEAR = new Date(new Date().getTime() - 365 * 24 * 3600 * 1000);

  const MAGIC_NUMBER = 1000;
  const total = packageNames.length;
  let done = 0;
  let ignored = 0;
  let failed = 0;

  console.log('Start collecting');

  for (let i = 0; i < total; i += MAGIC_NUMBER) {
    await Promise.all(
      packageNames
        .slice(i, i + MAGIC_NUMBER)
        .map(async name => {
          try {
            debug('Fetching package ' + name);
            const pkg = await getPackage(name);

            if (!pkg.repository?.url?.includes('://github.com')) {
              debug('Ignoring ' + name);
              ignored++;
              return;
            }

            const github = pkg.repository.url;

            const lastTime = new Date(Utils.lastTime(pkg.time));
            if (lastTime < LAST_YEAR) return;

            const lastTimeMY = new Date(lastTime.getTime() - 365 * 24 * 3600 * 1000);

            debug('Fetching downloads ' + name);
            const downloads = await getDownloads(name, `${Utils.formatDate(lastTimeMY)}:${Utils.formatDate(lastTime)}`);

            if ('error' in downloads) {
              debug('Ignoring ' + name);
              ignored++;
              return;
            }

            await collection.updateOne({_id: pkg._id}, {
              $set: {
                _id: pkg._id,
                pkg,
                github,
                downloads,
              }
            }, {upsert: true}).catch(console.log);

            done++;
          } catch (err) {
            failed++;
            console.error(`Failed for ${name}: ${err}`);
          }
        }));
    console.log(`${(done + ignored + failed) / total * 100}% (failed ${failed}, ignored ${ignored})`);
  }

  await mongodb.close();
})();
