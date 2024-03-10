import {Axios} from 'axios';

const npmRegistry = new Axios({baseURL: 'https://registry.npmjs.org'});
const npmApi = new Axios({baseURL: 'https://api.npmjs.org'});

export namespace Npm {
  export async function getPackage(pkg: string) {
    const res = await npmRegistry.get(pkg);

    return JSON.parse(res.data);
  }

  export async function getDownloads(pkg: string, time: string) {
    const res = await npmApi.get(`downloads/point/${time}/${pkg}`);

    return JSON.parse(res.data);
  }
}