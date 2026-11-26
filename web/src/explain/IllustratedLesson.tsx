import { useId, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import { LessonControls } from "./CapacityLesson";
import { useLessonPlayer } from "./lesson-player";
import "./illustration.css";

const tones = ["ink", "paper", "amber", "rose", "mint", "blue", "violet"] as const;
type Tone = typeof tones[number];
type Material = "paper" | "enamel";
type Surface = { material?: Material; depth?: number };
type Position = { x: number; y: number; tone: Tone; visible?: boolean; lift?: number; tilt?: number;
  scale_x?: number; scale_y?: number };
type Finish = "solid" | "outline" | "dashed" | "muted";
type Face = { w: number; h: number; pivot?: [number, number]; inscription?: string };
type Drawing = { id: string; arc?: number } & Position & (
  | (Surface & Face & { shape: "rect" | "ellipse"; finish?: Finish })
  | (Surface & { shape: "polygon"; points: [number, number][]; finish?: Finish })
  | { shape: "polyline" | "curve"; points: [number, number][]; finish?: Finish }
  | (Face & { shape: "sprite"; asset: string })
  | { shape: "trace"; commands: [string, ...number[]][]; reveal?: number; finish?: Finish }
  | { shape: "text"; text: string; size: "small" | "body" | "large"; align?: "start" | "middle" | "end"; font?: "sans" | "mono" }
);
export type Change = Partial<Position & { w: number; h: number; text: string; finish: Finish; reveal: number }>;
export type DrawingScene = { height: number; objects: Drawing[] };
type Frame = { caption: string; evidence_ids: string[]; changes: Record<string, Change> };
export type Illustration = DrawingScene & {
  kind: "illustrate"; id: string; after: number; title: string; prompt: string;
  choices: { id: string; label: string; frames: Frame[] }[];
};

export type Artwork = Record<string, string>;
type Pose = Pick<Frame, "changes">;
export type MotionCue = { at: number; changes: Record<string, Change> };

export function motionPose(before: Pose, target: Pose, fraction: number, cues: MotionCue[] = []) {
  const middle = cues.map(cue => ({
    at: cue.at / 100,
    pose: { changes: { ...before.changes, ...Object.fromEntries(Object.entries(cue.changes).map(
      ([id, patch]) => [id, { ...before.changes[id], ...patch }])) } },
  }));
  const poses = [{ at: 0, pose: before }, ...middle, { at: 1, pose: target }];
  const index = poses.findIndex((pose, index) => index > 0 && fraction <= pose.at);
  const [start, end] = [poses[index - 1], poses[index]];
  const local = (fraction - start.at) / (end.at - start.at);
  const progress = local * local * (3 - 2 * local);
  return { before: start.pose, target: end.pose, progress };
}

export function DrawingStage({ lesson, artwork, before, target, progress, description, inspected, onSelect }: {
  lesson: DrawingScene; artwork: Artwork; before: Pick<Frame, "changes">; target: Pick<Frame, "changes">;
  progress: number; description: string; inspected?: ReadonlySet<string>; onSelect?: ReadonlyMap<string, () => void>;
}) {
  const surfaceId = useId();
  const dimensional = lesson.objects.some(object => "material" in object);
  const mix = (a: number, b: number) => a + (b - a) * progress;
  return <svg className="illustration-stage" role="img" aria-label={description}
    viewBox={`0 0 320 ${lesson.height}`} width={320} height={lesson.height}
    style={{ "--stage-aspect": 320 / lesson.height } as CSSProperties}>
    {dimensional && <defs>
      {tones.flatMap(tone => (["paper", "enamel"] as const).map(material =>
        <linearGradient key={`${material}-${tone}`} id={`${surfaceId}-${material}-${tone}`} data-tone={tone}
          x1="12%" y1="0%" x2="70%" y2="100%" data-surface={material}>
          <stop offset="0" className="illustration-light" />
          <stop offset={material === "enamel" ? ".44" : ".58"} className="illustration-mid" />
          <stop offset="1" className="illustration-shade" />
        </linearGradient>
      ))}
    </defs>}
    {lesson.objects.map(object => {
      const previous = { ...object, ...Object.hasOwn(before.changes, object.id) && before.changes[object.id] };
      const next = { ...object, ...Object.hasOwn(target.changes, object.id) && target.changes[object.id] };
      const opacity = mix(Number(previous.visible !== false), Number(next.visible !== false));
      if (!opacity) return null;
      const visible = progress === 1 ? next : previous;
      let mark;
      switch (object.shape) {
        case "rect":
        case "ellipse": {
          const w = mix(previous.w ?? object.w, next.w ?? object.w);
          const h = mix(previous.h ?? object.h, next.h ?? object.h);
          mark = object.shape === "rect"
            ? <rect width={w} height={h} rx={Math.min(5, w / 2, h / 2)} />
            : <ellipse cx={w / 2} cy={h / 2} rx={w / 2} ry={h / 2} />;
          break;
        }
        case "polyline":
        case "polygon": {
          const points = object.points.map(point => point.join(",")).join(" ");
          mark = object.shape === "polygon" ? <polygon points={points} /> : <polyline points={points} />;
          break;
        }
        case "curve": {
          const [start, ...rest] = object.points;
          mark = <path d={`M ${start.join(" ")} C ${rest.flat().join(" ")}`} />;
          break;
        }
        case "sprite":
          mark = <image href={`data:image/png;base64,${artwork[object.asset]}`}
            width={mix(previous.w ?? object.w, next.w ?? object.w)}
            height={mix(previous.h ?? object.h, next.h ?? object.h)}
            aria-hidden="true" />;
          break;
        case "trace": {
          const reveal = mix(previous.reveal ?? object.reveal ?? 100, next.reveal ?? object.reveal ?? 100);
          if (!reveal) return null;
          const path = object.commands.map(command => command.join(" ")).join(" ");
          mark = <path d={path} pathLength={100} data-reveal={reveal}
            style={reveal < 100 ? { strokeDasharray: `${reveal} 100` } : undefined} />;
          break;
        }
        case "text":
          mark = <text data-size={object.size} data-font={object.font} textAnchor={object.align}
            y={0} dominantBaseline="hanging">{visible.text ?? object.text}</text>;
          break;
      }
      const arc = (previous.x !== next.x || previous.y !== next.y)
        ? (object.arc ?? 0) * 4 * progress * (1 - progress) : 0;
      const lift = mix(previous.lift ?? 0, next.lift ?? 0) + arc;
      const tilt = mix(previous.tilt ?? 0, next.tilt ?? 0);
      const scaleX = mix(previous.scale_x ?? 100, next.scale_x ?? 100) / 100;
      const scaleY = mix(previous.scale_y ?? 100, next.scale_y ?? 100) / 100;
      const x = mix(previous.x, next.x);
      const y = mix(previous.y, next.y) - lift;
      const [px, py] = "pivot" in object ? object.pivot ?? [0, 0] : [0, 0];
      const scaled = scaleX !== 1 || scaleY !== 1;
      const pose = [`translate(${x} ${y})`, tilt && `rotate(${tilt} ${px} ${py})`,
        scaled && (px || py) && `translate(${px} ${py})`, scaled && `scale(${scaleX} ${scaleY})`,
        scaled && (px || py) && `translate(${-px} ${-py})`]
        .filter(Boolean).join(" ");
      const material = "material" in object && visible.finish !== "outline" && visible.finish !== "dashed"
        ? object.material : undefined;
      const depth = "depth" in object ? object.depth ?? 0 : 0;
      const surface = material ? {
        "--face": `url(#${surfaceId}-${material}-${visible.tone})`,
        "--shadow-y": `${1.5 + lift * .18}px`,
        "--shadow-blur": `${1.5 + lift * .18}px`,
      } as CSSProperties : undefined;
      const select = onSelect?.get(object.id);
      return <g key={object.id} data-mark={object.id} data-tone={visible.tone} data-finish={visible.finish}
        data-material={material} data-inspected={inspected?.has(object.id) || undefined}
        data-selectable={Boolean(select) || undefined} onClick={select} opacity={opacity} transform={pose} style={surface}>
        {material && depth > 0 && <g className="illustration-edge" transform={`translate(0 ${depth})`} aria-hidden="true">{mark}</g>}
        {mark}
        {"inscription" in object && object.inscription && <text className="illustration-inscription"
          x={mix(previous.w ?? object.w, next.w ?? object.w) / 2}
          y={mix(previous.h ?? object.h, next.h ?? object.h) / 2}
          textAnchor="middle" dominantBaseline="central">{object.inscription}</text>}
      </g>;
    })}
  </svg>;
}

export function IllustratedLesson({ lesson, artwork, sources, anchor }: {
  lesson: Illustration; artwork: Artwork; sources: (ids: string[]) => ReactNode; anchor: string;
}) {
  const [choice, setChoice] = useState(0);
  const { frames } = lesson.choices[choice];
  const player = useLessonPlayer(frames.length - 1);
  const before = frames[Math.max(0, player.index - 1)];
  const target = frames[player.index];
  const visible = player.arrived ? target : before;
  const visibleIndex = player.arrived ? player.index : Math.max(0, player.index - 1);

  return <section id={anchor} className="learn-shell learn-chapter" aria-labelledby={`${anchor}-title`}>
    <h2 id={`${anchor}-title`}>{lesson.title}</h2>
    <p className="learn-objective">{lesson.prompt}</p>
    <div className="capacity-workbench illustration-workbench" data-format="illustrate">
      <div className="capacity-toolbar">
        <div role="group" aria-label="Try a choice">
          {lesson.choices.map((item, index) => <button key={item.id} type="button" aria-pressed={choice === index}
            onClick={() => { setChoice(index); player.reset(); }}>{item.label}</button>)}
        </div>
      </div>
      <div className="illustration-layout">
        <div className="illustration-board" data-studio={lesson.objects.some(object => "material" in object || object.shape === "sprite")}>
          <DrawingStage lesson={lesson} artwork={artwork} before={before} target={target} progress={player.progress} description={visible.caption} />
        </div>
        <div className="illustration-side">
          <div className="illustration-progress">
            <span>Step {visibleIndex + 1} of {frames.length}</span>
            <span className="illustration-progress-ticks" aria-hidden="true">
              {frames.map((_, index) => <i key={index} data-reached={index <= visibleIndex} />)}
            </span>
          </div>
          <div className="illustration-caption">
            <p role="status" aria-atomic="true">{visible.caption}</p>
          </div>
          <LessonControls player={player} />
          <p className="capacity-key">Illustrated example based on the source.</p>
        </div>
      </div>
      {sources(visible.evidence_ids)}
    </div>
  </section>;
}
