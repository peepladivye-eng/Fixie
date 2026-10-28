# Backend Notes

Gemini = dev only; final recordings and eval must use LLM_PROVIDER=nebius

## Tests Left for B2 (implementing run_agent_loop):
- `test_adaptive_k_and_max_rounds`: validates multi-round loop with adaptive K (K=2 in round 1, K=3 in round 2)
- `test_run_budget_abort_emits_error_and_finished`: validates loop abort and error event emission when spending budget is exceeded
- `test_full_fake_run_events_validate_against_schema`: validates complete end-to-end event stream from run_agent_loop against contract schema
