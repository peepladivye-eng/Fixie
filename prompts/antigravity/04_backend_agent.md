Branch: lane/backend-agent (create from master AFTER lane/backend-foundation is merged).
Read /AGENTS.md, everything in /contracts, then backend/app/agent/runner.py, llm.py, sandbox.py, emitter.py and
backend/eval/run_eval.py (only these first).

You own backend/app/agent/, backend/app/search.py, backend/app/github.py and backend/eval/. Do NOT touch main.py,
llm.py, sandbox.py (read and call them), contracts/ or frontend/. Zero cost: all work runs on fake providers and is
tested offline. Use the strongest model you have. Follow every hard rule in AGENTS.md.
After each stage run `python scripts/check.py`, fix once if red, commit, continue.

WHAT THE PRODUCT MUST DO (and today does not)
The current runner/prompts send only the issue text to the model, never code or failing output; the reproduce
result is never used or checked; branches run sequentially with an identical prompt; the winner is chosen only
on visible tests; hidden tests are never run; model_tier is a model name; durations and costs are 0.

STAGE 1: context and steps (one module per step in app/agent/steps/)
 - app/agent/context.py: rank repo files by grep over terms from the issue and the failing output; extract
   relevant functions/classes with the ast module plus a few surrounding lines; hard-cap output at the role's
   input cap. Never dump whole files or the whole repo.
 - app/agent/output.py: truncate any tool output to its first 40 and last 60 lines and at most 4000 chars;
   parse `pytest -q --tb=short -x` failures in code into a compact summary (test name, assertion, file:line).
 - triage (lightning): return up to 8 likely files as short JSON. Stop with run.error code NO_RELEVANT_FILES if none.
 - reproduce: run the visible test command in the sandbox, checkpoint A. If the tests PASS, emit run.error code
   NOT_REPRODUCED and finish (early exit). Otherwise keep the compact failure summary and take checkpoint B.
 - diagnose: root-cause note from the summary + selected code. At most ONE search per run via app/search.py
   (cached by query on disk or SQLite), and only when the failure names a module or exception not present in the
   repo; emit search.result with used=true/false. Real Tavily call is a TODO(VERIFY) httpx version; fake by default.

STAGE 2: branch and score (the signature feature)
 - app/agent/scoring.py: a pure function, never a model call. Rules: the reproduction test must pass (else score
   0); then rank by fewer new failures, smaller diff, less sandbox time. Return a float in [0,1] plus the sort
   key. Unit-test ordering and ties.
 - app/agent/steps/branch.py: Round 1 uses K=2 (a `patch` candidate and a `patch_alt` candidate); if none passes,
   round 2 uses K=3 with three DIFFERENT strategy prompts (minimal, root-cause, defensive); max 2 rounds. An
   `options["showcase"]` flag forces K=3 in round 1. Fork from checkpoint B, validate and apply each candidate
   diff with the existing validate_diff, run the reproduction test plus the related tests, ALL candidates in
   parallel with asyncio.gather. Stream terminal.chunk per branch with branch_id. As soon as a candidate passes
   with no new failures, cancel the others (asyncio task cancellation) and emit branch.cancelled for each.
   Retries send only the failure summary and the previous diff, never the conversation. Emit branch.forked with the
   distinct strategy labels, branch.result for each finished branch, branch.winner for the best.
 - Patches must be unified diffs (or search/replace blocks converted to diffs in code), never whole files.

STAGE 3: loop and events (app/agent/loop.py replacing runner.py's orchestration)
 - Emit events exactly per contracts/events.schema.json: real model_tier (lightning|super|ultra|none, derived from
   llm tier, never a model name), real step durations, llm.usage with real cost_usd and cached, deliver.ready,
   run.finished with real totals. On BudgetExceeded emit run.error with its code then run.finished(failed).
 - deliver: diff, root-cause note, pr_url null unless GITHUB_TOKEN is set AND OPEN_PR=true (real call is a
   TODO(VERIFY) path; fake by default).
 - Keep fake_runner.py working for the API tests; make runner.run_agent the single entry point main.py imports.

STAGE 4: evaluation (backend/eval/run_eval.py)
 - baseline = K=1 retries only; branching = adaptive K. After each run, grade the winner against hidden_tests/
   copied ONLY at grading time into a FRESH copy of the original repo with the winner diff applied. "resolved"
   means hidden tests pass. The agent sandbox never contains hidden_tests/ or solution.patch.
 - Record resolved, rounds, cost_usd, seconds, per-model split, provider. Max 4 concurrent instances. Resume
   safely; skip an instance after two infrastructure errors. Output keeps the existing eval.json shape plus
   "provider"; `synthetic` stays true whenever any provider is fake.
 - Replace the TODO placeholders in instances.json with one entry per directory in backend/eval/fixtures
   (source "fixture:<name>").

TESTS (offline, all must pass): context selection includes the buggy function; truncation limits; compact failure
summary; NOT_REPRODUCED early exit; three candidates with a 0.2s fake delay each finish well under 0.6s total;
loser cancellation emits branch.cancelled; adaptive K (2 then 3); scoring order; max 2 rounds; RUN_BUDGET abort
emits run.error then run.finished; a full fake run's events all validate against the schema; eval grades with
hidden tests and never exposes them to the agent sandbox.

ACCEPTANCE (paste real output): `python scripts/check.py` green; one full fake run printed as a short event-type
timeline; commit list. Final message: what is done, what failed twice (also NOTES.md), every TODO(VERIFY).
