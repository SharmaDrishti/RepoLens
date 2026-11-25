import { useEffect, useState } from "react";
import { advancePlayback, initialPlayback, tickPlayback, travelTime } from "./capacity";

export function useLessonPlayer(end: number) {
  const [playback, setPlayback] = useState(initialPlayback);
  const [speed, setSpeed] = useState(1);
  const [reduced, setReduced] = useState(() => matchMedia("(prefers-reduced-motion: reduce)").matches);
  const { index, elapsed, mode } = playback;
  const active = mode !== "paused";
  const arrived = elapsed >= travelTime;
  const ratio = Math.min(1, elapsed / travelTime);
  const progress = ratio * ratio * (3 - 2 * ratio);

  useEffect(() => {
    const media = matchMedia("(prefers-reduced-motion: reduce)");
    const change = () => {
      setReduced(media.matches);
      if (media.matches) setPlayback(current => ({ ...current, elapsed: travelTime, mode: "paused" }));
    };
    media.addEventListener("change", change);
    return () => media.removeEventListener("change", change);
  }, []);

  useEffect(() => {
    if (!active || reduced) return;
    let frame: number;
    let previous = performance.now();
    const update = (now: number) => {
      const delta = Math.min(64, now - previous) * speed;
      previous = now;
      setPlayback(current => tickPlayback(current, delta, end));
      frame = requestAnimationFrame(update);
    };
    frame = requestAnimationFrame(update);
    return () => cancelAnimationFrame(frame);
  }, [active, end, reduced, speed]);

  return {
    index, mode, arrived, progress, active, reduced, speed, setSpeed,
    finished: index === end && arrived,
    reset: () => setPlayback(initialPlayback),
    replay: () => setPlayback(reduced ? initialPlayback : advancePlayback(initialPlayback, end, "play")),
    toggle: () => setPlayback(current => current.mode === "play"
      ? { ...current, mode: "paused" } : advancePlayback(current, end, "play")),
    step: () => setPlayback(current => reduced
      ? { index: Math.min(end, current.index + 1), elapsed: travelTime, mode: "paused" }
      : advancePlayback(current, end, "step")),
  };
}
