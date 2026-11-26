export type ImportEdge = { id: string; from: string; to: string; line?: number };
export const nodeWidth = 192;
export const nodeHeight = 68;

export function category(path: string) {
  const parts = path.toLowerCase().split("/");
  const file = parts.at(-1) ?? "";
  if (parts.some(part => /^(__tests__|tests?|spec)$/.test(part)) || /(^test[_.-]|[._-](test|spec)\.)/.test(file)) return "Tests";
  if (parts.some(part => /^examples?$/.test(part)) || /^example[.-]/.test(file)) return "Examples";
  if (parts.some(part => /^bench(marks?)?$/.test(part)) || /^bench(mark)?[.-]/.test(file)) return "Benchmarks";
  if (/^(package\.json|pyproject\.toml|setup\.cfg|go\.mod|cargo\.toml|.*\.config\.)/.test(file)) return "Configuration";
  if (/^(index|main|__init__|__main__)\./.test(file) || parts.includes("src")) return "Source";
  return "Modules";
}

export function importLayout(paths: string[], edges: ImportEdge[]) {
  const incoming = new Map(paths.map(path => [path, [] as string[]]));
  const outgoing = new Map(paths.map(path => [path, [] as string[]]));
  for (const edge of edges) {
    if (!incoming.has(edge.to) || !outgoing.has(edge.from)) continue;
    incoming.get(edge.to)!.push(edge.from);
    outgoing.get(edge.from)!.push(edge.to);
  }
  // Work left from dependency sinks. Cycles remain connected, including when
  // there is no sink. The arrows, rather than the rank, express direction.
  const ranks = new Map<string, number>();
  const pending = paths.filter(path => !outgoing.get(path)!.length);
  pending.forEach(path => ranks.set(path, 0));
  for (let i = 0; i < pending.length; i++) {
    const target = pending[i];
    for (const source of incoming.get(target)!) {
      if (ranks.has(source)) continue;
      ranks.set(source, Math.min(3, ranks.get(target)! + 1));
      pending.push(source);
    }
  }
  const groups = new Map<number, string[]>();
  for (const path of [...paths].sort((a, b) => category(a).localeCompare(category(b)) || a.localeCompare(b))) {
    const rank = ranks.get(path) ?? 1;
    const group = groups.get(rank) ?? [];
    group.push(path);
    groups.set(rank, group);
  }
  const columns = [...groups.entries()].sort(([a], [b]) => b - a).flatMap(([, group]) => {
    const chunks = [];
    for (let i = 0; i < group.length; i += 8) chunks.push(group.slice(i, i + 8));
    return chunks;
  });
  const height = 40 + Math.max(1, ...columns.map(column => column.length)) * 102;
  const points = new Map<string, {x: number; y: number}>();
  columns.forEach((column, x) => column.forEach((path, y) => points.set(path,
    {x: 20 + x * 270, y: 20 + (height - 40 - column.length * 102) / 2 + y * 102})));
  return {points, width: 40 + Math.max(1, columns.length) * 270 - 78, height};
}

type Point = {x: number; y: number};

export function edgeDrawing(a: Point, b: Point) {
  const middle = nodeHeight / 2;
  if (a === b) return `M${a.x+nodeWidth-20} ${a.y} c35 -35 48 -13 23 18`;
  if (a.x === b.x) {
    const forward = a.y < b.y;
    const x = forward ? a.x + nodeWidth * .75 : a.x + nodeWidth * .27;
    return `M${x} ${a.y + (forward ? nodeHeight : 0)} V${b.y + (forward ? -4 : nodeHeight + 4)}`;
  }
  const right = a.x < b.x;
  const offset = right ? -7 : 7;
  const x1 = right ? a.x + nodeWidth : a.x, x2 = right ? b.x - 4 : b.x + nodeWidth + 4;
  const y1 = a.y + middle + offset, y2 = b.y + middle + offset, bend = (x1 + x2) / 2;
  return `M${x1} ${y1} C${bend} ${y1} ${bend} ${y2} ${x2} ${y2}`;
}
