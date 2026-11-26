// Manually authored design-prototype copy for one pinned public repository.
export const printStudioScene = {
  repo: "p-limit",
  commit: "a8a6fbec4e0e866d6d779b10889bb4f5567e70eb",
  source: "https://github.com/sindresorhus/p-limit/blob/",
  purpose: "p-limit sets how many tasks can run at the same time.",
  scenes: [
    { title: "Jobs pile up.", caption: "Send a batch of jobs together. The extras wait their turn.", waiting: 4, running: 0, done: 0 },
    { title: "Two presses start.", caption: "With the limit set to two, only two jobs start. The rest wait.", waiting: 2, running: 2, done: 0 },
    { title: "One finishes. Another starts.", caption: "When a press is free, it can take the next waiting job.", waiting: 1, running: 2, done: 1 },
  ],
  evidence: [
    { kind: "Documentation", title: "Limit how many tasks run together", file: "readme.md", lines: "L3",
      description: "The README describes running asynchronous work with a concurrency limit." },
    { kind: "Source code", title: "Start a waiting task when there’s room", file: "index.js", lines: "L16-L25",
      description: "The code checks both the active count and whether the queue has work before starting the next task." },
    { kind: "Source code", title: "Release capacity when work settles", file: "index.js", lines: "L27-L47",
      description: "When a running task settles, the active count decreases and the queue is checked again." },
    { kind: "Source code", title: "Put newly submitted jobs into the queue", file: "index.js", lines: "L50-L63",
      description: "The submission path enqueues the job and tries to start it if the active count is below the limit." },
  ],
} as const;
