# ADR-003: Run in Docker with the port published on loopback only

**Status:** Accepted
**Date:** 2026-11-08
**Deciders:** Srimugunthan

---

## Context

The PRD (§12) requires binding to `127.0.0.1` with no authentication, because the app holds a private contact network. Choosing React (ADR-001) adds a Node build step, and the owner asked for uv for Python tooling and for Docker (Q10). Folder import (FR-2) reads `Connections.csv` from a folder on the machine where the backend runs, and the SQLite file must persist.

---

## Decision

We will make Docker Compose the supported run path, using a multi-stage Dockerfile (a Node stage builds the React app, a Python stage runs `uv sync` and uvicorn). uvicorn listens on `0.0.0.0` inside the container, but Compose publishes the port only as `127.0.0.1:8000:8000`, the container runs as a non-root user, and `./data` and `./db` are mounted from the host. A `/api/health` endpoint backs a Compose healthcheck, with `restart: unless-stopped`. Development uses native `uv run` plus the Vite dev server.

---

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Native `uv run` only | No Docker needed; binds `127.0.0.1` directly | Needs Node to build the UI at install time; per-OS setup differences |
| Plain `docker run`, no Compose | Fewer files | Long command with mounts and port flags; easy to get wrong |
| Separate frontend and backend containers | Mirrors a typical production layout | Extra proxy and image for a one-user tool |
| **Docker Compose, single image (chosen)** | One command; reproducible build; data stays on the host | Docker required; localhost guarantee depends on the port mapping |

---

## Consequences

**Positive:**
- One command (`docker compose up`) to build and run.
- Reproducible build including the React bundle.
- Data and uploaded-CSV copies stay on the host through volume mounts; backup is a host-side copy.

**Negative / Accepted Tradeoffs:**
- The localhost-only guarantee now depends on the Compose port mapping, not on the app binding. Changing it to `8000:8000` would expose contacts to the network.
- Saving copies of uploaded CSVs uses the mounted `./data` volume (container path `/data`); if it is missing or read-only, saving fails quietly and uploads still work.
- Docker must be installed on the host.

---

## Compliance / Risk Notes

- Privacy: no hosting beyond localhost until authentication exists (PRD §12, §17).
- The README must warn against changing the port mapping.

---

## Follow-up Actions

- [ ] Document the loopback port mapping and the mounts in the README.

---

## Implementation notes (2026-11-08)

The `Dockerfile` (multi-stage, non-root user, single worker, healthcheck on `/api/health`) and `docker-compose.yml` (`127.0.0.1:8000:8000`, `./db` and `./data` volumes, `restart: unless-stopped`) were written and `docker compose config` validates, but the image was **not built or run** because the Docker daemon was not running; verify it before relying on this ADR's consequences. For development, `./start.sh` runs the backend and the Vite dev server natively, both bound to 127.0.0.1 (decision 69). The decision itself is unchanged.

Update (2026-11-08): the folder import mentioned above was removed (decision 73); the `./data` mount now only receives copies of uploaded CSVs. On Linux a bind-mounted `./data` must be writable by the container's non-root user (uid 10001) for copies to be saved; otherwise a warning is logged.
