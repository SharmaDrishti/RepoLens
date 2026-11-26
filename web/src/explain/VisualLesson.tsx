import { useEffect, useRef, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import { LessonControls } from "./CapacityLesson";
import { useLessonPlayer } from "./lesson-player";
import "./visual.css";

type Palette = "amber" | "rose" | "mint" | "blue" | "violet";
type VisualObject = { id: string; label: string; shape: "card" | "pill" | "circle" | "stack" | "gate";
  tone: Palette; column: number; row: number };
type Frame = {
  caption: string;
  evidence_ids: string[];
  values: Record<string, string>;
  placements: Record<string, string>;
  active: string[];
  paths: string[];
};

export type VisualPlan = {
  title: string;
  prompt: string;
  grid: { columns: number; rows: number };
  objects: VisualObject[];
  paths: { id: string; from: string; to: string }[];
  tokens: { id: string; label: string; tone: Palette }[];
  choices: { id: string; label: string; frames: Frame[] }[];
};

const ownValue = (values: Record<string, string>, id: string) =>
  Object.hasOwn(values, id) ? values[id] : undefined;

function Board({ plan, before, target, visible, progress }: {
  plan: VisualPlan; before: Frame; target: Frame; visible: Frame; progress: number;
}) {
  const board = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });
  const { columns, rows } = plan.grid;

  useEffect(() => {
    const element = board.current;
    if (!element) return;
    const measure = () => setSize({ width: element.clientWidth, height: element.clientHeight });
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    measure();
    return () => observer.disconnect();
  }, []);

  const positions = new Map(plan.objects.map(item => [item.id, {
    x: (item.column - .5) * 100 / columns,
    y: (item.row - .5) * 100 / rows,
  }]));
  const locateToken = (frame: Frame, id: string) => {
    const at = ownValue(frame.placements, id);
    if (!at) return;
    const position = positions.get(at)!;
    const stack = plan.tokens.filter(token => ownValue(frame.placements, token.id) === at);
    const offset = (stack.findIndex(token => token.id === id) - (stack.length - 1) / 2) * 22;
    return { ...position, offset };
  };
  const mix = (a: number, b: number) => a + (b - a) * progress;

  return <div className="visual-board" ref={board} aria-label="Lesson illustration"
    style={{ "--visual-columns": columns, "--visual-rows": rows } as CSSProperties}>
    <div className="visual-paths" aria-hidden="true">
      {plan.paths.map(path => {
        const from = positions.get(path.from)!;
        const to = positions.get(path.to)!;
        const dx = (to.x - from.x) * size.width / 100;
        const dy = (to.y - from.y) * size.height / 100;
        const length = Math.hypot(dx, dy);
        const reverse = plan.paths.some(other => other.from === path.to && other.to === path.from);
        const offset = reverse && length ? 6 / length : 0;
        return <span key={path.id} className="visual-path" data-path={path.id}
          data-active={visible.paths.includes(path.id)} style={{
            left: `calc(${from.x}% - ${dy * offset}px)`,
            top: `calc(${from.y}% + ${dx * offset}px)`, width: length,
            transform: `rotate(${Math.atan2(dy, dx)}rad)`,
          }} />;
      })}
    </div>
    {plan.objects.map(item => {
      const position = positions.get(item.id)!;
      const value = ownValue(visible.values, item.id);
      return <div key={item.id} data-object={item.id} className="visual-object"
        data-shape={item.shape} data-tone={item.tone} data-active={visible.active.includes(item.id)}
        style={{ left: `${position.x}%`, top: `${position.y}%` }}>
        <span>{item.label}</span>
        {value && <strong>{value}</strong>}
      </div>;
    })}
    <div className="visual-tokens" aria-hidden="true">
      {plan.tokens.map(token => {
        const previous = locateToken(before, token.id);
        const next = locateToken(target, token.id);
        if (!previous && !next) return null;
        const from = previous ?? next!;
        const to = next ?? previous!;
        return <span key={token.id} className="visual-token" data-token={token.id} data-tone={token.tone}
          data-at={ownValue(visible.placements, token.id) ?? ""}
          style={{
            left: `calc(${mix(from.x, to.x)}% + ${mix(from.offset, to.offset)}px)`,
            top: `calc(${mix(from.y, to.y)}% - var(--token-lift))`,
            opacity: mix(previous ? 1 : 0, next ? 1 : 0),
          }}>{token.label}</span>;
      })}
    </div>
  </div>;
}

export function VisualLesson({ plan, sources, anchor = "learn-try" }: {
  plan: VisualPlan; sources: (ids: string[]) => ReactNode; anchor?: string;
}) {
  const [choice, setChoice] = useState(0);
  const frames = plan.choices[choice].frames;
  const player = useLessonPlayer(frames.length - 1);
  const before = frames[Math.max(0, player.index - 1)];
  const target = frames[player.index];
  const visible = player.arrived ? target : before;

  return <section id={anchor} className="learn-shell learn-chapter" aria-labelledby={`${anchor}-title`}>
    <h2 id={`${anchor}-title`}>{plan.title}</h2>
    <p className="learn-objective">{plan.prompt}</p>
    <div className="capacity-workbench visual-workbench">
      <div className="capacity-toolbar">
        <div role="group" aria-label="Try a choice">
          {plan.choices.map((item, index) => <button key={item.id} type="button" aria-pressed={choice === index}
            onClick={() => { setChoice(index); player.reset(); }}>{item.label}</button>)}
        </div>
      </div>
      <Board plan={plan} before={before} target={target} visible={visible} progress={player.progress} />
      <div className="capacity-console">
        <div className="capacity-caption">
          <p role="status" aria-atomic="true">{visible.caption}</p>
        </div>
        <LessonControls player={player} />
      </div>
      <p className="capacity-key">Illustrated example. Follow the source evidence for each step.</p>
      {sources(visible.evidence_ids)}
    </div>
  </section>;
}
