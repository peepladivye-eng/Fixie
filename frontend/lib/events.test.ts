import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  createInitialState,
  foldEvent,
  type FixieEvent,
  type BranchForkedEvent,
  type BranchResultEvent,
  type BranchCancelledEvent,
  type BranchWinnerEvent,
  type LlmUsageEvent,
  type RunErrorEvent,
  type RunFinishedEvent,
} from "./events";
import { ReplaySource } from "./source";

describe("foldEvent reducer", () => {
  it("handles branch.forked (fork)", () => {
    const s0 = createInitialState("run-1");
    const forkEvent: BranchForkedEvent = {
      run_id: "run-1", seq: 1, ts: "2026-10-28T08:00:01.000Z", type: "branch.forked",
      data: { branches: [{ id: "branch-A", strategy: "direct_dict_fix" }, { id: "branch-B", strategy: "constant_derivation" }] },
    };
    const s1 = foldEvent(s0, forkEvent);
    expect(Object.keys(s1.branches)).toEqual(["branch-A", "branch-B"]);
    expect(s1.branches["branch-A"]).toEqual({ id: "branch-A", strategy: "direct_dict_fix", status: "running", score: null, diff_lines: null, sandbox_seconds: null });
    expect(s1.branches["branch-B"].status).toBe("running");
  });

  it("handles pass, fail, and cancel", () => {
    let s = createInitialState("run-1");
    s = foldEvent(s, {
      run_id: "run-1", seq: 1, ts: "2026-10-28T08:00:01.000Z", type: "branch.forked",
      data: { branches: [{ id: "branch-A", strategy: "sA" }, { id: "branch-B", strategy: "sB" }, { id: "branch-C", strategy: "sC" }] },
    } as BranchForkedEvent);

    const passEvt: BranchResultEvent = {
      run_id: "run-1", seq: 2, ts: "2026-10-28T08:00:02.000Z", type: "branch.result",
      data: { branch_id: "branch-A", tests_passed: true, diff_lines: 3, sandbox_seconds: 4.2, score: 0.95 },
    };
    s = foldEvent(s, passEvt);
    expect(s.branches["branch-A"].status).toBe("passed");
    expect(s.branches["branch-A"].score).toBe(0.95);

    const failEvt: BranchResultEvent = {
      run_id: "run-1", seq: 3, ts: "2026-10-28T08:00:03.000Z", type: "branch.result",
      data: { branch_id: "branch-B", tests_passed: false, diff_lines: 12, sandbox_seconds: 5.1, score: 0.0 },
    };
    s = foldEvent(s, failEvt);
    expect(s.branches["branch-B"].status).toBe("failed");

    const cancelEvt: BranchCancelledEvent = {
      run_id: "run-1", seq: 4, ts: "2026-10-28T08:00:04.000Z", type: "branch.cancelled",
      data: { branch_id: "branch-C", reason: "budget cap exceeded" },
    };
    s = foldEvent(s, cancelEvt);
    expect(s.branches["branch-C"].status).toBe("cancelled");
    expect(s.branches["branch-C"].reason).toBe("budget cap exceeded");
  });

  it("handles branch.winner", () => {
    let s = createInitialState("run-1");
    expect(s.winner).toBeNull();
    const winnerEvt: BranchWinnerEvent = {
      run_id: "run-1", seq: 5, ts: "2026-10-28T08:00:05.000Z", type: "branch.winner", data: { branch_id: "branch-A" },
    };
    s = foldEvent(s, winnerEvt);
    expect(s.winner).toBe("branch-A");
  });

  it("counts cached usage as zero cost", () => {
    let s = createInitialState("run-1");
    const cachedUsage: LlmUsageEvent = {
      run_id: "run-1", seq: 2, ts: "2026-10-28T08:00:01.000Z", type: "llm.usage",
      data: { model: "meta-llama/Llama-3.1-8B-Instruct", input_tokens: 500, output_tokens: 100, cost_usd: 0.05, cached: true },
    };
    s = foldEvent(s, cachedUsage);
    expect(s.cost_total).toBe(0);
    expect(s.cost_by_tier.lightning).toBe(0);

    const nonCachedUsage: LlmUsageEvent = {
      run_id: "run-1", seq: 3, ts: "2026-10-28T08:00:02.000Z", type: "llm.usage",
      data: { model: "meta-llama/Llama-3.1-8B-Instruct", input_tokens: 500, output_tokens: 100, cost_usd: 0.0025, cached: false },
    };
    s = foldEvent(s, nonCachedUsage);
    expect(s.cost_total).toBe(0.0025);
    expect(s.cost_by_tier.lightning).toBe(0.0025);
  });

  it("handles run.error then run.finished", () => {
    let s = createInitialState("run-1");
    const errEvt: RunErrorEvent = {
      run_id: "run-1", seq: 10, ts: "2026-10-28T08:00:10.000Z", type: "run.error",
      data: { code: "TIMEOUT", message: "Sandbox container failed" },
    };
    s = foldEvent(s, errEvt);
    expect(s.status).toBe("error");
    expect(s.error).toEqual({ code: "TIMEOUT", message: "Sandbox container failed" });

    const finishedEvt: RunFinishedEvent = {
      run_id: "run-1", seq: 11, ts: "2026-10-28T08:00:11.000Z", type: "run.finished",
      data: { status: "failed", total_cost_usd: 0.015, total_seconds: 11.2 },
    };
    s = foldEvent(s, finishedEvt);
    expect(s.status).toBe("failed");
    expect(s.is_finished).toBe(true);
    expect(s.cost_total).toBe(0.015);
    expect(s.elapsed_seconds).toBe(11.2);
    expect(s.error).toEqual({ code: "TIMEOUT", message: "Sandbox container failed" });
  });

  it("ignores unknown event types without throwing", () => {
    const s0 = createInitialState("run-1");
    const s1 = foldEvent(s0, { run_id: "run-1", seq: 99, ts: "2026-10-28T08:00:12.000Z", type: "unknown.type", data: {} });
    expect(s1).toBe(s0);
  });

  it("reduces entire sample_run.jsonl cleanly", async () => {
    const fs = await import("node:fs");
    const path = await import("node:path");
    const filePath = path.resolve(__dirname, "../../replays/sample_run.jsonl");
    const lines = fs.readFileSync(filePath, "utf-8").split("\n").filter((l) => l.trim().length > 0);
    const events = lines.map((l) => JSON.parse(l) as FixieEvent);

    let state = createInitialState();
    for (const ev of events) state = foldEvent(state, ev);

    expect(state.run_id).toBe("run_20261028_parse_duration");
    expect(state.winner).toBe("branch-A");
    expect(state.steps.triage.status).toBe("completed");
    expect(state.steps.deliver.status).toBe("completed");
    expect(state.branches["branch-A"].status).toBe("passed");
    expect(state.branches["branch-C"].status).toBe("failed");
    expect(state.diff).toBeDefined();
    expect(state.is_finished).toBe(true);
    expect(state.cost_total).toBeGreaterThan(0);
  });
});

describe("ReplaySource playback & speed control", () => {
  beforeEach(() => { vi.useFakeTimers(); });
  afterEach(() => { vi.useRealTimers(); });

  it("plays events with speed change mid-play without skipping or repeating", () => {
    const events: FixieEvent[] = [
      { run_id: "r1", seq: 0, ts: "2026-10-28T08:00:00.000Z", type: "run.started", data: { issue_title: "T", repo: "o/r", mode: "replay" } },
      { run_id: "r1", seq: 1, ts: "2026-10-28T08:00:01.000Z", type: "step.started", data: { step: "triage", model_tier: "lightning" } },
      { run_id: "r1", seq: 2, ts: "2026-10-28T08:00:03.000Z", type: "step.finished", data: { step: "triage", duration_ms: 2000, ok: true } },
    ];
    const received: FixieEvent[] = [];
    let completed = false;
    const source = new ReplaySource("r1", { rawEvents: events });
    source.subscribe((ev) => received.push(ev), undefined, () => { completed = true; });

    expect(received.length).toBe(1);
    vi.advanceTimersByTime(500);
    expect(received.length).toBe(1);

    source.setSpeed(2);
    vi.advanceTimersByTime(250);
    expect(received.length).toBe(2);
    expect(received[1].seq).toBe(1);

    vi.advanceTimersByTime(1000);
    expect(received.length).toBe(3);
    expect(received[2].seq).toBe(2);
    expect(completed).toBe(true);
    expect(received.map((e) => e.seq)).toEqual([0, 1, 2]);
  });

  it("handles pause and resume cleanly", () => {
    const events: FixieEvent[] = [
      { run_id: "r1", seq: 0, ts: "2026-10-28T08:00:00.000Z", type: "run.started", data: { issue_title: "T", repo: "o/r", mode: "replay" } },
      { run_id: "r1", seq: 1, ts: "2026-10-28T08:00:02.000Z", type: "step.started", data: { step: "triage", model_tier: "lightning" } },
    ];
    const received: FixieEvent[] = [];
    const source = new ReplaySource("r1", { rawEvents: events });
    source.subscribe((ev) => received.push(ev));

    expect(received.length).toBe(1);
    vi.advanceTimersByTime(1000);
    source.pause();
    vi.advanceTimersByTime(5000);
    expect(received.length).toBe(1);

    source.resume();
    vi.advanceTimersByTime(999);
    expect(received.length).toBe(1);
    vi.advanceTimersByTime(1);
    expect(received.length).toBe(2);
  });
});
