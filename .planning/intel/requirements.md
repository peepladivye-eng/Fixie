# Product Requirements

## REQ-triage-ingest
- source: README.md
- description: Ingest bug reports from GitHub issue URLs or benchmark evaluation fixtures.
- acceptance: System extracts issue title, problem description, repository coordinates, and reproduces issue context without manual prompt craft.
- scope: issue ingestion, triage

## REQ-reproduction-sandbox
- source: README.md
- description: Launch an isolated container execution sandbox, run reproduction commands, and capture failure evidence.
- acceptance: Sandbox spins up with dependencies; reproduction command executes; compact test failure summary (test name, assertion, file:line) is recorded; if tests pass unexpectedly, abort early with NOT_REPRODUCED error.
- scope: sandbox lifecycle, reproduction verification

## REQ-speculative-branching
- source: README.md
- description: Snapshot the post-reproduction sandbox state and fork into multiple parallel candidate patch attempts.
- acceptance: Checkpoint created from post-reproduction state; K candidate branches (e.g. K=2 in Round 1, K=3 in Round 2) initialized with distinct patch prompt strategies (minimal, root-cause, defensive) and evaluated concurrently.
- scope: state checkpointing, speculative branching, candidate forks

## REQ-parallel-verification
- source: README.md
- description: Execute test suites across all branched sandboxes simultaneously.
- acceptance: All candidate sandboxes execute verification tests concurrently via asyncio.gather; stdout/stderr streams per branch; candidates failing tests are cancelled early when a clean candidate succeeds.
- scope: parallel testing, execution concurrency, task cancellation

## REQ-winner-selection-delivery
- source: README.md
- description: Deterministically score candidate patches, select the verified winner, and package unified diffs, test evidence, and PR delivery.
- acceptance: Scoring is deterministic code evaluating test pass status, regression failure counts, diff brevity, and sandbox execution duration; winner diff generated; PR opened on GitHub if configured.
- scope: deterministic scoring, diff delivery, github pr

## REQ-live-observability
- source: README.md
- description: Stream run lifecycle events in real-time into a dark-mode web dashboard.
- acceptance: Server-Sent Events (SSE) stream step progression (triage, reproduce, diagnose, branch, deliver), live terminal logs with stdout/stderr ANSI coloring, interactive @xyflow/react branch graph, and dollar/second cost meters.
- scope: real-time streaming, web UI, event timeline, branch tree visualization
