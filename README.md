# Fixie

Fixie reproduces a bug, forks several candidate patches in parallel working copies, runs the tests on each, and keeps the first verified fix. It streams the whole run as a timeline, terminal and branch view.

Built for the Nebius x NVIDIA Global AI Hackathon, Track 1 (Coding and Agentic Engineering).

## What is real
- Models: NVIDIA Nemotron 3 Super (nvidia/nemotron-3-super-120b-a12b) called through Nebius Token Factory (OpenAI-compatible API).
- Agent loop: triage, reproduce (runs the repo's failing test), diagnose (model), branch (parallel candidate patches applied as search/replace edits, tested, first passing wins), deliver (diff and root cause).
- Candidates run in isolated local working copies, not containers.
- Replay: saved real runs stream in the UI (frontend/public/replays).

## Limits (honest)
- Demo fixtures only (small Python projects in backend/eval/fixtures). GitHub issue URLs are not wired up.
- No pull request is opened; pr_url stays empty.
- The evaluation page holds placeholder numbers, not measured results.
- Tavily and Nebius Sandboxes are not used in the recorded run.
- Dollar costs shown use placeholder per-token rates, so treat them as estimates.

## Run it
Backend: set NEBIUS_API_KEY in your terminal (never in a file), then:
  $env:LLM_PROVIDER="nebius"; python scripts/dev_run.py parse_duration --allow-paid
Frontend: cd frontend; npm install; npm run dev, then open /run/dev_nebius_parse_duration

License: MIT
