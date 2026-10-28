# Core Subsystem Interfaces

This document defines language-neutral interface contracts for LLM providers, sandbox runtimes, external search, and code host integrations.
All external interactions MUST go through these abstractions.
Where real remote API details or SDK behaviors are pending verification with live credentials, they are marked with `TODO(VERIFY)`.

---

## 1. LLM Interface

Language-neutral specification for LLM completion and structured tool invocation across tiers (`lightning`, `super`, `ultra`).

### `LLM.chat(role: String, messages: List[ChatMessage], tools: Optional[List[ToolDefinition]], max_tokens: Optional[Integer]) -> ChatResponse`

#### Parameters:
- `role`: Logical model role / tier (e.g. `"lightning"` -> fast/small, `"super"` -> medium reasoning, `"ultra"` -> heavy frontier reasoning).
- `messages`: Chronological list of message objects:
  - `role`: `"system" | "user" | "assistant" | "tool"`
  - `content`: `String` or structured parts
  - `tool_call_id`: `Optional[String]` (for tool result messages)
- `tools`: Optional array of tool declarations:
  - `name`: `String`
  - `description`: `String`
  - `parameters`: JSON Schema `Object`
- `max_tokens`: Maximum tokens to generate in response.

#### Returns: `ChatResponse`
- `content`: `Optional[String]` - Generated text reply (null if only invoking tools).
- `tool_calls`: `List[ToolCall]` - List of tool calls requested:
  - `id`: `String`
  - `name`: `String`
  - `arguments`: `Object | String` (parsed JSON map)
- `usage`: `UsageRecord`
  - `model`: `String` (resolved concrete model name)
  - `input_tokens`: `Integer`
  - `output_tokens`: `Integer`
  - `cost_usd`: `Float`

> **Note**: Backends wrap Nebius Token Factory / NVIDIA NIM API endpoints.
> `TODO(VERIFY)`: Confirm exact Nebius OpenAI-compatible endpoint schema, base URLs, and exact model IDs once API credentials are provided.

---

## 2. Sandbox Interface

Language-neutral specification for execution sandboxes, speculative branching, file I/O, and execution state forks (e.g., Contree SDK / Docker / MicroVM).

### `Sandbox.open(source: String) -> SandboxSession`
Initializes a base sandbox environment populated with repository files, environment dependencies, and test harnesses corresponding to `source` (git URL, local repo path, or benchmark instance ID).

### `session.run(cmd: String, timeout_seconds: Optional[Integer]) -> CommandResult`
Executes a shell command inside the active sandbox session.

#### Returns: `CommandResult`
- `exit_code`: `Integer` (0 indicates success)
- `stdout`: `String`
- `stderr`: `String`
- `duration_seconds`: `Float`

### `session.checkpoint() -> CheckpointHandle`
Creates an immutable snapshot of the current filesystem and container state.

#### Returns: `CheckpointHandle`
- `id`: `String`
- `created_at`: `String` (ISO 8601 timestamp)

### `Sandbox.fork(checkpoint: CheckpointHandle, n: Integer) -> List[SandboxSession]`
Clones a checkpoint into `n` isolated sandbox sessions running in parallel for speculative patch generation and concurrent test execution.

#### Returns: `List[SandboxSession]`
- Array of `n` independent session handles.

### `session.read_file(path: String) -> String`
Reads text content of a file relative to repository root inside the sandbox. Throws `FileNotFoundError` if missing.

### `session.write_file(path: String, text: String) -> Void`
Writes text content to a relative path inside the sandbox, creating parent directories if needed.

> **Note**: Sandboxes are backed by contree-sdk / mock container runtimes during development.
> `TODO(VERIFY)`: Verify contree-sdk live connection parameters, warm container pool sizing, and fork latency once SDK documentation / credentials become available.

---

## 3. Search Interface

Language-neutral abstraction for web and documentation searches (e.g. Tavily / documentation search).

### `Search.query(query: String, max_results: Optional[Integer]) -> List[SearchResult]`
Searches web, bug trackers, and documentation for relevant error logs or library APIs.

#### Returns: `List[SearchResult]`
- `query`: `String`
- `title`: `String`
- `url`: `String`
- `content`: `String`

> `TODO(VERIFY)`: Verify Tavily API rate limits and response structure under hackathon free tiers.

---

## 4. GitHub / VCS Interface

Language-neutral abstraction for cloning issues, querying repo trees, and creating pull requests.

### `GitHub.fetch_issue(issue_url: String) -> IssueData`
- Returns: `title: String`, `body: String`, `repo: String`, `issue_number: Integer`

### `GitHub.create_pr(repo: String, branch: String, title: String, body: String, diff: String) -> PRResult`
- Returns: `pr_url: String`, `pr_number: Integer`

> `TODO(VERIFY)`: Verify GitHub Token permissions (read issues, write pull requests/forks) and mock fallback behavior when token is unset.
