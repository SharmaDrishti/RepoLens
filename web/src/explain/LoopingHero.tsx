import { useEffect, useRef, useState } from "react";
import { DrawingStage, motionPose } from "./IllustratedLesson";
import type { Artwork, Change, DrawingScene, MotionCue } from "./IllustratedLesson";

type Pose = { duration_ms: number; changes: Record<string, Change>; cues?: MotionCue[] };
export type Hero = DrawingScene & { alt: string; title?: string; evidence_ids: string[]; frames: Pose[] };

export function LoopingHero({ hero, artwork }: { hero: Hero; artwork: Artwork }) {
  const element = useRef<HTMLElement>(null);
  const [paused, setPaused] = useState(false);
  const [onscreen, setOnscreen] = useState(false);
  const [reduced, setReduced] = useState(() => matchMedia("(prefers-reduced-motion: reduce)").matches);
  const [elapsed, setElapsed] = useState(0);
  const duration = hero.frames.reduce((total, frame) => total + frame.duration_ms, 0);

  useEffect(() => {
    const node = element.current;
    if (!node) return;
    const observer = new IntersectionObserver(([entry]) => setOnscreen(entry.isIntersecting));
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const preference = matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReduced(preference.matches);
    preference.addEventListener("change", update);
    return () => preference.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    if (paused || reduced || !onscreen) return;
    let request: number;
    let previous: number | undefined;
    const tick = (time: number) => {
      const delta = previous === undefined ? 0 : Math.min(50, time - previous);
      previous = time;
      setElapsed(current => (current + delta) % duration);
      request = requestAnimationFrame(tick);
    };
    request = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(request);
  }, [paused, reduced, onscreen, duration]);

  let local = reduced ? 0 : elapsed;
  const index = hero.frames.findIndex(frame => {
    if (local < frame.duration_ms) return true;
    local -= frame.duration_ms;
    return false;
  });
  const current = hero.frames[index];
  const next = hero.frames[(index + 1) % hero.frames.length];
  const drawing = motionPose(current, next, local / current.duration_ms, current.cues);

  return <figure ref={element} className="learn-loop-art">
    <DrawingStage lesson={hero} artwork={artwork} {...drawing} description={hero.alt} />
    {!reduced && <button type="button" className="learn-loop-control" onClick={() => setPaused(value => !value)}>
      {paused ? "Play illustration" : "Pause illustration"}
    </button>}
  </figure>;
}
