# CP Mod Web

Productized web-app scaffold for the thesis workflow.

This subtree intentionally leaves `src/mod-ref-benchmark` untouched. The backend copies and adapts the workflow concepts for a web product that supports authenticated uploads, change requests, workflow runs, and artifact inspection.

## Structure

- `backend/` FastAPI API, worker, product workflow, Supabase integration
- `frontend/` Next.js app for auth, projects, uploads, runs, and audit-trail viewing
- `supabase/` migration files for Postgres schema and RPCs
- `shared/` optional shared code/constants

## Environment

Frontend expects:
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`
- `NEXT_PUBLIC_API_URL`

Backend expects `CPMOD_WEB_*` variables such as:
- `CPMOD_WEB_SUPABASE_URL`
- `CPMOD_WEB_SUPABASE_SERVICE_ROLE_KEY`
- `CPMOD_WEB_OPENAI_API_KEY`
- `CPMOD_WEB_OPENROUTER_API_KEY`
- `CPMOD_WEB_E2B_API_KEY`

## Current state

This is an implementation scaffold intended to establish the product architecture and core contracts:
- strict model package upload contract
- DB-backed workflow runs and events
- E2B/local execution abstraction
- staged LangGraph workflow without thesis-specific unit tests
