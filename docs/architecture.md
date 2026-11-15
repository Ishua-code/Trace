# TRACE architecture

## Overview
TRACE links audit non-conformances (NCs) across departments and checks
whether closing one is safe, using a scoring engine over the NC history.

## Components
- **API**: FastAPI app in `api/`, deployed on Vercel (function region
  Tokyo, hnd1). Entry point `api/index.py` imports `app.main:app`.
- **Database**: Supabase Postgres (Tokyo), reached through the transaction
  pooler (port 6543). Schema managed by Alembic (`api/migrations`).
- **Engine**: `api/app/engine` (Hanu). Pure logic behind the `TraceEngine`
  protocol in `contracts.py`. It talks to storage only through the `NCStore`
  interface.
- **Store**: `PostgresStore` (`pg_store.py`) implements `NCStore` on Postgres.
  `InMemoryStore` is used by seed, tests and eval.
- **Seed and eval**: `api/seed` generates synthetic demo data (labelled
  synthetic). `api/eval` holds CV folds and metrics.
- **Web UI**: Next.js app (Harish), calling the API via `NEXT_PUBLIC_API_URL`.

## Data flow
UI -> FastAPI routers -> services -> engine / PostgresStore -> Supabase.
Events are written to a hash-chained `event_log` (prev_hash, hash).

## Demo reset
`POST /api/admin/reset-demo` truncates all tables and reloads the seed
bundle (about 3 s on Vercel).

## Configuration
See `api/.env.example`. Secrets live in `api/.env` locally and in Vercel
environment variables. Never commit them.