# Follow-up needed

Job B is restricted to the backend API paths, so it cannot modify the root README. Add this section when the repository owner permits a README edit:

```powershell
# From backend
$env:FIXIE_FORCE_FAKE_RUNNER='1'
..\.venv\Scripts\python -m uvicorn app.main:app --reload
curl.exe http://127.0.0.1:8000/health
curl.exe -X POST http://127.0.0.1:8000/runs -H "Content-Type: application/json" -d "{\"source\":\"demo\",\"mode\":\"live\"}"
curl.exe -N http://127.0.0.1:8000/runs/RUN_ID/events
curl.exe -X POST http://127.0.0.1:8000/runs -H "Content-Type: application/json" -d "{\"source\":\"sample.jsonl\",\"mode\":\"replay\"}"
curl.exe -N -H "Last-Event-ID: 2" http://127.0.0.1:8000/runs/RUN_ID/events
curl.exe http://127.0.0.1:8000/runs/RUN_ID
curl.exe http://127.0.0.1:8000/showcase
curl.exe http://127.0.0.1:8000/eval/summary
```
