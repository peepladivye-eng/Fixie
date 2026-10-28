# Fixie Core

Fixie is a zero-cost local orchestration core for the Nebius x NVIDIA Global AI
Hackathon. It accepts a GitHub issue payload, reproduces it in a sandbox, forks
candidate fixes, evaluates candidates concurrently, selects a winner, and emits
an evidence bundle plus a draft pull-request payload.

It uses deterministic fake providers by default: no network calls, API keys, or
paid services are needed. The production Contree adapter is intentionally thin
and imports `contree_sdk` only when one of its methods is called.

## Run

```powershell
.\.venv\Scripts\python -m unittest discover -s tests -v
.\.venv\Scripts\python -m fixie --issue examples\issue.json --output artifacts
```

The second command writes `evidence.json`, `winner.diff`, and `pull-request.json`
to the output directory. All commands must be run through `.\.venv\Scripts\python`.

## Provider boundary

`fixie.providers` defines the interfaces used by the orchestrator. Fake providers
are the default implementation. `ContreeSandbox` contains TODO(VERIFY) boundaries
until the actual Contree SDK contract is confirmed; it is never selected by default.
