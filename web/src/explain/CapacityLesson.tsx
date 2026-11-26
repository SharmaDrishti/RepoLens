import { useMemo, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import { capacityFrames, lanes } from "./capacity";
import type { CapacityBehavior, Lane } from "./capacity";
import { useLessonPlayer } from "./lesson-player";
import "./capacity.css";

const laneLabels = { waiting: "Waiting rack", running: "Presses", settled: "Finished tray" };
const position = (lane: Lane, slot: number) => ({
  x: (lanes.indexOf(lane) + .5) * 100 / 3,
  offset: slot % 2 ? 22 : -22,
  row: Math.floor(slot / 2),
});
const choiceLabel = (choice: number, starting: number) =>
  choice === starting ? `Keep at ${choice}` : choice > starting ? `Raise to ${choice}` : `Lower to ${choice}`;

export function CapacityCover({ behavior }: { behavior: CapacityBehavior }) {
  const { waiting, running, limit } = behavior.scenarios[0].initial_state;
  return <figure className="capacity-cover" aria-label={`${waiting} tasks waiting while ${running} run at a limit of ${limit}`}>
    <div className="capacity-cover-work" aria-hidden="true">
      <div className="capacity-cover-rack">{Array.from({ length: Math.min(3, waiting) }, (_, slot) => <i key={slot} />)}</div>
      <span className="capacity-cover-line" />
      <div className="capacity-cover-press">{Array.from({ length: Math.min(4, running) }, (_, slot) => <i key={slot} />)}</div>
    </div>
    <figcaption>Waiting work starts when a slot opens.</figcaption>
  </figure>;
}

export function LessonControls({ player }: { player: ReturnType<typeof useLessonPlayer> }) {
  return <div className="capacity-actions" role="group" aria-label="Playback">
    {!player.reduced && <>
      <button type="button" disabled={player.finished} onClick={player.toggle}>
        {player.mode === "play" ? "Pause" : "Play"}
      </button>
      <label>Speed <select value={player.speed} onChange={event => player.setSpeed(Number(event.target.value))}>
        <option value={.65}>Slow</option><option value={1}>Normal</option><option value={1.5}>Fast</option>
      </select></label>
    </>}
    <button type="button" disabled={player.finished || player.active} onClick={player.step}>Step</button>
    <button type="button" onClick={player.replay}>Replay</button>
  </div>;
}

export function CapacityLesson({ behavior, sources }: {
  behavior: CapacityBehavior;
  sources: (ids: string[]) => ReactNode;
}) {
  const [selection, setSelection] = useState(0);
  const scenario = behavior.scenarios[selection];
  const frames = useMemo(() => capacityFrames(scenario), [scenario]);
  const dimensions = useMemo(() => {
    const frames = behavior.scenarios.flatMap(capacityFrames);
    const presses = Math.max(...frames.map(frame => frame.presses.length));
    const rows = Math.ceil(Math.max(presses, ...frames.flatMap(frame =>
      [frame.queues.waiting.length, frame.queues.settled.length])) / 2);
    return { presses, rows };
  }, [behavior]);
  const player = useLessonPlayer(frames.length - 1);
  const { index, arrived, progress } = player;
  const before = frames[Math.max(0, index - 1)];
  const target = frames[index];
  const visible = arrived ? target : before;
  const lerp = (start: number, finish: number) => start + (finish - start) * progress;
  const beforePositions = new Map(lanes.flatMap(lane =>
    before.queues[lane].map((ticket, slot) =>
      [ticket, { ...position(lane, lane === "running" ? before.presses.indexOf(ticket) : slot), lane }] as const),
  ));
  const tickets = lanes.flatMap(lane => target.queues[lane].map((ticket, slot) => {
    const { x, offset, row } = position(lane, lane === "running" ? target.presses.indexOf(ticket) : slot);
    const from = beforePositions.get(ticket) ?? { x, offset, row, lane };
    return { ticket, lane: arrived ? lane : from.lane, style: {
      left: `calc(${lerp(from.x, x)}% + ${lerp(from.offset, offset)}px)`,
      "--ticket-row": lerp(from.row, row),
    } as CSSProperties };
  })).sort((a, b) => a.ticket - b.ticket);
  const evidenceIds = [...new Set(visible.step?.fact_ids.flatMap(id =>
    behavior.facts[id].evidence.map(ref => ref.id)) ?? [])];

  return <section id="learn-try" className="learn-shell learn-chapter capacity-lesson" aria-labelledby="capacity-title">
    <h2 id="capacity-title">When does waiting work start?</h2>
    <p className="learn-objective">{behavior.question}</p>
    <div className="capacity-workbench">
      <div className="capacity-toolbar">
        <div role="group" aria-label="Choose a concurrency limit">
          {behavior.scenarios.map((item, i) => <button key={item.id} type="button" aria-pressed={i === selection}
            onClick={() => { setSelection(i); player.reset(); }}>
            {choiceLabel(item.choice, item.initial_state.limit)}
          </button>)}
        </div>
        <strong>Limit <span data-testid="capacity-limit">{visible.limit}</span></strong>
      </div>
      <div className="capacity-stage" aria-label="Conceptual print shop" style={{ "--rows": dimensions.rows } as CSSProperties}>
        <div className="capacity-lanes">
          {lanes.map(lane => <div className="capacity-lane" key={lane} data-lane={lane}>
            <div className="capacity-lane-label">
              <span>{laneLabels[lane]}</span>
              <strong data-count={lane}>{visible.queues[lane].length}</strong>
            </div>
            <div className="capacity-machine" aria-hidden="true">
              {lane === "running" && <div className="capacity-ports">
                {Array.from({ length: dimensions.presses }, (_, slot) => (
                  <span key={slot} className="capacity-port" data-running={!!visible.presses[slot]} />
                ))}
              </div>}
            </div>
          </div>)}
        </div>
        <div className="capacity-tickets" aria-hidden="true">
          {tickets.map(({ ticket, lane, style }) =>
            <span data-ticket={ticket} data-lane={lane} className="capacity-ticket" key={ticket} style={style}>
              {String(ticket).padStart(2, "0")}
            </span>)}
        </div>
      </div>
      <div className="capacity-console">
        <div className="capacity-caption">
          <p role="status" aria-atomic="true">{visible.caption}</p>
          {visible.step?.provenance === "source_review" && <small>Step added during source review</small>}
        </div>
        <LessonControls player={player} />
      </div>
      <p className="capacity-key">Conceptual simulation. Tickets represent tasks. Presses represent running work. Timing is illustrative.</p>
      {evidenceIds.length > 0 && sources(evidenceIds)}
    </div>
  </section>;
}
