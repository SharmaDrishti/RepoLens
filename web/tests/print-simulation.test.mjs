import test from "node:test";
import assert from "node:assert/strict";
import { advance, newWorkshop, nextCompletion, setLimit } from "../src/print-studio/simulation.ts";

test("a completion frees a press for the first job in line", () => {
  const before = newWorkshop(2);
  const after = nextCompletion(before);
  assert.deepEqual(after.done.map(job => job.id), [1]);
  assert.deepEqual(after.running.map(job => job.id), [2, 3]);
  assert.equal(after.waiting[0].id, 4);
  assert.equal(before.done.length, 0);
});

test("lowering the limit lets existing jobs finish without starting extras", () => {
  let workshop = setLimit(newWorkshop(4), 1);
  assert.equal(workshop.running.length, 4);
  while (workshop.done.length < 4) {
    workshop = nextCompletion(workshop);
    if (workshop.done.length < 4) assert.equal(workshop.waiting[0].id, 5);
  }
  assert.deepEqual(workshop.running.map(job => job.id), [5]);
});

test("raising the limit opens more presses and the run finishes with eight jobs", () => {
  const workshop = setLimit(newWorkshop(1), 4);
  assert.deepEqual(workshop.running.map(job => job.id), [1, 2, 3, 4]);
  const finished = advance(workshop, 30000);
  assert.equal(finished.running.length, 0);
  assert.equal(finished.waiting.length, 0);
  assert.equal(finished.done.length, 8);
  assert.deepEqual(newWorkshop(4), workshop);
});

test("placement geometry is bounded and every job has one stable render identity", async () => {
  const { along, height, placements, route, width } = await import("../src/print-studio/track.ts");
  let workshop = newWorkshop();
  for (const limit of [4, 1, 1, 3, 2, 1, 4, 1, 1, 1, 1, 1]) {
    const prior = new Map(placements(workshop).map(item => [item.id, item]));
    workshop = nextCompletion(setLimit(workshop, limit));
    const tickets = placements(workshop);
    assert.deepEqual(tickets.map(item => item.id), [1, 2, 3, 4, 5, 6, 7, 8]);
    assert.equal(tickets.filter(item => item.state === "running").length, workshop.running.length);
    for (const item of tickets) {
      const previous = prior.get(item.id);
      const path = route(previous, item, previous.point);
      for (let step = 0; step <= 10; step++) {
        const point = along(path, step / 10);
        assert.ok(point.x >= 28 && point.x <= width - 28);
        assert.ok(point.y >= 18 && point.y <= height - 18);
      }
    }
  }
  assert.equal(workshop.done.length, 8);
});

test("speed changes use the same clock, and pausing freezes progress and captions", async () => {
  const { createPlayer, replay, tickPlayer, togglePlay, travelTime } = await import("../src/print-studio/player.ts");
  let player = replay(createPlayer());
  player = tickPlayer(player, 200);
  assert.equal(player.motion, 100);
  const paused = togglePlay(player);
  assert.equal(tickPlayer(paused, 100000), paused);
  player = tickPlayer(togglePlay({...paused, speed: 2}), (travelTime - 100) / 2);
  assert.equal(player.motion, travelTime);
  assert.equal(player.workshop.done.length, 0);
  player = tickPlayer(player, 625);
  assert.equal(player.workshop.done.length, 1);
  assert.match(player.caption, /next waiting task/);
  assert.equal(player.motion, 0);
});

test("rapid limit edits coalesce mid-handoff and keep all job identities", async () => {
  const { changeLimit, createPlayer, stepPlayer, tickPlayer, travelTime } = await import("../src/print-studio/player.ts");
  let player = stepPlayer(createPlayer());
  player = changeLimit(changeLimit(player, 4), 1);
  assert.equal(player.pendingLimit, 1);
  assert.equal(player.workshop.limit, 2);
  player = tickPlayer(player, travelTime * 2);
  assert.equal(player.workshop.limit, 1);
  assert.equal(player.workshop.running.length, 2);
  assert.match(player.caption, /Running jobs finish/);
  for (let i = 0; i < 8; i++) {
    player = tickPlayer(stepPlayer(player), travelTime * 2);
  }
  assert.equal(player.workshop.done.length, 8);
  assert.equal(new Set(player.workshop.done.map(job => job.id)).size, 8);
  assert.equal(player.mode, "paused");
});

test("guided events expire on the playback clock, including after a step", async () => {
  const { captionTime, createPlayer, playerClockActive, replay, stepPlayer, tickPlayer, togglePlay, travelTime } =
    await import("../src/print-studio/player.ts");
  const initial = createPlayer(2, 1);
  assert.equal(initial.caption, "");
  let player = replay(initial);
  assert.match(player.caption, /batch arrives/);
  player = tickPlayer(player, travelTime);
  player = togglePlay(player);
  assert.equal(tickPlayer(player, captionTime * 2), player);
  player = togglePlay({...player, speed: 2});
  player = tickPlayer(player, (captionTime - travelTime) / 2);
  assert.equal(player.caption, "");
  player = stepPlayer(player);
  assert.match(player.caption, /task settled/);
  player = tickPlayer(player, travelTime / 2);
  assert.equal(player.mode, "paused");
  assert.equal(playerClockActive(player), true);
  player = tickPlayer(player, (captionTime - travelTime) / 2);
  assert.equal(player.caption, "");
  assert.equal(playerClockActive(player), false);
  assert.match(replay(player).caption, /batch arrives/);
});

test("open station labels and peak count follow the run through limit changes and replay", async () => {
  const { stationStates } = await import("../src/print-studio/track.ts");
  const { changeLimit, createPlayer, replay, tickPlayer, travelTime } = await import("../src/print-studio/player.ts");
  let player = createPlayer(2, 1);
  assert.deepEqual(stationStates(player.workshop), ["running", "running", "closed", "closed"]);
  player = tickPlayer(changeLimit(player, 4), travelTime);
  assert.equal(player.peakActive, 4);
  player = changeLimit(player, 1);
  assert.deepEqual(stationStates(player.workshop), Array(4).fill("running"));
  assert.equal(player.peakActive, 4);
  player = replay(player);
  assert.equal(player.workshop.limit, 1);
  assert.equal(player.peakActive, 1);
  assert.deepEqual(stationStates(player.workshop), ["running", "closed", "closed", "closed"]);
  const sparse = {...player.workshop, limit: 2, running: [{...player.workshop.running[0], slot: 3}]};
  assert.deepEqual(stationStates(sparse), ["open", "closed", "closed", "running"]);
});
