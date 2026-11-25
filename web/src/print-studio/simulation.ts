// Deterministic classroom simulation. Durations are illustrative, in milliseconds.
const durations = [1250, 2200, 1750, 1500, 2500, 1850, 1400, 2050];

export type Job = { id: number; duration: number; remaining: number; slot?: number };
export type Workshop = { limit: number; waiting: Job[]; running: Job[]; done: Job[] };

export function setLimit(workshop: Workshop, limit: number): Workshop {
  const waiting = [...workshop.waiting];
  const running = [...workshop.running];
  while (waiting.length && running.length < limit) {
    const slot = [0, 1, 2, 3].find(index => !running.some(job => job.slot === index));
    running.push({ ...waiting.shift()!, slot });
  }
  return { ...workshop, limit, waiting, running };
}

export function newWorkshop(limit = 2): Workshop {
  return setLimit({
    limit, waiting: durations.map((duration, id) => ({ id: id + 1, duration, remaining: duration })),
    running: [], done: [],
  }, limit);
}

export function advance(workshop: Workshop, duration: number): Workshop {
  let remainingTime = duration;
  let result = workshop;
  while (remainingTime > 0 && result.running.length) {
    const elapsed = Math.min(remainingTime, ...result.running.map(job => job.remaining));
    const active = result.running.map(job => ({ ...job, remaining: job.remaining - elapsed }));
    result = setLimit({
      ...result, running: active.filter(job => job.remaining > 0),
      done: [...result.done, ...active.filter(job => job.remaining === 0)],
    }, result.limit);
    remainingTime -= elapsed;
  }
  return result;
}

export function nextCompletion(workshop: Workshop): Workshop {
  return workshop.running.length ? advance(workshop, Math.min(...workshop.running.map(job => job.remaining))) : workshop;
}
