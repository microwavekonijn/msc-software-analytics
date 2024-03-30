import {from, map, mergeMap, of, retry, Subject, tap, timer, catchError, EMPTY} from 'rxjs';

type Func<P extends Array<any>, R> = (...args: P) => Promise<R>;

export function retryWrapper<P extends Array<any>, R>(func: Func<P, R>): Func<P, R> {
  const queue = new Subject<{ args: P, resolve: (R) => void, reject: (any) => void }>();

  queue
    .pipe(
      mergeMap(req =>
        of(req).pipe(
          mergeMap(() => from(func(...req.args))),
          retry({
            count: 5,
            delay: (err, retryCount) => timer(1000 * Math.pow(4, retryCount))
          }),
          catchError(err => {
            req.reject(err);
            return EMPTY;
          }),
          map(res => req.resolve(res))
        )),
    )
    .subscribe();

  return (...args) => new Promise((resolve, reject) => {
    queue.next({args, resolve, reject});
  });
}
