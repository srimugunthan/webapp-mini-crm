# Phase 1: Foundation and scaffold

**Depends on:** None — can start immediately
**Status:** Implemented — see [phase report](../../docs/phase-reports/phase1.md)

## Design components touched

§2 Component boundaries, §6 Storage and migrations, §8 Security (loopback publish), §9 Deployment, ADR-001, ADR-002, ADR-003

## Objective

A running, containerised app skeleton: FastAPI with router/service/repository layering on SQLite, a migration runner with pre-migration backups, a React SPA shell served by FastAPI, and a Docker Compose setup bound to loopback. No domain features yet.

## Independently testable when

`docker compose up` starts the app; `GET /api/health` returns OK; the SPA shell loads at `http://127.0.0.1:8000` and displays the health status; the baseline migration is applied (`PRAGMA user_version` = 1); the pytest suite passes against a temporary SQLite file.

## Tasks

Each task is a thin vertical slice through every layer it touches, demoable or verifiable on its own. Design refs point to [system-design.md](../../system-design.md); PRD refs to [the PRD](../../linkedin-mini-crm-PRD.md).

### 1.1 Backend skeleton with health endpoint

- **Type:** AFK
- **Blocked by:** None
- **PRD reference:** FR-68, §12 NFR
- **System design reference:** §2, §6, §9

**Scope:** FastAPI app with routers/services/repositories packages, one short-lived sqlite3 connection per request (WAL, foreign keys on), `GET /api/health`, and a pytest fixture that gives each test a real temp SQLite file. Excludes migrations, the SPA and Docker.

**Acceptance criteria:**
- [x] `GET /api/health` returns 200 and fails when the DB file is unreadable
- [x] Connections have `foreign_keys=ON` and WAL mode (asserted in a test)
- [x] Layering holds: SQL appears only in repositories
- [x] Verifiable by running pytest

### 1.2 Migration runner with pre-migration backup

- **Type:** AFK
- **Blocked by:** 1.1
- **PRD reference:** §12 Reliability
- **System design reference:** §6, ADR-002

**Scope:** Numbered `.sql` files in `migrations/` applied at startup in a transaction, version in `PRAGMA user_version`; when a migration is pending, back up via the SQLite backup API into `db/backups/` and keep the last 5. Ships a baseline migration only; each later slice adds its own tables.

**Acceptance criteria:**
- [x] Pending migrations apply in order and bump `user_version`
- [x] A backup file is created before a pending migration and only the last 5 are kept
- [x] A failing migration rolls back and the app refuses to start (test with a bad fixture migration)
- [x] Verifiable with pytest

### 1.3 SPA shell served by FastAPI

- **Type:** AFK
- **Blocked by:** 1.1
- **PRD reference:** §13, FR-3x UI base
- **System design reference:** §2, §4, ADR-001

**Scope:** Vite + TypeScript + React Router + TanStack Query shell, TypeScript types generated from the OpenAPI schema, built `dist/` served by FastAPI with an `index.html` fallback; the shell calls `/api/health` and shows status.

**Acceptance criteria:**
- [x] Built SPA is served at `/` with client-side routes falling back to index.html
- [x] Generated API types compile against the OpenAPI schema
- [x] Health status renders in the shell
- [x] Demoable by running the backend with the built SPA

### 1.4 Docker image and Compose

- **Type:** AFK
- **Blocked by:** 1.3
- **PRD reference:** §12 Security, Portability
- **System design reference:** §8, §9, ADR-003

**Scope:** Multi-stage Dockerfile (Node builds SPA, Python with `uv sync` runs uvicorn, single worker, non-root user). Compose mounts `./db` and `./data`, publishes `127.0.0.1:8000:8000`, adds a healthcheck on `/api/health` and `restart: unless-stopped`.

**Acceptance criteria:**
- [ ] `docker compose up` serves the app on 127.0.0.1 only (not reachable on other interfaces)
- [ ] Container runs as non-root and healthcheck reports healthy
- [ ] The SQLite file persists on `./db` across `docker compose down`/`up`
- [ ] Verifiable manually

> Not verified: the Docker image was never built or run (daemon was down), so these boxes stay unticked.

### 1.5 Development start script

- **Type:** AFK
- **Blocked by:** 1.3
- **PRD reference:** §12 Portability ('one start command'), §13
- **System design reference:** §9 Develop (D32, D69)

**Scope:** `./start.sh` installs dependencies when missing, starts the backend with auto-reload on 127.0.0.1:8000 and the Vite dev server on 5173, and stops both on Ctrl+C. `./start.sh --built` builds the UI and serves everything from the backend on port 8000.

**Acceptance criteria:**
- [ ] Dev mode serves the UI on :5173 and proxies API calls to :8000
- [ ] Ctrl+C stops both processes
- [ ] `--built` serves the built UI and API from :8000
- [x] Script passes `bash -n`
