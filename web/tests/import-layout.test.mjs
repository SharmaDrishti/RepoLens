import test from "node:test";
import assert from "node:assert/strict";
import { category, edgeDrawing, importLayout } from "../src/developer/import-layout.ts";

test("branching dependencies share a target column and reciprocal arrows stay distinct", () => {
  const paths = ["examples/use.js", "index.test.js", "index.js", "internal.js"];
  const edges = [
    {id: "1", from: paths[0], to: paths[2]}, {id: "2", from: paths[1], to: paths[2]},
    {id: "3", from: paths[2], to: paths[3]}, {id: "4", from: paths[3], to: paths[2]},
  ];
  const {points} = importLayout(paths, edges);
  assert.equal(points.size, 4);
  const a = points.get(paths[2]), b = points.get(paths[3]);
  assert.notEqual(edgeDrawing(a, b), edgeDrawing(b, a));
  assert.notEqual(a.y, b.y);
  assert.deepEqual(paths.map(category), ["Examples", "Tests", "Source", "Modules"]);
});

test("layout follows import direction for a small acyclic graph and packs crowded columns", () => {
  const paths = Array.from({length: 35}, (_, i) => `src/file${i}.js`);
  const edges = paths.slice(1).map((from, i) => ({id: String(i), from, to: paths[0]}));
  const {points, height, width} = importLayout(paths, edges);
  assert.equal(new Set([...points.values()].map(({x, y}) => `${x},${y}`)).size, paths.length);
  assert.ok(height < 900);
  assert.ok(points.get(paths[1]).x < points.get(paths[0]).x);
  assert.ok(width >= 230);
  assert.equal(category("project/benchmarks/run.js"), "Benchmarks");
  assert.equal(category("tsconfig.config.js"), "Configuration");
});
