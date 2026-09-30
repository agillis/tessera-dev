// ---- How far a new screen's installation is (app 0.4.32) ----
// The add-on runs ESPHome and hands the page its log; the browser flasher reports its own phase. Neither says "40 %",
// but both say enough to count: ESP-IDF's ninja numbers every step it builds ("[412/1024] Building C object ..."), and
// esptool prints how much it has written ("Writing at 0x00010000... (45 %)", ESPHome's "Uploading: [===   ] 45%").
// This turns that into the few steps a person follows, each with its own share of one bar. Nothing here guesses a
// time: a step without a count is simply running.

export type StepKey = "prepare" | "build" | "write" | "restart" | "done";
export type StepState = "waiting" | "running" | "done" | "failed";
export type Step = { key: StepKey; state: StepState; percent: number | null };
export type Progress = { steps: Step[]; percent: number; failed: boolean; done: boolean };

type Job = { state?: string; stage?: string; action?: string } | null | undefined;
type Flash = { phase: string; percent: number } | null | undefined;

/** The last "[n/m]" of ninja in the log, as a share of 1; null before the build counts. */
export function buildShare(logs: readonly string[]): number | null {
  for (let i = logs.length - 1; i >= 0; i--) {
    const found = /^\s*\[(\d+)\/(\d+)\]/.exec(logs[i]);
    if (found && Number(found[2]) > 0) return Math.min(1, Number(found[1]) / Number(found[2]));
  }
  return null;
}

/** How much of the image an upload over USB has written, from esptool's or ESPHome's own line; null before it writes. */
export function writeShare(logs: readonly string[]): number | null {
  for (let i = logs.length - 1; i >= 0; i--) {
    const line = logs[i];
    if (!/writing at|uploading|wrote /i.test(line)) continue;
    const found = /(\d{1,3}(?:\.\d+)?)\s*%/.exec(line);
    if (found) return Math.min(1, Number(found[1]) / 100);
    if (/^wrote /i.test(line.trim())) return 1;
  }
  return null;
}

// Each step's part of the one bar. Download has no writing: the build is the whole of it.
const SHARES: Record<"install" | "download", [StepKey, number][]> = {
  install: [["prepare", 0.08], ["build", 0.62], ["write", 0.25], ["restart", 0.05]],
  download: [["prepare", 0.08], ["build", 0.92]],
};

/**
 * The steps and the bar for a job of the add-on, and for this browser's own writing when it installs (`browser`).
 * `mode` "download" builds a file to download and stops there.
 */
export function installProgress(job: Job, logs: readonly string[], opts: { browser?: boolean; mode?: "install" | "download"; flash?: Flash } = {}): Progress {
  const mode = opts.mode ?? (opts.browser ? "install" : job?.action === "download" ? "download" : "install");
  const shares = SHARES[mode];
  const keys = shares.map(([key]) => key);
  const state = job?.state;
  const flash = opts.flash;
  const built = state === "success";
  const buildFailed = !!state && state !== "running" && state !== "success";
  const flashFailed = opts.browser && flash?.phase === "failed";
  const share = buildShare(logs);
  // Where the work stands, as the index of the step running now; the length of the list when all is done.
  let at = 0;
  let within: number | null = null;
  if (built && (!opts.browser || mode === "download")) at = keys.length;
  else if (built && opts.browser) {
    const phase = flash?.phase || "waiting";
    if (phase === "done") at = keys.length;
    else if (phase === "restarting") at = keys.indexOf("restart");
    else { at = keys.indexOf("write"); within = phase === "writing" ? (flash?.percent ?? 0) / 100 : phase === "erasing" ? 0 : null; }
  } else if (job?.stage === "upload") {
    at = keys.indexOf("write");
    within = writeShare(logs);
  } else if (share !== null) {
    at = keys.indexOf("build");
    within = share;
  }
  const failedAt = buildFailed || flashFailed ? Math.min(at, keys.length - 1) : -1;
  const steps: Step[] = shares.map(([key], index) => ({
    key,
    state: index === failedAt ? "failed" : index < at ? "done" : index === at ? (failedAt >= 0 ? "waiting" : "running") : "waiting",
    percent: index === at && within !== null ? Math.round(within * 100) : index < at ? 100 : null,
  }));
  let percent = 0;
  shares.forEach(([, part], index) => {
    if (index < at) percent += part;
    else if (index === at && within !== null) percent += part * within;
  });
  const done = at >= keys.length;
  return { steps: [...steps, { key: "done", state: done ? "done" : "waiting", percent: null }], percent: done ? 100 : Math.round(percent * 100), failed: failedAt >= 0, done };
}
