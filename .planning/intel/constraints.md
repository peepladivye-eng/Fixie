# Technical Constraints & Interfaces

## SPEC-llm-interface
- source: contracts/interfaces.md
- type: api-contract
- content: LLM.chat(role: String, messages: List[ChatMessage], tools: Optional[List[ToolDefinition]], max_tokens: Optional[Integer]) -> ChatResponse. Supports logical tiers 'lightning', 'super', 'ultra'. Returns text, tool_calls, and usage (model, input_tokens, output_tokens, cost_usd). Must support fake, cassette, nvidia, and nebius providers with preflight input token caps.

## SPEC-sandbox-interface
- source: contracts/interfaces.md
- type: protocol
- content: Sandbox interface defines open(source) -> SandboxSession, session.run(cmd, timeout) -> CommandResult, session.checkpoint() -> CheckpointHandle, Sandbox.fork(checkpoint, n) -> List[SandboxSession], session.read_file(path), and session.write_file(path, text). LocalSandbox operates locally; ContreeSandbox is stubbed with contree-sdk pending live verification.

## SPEC-search-interface
- source: contracts/interfaces.md
- type: api-contract
- content: Search.query(query: String, max_results: Optional[Integer]) -> List[SearchResult] with fields query, title, url, content. Supports Tavily with disk/SQLite query caching and fake mock responses during offline testing.

## SPEC-github-interface
- source: contracts/interfaces.md
- type: api-contract
- content: GitHub.fetch_issue(issue_url: String) -> IssueData and GitHub.create_pr(repo: String, branch: String, title: String, body: String, diff: String) -> PRResult. Real calls gated behind GITHUB_TOKEN and OPEN_PR=true; mock fallback used offline.

## SPEC-events-schema
- source: contracts/events.schema.json
- type: schema
- content: Event streaming protocol requires strictly conforming JSON payloads. Step progression includes triage, reproduce, diagnose, branch, and deliver. model_tier must be lightning|super|ultra|none. Events include step.started, step.completed, terminal.chunk, branch.forked, branch.result, branch.winner, branch.cancelled, llm.usage, deliver.ready, run.finished, and run.error.

## SPEC-rest-openapi-contract
- source: contracts/openapi.yaml
- type: api-contract
- content: POST /runs returns 201 with {run_id}. Error responses use {error, message} structure. GET /runs/{id} returns RunDetail without inline events. GET /runs/{id}/events streams SSE events with Last-Event-ID resumption. GET /showcase returns replays/showcase.json. GET /eval/summary returns eval.json.

## SPEC-ui-run-view-architecture
- source: prompts/antigravity/01_ui_run_view.md
- type: nfr
- content: Three-column layout on desktop, tabs on mobile. Column 1: step timeline with aria-live polite announcements. Column 2: custom terminal with ANSI color support, branch tabs, sticky command header, and non-animated streaming lines. Column 3: @xyflow/react branch tree with animated state transitions (staggered spring on fork, green on pass, red on fail, dimmed on cancel, glowing accent on winner). Bottom bar contains animated dollar/second meters and tier cost breakdown.

## SPEC-ui-pages-architecture
- source: prompts/antigravity/02_ui_pages.md
- type: nfr
- content: Home page with URL input, 3 example chips, Replay/Live toggle, and showcase cards. Eval page with Recharts visualization comparing baseline vs branching resolve rate and cost per fix, per-instance table, and synthetic data warning badge. Dark mode theme only with CSS design tokens. Command palette (cmdk) for navigation.

## SPEC-backend-foundation-architecture
- source: prompts/antigravity/03_backend_foundation.md
- type: nfr
- content: Strictly asynchronous httpx client; role-to-tier model mapping via models.json; SQLite-backed response caching and cassette storage; persisted budget guards (HARD_CAP_USD, CALL_CAP, RUN_BUDGET_USD); async-wrapped sandbox operations; rate limiting and concurrency control for live streams.

## SPEC-agent-loop-architecture
- source: prompts/antigravity/04_backend_agent.md
- type: protocol
- content: Four-stage pipeline: Context selection using AST extraction and grep (hard-capped output), sandbox reproduction with early abort if passing, root-cause diagnosis with maximum 1 search query, and K-candidate parallel branching with deterministic scoring (reproduction pass, regression minimization, diff brevity, duration) and immediate task cancellation of competitors upon clean win.

## SPEC-smoke-test-protocol
- source: prompts/antigravity/05_smoke.md
- type: protocol
- content: Isolated smoke script backend/tools/smoke.py executed exclusively by repository owner with live keys. Validates Nemotron model connectivity on Nebius/NVIDIA, and contree-sdk container startup, outbound networking, and sandbox fork capability.
