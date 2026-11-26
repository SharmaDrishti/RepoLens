import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { EditorialHero, ProductionLine } from "./illustrations";
import { captionTime, changeLimit, createPlayer, playerClockActive, replay, stepPlayer, tickPlayer, togglePlay, travelTime } from "./player";
import { printStudioScene as scene } from "./scene";
import { capabilities, capabilityExamples, learningJourney, recipes, usage, usageCode } from "./content";
import { useSceneVisibility } from "./motion";
import { CopyCommand, StepControls, StoryTicket, TicketStrip } from "./StoryMotion";
import "./studio.css";

const source = (ref: string) => scene.source + scene.commit + "/" + ref;
function Citation({ refPath, children }: { refPath: string; children?: ReactNode }) {
  return <a className="studio-citation" href={source(refPath)}>{children ?? "Source"}</a>;
}

function Problem() {
  const [limited, setLimited] = useState(false);
  return <section id="studio-problem" className="studio-problem">
    <div className="studio-shell problem-layout">
      <div>
        <h2>Six requests. How many start?</h2>
        <p>{learningJourney[1].plain} <Citation refPath="recipes.md#L19-L37">Download recipe</Citation></p>
        <button type="button" className="studio-button ghost" aria-pressed={limited} onClick={() => setLimited(!limited)}>Limit to two at once</button>
      </div>
      <figure className="batch-example">
        <div className="batch-lanes" aria-hidden="true">
          <div className="batch-lane-labels"><span>Running</span><span>Waiting</span></div>
          <div className="batch-task-row">{Array.from({length: 6}, (_, index) =>
            <span key={index} className="batch-task" data-waiting={limited && index >= 2}><StoryTicket id={index + 1} /></span>)}</div>
        </div>
        <figcaption aria-live="polite">{limited ? "2 running · 4 waiting" : "6 running together"} · Conceptual comparison</figcaption>
      </figure>
    </div>
  </section>;
}

function QueueExplainer() {
  const [active, setActive] = useState(1);
  const [settled, setSettled] = useState(false);
  const full = active === 2 && !settled;
  return <section id="studio-rule" className="studio-shell studio-algorithm" aria-labelledby="studio-algorithm-heading">
    <div><h2 id="studio-algorithm-heading">How it works</h2>
      <Citation refPath="index.js#L16-L68">Queue and capacity code</Citation></div>
    <div className="story-options" role="group" aria-label="Active tasks with a limit of two">
      {[1, 2].map(count => <button key={count} type="button" className="studio-button ghost" aria-pressed={active === count}
        onClick={() => {setActive(count); setSettled(false);}}>{count} active · limit 2</button>)}
      <button type="button" className="studio-button filled" aria-disabled={!full} onClick={() => {if (full) setSettled(true);}}>Let a task settle</button>
    </div>
    <div className="queue-route">
      <div><StoryTicket /> <strong>Submit a task</strong></div>
      <div><strong>Room below the limit?</strong><span>{settled ? "1 active after settlement" : active + " active"}</span></div>
      <div className="queue-branches">
        <span data-route={!full}><strong>Yes → Start next task</strong></span>
        <span data-route={full}><strong>No → Stay pending</strong></span>
      </div>
    </div>
    <p className="queue-feedback" aria-live="polite">{full ? "Both slots are occupied. Ticket 01 waits." :
      settled ? "A task settled and freed a slot. Ticket 01 can start." :
      "One slot is open. Ticket 01 can start."} When a running task settles, the limiter checks for room again.</p>
  </section>;
}

function Playground() {
  const [player, setPlayer] = useState(createPlayer);
  const [guided, setGuided] = useState(true);
  const [reduced, setReduced] = useState(() => matchMedia("(prefers-reduced-motion: reduce)").matches);
  const { workshop, mode } = player;
  const {ref, visible} = useSceneVisibility<HTMLElement>();
  const clockActive = visible && playerClockActive(player);
  useEffect(() => {
    const media = matchMedia("(prefers-reduced-motion: reduce)");
    const change = () => setReduced(media.matches);
    media.addEventListener("change", change);
    return () => media.removeEventListener("change", change);
  }, []);
  useEffect(() => {
    if (!clockActive) return;
    let frame: number;
    let previous = performance.now();
    const update = (now: number) => {
      const delta = Math.max(0, Math.min(64, now - previous));
      previous = now;
      setPlayer(current => tickPlayer(current, delta));
      frame = requestAnimationFrame(update);
    };
    frame = requestAnimationFrame(update);
    return () => cancelAnimationFrame(frame);
  }, [clockActive]);
  return <section ref={ref} id="studio-play" className="studio-play" data-in-view={visible}>
    <div className="studio-shell play-layout">
      <div className="play-copy">
        <h2>Try it</h2>
        <p>Change the limit and watch the batch move through.</p>
      </div>
      <div className="studio-statline workshop-counts" role="group" aria-label="Job counts">
        <span><strong>{workshop.waiting.length}</strong> Waiting</span>
        <span><strong>{workshop.running.length}</strong> Running</span>
        <span><strong>{workshop.done.length}</strong> Completed</span>
        <span><strong>{workshop.limit}</strong> Concurrency limit</span>
      </div>
      <figure className="studio-main-scene">
        <ProductionLine workshop={workshop} previous={player.previous} motion={reduced ? 1 : player.motion / travelTime} arrival={player.arrival}
          title="Illustrated print studio with an intake, waiting rack, four processing stations and a finished tray" />
        <figcaption className="studio-scene-key"><span><b>Inbox</b> Submitted tasks</span><span><b>Waiting rack</b> Pending queue</span>
          <span><b>Presses</b> Slots for active work</span><span><b>Finished tray</b> Tasks that settled</span></figcaption>
      </figure>
      <div className="studio-play-controls">
      <div className="studio-console">
        <div className="studio-limit">
          <label htmlFor="studio-limit">Jobs allowed at once</label>
          <span aria-hidden="true">{player.pendingLimit ?? workshop.limit}</span>
          <input id="studio-limit" type="range" min="1" max="4" value={player.pendingLimit ?? workshop.limit}
            onChange={event => { const limit = Number(event.target.value); setPlayer(current => changeLimit(current, limit)); }} />
        </div>
        <label className="studio-speed">Playback speed
          <select value={player.speed} onChange={event => {
            const speed = Number(event.target.value); setPlayer(current => ({...current, speed}));
          }}><option value={.5}>Slow · 0.5×</option><option value={1}>Normal · 1×</option><option value={2}>Fast · 2×</option></select>
        </label>
        <div className="play-buttons">
          <button type="button" className="studio-button filled" disabled={!workshop.running.length && player.motion === travelTime}
            onClick={() => setPlayer(togglePlay)}>
            {mode === "playing" ? "Pause" : "Play"}</button>
          <button type="button" className="studio-button ghost" disabled={!workshop.running.length || mode === "step"}
            onClick={() => setPlayer(stepPlayer)}>Step</button>
          <button type="button" className="studio-button ghost" onClick={() => setPlayer(replay)}>Replay</button>
          <button type="button" className="studio-button ghost" onClick={() => setPlayer(current => createPlayer(2, current.speed))}>Reset</button>
        </div>
      </div>
      <div className="studio-caption-region">
        <label className="studio-caption-toggle"><input type="checkbox" checked={guided} onChange={event => setGuided(event.target.checked)} /> Guided captions <span>{guided ? "On" : "Off"}</span></label>
        <div className="studio-caption-slot" role="status" aria-atomic="true">
          {workshop.done.length > 0 && !workshop.running.length && !workshop.waiting.length && player.motion === travelTime ?
            <p className="studio-bubble studio-complete">All {workshop.done.length} tasks settled. Peak active this run: {player.peakActive}.</p> :
          guided && player.caption && <p key={player.caption} className="studio-bubble" style={{opacity: Math.min(1, (captionTime - player.captionAge) / 180)}}>{player.caption}</p>}
        </div>
      </div>
      {player.pendingLimit !== undefined && <p className="simulation-note">Limit {player.pendingLimit} applies after this handoff.</p>}
      <p className="simulation-note">Conceptual simulation. Each ticket represents one task. Job times are illustrative.</p>
      </div>
    </div>
  </section>;
}

function Usage() {
  const [active, setActive] = useState(0);
  const [showCode, setShowCode] = useState(false);
  const step = usage[active];
  const ticketLabels = [["Await setup", "Await setup", "Await setup"], ["Running", "Pending", "Pending"], ["Settled", "Settled", "Settled"]][active];
  return <section id="studio-usage" className="studio-shell studio-chapter">
    <p className="studio-kicker">From the studio to JavaScript</p><h2>How a developer uses it.</h2>
    <div className="story-options" aria-label="Documented example steps" role="group">
      {usage.map((item, index) => <button key={item.title} type="button" className="studio-button ghost"
        aria-pressed={active === index} onClick={() => setActive(index)}>{index + 1}. {item.title}</button>)}
    </div>
    <div className="story-feature">
      <TicketStrip key={active} count={3} labels={ticketLabels} move={active} />
      <p>{step.body}</p>
    </div>
    <p className="simulation-note">Conceptual walkthrough of the documented example.</p>
    <StepControls active={active} count={usage.length} select={setActive} />
    <button type="button" className="studio-button ghost" onClick={() => setShowCode(!showCode)} aria-expanded={showCode}
      aria-controls="studio-code">{showCode ? "Hide JavaScript example" : "Show JavaScript example"}</button>{" "}
    <Citation refPath="readme.md#L15-L29">README example</Citation>
    <pre id="studio-code" className="studio-code" hidden={!showCode}><code>{usageCode.map((line, index) =>
      <span key={index} data-highlight={index + 1 >= step.lines[0] && index + 1 <= step.lines[1]}>{line}{index < usageCode.length - 1 ? "\n" : ""}</span>)}</code></pre>
  </section>;
}

function More() {
  const [capability, setCapability] = useState(0);
  const [recipe, setRecipe] = useState(0);
  const [showEffect, setShowEffect] = useState(false);
  const [recipeRun, setRecipeRun] = useState(0);
  const current = capabilities[capability];
  const application = recipes[recipe];
  return <>
    <section id="studio-capabilities" className="studio-shell studio-chapter">
      <h2>What else can it do?</h2>
      <div className="story-options" role="group" aria-label="Capabilities">
        {capabilities.map((item, index) => <button key={item.api} type="button" className="studio-button ghost"
          aria-pressed={capability === index} onClick={() => {setCapability(index); setShowEffect(false);}}>{item.label}</button>)}
      </div>
      <div className="story-feature"><code>{current.api}</code><p>{current.plain} <Citation refPath={current.ref} /></p></div>
      <button type="button" className="studio-button ghost" aria-expanded={showEffect} aria-controls="studio-api-example"
        onClick={() => setShowEffect(!showEffect)}>{showEffect ? "Hide an example" : "See an example"}</button>
      <figure id="studio-api-example" className="api-example" hidden={!showEffect}>
        <div><small>Situation</small>{capabilityExamples[capability][0]}</div>
        <div className="story-enter"><small>After the operation</small>{capabilityExamples[capability][1]}
          {capability <= 2 && <TicketStrip count={5} move={capability}
            labels={capability === 0 ? ["Running", "Running", "Pending", "Pending", "Pending"] :
              capability === 1 ? ["Running", "Running", "Admitted", "Pending", "Pending"] :
                ["Still running", "Still running", "Discarded", "Discarded", "Discarded"]} />}</div>
        <figcaption>Illustrative example · <Citation refPath={current.ref}>API evidence</Citation></figcaption>
      </figure>
      <p>p-limit controls how much runs at once. It has no queue pause control. A job can also deadlock if it waits for another job scheduled through the same limiter. <Citation refPath="readme.md#L171-L175">README comparison</Citation> · <Citation refPath="readme.md#L76">Nested jobs warning</Citation></p>
    </section>
    <section id="studio-applications" className="studio-applications">
      <div className="studio-shell studio-chapter">
        <h2>What could you build?</h2>
        <div className="story-options" role="group" aria-label="Documented recipes">
          {recipes.map((item, index) => <button key={item.title} className="studio-button ghost" type="button"
            aria-pressed={recipe === index} onClick={() => {setRecipe(index); setRecipeRun(0);}}>{item.title}</button>)}
        </div>
        <button type="button" className="studio-button filled" onClick={() => setRecipeRun(value => value + 1)}>{recipeRun ? "Replay scenario" : "Show the workflow"}</button>
        <ol key={recipe + ":" + recipeRun} className={recipeRun ? "recipe-flow recipe-run" : "recipe-flow"} data-recipe={recipe} aria-label="Inputs, work and result">
          <li><small>Inputs</small><div className="recipe-tickets">{application.inputs.map((input, i) => <span key={i}>{input}</span>)}</div></li>
          <li><small>Jobs</small>{application.work}</li>
          <li><small>Result</small>{application.outcome}</li>
        </ol>
        <Citation refPath={application.ref}>Documented recipe</Citation> · Conceptual walkthrough
      </div>
    </section>
    <Setup />
    <section id="studio-boundaries" className="studio-shell studio-chapter">
      <h2>What the limit controls.</h2>
      <dl className="studio-boundaries">
        <div><dt>How many jobs can start</dt><dd>Change available capacity while jobs are running. <Citation refPath="index.js#L91-L104">Limit setter</Citation></dd></div>
        <div><dt>What happens to existing work</dt><dd>Clearing the queue discards jobs that have yet to start. Running jobs continue. <Citation refPath="readme.md#L98-L107">Queue behavior</Citation></dd></div>
        <div><dt>What the program still decides</dt><dd>Your functions decide what work to do, and your code handles their results or errors. <Citation refPath="readme.md#L60-L68">Task API</Citation> · <Citation refPath="index.js#L32-L47">Error behavior</Citation></dd></div>
      </dl>
    </section>
  </>;
}

function Setup() {
  const [active, setActive] = useState(0);
  const stages = ["Requirements", "Install", "Create a limiter", "Submit work", "Read the result"];
  const instructions = [
    <>The README lists browser support. This revision requires Node.js 20 or newer when you use Node. <Citation refPath="package.json#L19-L21">Node requirement</Citation> · <Citation refPath="readme.md#L3-L5">Browser support</Citation></>,
    <><code>npm install p-limit</code> <CopyCommand command="npm install p-limit" /> <Citation refPath="readme.md#L7-L11">Installation source</Citation></>,
    <>Import the library and call <code>pLimit(1)</code> to allow one active job at a time. <Citation refPath="readme.md#L16-L18">README setup</Citation></>,
    <>Pass your own functions to the limiter. It calls them as slots open. <a href="#studio-usage">Open the annotated example</a>.</>,
    <>If all three jobs succeed, the README example logs their results. The values depend on the functions you supply. <Citation refPath="readme.md#L20-L28">Documented example</Citation></>,
  ];
  return <section id="studio-setup" className="studio-shell studio-chapter">
    <h2>Getting started</h2>
    <div className="story-options" role="group" aria-label="Setup steps">
      {stages.map((title, index) => <button key={title} type="button" className="studio-button ghost"
        aria-pressed={active === index} onClick={() => setActive(index)}>{title}</button>)}
    </div>
    <div key={active} className="setup-stage story-enter"><h3>{stages[active]}</h3><p>{instructions[active]}</p></div>
    <StepControls active={active} count={stages.length} select={setActive} />
  </section>;
}

function HeroArt() {
  const {ref, visible, entered} = useSceneVisibility<HTMLElement>();
  const [run, setRun] = useState(0);
  return <figure ref={ref} className="hero-art" data-in-view={visible}>
    <EditorialHero key={run} animate={entered} />
    <figcaption><button type="button" className="studio-button ghost" onClick={() => setRun(value => value + 1)}>Replay ticket arrival</button></figcaption>
  </figure>;
}

export function PrintStudio({ developer }: { developer?: ReactNode }) {
  useEffect(() => {
    document.title = "RepoLens · p-limit Print Studio";
    if (location.hash) document.getElementById(location.hash.slice(1))?.scrollIntoView();
  }, []);
  return <div className="studio">
    <header className="studio-header"><div className="studio-shell studio-nav">
      <a className="studio-brand" href="#studio-top">RepoLens<span> / p-limit</span></a>
      <nav aria-label="Print Studio sections">
        <a href="#studio-top">Visual Story</a><a href="#studio-play">Try It</a><a href="#studio-setup">Getting Started</a><a href="#studio-source">Behind the Scenes</a>
      </nav>
    </div></header>
    <main id="studio-top">
      <section className="studio-hero">
        <div className="studio-shell hero-layout">
          <div className="hero-copy">
            <p className="studio-kicker">JavaScript library</p>
            <h1>p-limit<em>Too much at once?</em></h1>
            <p>{learningJourney[0].plain} <Citation refPath="readme.md#L1-L5">Project README</Citation></p>
            <a className="studio-button filled" href="#studio-problem">Follow a job</a>
          </div>
          <HeroArt />
        </div>
      </section>
      <Problem />
      <QueueExplainer />
      <Playground />
      <Usage />
      <More />
      <section id="studio-source" className="studio-shell studio-source">
        <h2>Behind the Scenes</h2>
        <nav className="studio-tech-nav" aria-label="Technical sections">
          {developer && <a href="#map">Architecture / Import Map</a>}
          <a href="#studio-code-evidence">Source Code</a>
          {developer && <><a href="#behavior">Behavior / Architecture</a><a href="#claims">Evidence and Verification</a><a href="#reading">Recommended Reading Order</a></>}
          <a href="#studio-setup">Getting Started</a>
        </nav>
        <h3 id="studio-code-evidence">Source Code · {scene.commit.slice(0, 7)}</h3>
        <ol className="studio-evidence">{scene.evidence.map(item => <li key={item.lines}>
          <Citation refPath={item.file + "#" + item.lines}>{item.title}</Citation> <small>{item.kind} · {item.file}:{item.lines}</small>
          <p>{item.description}</p>
        </li>)}</ol>
        {developer ? <div className="studio-developer">{developer}</div> : <p>Generate the matching p-limit report to open the import map, verification and reading order here.</p>}
      </section>
    </main>
  </div>;
}
