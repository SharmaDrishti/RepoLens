import { useState } from "react";
import type { ReactNode } from "react";
import { LessonControls } from "./CapacityLesson";
import { useLessonPlayer } from "./lesson-player";
import "./request.css";

type RequestState = { method: string; path: string; match: string; handler: string; response: string };
type RequestStep = { id: string; event: "submit" | "match" | "dispatch" | "respond";
  state: RequestState; caption: string; fact_ids: string[] };
export type RequestBehavior = {
  family: "request";
  question: string;
  scenarios: { id: string; choice: string; initial_state: RequestState; steps: RequestStep[] }[];
  facts: Record<string, { evidence: { id: string }[] }>;
  generation: { model?: string };
};

function stopFor(step?: RequestStep): [number, number] {
  if (!step) return [13, 25];
  if (step.event === "submit") return [38, 25];
  if (step.event === "match") return step.state.match === "matched" ? [38, 25] : [63, 70];
  if (step.event === "dispatch") return [63, 25];
  return [88, 25];
}

export function RequestCover() {
  return <figure className="request-cover">
    <div aria-hidden="true"><span className="request-envelope" /><i /><span className="request-window" /></div>
    <figcaption>Follow an address from the request to the reply.</figcaption>
  </figure>;
}

export function RequestLesson({ behavior, sources }: {
  behavior: RequestBehavior;
  sources: (ids: string[]) => ReactNode;
}) {
  const [selection, setSelection] = useState(0);
  const scenario = behavior.scenarios[selection];
  const player = useLessonPlayer(scenario.steps.length);
  const before = scenario.steps[player.index - 2];
  const next = scenario.steps[player.index - 1];
  const visible = player.arrived ? next : before;
  const state = visible?.state ?? scenario.initial_state;
  const from = stopFor(before);
  const to = stopFor(next);
  const interpolate = (axis: 0 | 1) => from[axis] + (to[axis] - from[axis]) * player.progress;
  const evidence = [...new Set(visible?.fact_ids.flatMap(id => behavior.facts[id].evidence.map(ref => ref.id)) ?? [])];
  return <section id="learn-try" className="learn-shell learn-chapter" aria-labelledby="request-title">
    <h2 id="request-title">Follow a request</h2>
    <p className="learn-objective">{behavior.question}</p>
    <div className="capacity-workbench request-workbench">
      <div className="capacity-toolbar">
        <div role="group" aria-label="Choose a request path">
          {behavior.scenarios.map((item, i) => <button key={item.id} type="button" aria-pressed={i === selection}
            onClick={() => { setSelection(i); player.reset(); }}>
            <code>{item.initial_state.method} {item.choice}</code>
          </button>)}
        </div>
      </div>
      <figure className="request-stage" aria-label="Request, route lookup, response source, and reply">
        <div className="request-stops">
          <span className="request-stop request-client">Request</span>
          <span className="request-stop request-route">Route lookup</span>
          <span className="request-stop request-view">View</span>
          <span className="request-stop request-error">Routing error</span>
          <span className="request-stop request-reply">Reply</span>
        </div>
        <span className="request-envelope request-traveler" aria-hidden="true"
          style={{ left: `${interpolate(0)}%`, top: `${interpolate(1)}%` }} />
      </figure>
      <dl className="request-result" aria-label="Current request state">
        <div><dt>Path</dt><dd>{state.path || "Ready"}</dd></div>
        <div><dt>Route</dt><dd>{state.match || "Waiting"}</dd></div>
        <div><dt>View</dt><dd>{state.handler || (state.match === "unmatched" ? "No view called" : "Waiting")}</dd></div>
        <div><dt>Response</dt><dd>{state.response || "Waiting"}</dd></div>
      </dl>
      <div className="capacity-console">
        <div className="capacity-caption">
          <p role="status" aria-atomic="true">{visible?.caption ?? "Choose an address and follow what this example does with it."}</p>
        </div>
        <LessonControls player={player} />
      </div>
      <p className="capacity-key">Conceptual walkthrough of the cited example.</p>
      {evidence.length > 0 && sources(evidence)}
    </div>
  </section>;
}
