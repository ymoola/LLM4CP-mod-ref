# CP Mod Web Deployment Guide

This product code lives entirely under `src/cpmod_web/`. The thesis benchmark under `src/mod-ref-benchmark/` stays unchanged.

## Production topology

- Frontend: Vercel
- Backend API: Railway
- Worker: Railway (separate process/service)
- Database/Auth/Storage: Supabase
- Code execution: E2B

## Supabase

Run all SQL migrations in order from `src/cpmod_web/supabase/migrations/`:

1. `001_initial_schema.sql`
2. `002_change_request_input_override.sql`
3. `003_change_request_optional_stability_note.sql`
4. `004_change_request_override_input_notes.sql`
5. `005_run_model_selection_and_user_credentials.sql`

Create the private storage buckets:

- `models`
- `artifacts`

## Backend environment (`CPMOD_WEB_*`)

Required:

- `CPMOD_WEB_APP_ENV=production`
- `CPMOD_WEB_SUPABASE_URL`
- `CPMOD_WEB_SUPABASE_SERVICE_ROLE_KEY`
- `CPMOD_WEB_SUPABASE_PUBLISHABLE_KEY`
- `CPMOD_WEB_CREDENTIAL_ENCRYPTION_SECRET`
- `CPMOD_WEB_BACKEND_BASE_URL`
- `CPMOD_WEB_FRONTEND_BASE_URL`
- `CPMOD_WEB_EXECUTION_BACKEND=e2b`
- `CPMOD_WEB_E2B_API_KEY`

Optional / recommended:

- `CPMOD_WEB_E2B_TEMPLATE`
- `CPMOD_WEB_MODELS_BUCKET=models`
- `CPMOD_WEB_ARTIFACTS_BUCKET=artifacts`
- `CPMOD_WEB_MAX_PLANNER_VALIDATION_LOOPS=5`
- `CPMOD_WEB_MAX_EXECUTION_LOOPS=5`
- `CPMOD_WEB_MAX_VALIDATOR_LOOPS=5`
- `CPMOD_WEB_EXECUTION_TIMEOUT_SECONDS=30`

Generate a strong encryption secret with something like:

```bash
python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
```

## Frontend environment

Required:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`
- `NEXT_PUBLIC_API_URL`

For Vercel, set the project root to `src/cpmod_web/frontend`.

## Railway setup

Create two Railway services that both point at this repository:

### API service

- Install command:

```bash
pip install -r src/cpmod_web/backend/requirements.txt
```

- Start command:

```bash
uvicorn cpmod_web.backend.main:app --host 0.0.0.0 --port $PORT --app-dir src
```

### Worker service

- Install command:

```bash
pip install -r src/cpmod_web/backend/requirements.txt
```

- Start command:

```bash
PYTHONPATH=src python -m cpmod_web.backend.worker
```

## Runtime checks

The backend exposes:

- `/health` - liveness
- `/ready` - configuration readiness

Use `/ready` after setting Railway env vars. It returns `503` until required production settings are present.

## E2B smoke test checklist

Before shipping, run one validated package through both development and production execution backends:

1. Upload a `build_model` package and confirm validation succeeds.
2. Upload a `script` package and confirm validation succeeds.
3. Launch one workflow run for each mode using saved provider keys.
4. Confirm the run produces:
   - generated model artifact
   - execution log
   - validator report
   - diff
5. Confirm timeout failures surface as `failed` with execution logs captured.

## Vercel / Railway handoff

- Frontend talks only to the FastAPI API URL.
- Backend talks to Supabase with the service-role key.
- Browser never sees provider API keys.
- Worker claims pending runs via the `claim_pending_run()` RPC and resumes clarification-safe state from Postgres.
