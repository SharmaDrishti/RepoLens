import { Fragment, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { CapacityCover, CapacityLesson } from "./CapacityLesson";
import type { CapacityBehavior } from "./capacity";
import { RequestCover, RequestLesson } from "./RequestLesson";
import type { RequestBehavior } from "./RequestLesson";
import { VisualLesson } from "./VisualLesson";
import type { VisualPlan } from "./VisualLesson";
import { TeachingLesson, lessonAnchor } from "./TeachingLesson";
import type { Lesson } from "./TeachingLesson";
import type { Artwork } from "./IllustratedLesson";
import { LoopingHero } from "./LoopingHero";
import type { Hero } from "./LoopingHero";
import { GuidedStory } from "./GuidedStory";
import type { Guide } from "./GuidedStory";
import { sceneStep } from "./progression";
import "./story.css";

type Claim = { label: string; text: string; section: string; evidence_ids: string[] };
type Scene = { kind: string; title: string; objective: string; accessibility: string; claim_ids: string[] };
type Location = { path: string; line: number; end_line: number };
type Source = Partial<Location> & { location?: Location; url?: string | null; excerpt: string; type: string };
type Item = { kind: string; text: string; evidence_ids: string[] };
type SectionArt = { asset: string; alt: string; evidence_ids: string[] };
export type ProjectStory = {
  schema_version: number;
  project: { repo: string; commit: { sha: string; short?: string } };
  claims: Record<string, Claim>; scenes: Scene[]; evidence: Record<string, Source>;
  setup: Record<string, Item[]>; unknowns: string[]; checklist: Record<string, string>;
  mode: "ai" | "deterministic" | "synthetic_test";
  origin?: "codex_skill";
  behavior?: CapacityBehavior | RequestBehavior;
  visual?: VisualPlan;
  lessons?: Lesson[];
  lesson_menu?: string[];
  intro_lesson?: string;
  section_art?: Record<string, SectionArt>;
  artwork?: Artwork;
  hero?: Hero;
  guide?: Guide;
  cover?: { alt: string; width: number; height: number; data: string; evidence_ids: string[] };
};

function Sources({ ids, story }: {ids: string[]; story: ProjectStory}) {
  const safe = (link?: string | null) => link &&
    /^https:\/\/github\.com\/[\w.-]+\/[\w.-]+\/blob\/[a-f0-9]{40,64}\//.test(link) &&
    link.includes("/blob/" + story.project.commit.sha + "/") ? link : undefined;
  return <details className="learn-sources"><summary>Source evidence</summary>
    {ids.map(id => {
      const source = story.evidence[id];
      if (!source) return null;
      const loc = source.location || source;
      const label = `${loc.path}:${loc.line}${loc.end_line !== loc.line ? "–" + loc.end_line : ""}`;
      const url = safe(source.url);
      return <div key={id}><small>{source.type.replaceAll("_", " ")}</small>
        {url ? <a href={url}>{label}</a> : <code>{label}</code>}
        <pre><code>{source.excerpt}</code></pre></div>;
    })}
  </details>;
}

function SupportingArt({ art, artwork }: { art: SectionArt; artwork: Artwork }) {
  return <figure className="learn-support-art"><img loading="lazy" decoding="async"
    src={`data:image/png;base64,${artwork[art.asset]}`} alt={art.alt} /></figure>;
}

function LessonMenu({ lessons, story, active, select, children }: {
  lessons: Lesson[]; story: ProjectStory; active?: string; select: (id: string) => void; children: ReactNode;
}) {
  return <section id="learn-lessons" className="learn-lesson-area learn-chapter" aria-labelledby="learn-lessons-title">
    <div className="learn-shell">
    <h2 id="learn-lessons-title">How it works</h2>
    <ul className="learn-lesson-menu">
      {lessons.map(lesson => {
        const anchor = lessonAnchor(lesson.id);
        const content = lesson.kind === "guide" ? lesson.guide : lesson.kind === "animate" ? lesson.plan : lesson;
        const asset = story.section_art?.[anchor]?.asset;
        return <li key={lesson.id}><a href={`#${anchor}`} aria-current={lesson.id === active ? "true" : undefined}
          onClick={event => {
            if (event.button || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
            event.preventDefault();
            select(lesson.id);
          }}>
          {asset && <img loading="lazy" decoding="async" src={`data:image/png;base64,${story.artwork?.[asset]}`} alt="" />}
          <strong>{content.title}</strong>
        </a></li>;
      })}
    </ul>
    </div>
    {children}
  </section>;
}

function SceneView({ scene, story, index, reverse }: {
  scene: Scene; story: ProjectStory; index: number; reverse: boolean;
}) {
  const claims = scene.claim_ids.map(id => story.claims[id]).filter(Boolean);
  const [active, setActive] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [reduced, setReduced] = useState(() => matchMedia("(prefers-reduced-motion: reduce)").matches);
  const ordered = scene.kind === "flow" || scene.kind === "walkthrough";
  useEffect(() => {
    const query = matchMedia("(prefers-reduced-motion: reduce)");
    const change = () => {setReduced(query.matches); if (query.matches) setPlaying(false);};
    query.addEventListener("change", change);
    return () => query.removeEventListener("change", change);
  }, []);
  useEffect(() => {
    if (!playing || reduced || active >= claims.length - 1) return;
    const timer = window.setTimeout(() => {
      setActive(sceneStep(active, claims.length, "next"));
      if (active + 1 >= claims.length - 1) setPlaying(false);
    }, 2200);
    return () => window.clearTimeout(timer);
  }, [playing, reduced, active, claims.length]);
  if (!claims.length) return null;
  const selected = claims[active] || claims[0];
  const art = story.section_art?.[`chapter-${index}-${scene.claim_ids[active]}`] ?? story.section_art?.[`chapter-${index}`];
  const example = scene.kind === "example" ? story.setup.first_run?.find(item => item.kind === "code_example") : undefined;
  const select = (index: number) => {setActive(index); setPlaying(false);};
  const move = (action: "previous" | "next" | "replay") => select(sceneStep(active, claims.length, action));
  return <section id={`chapter-${index}`} className="learn-shell learn-chapter" aria-label={scene.accessibility || scene.title}>
    <h2>{scene.title}</h2>
    <p className="learn-objective">{scene.objective}</p>
    {ordered && <p className="learn-note">Conceptual walkthrough. The order helps explain the idea.</p>}
    {scene.kind === "relationships" && <p className="learn-note">Conceptual relationships. See the import map for measured links.</p>}
    <div className="learn-section-layout" data-art={!!art} data-reverse={reverse}>
      <div className="learn-scene" data-kind={scene.kind} onKeyDown={event => {
        if (!ordered || !["ArrowLeft", "ArrowRight"].includes(event.key)) return;
        event.preventDefault(); move(event.key === "ArrowLeft" ? "previous" : "next");
      }}>
        {claims.length > 1 && <div className="learn-nodes" role="group" aria-label="Explore this scene">
          {claims.map((claim, i) => <button type="button" key={i} aria-pressed={active === i}
            onClick={() => select(i)}><span className="learn-dot" aria-hidden="true">{ordered ? i + 1 : ""}</span>{claim.label}</button>)}
        </div>}
        <div className={example ? "learn-example" : undefined}>
          <div>
            <div className="learn-caption" aria-live="polite" key={active}>
              <h3>{selected.label}</h3><p>{selected.text}</p>
            </div>
          </div>
          {example && <div className="learn-setup"><h3>Documented example</h3><pre><code>{example.text}</code></pre></div>}
        </div>
        {ordered && claims.length > 1 && <div className="learn-controls">
          <button type="button" disabled={active === 0} onClick={() => move("previous")}>Previous</button>
          <button type="button" disabled={active === claims.length - 1} onClick={() => move("next")}>Next</button>
          <button type="button" onClick={() => move("replay")}>Replay</button>
          {!reduced && <button type="button" onClick={() => {
            if (!playing && active === claims.length - 1) setActive(0);
            setPlaying(!playing);
          }}>{playing ? "Pause" : "Play"}</button>}
          <span>{active + 1} of {claims.length}</span>
        </div>}
      </div>
      {art && <SupportingArt key={art.asset} art={art} artwork={story.artwork ?? {}} />}
      <Sources key={active} ids={[...new Set([
        ...selected.evidence_ids, ...(example?.evidence_ids ?? []), ...(art?.evidence_ids ?? []),
      ])]} story={story} />
    </div>
  </section>;
}

const setupGroups = [["requirements", "Requirements"], ["install", "Install"], ["first_run", "First example"],
  ["expected_output", "Documented outcome"], ["gotchas", "Documented notes"]];

function Setup({ story, reverse }: {story: ProjectStory; reverse: boolean}) {
  const groups = setupGroups.filter(([key]) => story.setup[key]?.length);
  const [active, setActive] = useState(0);
  const [feedback, setFeedback] = useState("");
  const group = groups[active];
  const art = (group && story.section_art?.[`learn-setup-${group[0]}`]) ?? story.section_art?.["learn-setup"];
  return <section id="learn-setup" className="learn-shell learn-chapter">
    <h2>Getting started</h2>
    <div className="learn-section-layout" data-art={!!art} data-reverse={reverse}>
      <div>
        {!group ? <p>There were no startup instructions that could be matched to the repository sources.</p> : <>
          <div className="learn-controls" role="group" aria-label="Setup stages">{groups.map(([, title], index) =>
            <button type="button" aria-pressed={active === index} key={title} onClick={() => {setActive(index); setFeedback("");}}>{title}</button>)}</div>
          {story.setup[group[0]].map((item, index) => <div key={`${active}-${index}`} className="learn-setup learn-caption">
            {["code_example", "command", "expected_output"].includes(item.kind) ? <pre><code>{item.text}</code></pre> : <p>{item.text}</p>}
            {item.kind === "command" && <button type="button" onClick={async () => {
              try {await navigator.clipboard.writeText(item.text); setFeedback("Copied.");}
              catch {setFeedback("Select the command above to copy it.");}
            }}>Copy command</button>}
          </div>)}
          <p role="status">{feedback}</p>
        </>}
      </div>
      {art && <SupportingArt key={art.asset} art={art} artwork={story.artwork ?? {}} />}
      {(group || art) && <Sources key={active} story={story} ids={[...new Set([
        ...(group ? story.setup[group[0]].flatMap(item => item.evidence_ids) : []),
        ...(art?.evidence_ids ?? []),
      ])]} />}
    </div>
  </section>;
}

export function Story({ story, developer, hasMap }: { story: ProjectStory; developer: ReactNode; hasMap: boolean }) {
  const report = useRef<HTMLDivElement>(null);
  const purpose = Object.values(story.claims).find(claim => claim.section === "purpose");
  const behavior = story.behavior;
  const cover = story.cover;
  const hero = story.hero;
  const projectName = hero?.title ?? story.project.repo;
  const openingEvidence = [...new Set([...(purpose?.evidence_ids ?? []), ...(hero?.evidence_ids ?? cover?.evidence_ids ?? [])])];
  const highlights = Object.values(story.claims)
    .filter(claim => ["capability", "mechanism", "application"].includes(claim.section)).slice(0, 3);
  const mode = story.origin === "codex_skill" ? "Codex lesson · pinned evidence" :
    behavior ? "Generated lesson with source review" : {ai: "AI explanation · source locations checked", deterministic: "Deterministic preview · extracted context",
    synthetic_test: "Synthetic fixture · example model responses"}[story.mode];
  const sources = (ids: string[]) => <Sources ids={ids} story={story} />;
  const lesson = story.visual ? <VisualLesson plan={story.visual} sources={sources} /> :
    behavior?.family === "capacity" ? <CapacityLesson behavior={behavior} sources={sources} /> :
    behavior?.family === "request" ? <RequestLesson behavior={behavior} sources={sources} /> : null;
  const sections = story.lessons ?? [];
  const menu = (story.lesson_menu ?? []).flatMap(id => sections.filter(item => item.id === id));
  const menuIds = story.lesson_menu;
  const [selected, setSelected] = useState(() => window.location.hash.slice("#lesson-".length));
  const active = menu.find(item => item.id === selected) ?? menu[0];
  const intro = sections.find(item => item.id === story.intro_lesson);
  const firstSection = [...sections].sort((a, b) => a.after - b.after)
    .find(item => item.kind !== "guide" && item !== intro);
  const tryAnchor = firstSection ? lessonAnchor(firstSection.id) : lesson ? "learn-try" : null;
  const sourceArt = story.section_art?.["learn-source"];
  const renderLesson = (item: Lesson) =>
    <TeachingLesson key={item.id} lesson={item} artwork={story.artwork ?? {}} sources={sources}
      next={item === intro ? (menu.length ? "learn-lessons" : "learn-journey") : undefined} getExcerpt={id => {
      const source = story.evidence[id];
      const loc = source.location ?? source;
      return { path: loc.path ?? "", first: loc.line ?? 1, text: source.excerpt };
    }} />;
  const at = (chapter: number) => sections.filter(item => item.after === chapter && item !== intro &&
    !menuIds?.includes(item.id)).map(renderLesson);
  const hasArt = (key: string) => Object.keys(story.section_art ?? {}).some(id => id === key || id.startsWith(key + "-"));
  const artRows = story.scenes.map((_, i) => `chapter-${i}`).concat("learn-setup", "learn-source").filter(hasArt);
  const reverse = (key: string) => artRows.indexOf(key) % 2 === 1;
  const select = (id: string) => {
    const hash = "#" + lessonAnchor(id);
    if (window.location.hash !== hash) window.history.pushState(null, "", hash);
    setSelected(id);
  };
  useEffect(() => {document.title = `RepoLens · ${projectName}`;}, [projectName]);
  useEffect(() => {
    const target = document.getElementById(window.location.hash.slice(1));
    if (target && report.current?.contains(target)) target.scrollIntoView();
  }, []);
  useEffect(() => {
    const fromHash = () => {
      const hash = window.location.hash;
      const id = hash.startsWith("#lesson-") ? hash.slice("#lesson-".length) : "";
      if (menuIds?.includes(id)) {
        const missing = !document.getElementById(lessonAnchor(id));
        setSelected(id);
        if (missing) document.getElementById("learn-lessons")?.scrollIntoView();
      } else if (hash === "#learn-lessons" || hash === "#learn-journey") {
        setSelected("");
      }
    };
    window.addEventListener("hashchange", fromHash);
    return () => window.removeEventListener("hashchange", fromHash);
  }, [menuIds]);
  return <div className="learn studio" ref={report}>
    <header className="learn-header"><div className="learn-shell">
      <a href="#learn-top" className="learn-brand">RepoLens</a>
      <nav aria-label="Story navigation"><a href={menu.length ? "#learn-lessons" : "#learn-journey"}>Lessons</a>{tryAnchor && <a href={`#${tryAnchor}`}>Try It</a>}<a href="#learn-setup">Getting Started</a>
        <a href="#learn-source">Behind the Scenes</a></nav>
    </div></header>
    <main id="learn-top">
      <section className="learn-shell learn-hero" data-illustrated={!!(hero || cover)} data-loop={!!hero}>
        <div><p className="learn-kicker">{mode}</p><h1>{projectName}</h1>
          <p className="learn-lead">{purpose?.text ?? "Project purpose could not be established from the available evidence."}</p>
          <a className="learn-cta" href={intro ? `#${lessonAnchor(intro.id)}` : "#learn-journey"}>Explore the project</a>
        </div>
        {hero ? <LoopingHero hero={hero} artwork={story.artwork ?? {}} /> : cover ? <figure className="learn-cover">
          <img src={`data:image/jpeg;base64,${cover.data}`} alt={cover.alt} width={cover.width} height={cover.height} />
        </figure> : behavior?.family === "capacity" ? <CapacityCover behavior={behavior} /> :
          behavior?.family === "request" ? <RequestCover /> : <div className="learn-overview-art" aria-label="Concept overview">
          <div className="learn-center">{story.project.repo}</div>
          {highlights.length ? highlights.map((item, i) => <div className="learn-satellite" key={i}>{item.label}</div>) :
            <div className="learn-satellite">Source evidence</div>}
        </div>}
        {openingEvidence.length > 0 && <Sources story={story} ids={openingEvidence} />}
      </section>
      {intro && renderLesson(intro)}
      <div id="learn-journey">
        {active && <LessonMenu lessons={menu} story={story} active={active.id} select={select}>
          {renderLesson(active)}
        </LessonMenu>}
        {story.guide && <GuidedStory guide={story.guide} artwork={story.artwork ?? {}} sources={sources} tryAnchor={tryAnchor} />}
        {at(0)}
        {lesson && !story.scenes.length && lesson}
        {story.scenes.length ? story.scenes.map((scene, index) =>
          <Fragment key={index}>
            <SceneView scene={scene} story={story} index={index} reverse={reverse(`chapter-${index}`)} />
            {index === 0 && lesson}
            {at(index + 1)}
          </Fragment>) : !sections.length && !lesson && !story.guide &&
          <section className="learn-shell learn-chapter"><h2>What we could establish</h2><p>No cited story claims were available.</p></section>}
      </div>
      <Setup story={story} reverse={reverse("learn-setup")} />
      <section className="learn-shell learn-chapter" id="learn-source">
        <h2>Behind the scenes</h2>
        <div className="learn-section-layout" data-art={!!sourceArt} data-reverse={reverse("learn-source")}>
          <div>
            <p>Analyzed commit <code>{story.project.commit.short || story.project.commit.sha.slice(0, 7)}</code>.</p>
            {behavior?.generation.model && <p>Behavior draft model <code>{behavior.generation.model}</code>.</p>}
            <p>{behavior ? "The illustration follows the cited behavior. Added steps are marked in the walkthrough." :
              "Source checks verify excerpts and locations. AI wording may need independent review."}</p>
            {story.unknowns.length > 0 && <><h3>Unknowns and limits</h3><ul>{story.unknowns.map((item, i) => <li key={i}>{item}</li>)}</ul></>}
            <details><summary>Project understanding checklist</summary>
              <dl>{Object.entries(story.checklist).map(([key, value]) => <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{value}</dd></div>)}</dl>
            </details>
          </div>
          {sourceArt && <SupportingArt art={sourceArt} artwork={story.artwork ?? {}} />}
          {sourceArt && <Sources ids={sourceArt.evidence_ids} story={story} />}
        </div>
        <details className="learn-developer">
          <summary><span><strong>Developer report</strong>
            <small>{hasMap ? "Import map, source evidence, and recommended reading."
              : "Source evidence and recommended reading."}</small></span>
            <span className="learn-developer-indicator" aria-hidden="true"></span>
          </summary>
          <nav aria-label="Developer report sections">
            {hasMap && <a href="#map">Import map</a>}
            <a href="#reading">Reading guide</a><a href="#claims">Evidence and verification</a>
          </nav>
          {developer}
        </details>
      </section>
    </main>
  </div>;
}
