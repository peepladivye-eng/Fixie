Branch: lane/backend-foundation. Read /AGENTS.md, everything in /contracts, then backend/app/llm.py,
sandbox.py, main.py, replay.py, limits.py, store.py and backend/tests/ (only these).

You own backend/app/{llm.py,models.json,sandbox.py,main.py,replay.py,limits.py,store.py}, backend/tests/, and
scripts/. Do NOT touch backend/app/agent/, search.py, github.py, backend/eval/, contracts/ or frontend/. Zero
cost: nothing may call a real API; everything is tested on fakes. Mark unknown external APIs TODO(VERIFY).
Python 3.12; import root is backend/ (modules are app.*). Follow every hard rule in AGENTS.md.
After each stage run `python scripts/check.py`, fix once if red, commit, continue.

KNOWN PROBLEMS TO FIX (found in review)
- llm.py is synchronous httpx inside async code, so one model call would freeze the SSE stream.
- One LLM_MODEL env for all roles: no tier routing. No price table, no cost, no guards, no cache.
- Replay: replay.py silently falls back to a 4-event built-in stub, so the real 56-event
  replays/sample_run.jsonl is never served. GET /showcase returns DB rows instead of replays/showcase.json.
- POST /runs returns 200 (contract says 201); errors use FastAPI "detail" instead of {error, message}.
- The SSE stream closes on run.error, so clients never receive the following run.finished.
- Limiter counts are in memory; `emitters` is never cleaned; LIVE_ENABLED defaults on.

STAGE 1: LLM layer (app/llm.py + app/models.json)
 - Async only: httpx.AsyncClient. Keep the existing retry on 429/5xx and the tool-call text extraction.
 - LLM_PROVIDER=fake|cassette|nvidia|nebius, default fake. Base URLs (TODO(VERIFY)): nvidia
   https://integrate.api.nvidia.com/v1 with NVIDIA_API_KEY; nebius https://api.tokenfactory.nebius.com/v1/
   with NEBIUS_API_KEY.
 - models.json maps role -> tier (triage:lightning, reproduce:super, patch:super, patch_alt:lightning,
   diagnose:super, or ultra when USE_ULTRA=true) and tier -> model id PER PROVIDER (placeholder ids), prices per
   1M tokens (placeholders), per-role max_tokens (triage 600, reproduce 1200, patch 1500, diagnose 1200) and
   input caps in approximate tokens (6000, 8000, 10000, 8000; tokens = chars/4). Temperature 0. Reasoning off by
   default via a per-role flag (the provider's parameter name is TODO(VERIFY)).
 - API: `await llm.chat(role, messages, tools=None) -> ChatResult(text, tool_calls, model, tier, input_tokens,
   output_tokens, cost_usd, cached, latency_ms)`. Preflight refuses over-cap input, logs it, raises
   InputTooLarge. Fake provider returns deterministic canned JSON per role (reuse the existing canned answers).
 - SQLite response cache and cassette store (backend/cassettes/) keyed by sha256 of provider, model, messages,
   params. LLM_PROVIDER=cassette never touches the network and raises a clear error on a miss. Never store keys
   or headers. Cached calls have cost_usd 0 and cached=True.
 - Guards persisted in SQLite and surviving restarts: HARD_CAP_USD (Nebius dollars), CALL_CAP (NVIDIA calls),
   RUN_BUDGET_USD default 0.08. Exceeding raises BudgetExceeded(code) with code BUDGET_EXCEEDED or RUN_BUDGET.
 - Rename models.yaml references to models.json everywhere.
 Tests: cache hit costs zero; cassette record then replay; cassette miss errors; preflight refusal;
 RUN_BUDGET abort; HARD_CAP and CALL_CAP persist across a new process-level store instance.

STAGE 2: Sandbox interface (app/sandbox.py)
 - Define a Protocol: open(source), run(cmd, timeout), checkpoint(), fork(n), apply_diff(diff), read_file(path),
   write_file(path, text), close(). Keep LocalSandbox working. Add ContreeSandbox as a clearly marked stub
   (SANDBOX_PROVIDER=contree) that raises "not implemented, see smoke results". Select by SANDBOX_PROVIDER
   (default local). Add async wrappers that run blocking sandbox calls via asyncio.to_thread.
 Tests: fork isolation (editing one fork does not change another); parallel runs via gather.

STAGE 3: API fixes (main.py, replay.py, limits.py, store.py)
 - POST /runs -> 201 with {run_id}; all errors as JSON {error, message} with correct status codes.
 - `source` accepts fixture:<name>, instance:<id>, GitHub issue URL, and in replay mode a showcase id mapped to
   replays/<id>.jsonl (REPLAYS_DIR env overrides; path traversal impossible). A missing replay is a 404. Remove
   the silent fallback stub.
 - GET /showcase returns replays/showcase.json. GET /runs/{id} returns RunDetail from the contract without
   inline events. GET /eval/summary returns backend/eval/eval.json unchanged (404 JSON if missing).
 - SSE: after run.error, always deliver the following run.finished before closing. Clients reconnecting with
   Last-Event-ID past the end get a clean close, not an endless heartbeat. Remove finished emitters from memory.
 - Live: LIVE_ENABLED env default false. Per-IP and global daily counts persisted in SQLite. Return error code
   LIVE_PAUSED (429) when capped, LIVE_BUSY when concurrency is full.
 Tests: replay of the real sample_run.jsonl serves all 56 events in seq order and each validates with the schema
 logic from backend/tools/validate_events.py; showcase matches showcase.json; 201 and error shapes; run.finished
 follows run.error; LIVE_PAUSED at cap 1; live disabled by default.

STAGE 4: A fake-live contract test: start a fake live run in-process, collect its SSE events, and validate every
 event against contracts/events.schema.json (this fails today wherever model_tier is a model name; if it fails
 only because of fake_runner.py, fix fake_runner.py so it emits valid events).

ACCEPTANCE (paste real output): `python scripts/check.py` green; list the tests added; commit list. Final message:
what is done, what failed twice (also in NOTES.md), and every TODO(VERIFY).
