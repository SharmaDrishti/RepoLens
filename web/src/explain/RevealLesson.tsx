import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { DrawingStage, motionPose } from "./IllustratedLesson";
import type { Artwork, Change, DrawingScene, MotionCue } from "./IllustratedLesson";

type State = { label: string; caption: string; changes: Record<string, Change>; evidence_ids: string[] };
export type Reveal = DrawingScene & {
  kind: "reveal"; id: string; after: number; title: string; prompt: string; alt: string;
  duration_ms: number; states: [State, State]; cues?: MotionCue[];
};

export function RevealLesson({ lesson, artwork, sources, anchor, next }: {
  lesson: Reveal; artwork: Artwork; sources: (refs: string[]) => ReactNode; anchor: string; next?: string;
}) {
  const [opened, setOpened] = useState(false);
  const [fraction, setFraction] = useState(0);
  const position = useRef(0);
  const target = Number(opened);
  useEffect(() => {
    const preference = matchMedia("(prefers-reduced-motion: reduce)");
    let request = 0;
    let before: number | undefined;
    const step = (now: number) => {
      const delta = before === undefined ? 0 : Math.min(64, now - before) / lesson.duration_ms;
      before = now;
      const local = position.current;
      position.current = preference.matches ? target : local < target
        ? Math.min(target, local + delta) : Math.max(target, local - delta);
      setFraction(position.current);
      if (position.current !== target) request = requestAnimationFrame(step);
    };
    const update = () => {
      cancelAnimationFrame(request);
      if (preference.matches) {
        position.current = target;
        setFraction(target);
      } else if (position.current !== target) {
        request = requestAnimationFrame(step);
      }
    };
    update();
    preference.addEventListener("change", update);
    return () => {
      cancelAnimationFrame(request);
      preference.removeEventListener("change", update);
    };
  }, [target, lesson.duration_ms]);

  const [initial, result] = lesson.states;
  const settled = fraction === 1 ? result : initial;
  const drawing = motionPose(initial, result, fraction, lesson.cues);
  return <section id={anchor} className="learn-shell learn-chapter learn-reveal-example" aria-labelledby={`${anchor}-title`}>
    <div className="learn-reveal-layout">
      <div className="learn-reveal-heading">
        <h2 id={`${anchor}-title`}>{lesson.title}</h2>
        <p>{lesson.prompt}</p>
      </div>
      <figure className="learn-reveal-art">
        <DrawingStage lesson={lesson} artwork={artwork} {...drawing} description={lesson.alt} />
      </figure>
      <div className="learn-reveal-action">
        <div className="learn-reveal-links">
          <button type="button" onClick={() => setOpened(value => !value)}>{lesson.states[target].label}</button>
          {next && <a href={`#${next}`}>How it works <span aria-hidden="true">↓</span></a>}
        </div>
        <p role="status">{settled.caption}</p>
      </div>
    </div>
    {sources([...new Set([...initial.evidence_ids, ...result.evidence_ids])])}
  </section>;
}
