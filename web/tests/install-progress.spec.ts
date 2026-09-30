// How far a new screen's installation is (app 0.4.32): counted from ESPHome's own log and the browser flasher's phase,
// never guessed.
import { describe, expect, it } from "vitest";
import { buildShare, installProgress, writeShare } from "../src/model/install-progress";

const states = (p: ReturnType<typeof installProgress>) => p.steps.map((step) => `${step.key}:${step.state}${step.percent !== null ? `:${step.percent}` : ""}`);

describe("the steps of an installation", () => {
  it("reads ninja's count while it builds, and esptool's percentage while it writes", () => {
    expect(buildShare(["INFO Compiling app...", "[312/1184] Building C object a.c.obj", "[592/1184] Building C object b.c.obj"])).toBe(0.5);
    expect(buildShare(["INFO Reading configuration"])).toBeNull();
    expect(writeShare(["Connecting....", "Writing at 0x00064000... (58 %)"])).toBe(0.58);
    expect(writeShare(["Uploading: [=====     ] 45%"])).toBe(0.45);
    expect(writeShare(["Wrote 1581184 bytes"])).toBe(1);
    expect(writeShare(["Chip is ESP32-S3"])).toBeNull();
  });

  it("gets ready, builds and writes over USB on the Home Assistant machine, one bar for all of it", () => {
    const job = { state: "running", stage: "compile", action: "install" };
    expect(states(installProgress(job, ["INFO Reading configuration"]))).toEqual(["prepare:running", "build:waiting", "write:waiting", "restart:waiting", "done:waiting"]);
    const building = installProgress(job, ["[592/1184] Building"]);
    expect(states(building)).toEqual(["prepare:done:100", "build:running:50", "write:waiting", "restart:waiting", "done:waiting"]);
    expect(building.percent).toBe(39);
    const writing = installProgress({ ...job, stage: "upload" }, ["[1184/1184] Linking", "Writing at 0x1000... (40 %)"]);
    expect(states(writing)[2]).toBe("write:running:40");
    expect(writing.percent).toBe(80);
    const done = installProgress({ state: "success", stage: "upload", action: "install" }, ["Wrote 1 bytes"]);
    expect(done.done).toBe(true);
    expect(done.percent).toBe(100);
  });

  it("marks the step it stopped in when it fails, and keeps the rest waiting", () => {
    const failed = installProgress({ state: "failed", stage: "compile", action: "install" }, ["[980/1184] Building", "error: expected ;"]);
    expect(failed.failed).toBe(true);
    expect(states(failed)).toEqual(["prepare:done:100", "build:failed:83", "write:waiting", "restart:waiting", "done:waiting"]);
  });

  it("only builds for a download, and follows the browser's own writing when this computer installs", () => {
    expect(installProgress({ state: "running", stage: "compile", action: "download" }, ["[1/2] a"]).steps.map((s) => s.key)).toEqual(["prepare", "build", "done"]);
    const job = { state: "success", stage: "compile", action: "download" };
    expect(states(installProgress(job, [], { browser: true, flash: { phase: "writing", percent: 30 } }))[2]).toBe("write:running:30");
    expect(states(installProgress(job, [], { browser: true, flash: { phase: "restarting", percent: 100 } }))[3]).toBe("restart:running");
    expect(installProgress(job, [], { browser: true, flash: { phase: "done", percent: 100 } }).done).toBe(true);
    expect(installProgress(job, [], { browser: true, flash: { phase: "failed", percent: 12 } }).failed).toBe(true);
  });
});
