export type CapacityState = { limit: number; waiting: number; running: number; settled: number };
export type CapacityStep = {
  id: string;
  event: "limit" | "settle";
  state: CapacityState;
  caption: string;
  fact_ids: string[];
  provenance?: "source_review";
};
export type CapacityScenario = {
  id: string;
  choice: number;
  initial_state: CapacityState;
  steps: CapacityStep[];
};
export type CapacityBehavior = {
  family: "capacity";
  question: string;
  scenarios: CapacityScenario[];
  facts: Record<string, { evidence: { id: string }[] }>;
  generation: { model?: string };
};
export const lanes = ["waiting", "running", "settled"] as const;
export type Lane = typeof lanes[number];
type Queues = Record<Lane, number[]>;
type Frame = { limit: number; queues: Queues; caption: string; step?: CapacityStep; presses: number[] };

export function capacityFrames(scenario: CapacityScenario): Frame[] {
  let ticket = 0;
  const initial = scenario.initial_state;
  const start = (count: number) => Array.from({ length: count }, () => ++ticket);
  let queues = { settled: start(initial.settled), running: start(initial.running), waiting: start(initial.waiting) };
  const frames: Frame[] = [];
  const addFrame = (limit: number, caption: string, step?: CapacityStep) => {
    const presses = (frames.at(-1)?.presses ?? []).map(id => queues.running.includes(id) ? id : 0);
    for (const id of queues.running) {
      if (presses.includes(id)) continue;
      const open = presses.indexOf(0);
      if (open === -1) presses.push(id);
      else presses[open] = id;
    }
    frames.push({ limit, queues, caption, step, presses });
  };
  addFrame(initial.limit, "The presses run the active tasks. The next task waits for room to start.");
  for (const step of scenario.steps) {
    const limit = step.state.limit;
    const admitted = queues.waiting.length - step.state.waiting;
    let caption = `The limit changes to ${limit}. There is room to start waiting work.`;
    if (step.event === "settle") {
      const [finished, ...remaining] = queues.running;
      queues = { ...queues, running: remaining, settled: [...queues.settled, finished] };
      caption = "A running task finishes. The count falls below the limit, opening a slot.";
    }
    if (admitted) {
      // The saved state describes the stable point after admission. Give the
      // completion or limit change its own frame before moving the queued work.
      addFrame(limit, caption, step);
      queues = {
        ...queues,
        waiting: queues.waiting.slice(admitted),
        running: [...queues.running, ...queues.waiting.slice(0, admitted)],
      };
    }
    addFrame(limit, step.caption, step);
  }
  return frames;
}

export const travelTime = 600;
const frameTime = 1550;
export type Playback = { index: number; elapsed: number; mode: "paused" | "play" | "step" };
export const initialPlayback: Playback = { index: 0, elapsed: travelTime, mode: "paused" };

export function advancePlayback(playback: Playback, end: number, mode: "play" | "step"): Playback {
  if (playback.elapsed < travelTime) return { ...playback, mode };
  if (playback.index === end) return playback;
  return { index: playback.index + 1, elapsed: 0, mode };
}

export function tickPlayback(playback: Playback, elapsed: number, end: number): Playback {
  if (playback.mode === "paused") return playback;
  const time = playback.elapsed + elapsed;
  if (playback.mode === "step" || playback.index === end) {
    return time >= travelTime
      ? { ...playback, elapsed: travelTime, mode: "paused" }
      : { ...playback, elapsed: time };
  }
  return time >= frameTime
    ? { index: playback.index + 1, elapsed: time - frameTime, mode: "play" }
    : { ...playback, elapsed: time };
}
