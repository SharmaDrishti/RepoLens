import { useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import { DrawingStage, motionPose } from "./IllustratedLesson";
import type { Artwork, Change, DrawingScene, MotionCue } from "./IllustratedLesson";
import "./guide.css";

type Beat = { duration_ms: number; motion_ms?: number; caption: string; evidence_ids: string[];
  changes: Record<string, Change>; cues?: MotionCue[]; callout?: { text: string; x: number; y: number } };
type Chapter = DrawingScene & { id: string; title: string; frames: Beat[] };
export type Guide = { title: string; prompt: string; chapters: Chapter[] };
const motionTime = (frame: Beat) => frame.motion_ms ?? 850;

export function GuidedStory({ guide, artwork, sources, tryAnchor, anchor = "learn-guide" }: {
  guide: Guide; artwork: Artwork; sources: (ids: string[]) => ReactNode; tryAnchor: string | null; anchor?: string;
}) {
  const stage = useRef<HTMLDivElement>(null);
  const beats = useMemo(() => guide.chapters.flatMap((chapter, chapterIndex) =>
    chapter.frames.map((frame, frameIndex) => ({ chapter, chapterIndex, frame, frameIndex }))), [guide]);
  const [speed, setSpeed] = useState(1);
  const [reduced, setReduced] = useState(() => matchMedia("(prefers-reduced-motion: reduce)").matches);
  const [current, setCurrent] = useState({ index: 0, elapsed: 0, playing: !reduced });
  const [onscreen, setOnscreen] = useState(false);
  const active = beats[current.index];
  const last = beats.length - 1;
  const complete = current.index === last && current.elapsed === active.frame.duration_ms;

  useEffect(() => {
    const node = stage.current;
    if (!node) return;
    const observer = new IntersectionObserver(([entry]) => setOnscreen(entry.isIntersecting));
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const preference = matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => {
      setReduced(preference.matches);
      if (preference.matches) setCurrent(state => ({ ...state, playing: false }));
    };
    preference.addEventListener("change", update);
    return () => preference.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    if (!current.playing || !onscreen) return;
    let request: number;
    let previous: number | undefined;
    const tick = (time: number) => {
      const delta = previous === undefined ? 0 : Math.min(100, time - previous) * speed;
      previous = time;
      setCurrent(state => {
        if (!state.playing) return state;
        const duration = beats[state.index].frame.duration_ms;
        const elapsed = state.elapsed + delta;
        if (elapsed < duration) return { ...state, elapsed };
        return state.index === last
          ? { ...state, elapsed: duration, playing: false }
          : { index: state.index + 1, elapsed: elapsed - duration, playing: true };
      });
      request = requestAnimationFrame(tick);
    };
    request = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(request);
  }, [beats, current.playing, last, onscreen, speed]);

  const jump = (index: number) => setCurrent({
    index, elapsed: motionTime(beats[index].frame), playing: false,
  });
  const previous = active.chapter.frames[active.frameIndex - 1] ?? active.frame;
  const motion = reduced || active.frameIndex === 0 ? 1 : Math.min(1, current.elapsed / motionTime(active.frame));
  const drawing = motionPose(previous, active.frame, motion, active.frame.cues);
  const visible = motion === 1 ? active.frame : previous;
  const total = beats.reduce((sum, beat) => sum + beat.frame.duration_ms, 0);
  const elapsed = beats.slice(0, current.index).reduce((sum, beat) => sum + beat.frame.duration_ms, current.elapsed);

  return <section id={anchor} className="learn-shell learn-chapter" aria-labelledby={`${anchor}-title`}>
    <h2 id={`${anchor}-title`}>{guide.title}</h2>
    <p className="learn-objective">{guide.prompt}</p>
    {guide.chapters.length > 1 && <div className="guide-chapters" role="group" aria-label="Story chapters">
      {guide.chapters.map((chapter, i) => <button type="button" key={chapter.id}
        aria-pressed={i === active.chapterIndex}
        onClick={() => jump(beats.findIndex(beat => beat.chapterIndex === i))}>{chapter.title}</button>)}
    </div>}
    <div className="guide-stage">
      <div ref={stage} className="guide-drawing">
        <div className="guide-composition" style={{ "--guide-aspect": 320 / active.chapter.height } as CSSProperties}>
          <DrawingStage key={active.chapter.id} lesson={active.chapter} artwork={artwork}
            {...drawing} description={visible.caption} />
          {motion === 1 && active.frame.callout && <span key={current.index} className="guide-callout"
            style={{ left: `clamp(22%, ${active.frame.callout.x}%, 78%)`, top: `${active.frame.callout.y}%` }}>
            {active.frame.callout.text}
          </span>}
        </div>
      </div>
      <div className="guide-description">
        <div className="guide-caption">
          {beats.map(({ frame }, index) => <span key={index} aria-hidden="true">{frame.caption}</span>)}
          <p aria-live={current.playing ? "off" : "polite"}>{visible.caption}</p>
        </div>
        <div className="guide-playback">
        <progress aria-label="Story progress" max={total} value={elapsed} />
        <span className="guide-counter">Step {active.frameIndex + 1} of {active.chapter.frames.length}</span>
        <div className="guide-controls" role="group" aria-label="Story playback">
          <button type="button" disabled={complete} onClick={() => setCurrent(state => ({ ...state, playing: !state.playing }))}>
            {current.playing ? "Pause" : "Play"}
          </button>
          <button type="button" onClick={() => setCurrent({ index: 0, elapsed: 0, playing: !reduced })}>Replay</button>
          <button type="button" disabled={current.index === 0} onClick={() => jump(current.index - 1)}>Back</button>
          <button type="button" disabled={current.index === last} onClick={() => jump(current.index + 1)}>Next</button>
        </div>
        <label className="guide-speed">Speed <select value={speed} onChange={event => setSpeed(Number(event.target.value))}>
          <option value={.75}>Slow</option><option value={1}>Normal</option><option value={1.25}>Fast</option>
        </select></label>
        </div>
        <p className="learn-note guide-note">Illustrated example based on the source.</p>
        {tryAnchor && <a href={`#${tryAnchor}`} onClick={() => setCurrent(state => ({ ...state, playing: false }))}>
          {complete ? "Go to Try It" : "Skip to Try It"}
        </a>}
      </div>
    </div>
    {sources(visible.evidence_ids)}
  </section>;
}
