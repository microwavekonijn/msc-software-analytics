import {from, map, mergeMap, of, retry, Subject, tap, timer} from 'rxjs';

type Func<P extends Array<any>, R> = (...args: P) => Promise<R>;

export function retryWrapper<P extends Array<any>, R>(func: Func<P, R>): Func<P, R> {
  const queue = new Subject<{ args: P, resolve: (R) => void }>();

  queue
    .pipe(
      mergeMap(req =>
        of(req).pipe(
          mergeMap(() => from(func(...req.args))),
          tap({error: err => console.log({req, err})}),
          retry({
            delay: (err, retryCount) => timer(Math.pow(1000, retryCount))
          }),
          map(res => req.resolve(res))
        )),
    )
    .subscribe();

  return (...args) => new Promise(resolve => {
    queue.next({args, resolve});
  });
}
