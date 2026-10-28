# Antigravity launch guide

Source of truth for rules is `AGENTS.md` at the repo root. Mirror it into Antigravity's rules mechanism by
creating a rules file that says only: "Read and follow /AGENTS.md before doing anything." (Where Antigravity
reads project rules from can differ by version; check its Customizations/Rules panel. Keep AGENTS.md as the one
real copy.)

## Before you launch
1. Everything is committed and pushed on `master` (consolidation, contracts CR-001, this bundle).
2. For each agent: create its branch from `master` first (`git switch -c lane/ui-run`) and open that branch.
3. One agent per prompt. Paste the whole prompt file as the first and only message. Do not chat back and forth;
   collect fixes and send one follow-up with exact error text.
4. If your build has a Fast vs Planning mode, use Fast and decline plan/walkthrough artifacts, because they burn
   quota. Use the strongest model only for prompt 04; a cheaper model is fine for 01, 02, 03.
5. If an agent stalls on quota, commit, then paste the SAME prompt into Cursor or Trae on the same branch.

## Launch order
| Step | Prompt | Branch | Runs |
|---|---|---|---|
| 1 | 01_ui_run_view.md | lane/ui-run | now, parallel |
| 1 | 02_ui_pages.md | lane/ui-pages | now, parallel |
| 1 | 03_backend_foundation.md | lane/backend-foundation | now, parallel |
| 2 | 05_smoke.md | lane/smoke | when keys exist, any time (owner runs it) |
| 3 | 04_backend_agent.md | lane/backend-agent | after 03 is merged; use Contree results from 05 if available |

Merge each branch to `master` yourself only after its acceptance output is green, in this order: 03, 01, 02, 04.
After every merge run `python scripts/check.py --frontend` and paste any failure to Claude.
