# Project Context & Operational Background

## Hackathon Context & Track Objectives
- source: README.md
- Built for the Nebius x NVIDIA Global AI Hackathon, Track 1: Coding and Agentic Engineering.
- Fixie demonstrates an end-to-end autonomous agent workflow combining reproduction sandboxes, speculative branching, parallel candidate evaluation, and live SSE observability.

## Agent Guidelines & Collaboration Rules
- source: AGENTS.md
- Single source of truth for repository rules is AGENTS.md.
- Agents operate on dedicated lane branches and do not touch unowned files.
- Testing verification is driven centrally via `python scripts/check.py` and `python scripts/check.py --frontend`.
- Changes to frozen contracts require formal requests logged in `contracts/CHANGE_REQUESTS.md`.

## Multi-Agent Launch Order & Execution Flow
- source: prompts/antigravity/README.md
- Step 1: Concurrent launch of UI Run View (`lane/ui-run`), UI Pages (`lane/ui-pages`), and Backend Foundation (`lane/backend-foundation`).
- Step 2: Smoke test runner (`lane/smoke`) executed by owner with live credentials.
- Step 3: Backend Agent (`lane/backend-agent`) executed after Backend Foundation is merged.
- Final integration verified through in-process clients and `scripts/check.py`.
