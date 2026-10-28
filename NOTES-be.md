# Backend Notes

Gemini = dev only; final recordings and eval must use LLM_PROVIDER=nebius

## Stage 2 / B2 Status
- `run_agent_loop` implemented in `app/agent/loop.py` as the single entry point.
- `app/agent/runner.py::run_agent` delegates to `run_agent_loop`.
- All tests in `test_agent.py` pass.

## Stage 3 / B3 Status
- `backend/tools/smoke.py`: Nebius default URL updated to `https://api.tokenfactory.nebius.com/v1/`; gemini added.
- `scripts/dev_run.py`: Created; refuses paid providers without `--allow-paid`; writes `replays/dev_<provider>_<fixture>.jsonl`.
- `backend/eval/run_eval.py`: Baseline+branching eval, grade_with_hidden_tests, 4-worker semaphore, resumable, synthetic flag.
- `backend/eval/instances.json`: 6 eval fixtures (csv_quotes, duration, overlap, pagination, slug_unicode, word_wrap).
- `test_cache_hit_costs_zero` is hermetic (uses tmp_path DB).
- All 49 tests pass.

## Failed Items (Encountered twice & skipped)
(None)
