export namespace Utils {
  export function lastTime(times: Record<string, string>) {
    let lastTime = '';

    for (const key in times)
      if (lastTime.localeCompare(times[key]))
        lastTime = times[key];

    return lastTime;
  }

  export function formatDate(date: Date) {
    return [date.getFullYear(), date.getMonth() + 1, date.getDate()].join('-');
  }
}
