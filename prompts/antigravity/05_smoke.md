Branch: lane/smoke. Read /AGENTS.md. This lane writes ONE new file: backend/tools/smoke.py. The project owner runs
it with real keys; you must NOT run it and must not read, print or log .env or any key.

Write backend/tools/smoke.py (stdlib + httpx + contree-sdk; pin contree-sdk in a new
backend/requirements-smoke.txt, Python 3.12). It takes env LLM_PROVIDER=nvidia|nebius and
SANDBOX_PROVIDER=contree|none, and args --lightning, --super, --ultra (model ids; skip any not given).
1. List the provider's models and print only IDs containing "nemotron" (case-insensitive).
2. Make ONE tiny chat call (max_tokens=20) to each given model id. Print model, input and output tokens,
   latency, and any error text exactly. If the provider documents a reasoning-off parameter, try it once and print
   what happens.
3. If SANDBOX_PROVIDER=contree, using contree-sdk (read its official docs; do not guess method names):
   a) images.use("python:3.11-slim"); run `python -V`; print stdout and the resulting image/version id.
   b) test outbound network from inside the sandbox: `pip download --no-deps --dest /tmp six` and
      `git ls-remote https://github.com/pallets/click`; print exit codes.
   c) fork: from ONE result object run three different commands in parallel with asyncio.gather and print the three
      outputs and ids. If it raises, print the exact exception, then try three sessions started from the same
      image id and print that result too.
4. Print a final PASS/FAIL table per check. No retries beyond one. Total spend must stay under a few cents.
Mark every assumed SDK or API detail TODO(VERIFY) and say which official doc page you read.
Final message: the exact command lines the owner should run (PowerShell), and nothing else.
