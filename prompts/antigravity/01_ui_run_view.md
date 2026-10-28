Branch: lane/ui-run. Read /AGENTS.md and everything in /contracts first.

You are building the run view of Fixie. You own ONLY frontend/lib, frontend/components/run, frontend/app/run.
Do not edit contracts/, backend/, or any other frontend folder. Work from replays/sample_run.jsonl only; no backend
is needed. Follow every hard rule in AGENTS.md (no keys, no live APIs, colours only from frontend/styles/tokens.css,
pin dependencies exactly, files under ~300 lines, no plan documents, no browser tool until the final step).

BUILD
1. frontend/lib/events.ts: TypeScript types for every event in contracts/events.schema.json, including
   branch.cancelled {branch_id} and the optional `cached` boolean on llm.usage. Write a pure reducer
   foldEvent(state, event) -> state producing: steps (status, tier, duration), terminal lines keyed by
   branch_id|null, branches (id, strategy, status running|passed|failed|cancelled, score, diff_lines,
   sandbox_seconds), winner, cost total and per-tier split, elapsed seconds, searches, diff, root_cause, pr_url,
   error. Branch ids are arbitrary strings. Unknown event types are ignored, never throw. Add reducer unit tests
   (vitest, pinned) covering: fork, pass/fail/cancel, winner, cached usage counted as zero cost, run.error then
   run.finished.
2. frontend/lib/source.ts: a small interface { subscribe, pause, resume, setSpeed }.
   ReplaySource fetches /replays/<id>.jsonl and plays events at their original relative timing with speed
   1x/2x/4x and pause; changing speed mid-play must not skip or repeat events.
   LiveSource uses EventSource on NEXT_PUBLIC_API_URL + /runs/<id>/events, reconnects with Last-Event-ID, and
   falls back to a clear "unavailable" state when the URL is missing or GET /health says live_enabled is false.
   Treat run.error as terminal only after run.finished arrives or after a 3-second grace period.
3. frontend/scripts/copy-replays.mjs copies ../replays/*.jsonl and showcase.json into frontend/public/replays.
   Wire it to the "predev" and "prebuild" npm scripts.
4. Route /run/[id]. Desktop: three columns. Mobile: tabs.
   - Timeline (left): the 5 steps, tier badge (lightning/super/ultra/none), live status, duration; aria-live
     "polite" on status changes.
   - Terminal (centre): custom log component (NO xterm), ANSI colour support, stdout vs stderr colours, sticky
     header with the current command, branch filter tabs. Streamed lines append; never animate per line.
   - Branch tree (right): @xyflow/react. On branch.forked the nodes appear from a parent with a staggered spring;
     running nodes pulse softly; failed nodes fade with a red mark; passed nodes show green; cancelled nodes dim
     with a stop mark; on branch.winner one node glows once in the accent colour, then settles, and the rest dim.
   - Result panel: tabs Diff, Evidence, Root cause (search.result entries as citations), PR. Buttons "Copy patch"
     and "Open PR" (only when pr_url exists).
   - Fixed bottom meter: animated dollars and seconds counters and a segmented bar by tier; cached usage is free.
5. Use motion/react. Animate state changes only. Use layout animations for reflow. Honour prefers-reduced-motion.
   Visible focus rings; everything keyboard navigable.
6. States: loading skeleton, error with retry, run not found.

ACCEPTANCE (run and paste real output): reducer tests pass; `npm run lint` passes; `npm run build` passes. THEN,
exactly once, open /run/run_20261028_parse_duration with the browser tool, save screenshots of the finished
state at 1440px and 390px, and describe the fork-and-win animation in three sentences.
Final message: commits made, anything you could not finish, and any change you need in files you do not own.
