import { useState } from "react";

export function StoryTicket({ id = 1 }: { id?: number }) {
  return <span className="story-ticket" data-identity={id}>{String(id).padStart(2, "0")}</span>;
}

export function TicketStrip({ count, labels, move, taskLabel = "Task" }: {
  count: number; labels: readonly string[]; move: number; taskLabel?: string;
}) {
  return <div className="story-ticket-strip" data-move={move}>
    {Array.from({length: count}, (_, i) => <span key={i} className="story-ticket-stop">
      <span className="story-ticket" data-identity={i + 1}>{String(i + 1).padStart(2, "0")}</span>
      <small>{taskLabel} {i + 1} · {labels[i]}</small>
    </span>)}
  </div>;
}

export function StepControls({ active, count, select }: {active: number; count: number; select: (index: number) => void}) {
  return <div className="story-step-controls" aria-label="Walkthrough controls">
    <button type="button" className="studio-button ghost" disabled={active === 0} onClick={() => select(active - 1)}>Back</button>
    <button type="button" className="studio-button filled" onClick={() => select(active === count - 1 ? 0 : active + 1)}>
      {active === count - 1 ? "Replay walkthrough" : "Next"}
    </button>
  </div>;
}

export function CopyCommand({ command }: {command: string}) {
  const [message, setMessage] = useState("");
  async function copy() {
    try {
      await navigator.clipboard.writeText(command);
      setMessage("Copied.");
    } catch {
      setMessage("Select the command to copy it.");
    }
  }
  return <><button type="button" className="studio-button ghost" onClick={copy}>Copy command</button> <span role="status">{message}</span></>;
}
