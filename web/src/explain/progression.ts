export function sceneStep(current: number, count: number, action: "next" | "previous" | "replay") {
  if (count < 1 || action === "replay") return 0;
  return Math.max(0, Math.min(count - 1, current + (action === "next" ? 1 : -1)));
}
