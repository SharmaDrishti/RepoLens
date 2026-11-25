import test from "node:test";
import assert from "node:assert/strict";
import { sceneStep } from "../src/explain/progression.ts";
import { advancePlayback, capacityFrames, initialPlayback, tickPlayback, travelTime } from "../src/explain/capacity.ts";

test("traversal advances, bounds the active step, and replays at the start", () => {
  assert.equal(sceneStep(0, 3, "previous"), 0);
  assert.equal(sceneStep(0, 3, "next"), 1);
  assert.equal(sceneStep(2, 3, "next"), 2);
  assert.equal(sceneStep(2, 3, "previous"), 1);
  assert.equal(sceneStep(2, 3, "replay"), 0);
  assert.equal(sceneStep(0, 0, "next"), 0);
});

test("a lowered limit keeps the waiting ticket in place until completions open a slot", () => {
  const scenario = {
    id: "lower", choice: 1,
    initial_state: {limit: 2, waiting: 1, running: 2, settled: 0},
    steps: [
      {id: "lower", event: "limit", state: {limit: 1, waiting: 1, running: 2, settled: 0}},
      {id: "first", event: "settle", state: {limit: 1, waiting: 1, running: 1, settled: 1}},
      {id: "second", event: "settle", state: {limit: 1, waiting: 0, running: 1, settled: 2}},
    ],
  };
  const frames = capacityFrames(scenario);
  assert.deepEqual(frames.map(frame => [frame.limit, frame.queues.waiting, frame.queues.running, frame.queues.settled]), [
    [2, [3], [1, 2], []], [1, [3], [1, 2], []], [1, [3], [2], [1]],
    [1, [3], [], [1, 2]], [1, [], [3], [1, 2]],
  ]);
  assert.deepEqual(frames[2].presses, [0, 2]);
});

test("a paused handoff resumes from the same elapsed time and steps stop on arrival", () => {
  const traveling = tickPlayback(advancePlayback(initialPlayback, 4, "play"), 220, 4);
  const paused = { ...traveling, mode: "paused" };
  assert.deepEqual(tickPlayback(paused, 2000, 4), paused);
  const resumed = advancePlayback(paused, 4, "step");
  assert.equal(resumed.index, 1);
  assert.equal(resumed.elapsed, 220);
  assert.deepEqual(tickPlayback(resumed, 500, 4), {index: 1, elapsed: travelTime, mode: "paused"});
});
