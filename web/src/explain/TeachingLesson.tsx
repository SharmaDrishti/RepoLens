import { useState } from "react";
import type { ReactNode } from "react";
import { FilterExperiment } from "./FilterExperiment";
import { GuidedStory } from "./GuidedStory";
import type { Guide } from "./GuidedStory";
import type { Experiment } from "./FilterExperiment";
import { PictureLesson } from "./PictureLesson";
import type { Picture } from "./PictureLesson";
import { RevealLesson } from "./RevealLesson";
import type { Reveal } from "./RevealLesson";
import { IllustratedLesson } from "./IllustratedLesson";
import type { Artwork, Illustration } from "./IllustratedLesson";
import { VisualLesson } from "./VisualLesson";
import type { VisualPlan } from "./VisualLesson";
import "./teaching.css";

type Placement = { id: string; after: number };
type Section = Placement & { title: string; prompt: string };
type Citation = { evidence_ids: string[] };
type Compare = Section & { kind: "compare"; columns: string[];
  rows: { label: string; cells: ({ text: string } & Citation)[] }[] };
type Annotate = Section & { kind: "annotate"; source_id: string;
  notes: ({ label: string; first: number; last: number; caption: string } & Citation)[] };
type Explore = Section & { kind: "explore"; parts: ({ label: string; example: string; caption: string } & Citation)[] };
export type Lesson = Compare | Annotate | Explore | Illustration | Experiment | Picture | Reveal
  | (Placement & { kind: "animate"; plan: VisualPlan }) | (Placement & { kind: "guide"; guide: Guide });

type Sources = (refs: string[]) => ReactNode;
type Excerpt = { path: string; first: number; text: string };
export const lessonAnchor = (id: string) => `lesson-${id}`;

function Comparison({ lesson, sources }: { lesson: Compare; sources: Sources }) {
  const [selected, select] = useState({ row: 0, column: 0 });
  const row = lesson.rows[selected.row];
  return <>
    <table className="teaching-comparison">
      <thead><tr><th scope="col" aria-label="Aspect" />
        {lesson.columns.map(column => <th key={column} scope="col">{column}</th>)}
      </tr></thead>
      <tbody>{lesson.rows.map((item, rowIndex) => <tr key={rowIndex}>
        <th scope="row">{item.label}</th>
        {item.cells.map((cell, column) => <td key={column}>
          <button type="button" aria-pressed={rowIndex === selected.row && column === selected.column}
            onClick={() => select({ row: rowIndex, column })}>{cell.text}</button>
        </td>)}
      </tr>)}</tbody>
    </table>
    <p className="teaching-selection" role="status">{row.label} · {lesson.columns[selected.column]}</p>
    {sources(row.cells[selected.column].evidence_ids)}
  </>;
}

function AnnotatedExample({ lesson, excerpt, sources }: { lesson: Annotate; excerpt: Excerpt; sources: Sources }) {
  const [selected, select] = useState(0);
  const note = lesson.notes[selected];
  return <>
    <div className="teaching-buttons" role="group" aria-label="Choose a part of the example">
      {lesson.notes.map((item, i) => <button type="button" key={i} aria-pressed={i === selected}
        onClick={() => select(i)}>{item.label}</button>)}
    </div>
    <figure className="teaching-annotation">
      <figcaption><code>{excerpt.path}</code></figcaption>
      <pre><code>{excerpt.text.split("\n").map((line, i) => <span key={i} className="teaching-line"
        data-highlighted={i + 1 >= note.first && i + 1 <= note.last}>
        <span aria-hidden="true">{excerpt.first + i}</span><span>{line || " "}</span>
      </span>)}</code></pre>
    </figure>
    <p className="teaching-selection" role="status">{note.caption}</p>
    {sources([...new Set([lesson.source_id, ...note.evidence_ids])])}
  </>;
}

function Parts({ lesson, sources }: { lesson: Explore; sources: Sources }) {
  const [selected, select] = useState(0);
  const part = lesson.parts[selected];
  return <>
    <div className="teaching-buttons" role="group" aria-label="Choose a part to explore">
      {lesson.parts.map((item, i) => <button type="button" key={item.label} aria-pressed={i === selected}
        onClick={() => select(i)}>{item.label}</button>)}
    </div>
    <div className="teaching-part" role="status">
      <code>{part.example}</code><p>{part.caption}</p>
    </div>
    {sources(part.evidence_ids)}
  </>;
}

export function TeachingLesson({ lesson, artwork, sources, getExcerpt, next }: {
  lesson: Lesson; artwork: Artwork; sources: Sources; getExcerpt: (id: string) => Excerpt; next?: string;
}) {
  const anchor = lessonAnchor(lesson.id);
  if (lesson.kind === "reveal") return <RevealLesson lesson={lesson} artwork={artwork} sources={sources} anchor={anchor} next={next} />;
  if (lesson.kind === "guide") return <GuidedStory guide={lesson.guide} artwork={artwork}
    sources={sources} tryAnchor={null} anchor={anchor} />;
  if (lesson.kind === "picture") return <PictureLesson lesson={lesson} artwork={artwork} sources={sources} anchor={anchor} />;
  if (lesson.kind === "experiment") return <FilterExperiment lesson={lesson} artwork={artwork} sources={sources} anchor={anchor} />;
  if (lesson.kind === "illustrate") return <IllustratedLesson lesson={lesson} artwork={artwork} sources={sources} anchor={anchor} />;
  if (lesson.kind === "animate") return <VisualLesson plan={lesson.plan} sources={sources} anchor={anchor} />;
  return <section id={anchor} className="learn-shell learn-chapter" aria-labelledby={`${anchor}-title`}>
    <h2 id={`${anchor}-title`}>{lesson.title}</h2>
    <p className="learn-objective">{lesson.prompt}</p>
    <div className="teaching-panel" data-format={lesson.kind}>
      {lesson.kind === "compare" && <Comparison lesson={lesson} sources={sources} />}
      {lesson.kind === "annotate" && <AnnotatedExample lesson={lesson}
        excerpt={getExcerpt(lesson.source_id)} sources={sources} />}
      {lesson.kind === "explore" && <Parts lesson={lesson} sources={sources} />}
    </div>
  </section>;
}
