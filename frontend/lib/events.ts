// Fixie event contracts and state reducer (strictly derived from contracts/events.schema.json)

export type StepName = "triage" | "reproduce" | "diagnose" | "branch" | "deliver";
export type ModelTier = "lightning" | "super" | "ultra" | "none";
export type StepStatus = "pending" | "running" | "completed" | "failed";
export type BranchStatus = "running" | "passed" | "failed" | "cancelled";
export type RunOverallStatus = "idle" | "running" | "success" | "failed" | "error";

export interface BaseEvent<TType extends string, TData> {
  run_id: string;
  seq: number;
  ts: string;
  type: TType;
  data: TData;
}

export type RunStartedEvent = BaseEvent<"run.started", { issue_title: string; repo: string; mode: "live" | "replay" }>;
export type StepStartedEvent = BaseEvent<"step.started", { step: StepName; model_tier: ModelTier }>;
export type StepFinishedEvent = BaseEvent<"step.finished", { step: StepName; duration_ms: number; ok: boolean }>;
export type LlmUsageEvent = BaseEvent<"llm.usage", { model: string; input_tokens: number; output_tokens: number; cost_usd: number; cached?: boolean }>;
export type TerminalChunkEvent = BaseEvent<"terminal.chunk", { stream: "stdout" | "stderr"; text: string; branch_id: string | null }>;
export type SearchResultEvent = BaseEvent<"search.result", { query: string; title: string; url: string; used: boolean }>;
export type BranchForkedEvent = BaseEvent<"branch.forked", { branches: Array<{ id: string; strategy: string }> }>;
export type BranchResultEvent = BaseEvent<"branch.result", { branch_id: string; tests_passed: boolean; diff_lines: number; sandbox_seconds: number; score: number }>;
export type BranchCancelledEvent = BaseEvent<"branch.cancelled", { branch_id: string; reason?: string }>;
export type BranchWinnerEvent = BaseEvent<"branch.winner", { branch_id: string }>;
export type DeliverReadyEvent = BaseEvent<"deliver.ready", { diff: string; root_cause: string; pr_url: string | null }>;
export type RunFinishedEvent = BaseEvent<"run.finished", { status: "success" | "failed"; total_cost_usd: number; total_seconds: number }>;
export type RunErrorEvent = BaseEvent<"run.error", { code: string; message: string }>;

export type FixieEvent =
  | RunStartedEvent | StepStartedEvent | StepFinishedEvent | LlmUsageEvent
  | TerminalChunkEvent | SearchResultEvent | BranchForkedEvent | BranchResultEvent
  | BranchCancelledEvent | BranchWinnerEvent | DeliverReadyEvent | RunFinishedEvent | RunErrorEvent;

export interface StepState {
  name: StepName;
  status: StepStatus;
  tier: ModelTier | null;
  duration_ms: number;
  duration: number;
  ok: boolean | null;
}

export interface TerminalLine {
  stream: "stdout" | "stderr";
  text: string;
  branch_id: string | null;
  ts: string;
}

export interface BranchState {
  id: string;
  strategy: string;
  status: BranchStatus;
  score: number | null;
  diff_lines: number | null;
  sandbox_seconds: number | null;
  reason?: string;
}

export interface SearchItem {
  query: string;
  title: string;
  url: string;
  used: boolean;
}

export interface RunError {
  code: string;
  message: string;
}

export interface RunState {
  run_id: string | null;
  issue_title: string | null;
  repo: string | null;
  mode: "live" | "replay" | null;
  status: RunOverallStatus;
  start_ts: string | null;
  elapsed_seconds: number;
  current_step: StepName | null;
  current_tier: ModelTier | null;
  steps: Record<StepName, StepState>;
  terminal: Record<string, TerminalLine[]>;
  branches: Record<string, BranchState>;
  winner: string | null;
  cost_total: number;
  cost_by_tier: Record<ModelTier, number>;
  /** Distinct model names seen in llm.usage events, in order of first appearance. */
  models_used: string[];
  searches: SearchItem[];
  diff: string | null;
  root_cause: string | null;
  pr_url: string | null;
  error: RunError | null;
  is_finished: boolean;
}

export const STEP_ORDER: StepName[] = ["triage", "reproduce", "diagnose", "branch", "deliver"];

export function createInitialState(runId: string | null = null): RunState {
  const mkStep = (name: StepName): StepState => ({ name, status: "pending", tier: null, duration_ms: 0, duration: 0, ok: null });
  return {
    run_id: runId,
    issue_title: null,
    repo: null,
    mode: null,
    status: "idle",
    start_ts: null,
    elapsed_seconds: 0,
    current_step: null,
    current_tier: null,
    steps: {
      triage: mkStep("triage"),
      reproduce: mkStep("reproduce"),
      diagnose: mkStep("diagnose"),
      branch: mkStep("branch"),
      deliver: mkStep("deliver"),
    },
    terminal: { null: [] },
    branches: {},
    winner: null,
    cost_total: 0,
    cost_by_tier: { lightning: 0, super: 0, ultra: 0, none: 0 },
    models_used: [],
    searches: [],
    diff: null,
    root_cause: null,
    pr_url: null,
    error: null,
    is_finished: false,
  };
}

export function inferTierFromModel(model: string, fallbackTier?: ModelTier | null): ModelTier {
  const m = model.toLowerCase();
  if (m.includes("8b") || m.includes("lightning")) return "lightning";
  if (m.includes("70b") || m.includes("super") || m.includes("nemotron")) return "super";
  if (m.includes("llama-3.3") || m.includes("ultra")) return "ultra";
  if (m.includes("none")) return "none";
  return fallbackTier || "lightning";
}

function updateElapsed(state: RunState, ts: string): number {
  if (state.is_finished) return state.elapsed_seconds;
  if (!state.start_ts) return 0;
  const t0 = new Date(state.start_ts).getTime();
  const t1 = new Date(ts).getTime();
  if (isNaN(t0) || isNaN(t1)) return state.elapsed_seconds;
  return Number(Math.max(state.elapsed_seconds, Math.max(0, (t1 - t0) / 1000)).toFixed(2));
}

export function foldEvent(state: RunState, event: unknown): RunState {
  if (!event || typeof event !== "object" || !("type" in event)) return state;

  const ev = event as FixieEvent;
  const baseStartTs = state.start_ts ?? (typeof ev.ts === "string" ? ev.ts : null);
  const nextElapsed = typeof ev.ts === "string" ? updateElapsed({ ...state, start_ts: baseStartTs }, ev.ts) : state.elapsed_seconds;
  const common = { start_ts: baseStartTs, elapsed_seconds: nextElapsed };

  switch (ev.type) {
    case "run.started":
      return { ...state, ...common, run_id: ev.run_id ?? state.run_id, issue_title: ev.data.issue_title, repo: ev.data.repo, mode: ev.data.mode, status: "running" };

    case "step.started": {
      const step = ev.data.step;
      return {
        ...state, ...common, status: "running", current_step: step, current_tier: ev.data.model_tier,
        steps: { ...state.steps, [step]: { ...state.steps[step], status: "running", tier: ev.data.model_tier } },
      };
    }

    case "step.finished": {
      const step = ev.data.step;
      return {
        ...state, ...common,
        steps: { ...state.steps, [step]: { ...state.steps[step], status: ev.data.ok ? "completed" : "failed", duration_ms: ev.data.duration_ms, duration: Number((ev.data.duration_ms / 1000).toFixed(2)), ok: ev.data.ok } },
      };
    }

    case "llm.usage": {
      const isCached = Boolean(ev.data.cached);
      const cost = isCached ? 0 : (ev.data.cost_usd ?? 0);
      const tier = inferTierFromModel(ev.data.model, state.current_tier);
      const modelName = ev.data.model;
      const models_used = state.models_used.includes(modelName)
        ? state.models_used
        : [...state.models_used, modelName];
      return {
        ...state, ...common,
        cost_total: Number((state.cost_total + cost).toFixed(6)),
        cost_by_tier: { ...state.cost_by_tier, [tier]: Number((state.cost_by_tier[tier] + cost).toFixed(6)) },
        models_used,
      };
    }

    case "terminal.chunk": {
      const k = ev.data.branch_id === null ? "null" : ev.data.branch_id;
      const line: TerminalLine = { stream: ev.data.stream, text: ev.data.text, branch_id: ev.data.branch_id, ts: ev.ts };
      return { ...state, ...common, terminal: { ...state.terminal, [k]: [...(state.terminal[k] ?? []), line] } };
    }

    case "search.result":
      return { ...state, ...common, searches: [...state.searches, { query: ev.data.query, title: ev.data.title, url: ev.data.url, used: ev.data.used }] };

    case "branch.forked": {
      const nextBranches = { ...state.branches };
      for (const b of ev.data.branches) {
        nextBranches[b.id] = { id: b.id, strategy: b.strategy, status: "running", score: null, diff_lines: null, sandbox_seconds: null };
      }
      return { ...state, ...common, branches: nextBranches };
    }

    case "branch.result": {
      const prev = state.branches[ev.data.branch_id] ?? { id: ev.data.branch_id, strategy: "", status: "running", score: null, diff_lines: null, sandbox_seconds: null };
      return {
        ...state, ...common,
        branches: { ...state.branches, [ev.data.branch_id]: { ...prev, status: ev.data.tests_passed ? "passed" : "failed", score: ev.data.score, diff_lines: ev.data.diff_lines, sandbox_seconds: ev.data.sandbox_seconds } },
      };
    }

    case "branch.cancelled": {
      const prev = state.branches[ev.data.branch_id] ?? { id: ev.data.branch_id, strategy: "", status: "running", score: null, diff_lines: null, sandbox_seconds: null };
      return {
        ...state, ...common,
        branches: { ...state.branches, [ev.data.branch_id]: { ...prev, status: "cancelled", reason: ev.data.reason } },
      };
    }

    case "branch.winner":
      return { ...state, ...common, winner: ev.data.branch_id };

    case "deliver.ready":
      return { ...state, ...common, diff: ev.data.diff, root_cause: ev.data.root_cause, pr_url: ev.data.pr_url };

    case "run.error":
      return { ...state, ...common, status: "error", error: { code: ev.data.code, message: ev.data.message } };

    case "run.finished":
      return { ...state, start_ts: baseStartTs, status: ev.data.status, is_finished: true, cost_total: ev.data.total_cost_usd, elapsed_seconds: ev.data.total_seconds };

    default:
      return state;
  }
}
