# EdgeAI Product API

FastAPI bridge for the Next.js control plane.

```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

The API only runs explicit allowlisted `edgeai` commands and never uses `shell=True`.
Job metadata and logs are stored in `outputs/jobs/<job_id>/`.
