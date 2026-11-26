import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";
import { Story } from "./explain/Story";
import type { ProjectStory } from "./explain/Story";
import { ImportExplorer } from "./developer/ImportExplorer";
import { PrintStudio } from "./print-studio/PrintStudio";
import { printStudioScene } from "./print-studio/scene";

type Evidence = { path: string; line?: number; key?: string; edge_id?: string; snippet?: string; url?: string | null };
type Claim = { id: string; kind: "FACT" | "INTERPRETATION"; text: string; evidence: Evidence[] };
type Edge = { id: string; from: string; to: string; line?: number };
type Recommendation = { path: string; reason: string; evidence: Evidence; history_note?: string };
type Flow = { files: string[]; edge_ids: string[]; entry_evidence: Evidence; entry_scope?: {kind: string; path: string | null} };
type Wording = { text: string; evidence_ids: string[]; plain?: { text: string; evidence_ids: string[] } | null };
type GuideItem = Wording & { kind: string };
type Knowledge = {
  context: {
    purpose: {what_it_is: Wording; who_uses_it: {items: Wording[]}; problem_it_solves: Wording};
    use_cases: {use_cases: {id: string; title: string; scenario: string; evidence_ids: string[];
      plain?: {title: string; scenario: string; evidence_ids: string[]}}[]};
    getting_started: Record<string, {items: GuideItem[]; status: string}>;
  };
  evidence: Record<string, {path: string; line: number; excerpt: string; url: string | null}>;
  snapshot: {working_tree: string; cache: {mode: string; remote_freshness: string}};
  developer: {entry_declarations: {kind: string; path: string | null; evidence_ids: string[];
    scope: {kind: string; path: string | null}; evidence: Evidence}[]};
};
type Overview = {
  description?: Evidence & { text: string; end_line: number };
  hooks?: { event: string; script: string; arguments: string[]; template: boolean; evidence: Evidence }[];
};
type Payload = {
  story?: ProjectStory;
  report: {
    repo: string; commit: { short?: string; sha?: string; pinned: boolean };
    claims: Claim[]; sections?: Record<string, string[]>;
    reading_guide?: { recommendations: Recommendation[]; flow: Flow | null };
    rejected_claims?: { reason: string; text?: string | null }[];
    overview?: Overview;
    evidence_diagnostics?: { evidence_id: string; reason: string }[];
  };
  edges: Edge[];
  evidence: Record<string, Evidence>;
  history?: { status: string; commits_analyzed: number; files: { path: string; change_count: number }[] };
  knowledge?: Knowledge;
};

const basename = (path: string) => path.split("/").at(-1) || path;
const folder = (path: string) => path.includes("/") ? path.slice(0, path.lastIndexOf("/")) : "Repository root";

function githubLink(url?: string | null) {
  if (!url) return undefined;
  try {
    const link = new URL(url);
    return link.origin === "https://github.com" && /\/blob\/[a-f0-9]{40,64}\//.test(link.pathname)
      ? link.href : undefined;
  } catch {
    return undefined;
  }
}

function EvidenceCard({ evidence }: { evidence: Evidence }) {
  const url = githubLink(evidence.url);
  return <div className="citation">
    <div className="citation-title">
      <code>{evidence.path}{evidence.line ? ":" + evidence.line : ""}{evidence.key ? " · " + evidence.key : ""}</code>
      {url && <a href={url}>View on GitHub</a>}
    </div>
    {evidence.snippet && <pre><code>{evidence.snippet}</code></pre>}
  </div>;
}

function Citations({ ids, knowledge }: { ids: string[]; knowledge: Knowledge }) {
  if (!ids.length) return null;
  return <details className="citation"><summary>Source evidence</summary>
    {ids.map(id => { const item = knowledge.evidence[id]; return item ? <EvidenceCard key={id}
      evidence={{path: item.path, line: item.line, url: item.url, snippet: item.excerpt}} /> : null; })}
  </details>;
}

function BeginnerContext({ knowledge }: { knowledge: Knowledge }) {
  const { purpose, use_cases, getting_started } = knowledge.context;
  const problem = purpose.problem_it_solves;
  const groups = [["requirements", "Requirements"], ["install", "Install"], ["first_run", "First example or command"],
    ["expected_output", "Expected result"], ["gotchas", "Documented notes"]];
  return <>
    {problem.text !== "unknown" && <section className="section">
      <h2>Why it exists</h2><p>{problem.plain?.text ?? problem.text}</p>
      {problem.plain && <small>Interpretation</small>}
      <Citations ids={problem.evidence_ids} knowledge={knowledge} />
    </section>}
    <section className="section" id="uses">
      <h2>What you can use it for</h2>
      {use_cases.use_cases.length ? <ul className="reading-list">{use_cases.use_cases.map(item => <li key={item.id}>
        <strong>{item.plain?.title ?? item.title}</strong> <small>Interpretation</small>
        {(item.plain?.scenario ?? item.scenario).replace(/\.$/, "") !== (item.plain?.title ?? item.title) &&
          <p>{item.plain?.scenario ?? item.scenario}</p>}
        <Citations ids={item.evidence_ids} knowledge={knowledge} />
      </li>)}</ul> : <p>The available sources do not establish any use cases.</p>}
    </section>
    <section className="section" id="setup">
      <h2>Getting started</h2>
      {groups.map(([key, title]) => {
        const group = getting_started[key];
        return <div className="reading-list" key={key}>
          <h3>{title}</h3>
          {group.items.length ? group.items.map((item, index) => <div className="citation" key={index}>
            {["command", "code_example", "expected_output"].includes(item.kind)
              ? <pre><code>{item.text}</code></pre> : <p>{item.plain?.text ?? item.text}</p>}
            <Citations ids={item.evidence_ids} knowledge={knowledge} />
          </div>) : <p>{group.status === "unknown" ? "Unknown from available sources." : "Not documented in the sources found."}</p>}
        </div>;
      })}
    </section>
  </>;
}

function App({ data, embedded = false }: { data: Payload; embedded?: boolean }) {
  const Content = embedded ? "div" : "main";
  const { report, edges, evidence, history } = data;
  const knowledge = data.knowledge;
  const purpose = knowledge?.context.purpose;
  const guide = report.reading_guide;
  const flow = guide?.flow ?? null;
  const recommendations = guide?.recommendations ?? [];
  const paths = [...new Set([...(flow?.files ?? []), ...recommendations.map(item => item.path),
    ...edges.flatMap(edge => [edge.from, edge.to]), ...report.claims.flatMap(claim => claim.evidence.map(item => item.path))])].slice(0, 24);
  const [active, setActive] = useState(0);
  const [selected, setSelected] = useState(paths[0]);
  const [selectedEdge, setSelectedEdge] = useState<string>();
  const [mapMode, setMapMode] = useState<"path" | "all">(flow ? "path" : "all");
  const [playing, setPlaying] = useState(
    () => Boolean(flow && flow.files.length > 1 && !window.matchMedia("(prefers-reduced-motion: reduce)").matches),
  );
  const last = Math.max(0, (flow?.files.length ?? 1) - 1);
  useEffect(() => {
    if (!flow || !playing || active >= last) return;
    const timer = window.setTimeout(() => {
      const step = active + 1;
      setActive(step);
      setSelected(flow.files[step]);
      setSelectedEdge(flow.edge_ids[step - 1]);
      if (step === last) setPlaying(false);
    }, 850);
    return () => window.clearTimeout(timer);
  }, [active, flow, last, playing]);
  const seek = (step: number) => {
    setPlaying(false);
    setActive(step);
    setSelectedEdge(flow?.edge_ids[step - 1]);
    if (flow) setSelected(flow.files[step]);
  };
  const chooseFile = (path: string) => {
    setPlaying(false);
    setSelected(path);
    setSelectedEdge(undefined);
    const index = flow?.files.indexOf(path) ?? -1;
    if (index >= 0) setActive(index);
    else setMapMode("all");
  };
  const inspectEdge = (edge: Edge) => {
    const index = flow?.edge_ids.indexOf(edge.id) ?? -1;
    if (index >= 0) seek(index + 1);
    else chooseFile(edge.to);
    setSelectedEdge(edge.id);
  };
  const visiblePaths = mapMode === "path" && flow ? flow.files : paths;
  const visibleEdges = mapMode === "path" ? edges.filter(edge => flow?.edge_ids.includes(edge.id)) : edges;
  const connection = selectedEdge ? edges.find(edge => edge.id === selectedEdge) : undefined;
  const selectedRecommendation = recommendations.find(item => item.path === selected);
  const related = new Map<string, Evidence>();
  const show = (item?: Evidence) => {
    if (item) related.set(item.path + ":" + (item.line ?? item.key ?? ""), item);
  };
  const stepId = selected === flow?.files[active] && active > 0 ? flow?.edge_ids[active - 1] : undefined;
  if (stepId) show(evidence[stepId]);
  if (selected === flow?.files[0]) show(flow?.entry_evidence);
  if (selectedRecommendation) show(evidence[selectedRecommendation.evidence.edge_id ?? ""] ?? selectedRecommendation.evidence);
  edges.filter(edge => edge.from === selected || edge.to === selected).forEach(edge => show(evidence[edge.id]));
  report.claims.flatMap(claim => claim.evidence).filter(item => item.path === selected).forEach(show);
  const summaryIds = report.sections?.summary ?? [];
  const claims = [...report.claims].sort((a, b) => Number(summaryIds.includes(b.id)) - Number(summaryIds.includes(a.id)));
  const lead = claims.find(claim => summaryIds.includes(claim.id));
  const overview = report.overview;
  const intro = overview?.description;
  const hasMap = edges.length > 0;
  const factual = claims.filter(claim => claim.kind === "FACT").length;
  const rejected = report.rejected_claims ?? [];
  const unavailable = report.evidence_diagnostics ?? [];
  return <>
    <header className="topbar">
      <a className="brand" href="#top"><span className="brand-mark" aria-hidden="true">RL</span>RepoLens</a>
      <nav aria-label="Report sections">{knowledge && <><a href="#uses">Use cases</a><a href="#setup">Getting started</a></>}
        {hasMap && <a href="#map">Developer import map</a>}<a href="#reading">Reading guide</a><a href="#claims">Claims</a></nav>
    </header>
    <Content id="top">
      <section className="hero flex flex-wrap items-end justify-between gap-6">
        <div><h1>{report.repo}</h1>
          {knowledge && purpose ? <>
            <p className="lead">{purpose.what_it_is.text === "unknown" ? "Project purpose is unknown from the available sources."
              : purpose.what_it_is.plain?.text ?? purpose.what_it_is.text}</p>
            {purpose.what_it_is.plain && <small>Interpretation</small>}
            <Citations ids={purpose.what_it_is.evidence_ids} knowledge={knowledge} />
            {purpose.who_uses_it.items.length ? purpose.who_uses_it.items.map((item, index) => <div key={index}>
              <p>Who uses it · {item.plain?.text ?? item.text}</p>
              {item.plain && <small>Interpretation</small>}
              <Citations ids={item.evidence_ids} knowledge={knowledge} />
            </div>) : <p>Audience is unknown from the available sources.</p>}
            <small>Working tree · {knowledge.snapshot.working_tree} · {knowledge.snapshot.cache.mode}
              {knowledge.snapshot.cache.remote_freshness === "not_checked" ? " · Remote freshness not checked" : ""}</small>
          </> : intro ? <>
            <p className="lead">{intro.text}</p>
            <p className="overview-source">Project README · {githubLink(intro.url)
              ? <a href={githubLink(intro.url)}>lines {intro.line}–{intro.end_line}</a>
              : <code>{intro.path}:{intro.line}</code>}</p>
          </> : lead && <p className="lead"><a href={"#" + lead.id}>{lead.kind === "FACT" ? "Fact" : "Interpretation"}</a> {lead.text}</p>}
        </div>
        <dl className="metrics">
          <div><dt>Commit</dt><dd><code>{report.commit.pinned ? (report.commit.short || report.commit.sha?.slice(0, 7) || "Pinned") : "Unpinned"}</code></dd></div>
          <div><dt>Facts</dt><dd>{factual}</dd></div>
          <div><dt>Interpretations</dt><dd>{claims.length - factual}</dd></div>
        </dl>
      </section>
      {knowledge && <BeginnerContext knowledge={knowledge} />}

      {overview?.hooks && overview.hooks.length > 0 && <section className="section" id="starts">
        <div className="section-heading"><h2>How it starts</h2></div>
        <div className="claim-grid">{overview.hooks.map(hook => <article className="claim" key={hook.evidence.path + ":" + hook.evidence.line}>
          <h3>{hook.event}</h3>
          <p>The {hook.template ? "hook template" : "hook settings"} name <code>{hook.script}</code>
            {hook.arguments.length > 0 && <> with the <code>{hook.arguments.join(" ")}</code> argument</>}.</p>
          <EvidenceCard evidence={hook.evidence} />
        </article>)}</div>
      </section>}
      {hasMap && <section id="map" className="section">
        <div className="map-heading">
          <div className="section-heading"><h2>Import / Dependency View</h2>
            <p>Static import tour. Playback follows import links, without indicating runtime execution order.</p>
            {flow && <p>Tour starts at <code>{flow.files[0]}</code>
              {flow.entry_scope?.kind === "example" && <> · Example entry in <code>{flow.entry_scope.path}</code></>}.</p>}
          </div>
          {flow && <div className="map-switch" aria-label="Map view">
            <button type="button" aria-pressed={mapMode === "path"} onClick={() => {
              setMapMode("path");
              if (!flow.files.includes(selected)) seek(0);
            }}>Import path</button>
            <button type="button" aria-pressed={mapMode === "all"} onClick={() => setMapMode("all")}>Connected files</button>
          </div>}
        </div>
        <div className="workbench">
          <div className="graph">
            {paths.length > 0 ? <ImportExplorer paths={visiblePaths} edges={visibleEdges} activeEdges={flow?.edge_ids.slice(0, active) ?? []}
              selected={selected} selectedEdge={selectedEdge} select={chooseFile} inspect={inspectEdge} />
              : <p className="empty">This report has no files to map.</p>}
            <div className="playback">
              {flow && last > 0 ? <>
                <button type="button" className="primary" onClick={() => {
                  if (playing) { setPlaying(false); return; }
                  if (active >= last || !flow.files.includes(selected)) seek(0);
                  setMapMode("path");
                  setPlaying(true);
                }}>{playing ? "Pause" : active >= last ? "Replay" : "Play path"}</button>
                <input type="range" min={0} max={last} value={active} aria-label="Import path step"
                  onChange={event => seek(Number(event.target.value))} />
                <span aria-live="polite">{active + 1} / {last + 1}</span>
              </> : <p>No import path from a confirmed entry point.</p>}
            </div>
          </div>
          <aside className="source-panel evidence-inspector" aria-label="Source evidence">
            <div className="inspector-heading"><h3>Source evidence</h3>{connection && <span>Import selected</span>}</div>
            {connection && <div className="current-connection">
              <dl><dt>Relationship</dt><dd>Static import</dd><dt>From</dt><dd><code>{connection.from}</code></dd><dt>To</dt><dd><code>{connection.to}</code></dd></dl>
              {evidence[connection.id] ? <EvidenceCard evidence={evidence[connection.id]} />
                : <p>No verified excerpt is available for this import.</p>}
            </div>}
            {paths.length > 0 && <label className="file-select">File
              <select value={selected ?? ""} onChange={event => chooseFile(event.target.value)}>
                {[...new Set(paths.map(folder))].sort().map(group => <optgroup key={group} label={group}>
                  {paths.filter(path => folder(path) === group).map(path => <option key={path} value={path}>{basename(path)}</option>)}
                </optgroup>)}
              </select>
            </label>}
            {selected && <p className="inspector-path"><code>{selected}</code></p>}
            {selectedRecommendation && <p>{selectedRecommendation.reason}</p>}
            {related.size ? [...related.entries()].filter(([, item]) => item !== evidence[selectedEdge ?? ""])
              .slice(0, 6).map(([key, item]) => <EvidenceCard key={key} evidence={item} />)
              : <p>No source excerpt is available for this selection.</p>}
          </aside>
        </div>
      </section>}
      <section id="behavior" className="section">
        <h2>Behavior / Architecture View</h2>
        <p>This report has no verified behavior graph. The static import explorer shows file dependencies.</p>
      </section>
      <section id="reading" className="section">
        <div className="section-heading"><h2>Recommended reading</h2><p>Why these files are useful to read.</p></div>
        {recommendations.length ? <ol className="reading-list">{recommendations.map(item => <li key={item.path}>
          {hasMap ? <a href="#map" onClick={() => chooseFile(item.path)}>{item.path}</a> : <code>{item.path}</code>}
          <p>{item.reason}</p>{item.history_note && <small>{item.history_note}</small>}
          {!hasMap && <EvidenceCard evidence={Object.values(evidence).find(value =>
            value.path === item.evidence.path && value.line === item.evidence.line) ?? item.evidence} />}
        </li>)}</ol> : <p className="empty">No reading recommendations are available.</p>}
        {knowledge && <details className="citation">
          <summary>Scoped entry declarations ({knowledge.developer.entry_declarations.length})</summary>
          {knowledge.developer.entry_declarations.length ? <ul className="reading-list">
            {knowledge.developer.entry_declarations.map((entry, index) => <li key={index}>
              <strong>{entry.scope.kind}</strong> {entry.scope.path && <code>{entry.scope.path}</code>}
              <p>{entry.path ?? "Target file could not be resolved."}</p>
              {entry.evidence_ids.length ? <Citations ids={entry.evidence_ids} knowledge={knowledge} />
                : <EvidenceCard evidence={entry.evidence} />}
            </li>)}
          </ul> : <p>No entry declarations were established.</p>}
        </details>}
      </section>
      <section id="claims" className="section">
        <div className="section-heading"><h2>Claims and evidence</h2></div>
        <div className="claim-grid">{claims.map(claim => <article key={claim.id} id={claim.id} className="claim">
          <span className={"badge " + (claim.kind === "FACT" ? "fact" : "interpretation")}>
            {claim.kind === "FACT" ? "Verified fact" : "Interpretation"}
          </span><p>{claim.text}</p>
          {claim.evidence.map((item, index) => <EvidenceCard key={index} evidence={item} />)}
        </article>)}</div>
        {claims.length === 0 && <p className="empty">No claims with evidence are available.</p>}
      </section>
      {history && <section className="section">
        <div className="section-heading"><h2>Git history</h2><p>{history.status} · {history.commits_analyzed} commits analyzed</p></div>
        <ul className="history-list">{history.files.slice(0, 5).map(item => <li key={item.path}>
          <code>{item.path}</code><span>{item.change_count} changes</span>
        </li>)}</ul>
      </section>}
      <section className="section">
        <details className="audit"><summary>Rejections and unavailable evidence ({rejected.length + unavailable.length})</summary>
          {rejected.length + unavailable.length === 0 && <p>No rejections or evidence issues were recorded.</p>}
          <ul>{rejected.map((item, index) => <li key={"r" + index}>{item.reason}{item.text && <p>{item.text}</p>}</li>)}
            {unavailable.map((item, index) => <li key={"e" + index}><code>{item.evidence_id}</code> · {item.reason}</li>)}</ul>
        </details>
      </section>
    </Content>
  </>;
}

const root = createRoot(document.getElementById("root")!);
const raw = document.getElementById("repolens-data")?.textContent;
const data: Payload | undefined = raw?.startsWith("{") ? JSON.parse(raw) : undefined;
const studio = location.pathname.replace(/\/$/, "") === "/print-studio"
  || document.documentElement.dataset.repolensPrototype === "print-studio";
if (studio) {
  const matchingReport = data?.report.repo === "p-limit" && data.report.commit.sha === printStudioScene.commit;
  root.render(<PrintStudio developer={matchingReport && <App data={data} embedded />} />);
} else if (data?.story?.schema_version === 1) {
  root.render(<Story story={data.story} hasMap={data.edges.length > 0}
    developer={<div className="studio-developer"><App data={data} embedded /></div>} />);
} else if (data) {
  root.render(<App data={data} />);
} else {
  root.render(<main><h1>RepoLens</h1><p>Generate a report with <code>python -m repolens page</code> to view repository data.</p></main>);
}
