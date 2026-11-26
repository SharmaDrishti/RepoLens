import { useState } from "react";
import type { ReactNode } from "react";
import { DrawingStage } from "./IllustratedLesson";
import type { Artwork, Change, DrawingScene } from "./IllustratedLesson";
import "./experiment.css";

type Group = { id: string; label: string };
type Item = { id: string; label: string; values: Record<string, string>; hidden: Record<string, Change> };
export type Experiment = DrawingScene & {
  id: string; after: number; kind: "experiment"; title: string; prompt: string; explanation: string;
  groups: Group[]; items: Item[]; evidence_ids: string[];
};

export function FilterExperiment({ lesson, artwork, sources, anchor }: {
  lesson: Experiment; artwork: Artwork; sources: (ids: string[]) => ReactNode; anchor: string;
}) {
  const [selected, select] = useState<Map<string, Set<string>>>(new Map());
  const [inspected, inspect] = useState(lesson.items[0]);
  const options = (group: Group) => [...new Set(lesson.items.map(item => item.values[group.id]))];
  const toggle = (groupId: string, value: string) => select(current => {
    const updated = new Map(current);
    const values = new Set(current.get(groupId));
    if (values.has(value)) values.delete(value);
    else values.add(value);
    if (values.size) updated.set(groupId, values);
    else updated.delete(groupId);
    return updated;
  });

  const misses = (item: Item) => lesson.groups.filter(group => {
    const choices = selected.get(group.id);
    return choices && !choices.has(item.values[group.id]);
  });
  const hidden = new Set(lesson.items.filter(item => misses(item).length).map(item => item.id));
  const changes = Object.fromEntries(lesson.items.filter(item => hidden.has(item.id))
    .flatMap(item => Object.entries(item.hidden)));
  const count = lesson.items.length - hidden.size;
  const status = `${count} of ${lesson.items.length} shown`;
  const screenedOut = misses(inspected);
  const shown = !hidden.has(inspected.id);
  const inspectMarks = new Map(lesson.items.flatMap(item =>
    Object.keys(item.hidden).map(mark => [mark, () => inspect(item)] as const)));

  return <section id={anchor} className="learn-shell learn-chapter" aria-labelledby={`${anchor}-title`}>
    <h2 id={`${anchor}-title`}>{lesson.title}</h2>
    <p className="learn-objective">{lesson.prompt}</p>
    <div className="filter-experiment">
      <div className="filter-stage">
        <DrawingStage lesson={lesson} artwork={artwork} before={{ changes }} target={{ changes }}
          progress={1} onSelect={inspectMarks} inspected={new Set(Object.keys(inspected.hidden))} description={status + ". Select a record to see why it is shown or hidden."} />
      </div>
      <div className="filter-controls">
        {lesson.groups.map(group => <fieldset key={group.id}>
          <legend>{group.label}</legend>
          <div>{options(group).map(option => <label key={option}>
            <input type="checkbox" checked={selected.get(group.id)?.has(option) ?? false}
              onChange={() => toggle(group.id, option)} />
            <span>{option}</span>
          </label>)}</div>
        </fieldset>)}
        <button type="button" disabled={!selected.size} onClick={() => select(new Map())}>Clear filters</button>
        <p role="status">{status}</p>
      </div>
      <div className="filter-inspect">
        <div role="group" aria-label="Inspect a record">
          {lesson.items.map(item => <button type="button" key={item.id} aria-pressed={inspected.id === item.id}
            onClick={() => inspect(item)}>{item.label}</button>)}
        </div>
        <p aria-live="polite"><strong>{inspected.label} · {shown ? "Shown" : "Hidden"}</strong>
          <span>{lesson.groups.map(group => `${group.label} · ${inspected.values[group.id]}`).join("   /   ")}</span>
          {screenedOut.length
            ? <span>{screenedOut.map(group =>
              `${group.label} is ${inspected.values[group.id]}. You selected ${[...selected.get(group.id)!].join(" or ")}.`
            ).join(" ")}</span>
            : <span>{selected.size ? "This record matches every active filter." : "All records are shown while no filters are selected."}</span>}
        </p>
      </div>
      <p className="filter-rule">{lesson.explanation}</p>
      {sources(lesson.evidence_ids)}
    </div>
  </section>;
}
