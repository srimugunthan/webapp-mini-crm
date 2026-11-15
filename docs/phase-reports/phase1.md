# Phase 1 report: Foundation and scaffold

Spec: [phase1-foundation-scaffold.md](../../specs/linkedin-mini-crm-v1/phase1-foundation-scaffold.md) — tasks 1.1–1.4.

## Files touched (all new)
- Backend: `backend/pyproject.toml`, `.python-version`, `uv.lock`; `backend/app/{config,clock,errors,db,main,asgi,openapi}.py`;
  `backend/app/routers/{deps,health}.py`; `backend/migrations/001_baseline.sql`; `backend/tests/{conftest.py,test_phase1_foundation.py}`
- Frontend scaffold: `frontend/{package.json,tsconfig.json,vite.config.ts,index.html,playwright.config.ts}`,
  `frontend/src/{main.tsx,App.tsx,api.ts,types.ts,util.ts,styles.css,vite-env.d.ts,setupTests.ts,api-types.ts}`, `frontend/openapi.json`
- Packaging: `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `.gitignore`, `README.md`
- (`App.tsx`, `types.ts`, etc. grew in later phases; listed here where first created.)

## How to test by hand
**Start the app for manual testing** (once, reuse for later phases): `cd frontend && npm install && npm run build`, then `cd backend && uv sync && uv run uvicorn app.asgi:app` and open http://127.0.0.1:8000 (data goes to `./db/crm.sqlite`; delete that folder to start fresh). For live UI edits use `npm run dev` in `frontend/` and open http://localhost:5173.
1. Open the app: the top bar shows **● backend ok** (green) at the right. Stop the backend and wait up to 30 s: it turns **● backend down**.
2. Open http://127.0.0.1:8000/api/health → `{"status":"ok","schema_version":7}`.
3. Open http://127.0.0.1:8000/groups directly (a deep link): the SPA loads (client-side route fallback), not a 404.
4. Migration backup: after the app has run once, add a file `backend/migrations/008_x.sql` containing `CREATE TABLE x (a);`, restart, and see `db/backups/pre-migration-v7-*.sqlite`. Delete the file/table afterwards (or the `db` folder).
5. Docker (not tested by me): `docker compose up --build`; check `docker ps` shows `127.0.0.1:8000->8000`, then `docker compose ps` shows *healthy*.

## Testing done
- `uv run pytest tests/test_phase1_foundation.py` → **7 passed**: health OK / 503 when the DB is unusable; WAL + foreign keys on;
  migrations set `user_version` = 7; backup is made before a pending migration and only 5 are kept; failing migration rolls back
  (version stays, table not created) and raises; SPA fallback and static assets.
- Frontend `npm run build` (tsc + vite) passes; `npm run gen:api` works (needed TypeScript pinned to 5.9 for openapi-typescript).
- **Not done:** Docker build/run (daemon down); startup refusal of a half-migrated schema is only tested at the `migrate()` function level.

## Notes
- Each later slice adds its own migration (002 contacts … 007 bulk); there is no "create all tables" migration.
- Layering: routers → services → repositories (SQL only in `repositories/`).
