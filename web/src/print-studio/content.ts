// This hand-authored chapter model is independent of simulation and layout.
export type Chapter = {
  id: string;
  objective: string;
  plain: string;
  sources: readonly string[];
  visual: string;
  interaction?: string;
  takeaway: string;
  depth: "quick" | "essential" | "optional";
};

export const learningJourney: readonly Chapter[] = [
  {id: "overview", objective: "Identify the project and audience", plain: "p-limit is a JavaScript library for developers who want to control how many background tasks run at once.", sources: ["readme.md#L1-L5","readme.md#L13-L28"], visual: "Studio scene with a shared workbench", takeaway: "A program can start work in batches without starting everything together.", depth: "quick"},
  {id: "problem", objective: "Separate batch size from work happening now", plain: "A page might need to load six resources. Starting all six together can create more simultaneous work than you want.", sources: ["recipes.md#L19-L37","recipes.md#L116-L118"], visual: "Compare the same six-job batch at two limits", interaction: "Toggle the limit", takeaway: "The batch stays the same. The limit controls how many jobs it starts at once.", depth: "essential"},
  {id: "play", objective: "Understand how space frees up", plain: "Jobs wait until there is room. After a job settles, a waiting job can start.", sources: ["index.js#L16-L47","index.js#L50-L68"], visual: "Numbered tickets travel from inbox to press to finished tray", interaction: "Change the limit, play, pause or step", takeaway: "The waiting rack is the queue. A press represents capacity. The library doesn't create workers.", depth: "essential"},
  {id: "usage", objective: "Connect the metaphor to the real API", plain: "Choose a limit, hand the library functions to call later, and wait for results.", sources: ["readme.md#L13-L28","readme.md#L60-L68"], visual: "Three actions synchronized with the README example", interaction: "Select an action to highlight its JavaScript", takeaway: "Pass a function to the limiter so it can decide when the task starts.", depth: "essential"},
  {id: "capabilities", objective: "Recognize optional tools and boundaries", plain: "A program can watch the queue, change the limit, or discard work that hasn't started.", sources: ["readme.md#L46-L52","readme.md#L76-L119","readme.md#L171-L175","index.js#L32-L47"], visual: "Selectable API examples", interaction: "Reveal the effect and caveat for each operation", takeaway: "Clearing the queue cannot stop already running work.", depth: "optional"},
  {id: "applications", objective: "Choose a practical use", plain: "Use the same pattern to fetch URLs or process a folder of files.", sources: ["recipes.md#L3-L37"], visual: "Two batches with different inputs and outcomes", interaction: "Switch recipe", takeaway: "You decide the task; the limiter decides when to start it.", depth: "essential"},
  {id: "setup", objective: "Find the documented first steps", plain: "Install the package, import it, then submit your own functions.", sources: ["package.json#L13-L21","readme.md#L5-L28"], visual: "Three short setup steps", interaction: "Jump to the example", takeaway: "The README example uses placeholder functions; supply your own before running it.", depth: "essential"},
  {id: "source", objective: "Trace explanations to implementation", plain: "Read the queue and admission code or explore the static import map.", sources: ["index.js#L16-L68","index.js#L70-L127"], visual: "Direct evidence and technical section links", takeaway: "An import shows a dependency, while the queue code explains admission.", depth: "optional"},
];

export const usageCode = [
  "import pLimit from 'p-limit';", "", "const limit = pLimit(1);", "", "const input = [",
  "\tlimit(() => fetchSomething('foo')),", "\tlimit(() => fetchSomething('bar')),", "\tlimit(() => doSomething())",
  "];", "", "// Only one promise is run at once", "const result = await Promise.all(input);", "console.log(result);",
];
export const usage = [
  {title: "Set the limit", body: "The number 1 means only one task can run at a time.", lines: [3, 3]},
  {title: "Hand over three jobs", body: "Each arrow wraps a job so p-limit can start it when there is room.", lines: [5, 9]},
  {title: "Collect the results", body: "If all three jobs succeed, the program logs their results. The README leaves the job functions for you to supply.", lines: [11, 13]},
];
export const capabilities = [
  {label: "Watch the queue", api: "activeCount / pendingCount", plain: "Check how many tasks are running and how many are still waiting.", ref: "readme.md#L90-L96"},
  {label: "Change the limit", api: "limit.concurrency", plain: "Change how many tasks can start. Lowering the limit leaves current work running.", ref: "index.js#L91-L104"},
  {label: "Clear waiting jobs", api: "limit.clearQueue()", plain: "Discard queued work. Running jobs continue. Enable rejectOnClear if callers need discarded tasks to reject; otherwise their promises remain unsettled.", ref: "readme.md#L98-L107"},
  {label: "Process a collection", api: "limit.map(inputs, fn)", plain: "Apply a function to each input under the same limit. If reading the input fails, already scheduled jobs still run.", ref: "readme.md#L78-L88"},
  {label: "Limit one function", api: "limitFunction(fn, options)", plain: "Wrap a single function so repeated calls share their own limit.", ref: "readme.md#L113-L119"},
  {label: "Handle failure", api: "Promise.allSettled(…)", plain: "A failed job still frees capacity and the caller receives the rejection. The recipe shows how to collect successes and failures together.", ref: "recipes.md#L40-L74"},
];
export const recipes = [
  {title: "Fetch a list of URLs", inputs: ["URL 1","URL 2","URL 3","URL 4","URL 5"], work: "Fetch and decode JSON", outcome: "Collected API responses", ref: "recipes.md#L19-L37"},
  {title: "Process a folder of files", inputs: ["file","file","file"], work: "Read each file and parse JSON", outcome: "Parsed contents from the uploads folder", ref: "recipes.md#L3-L17"},
];

export const capabilityExamples = [
  ["Five tasks submitted at a limit of two.", "Read two active and three pending before any job completes."],
  ["Two running, three waiting. Raise the limit to three.", "One waiting job can start. Two are still waiting."],
  ["Two jobs running while three wait.", "Clear the queue and those three waiting jobs are discarded. The running jobs continue."],
  ["A collection of file paths.", "Give every file to the same operation while the limiter controls how many run."],
  ["One function called several times.", "The wrapped function has a single limit shared by those calls."],
  ["One request fails while another succeeds.", "Promise.allSettled reports the outcome of each request."],
] as const;
