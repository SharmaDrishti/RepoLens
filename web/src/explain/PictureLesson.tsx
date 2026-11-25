import { useState } from "react";
import type { ReactNode } from "react";
import type { Artwork } from "./IllustratedLesson";
import "./picture.css";

type Point = { x: number; y: number; label: string; caption: string; evidence_ids: string[] };
type View = { label: string; alt: string; asset: string; points: Point[] };
export type Picture = { id: string; after: number; kind: "picture"; title: string; prompt: string; views: View[] };

export function PictureLesson({ lesson, artwork, sources, anchor }: {
  lesson: Picture; artwork: Artwork; sources: (ids: string[]) => ReactNode; anchor: string;
}) {
  const [viewIndex, showView] = useState(0);
  const [pointIndex, showPoint] = useState(0);
  const view = lesson.views[viewIndex];
  const point = view.points[pointIndex];

  return <section id={anchor} className="learn-shell learn-chapter" aria-labelledby={`${anchor}-title`}>
    <h2 id={`${anchor}-title`}>{lesson.title}</h2>
    <p className="learn-objective">{lesson.prompt}</p>
    {lesson.views.length > 1 && <div className="picture-views" role="group" aria-label="Illustration views">
      {lesson.views.map((state, index) => <button type="button" key={state.asset} aria-pressed={viewIndex === index}
        onClick={() => { showView(index); showPoint(0); }}>{state.label}</button>)}
    </div>}
    <div className="picture-layout">
      <figure className="picture-canvas">
        <img src={`data:image/png;base64,${artwork[view.asset]}`} alt={view.alt} />
        {view.points.map((detail, index) => <button key={index} type="button" className="picture-marker"
          style={{ left: `${detail.x}%`, top: `${detail.y}%` }}
          aria-label={detail.label} aria-pressed={index === pointIndex} onClick={() => showPoint(index)}>
          <span aria-hidden="true">{index + 1}</span>
        </button>)}
      </figure>
      <div className="picture-detail">
        <div aria-live="polite">
          <h3>{point.label}</h3>
          <p>{point.caption}</p>
        </div>
      </div>
    </div>
    {sources(point.evidence_ids)}
  </section>;
}
