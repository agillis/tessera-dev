// Firmware & USB -> Stop (app 0.4.27): the button is there only while something runs, and the answer to the stop is
// what the page shows, so the log and the state are on screen without waiting for the next poll.
import { flushPromises, mount } from "@vue/test-utils";
import { readFileSync } from "node:fs";
import { afterEach, describe, expect, it, vi } from "vitest";
import FirmwareView from "../src/components/FirmwareView.vue";
import InstallerView from "../src/components/InstallerView.vue";
import { state } from "../src/store";

type Job = { file: string; action: string; state: string; started: number } | null;

// The add-on: /api/firmware says what the job is, a stop ends it and answers with that same status.
function addon(job: Job, stop: { error?: string } = {}) {
  const posted: string[] = [];
  const status = () => ({ available: true, ports: [], logs: job ? [`ESPHome: compile`] : [], wifi: { state: "ready" },
    boards: {}, downloads: [], taken: { nodes: [], friendly: [] }, profiles: [{ file: "hall.yaml" }], job });
  vi.stubGlobal("fetch", vi.fn(async (url: string, options: any = {}) => {
    const path = String(url);
    if (options.method === "POST" && path.endsWith("api/firmware/jobs/cancel")) {
      posted.push(path);
      if (stop.error) return new Response(JSON.stringify({ error: stop.error }), { status: 400 });
      job = job && { ...job, state: "interrupted" };
      return new Response(JSON.stringify({ ...status(), logs: ["ESPHome: compile", "Stopped: build"] }));
    }
    return new Response(JSON.stringify(status()));
  }));
  return posted;
}

afterEach(() => { vi.unstubAllGlobals(); state.toast = null; });

describe("stopping a build", () => {
  it("offers Stop only while a job runs, and shows what the stop answered", async () => {
    const posted = addon({ file: "hall.yaml", action: "build", state: "running", started: 7 });
    const view = mount(FirmwareView);
    await flushPromises();
    expect(view.find("#firmware-stop").exists()).toBe(true);
    expect(view.find("#firmware-build").attributes("disabled")).toBeDefined();
    await view.find("#firmware-stop").trigger("click");
    await flushPromises();
    expect(posted).toHaveLength(1);
    expect(view.find("#firmware-status").text()).toContain("interrupted");
    expect(view.find("#firmware-log").text()).toContain("Stopped: build");
    // The job is over: Stop goes away and the three buttons come back.
    expect(view.find("#firmware-stop").exists()).toBe(false);
    expect(view.find("#firmware-build").attributes("disabled")).toBeUndefined();
  });

  it("has no Stop when nothing runs", async () => {
    addon(null);
    const view = mount(FirmwareView);
    await flushPromises();
    expect(view.find("#firmware-stop").exists()).toBe(false);
    expect(view.find("#firmware-build").attributes("disabled")).toBeUndefined();
  });

  it("says what went wrong and leaves the job alone when the stop is refused", async () => {
    addon({ file: "hall.yaml", action: "build", state: "running", started: 7 },
          { error: "No build or installation is running." });
    const view = mount(FirmwareView);
    await flushPromises();
    await view.find("#firmware-stop").trigger("click");
    await flushPromises();
    expect(view.find("#firmware-status").text()).toContain("running");
    expect(state.toast?.message).toBe("No build or installation is running.");
  });
});

// New screen: the same Stop, on the build the wizard started. A stop is not a failure, so the card says so and the
// log stays shut; Retry builds the profile that was already written again.
describe("stopping a build in the New screen wizard", () => {
  const SHAPES = JSON.parse(readFileSync("../screen_manager/app/boards.json", "utf8"));
  const boards = { cyd: { ...SHAPES.cyd, ...SHAPES.cyd.catalog, orientations: SHAPES.cyd.orientations } };
  const flush = async () => { await flushPromises(); await new Promise((done) => setTimeout(done, 0)); await flushPromises(); };

  // The add-on: New screen writes the profile and starts the installation, and a stop ends it.
  function wizard() {
    const posted: string[] = [];
    let job: any = null;
    const status = () => ({ available: true, ports: ["/dev/ttyUSB0"], profiles: [], downloads: [], boards,
      wifi: { state: "ready" }, taken: { nodes: [], prefixes: [] }, logs: job ? ["ESPHome: compile"] : [], job });
    vi.stubGlobal("fetch", vi.fn(async (url: string, options: any = {}) => {
      const path = String(url);
      if (options.method === "POST" && path.endsWith("api/firmware/profiles")) {
        job = { file: "hall.yaml", action: "install", state: "running", started: 7 };
        return new Response(JSON.stringify({ file: "hall.yaml", api_key: "k", job }));
      }
      if (options.method === "POST" && path.endsWith("api/firmware/jobs/cancel")) {
        posted.push(path);
        job = { ...job, state: "interrupted" };
        return new Response(JSON.stringify(status()));
      }
      return new Response(JSON.stringify(status()));
    }));
    return posted;
  }

  it("stops the installation it started, and says stopped rather than failed", async () => {
    const posted = wizard();
    const view = mount(InstallerView);
    await flush();
    // The wizard's three steps (app 0.4.32): the board, the name, then the way in.
    await view.find("#setup-next").trigger("click");
    await view.find("#friendly_name").setValue("Hall");
    await view.find("#setup-next").trigger("click");
    await view.find('#install-target input[value="/dev/ttyUSB0"]').setValue();
    await view.find("#install-form").trigger("submit");
    await flush();
    expect(view.find("#progress-title").text()).toContain("Building");
    await view.find("#install-stop").trigger("click");
    await flush();
    expect(posted).toHaveLength(1);
    expect(view.find("#progress-title").text()).toBe("Build stopped");
    expect(view.find("#progress-detail").text()).toContain("Nothing was put on a screen");
    // The screen in the art wears a red badge for a failure (app 0.4.32); a stop earns none.
    expect(view.find(".device-art").classes()).not.toContain("failed");
    expect(view.find("#install-stop").exists()).toBe(false);
    expect(view.find("#install-retry").exists()).toBe(true);
    expect(view.find("#install-log-wrap").attributes("open")).toBeUndefined();
  });
});
