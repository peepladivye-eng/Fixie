# Backend Notes

Gemini = dev only; final recordings and eval must use LLM_PROVIDER=nebius

## Stage 2 / B2 Status
- `run_agent_loop` implemented in `app/agent/loop.py` as the single entry point.
- `app/agent/runner.py::run_agent` delegates to `run_agent_loop`.
- All tests in `test_agent.py` pass.
- B3 will wire full benchmark evaluation suite in `backend/eval/run_eval.py`.

## Failed Items (Encountered twice & skipped)
(None)
