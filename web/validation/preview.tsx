import { useState } from "react";
import { createRoot } from "react-dom/client";
import { StepControls } from "../src/print-studio/StoryMotion";
import "../src/style.css";
import "../src/print-studio/studio.css";
import "./routing.css";

const revision = "49943b5a94413a530761350f04e896f76e8d620e";
const source = `https://github.com/pallets/flask/blob/${revision}/`;
const steps = [
  { title: "Ask for /", words: "The browser asks the example app for its home page." },
  { title: "Match the address", words: "The route for / points to the hello_world function." },
  { title: "Return the greeting", words: "That function returns HTML. The browser can display its Hello, World! greeting." },
];

function RoutingFixture() {
  const [step, setStep] = useState(0);
  const current = steps[step];
  return <div className="studio">
    <header className="studio-header"><div className="studio-shell studio-nav">
      <span className="studio-brand">RepoLens / Validation</span>
      <a href="/print-studio">p-limit reference</a>
    </div></header>
    <main className="routing-fixture">
      <section className="studio-shell studio-chapter">
        <p className="studio-kicker">Flask · Routing proof of concept</p>
        <h1>What answers this address?</h1>
        <p>Follow one home-page request in Flask’s documented minimal example.</p>
        <ol className="routing-map">
          {steps.map((item, index) => <li key={item.title}>
            <button type="button" aria-pressed={index === step} onClick={() => setStep(index)}>
              <svg viewBox="0 0 110 65" aria-hidden="true">
                <rect x="6" y="6" width="98" height="53" rx="7" fill={["#e7dbf6", "#f8d8cb", "#d7efe1"][index]} stroke="#65435a" strokeWidth="2"/>
                <path d="M7 20h96" stroke="#65435a" strokeWidth="2"/>
                <text x="55" y="43" textAnchor="middle" fill="#41263d" fontSize="13" fontWeight="700">
                  {["GET /", "/ → hello_world", "Hello, World!"][index]}
                </text>
              </svg>
              {item.title}
            </button>
          </li>)}
        </ol>
        <p key={step} className="routing-caption story-enter" role="status">{current.words}</p>
        <StepControls active={step} count={steps.length} select={setStep} />
        <p>Conceptual view of a successful request. It omits server setup, hooks, errors, and response processing details. It runs no Flask code.</p>
        <p><a href={source + "docs/quickstart.rst#L11-L36"}>Documented example</a> ·{" "}
          <a href={source + "docs/lifecycle.rst#L109-L152"}>Request lifecycle</a> · <code>{revision.slice(0, 7)}</code></p>
      </section>
    </main>
  </div>;
}

createRoot(document.getElementById("root")!).render(<RoutingFixture />);
