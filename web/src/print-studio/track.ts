import type { Workshop } from "./simulation";

export type Point = { x: number; y: number };
export type Placement = { id: number; state: "waiting" | "running" | "done"; point: Point; progress?: number; slot?: number };
export const stations = [{x: 346,y: 103}, {x: 510,y: 103}, {x: 346,y: 282}, {x: 510,y: 282}];
export const origin = {x: 93, y: 96};
export const width = 820;
export const height = 412;

export function placements(workshop: Workshop): Placement[] {
  return [
    ...workshop.waiting.map((job): Placement => ({
      id: job.id, state: "waiting", point: {x: 85 + (job.id - 1) % 2 * 61, y: 172 + Math.floor((job.id - 1) / 2) * 42},
    })),
    ...workshop.running.map((job): Placement => ({
      id: job.id, state: "running", slot: job.slot, point: stations[job.slot!],
      progress: 1 - job.remaining / job.duration,
    })),
    ...workshop.done.map((job, index): Placement => ({
      id: job.id, state: "done", point: {x: 675 + index % 2 * 61, y: 172 + Math.floor(index / 2) * 42},
    })),
  ].sort((left, right) => left.id - right.id);
}

export function route(from: Placement | undefined, to: Placement, current: Point): Point[] {
  if (!from || from.state === to.state) return [current, to.point];
  return [current, {x: current.x, y: 193}, {x: to.point.x, y: 193}, to.point];
}

export function along(points: Point[], fraction: number): Point {
  const distances = points.slice(1).map((end, index) => Math.hypot(end.x - points[index].x, end.y - points[index].y));
  let remaining = distances.reduce((sum, length) => sum + length, 0) * Math.min(1, Math.max(0, fraction));
  for (const [index, length] of distances.entries()) {
    if (length > 0 && remaining < length) {
      const start = points[index], end = points[index + 1];
      return {x: start.x + (end.x - start.x) * remaining / length, y: start.y + (end.y - start.y) * remaining / length};
    }
    remaining -= length;
  }
  return points[points.length - 1];
}

export function stationStates(workshop: Workshop): ("running" | "open" | "closed")[] {
  const occupied = new Set(workshop.running.map(job => job.slot));
  let free = Math.max(0, workshop.limit - occupied.size);
  return stations.map((_, index) => {
    if (occupied.has(index)) return "running";
    if (free === 0) return "closed";
    free--;
    return "open";
  });
}
