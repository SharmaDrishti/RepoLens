import { advance, newWorkshop, nextCompletion, setLimit } from "./simulation.ts";
import type { Workshop } from "./simulation.ts";

export const travelTime = 720;
export const captionTime = 1600;
export type Player = {
  workshop: Workshop;
  peakActive: number;
  previous?: Workshop;
  arrival: boolean;
  started: boolean;
  pendingLimit?: number;
  motion: number;
  mode: "paused" | "playing" | "step";
  speed: number;
  caption: string;
  captionAge: number;
  captionFrozen: boolean;
};

export function describe(workshop: Workshop): string {
  if (!workshop.running.length) return "Every task has settled. The finished tray holds the whole batch.";
  if (workshop.waiting.length) return `${workshop.running.length} running. ${workshop.waiting.length} still waiting for room.`;
  return "The last jobs are running. The waiting rack is empty.";
}

export function createPlayer(limit = 2, speed = .5): Player {
  const workshop = newWorkshop(limit);
  return {workshop, peakActive: workshop.running.length, arrival: false, started: false, motion: travelTime, mode: "paused", speed, caption: "", captionAge: 0, captionFrozen: false};
}

function change(player: Player, workshop: Workshop, caption: string): Player {
  return {...player, previous: player.workshop, workshop, peakActive: Math.max(player.peakActive, workshop.running.length), motion: 0, arrival: false, caption, captionAge: 0, captionFrozen: false};
}

export function replay(player: Player): Player {
  const fresh = createPlayer(player.workshop.limit, player.speed);
  return {...fresh, mode: "playing", arrival: true, started: true, motion: 0,
    caption: `The batch arrives. ${describe(fresh.workshop)}`};
}

function finish(player: Player, workshop: Workshop): Player {
  const done = workshop.done.length - player.workshop.done.length;
  const started = player.workshop.waiting.length - workshop.waiting.length;
  const settled = done === 1 ? "A task settled." : `${done} tasks settled.`;
  return change(player, workshop, started
    ? settled + (started === 1 ? " The next waiting task can start." : ` ${started} waiting tasks can start.`)
    : settled + " " + describe(workshop));
}

export function togglePlay(player: Player): Player {
  if (player.mode === "playing") return {...player, mode: "paused", captionFrozen: true};
  return !player.started && player.motion === travelTime && !player.workshop.done.length
    ? replay(player) : {...player, mode: "playing", captionFrozen: false};
}

export function stepPlayer(player: Player): Player {
  if (player.motion < travelTime) return {...player, mode: "step", captionFrozen: false};
  if (!player.workshop.running.length) return player;
  return finish({...player, mode: "step", started: true}, nextCompletion(player.workshop));
}

export function changeLimit(player: Player, limit: number): Player {
  if (player.motion < travelTime) return {...player, pendingLimit: limit,
    mode: player.mode === "paused" ? "step" : player.mode};
  const workshop = setLimit(player.workshop, limit);
  const caption = workshop.running.length > limit
    ? "The limit dropped. Running jobs finish before another task can start."
    : `Limit set to ${limit}. ${describe(workshop)}`;
  return workshop.waiting.length === player.workshop.waiting.length
    ? {...player, workshop, caption, captionAge: 0, captionFrozen: false}
    : change({...player, mode: player.mode === "paused" ? "step" : player.mode}, workshop, caption);
}

export function playerClockActive(player: Player): boolean {
  return player.mode !== "paused" || (!!player.caption && !player.captionFrozen);
}

export function tickPlayer(player: Player, wallTime: number): Player {
  if (!playerClockActive(player)) return player;
  const elapsed = wallTime * player.speed;
  if (player.caption && !player.captionFrozen) {
    const captionAge = player.captionAge + elapsed;
    player = {...player, captionAge, caption: captionAge >= captionTime ? "" : player.caption};
  }
  if (player.mode === "paused") return player;
  if (player.motion < travelTime) {
    const motion = Math.min(travelTime, player.motion + elapsed);
    const updated: Player = {...player, motion, mode: motion === travelTime &&
      (player.mode === "step" || !player.workshop.running.length) ? "paused" : player.mode};
    return motion === travelTime && player.pendingLimit !== undefined
      ? changeLimit({...updated, pendingLimit: undefined}, player.pendingLimit) : updated;
  }
  if (!player.workshop.running.length) return {...player, mode: "paused"};
  // Advance only to the next settlement, so every handoff has a readable beat.
  const remaining = Math.min(...player.workshop.running.map(job => job.remaining));
  const workshop = advance(player.workshop, Math.min(elapsed, remaining));
  return workshop.done.length > player.workshop.done.length
    ? finish(player, workshop) : {...player, workshop};
}
