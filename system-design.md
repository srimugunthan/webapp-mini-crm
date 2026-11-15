# System Design: LinkedIn Mini CRM

> Derived from PRD: [linkedin-mini-crm-PRD.md](linkedin-mini-crm-PRD.md) (v0.2). Every decision below was either
> stated by the PRD or settled through a grilling session with Srimugunthan, and is recorded in
> [decision-log.md](decision-log.md) (decision numbers appear as `D#`). **Revised 2026-11-08** to match the built v1 and later changes (decisions D60–D72); see the decision log for what changed and why. Endpoint names that the PRD does not list
> are proposed names for settled behavior and are marked "(new)".

## 1. Overview

LinkedIn Mini CRM is a private, single-user web app that runs on the owner's machine in Docker. It imports the LinkedIn connections export (by upload; a copy of every uploaded CSV is kept in the data folder), lets the user organize contacts into groups, and tracks last visited and last messaged dates. Groups can have a stage pipeline applied from a reusable template, or none. A React single-page app talks to a FastAPI backend that stores everything in one SQLite file. It covers PRD goals G1–G7 and requirements FR-1 to FR-72 (FR-2, FR-3, FR-62 and FR-63 were dropped).

## 2. Component Boundaries

```
  Browser (127.0.0.1:8000 only)
  +------------------------------------------------------------+
  |  React SPA (TypeScript, Vite, TanStack Query, Router)      |
  |  Contacts | Groups | Group page (table/board) | Import     |
  +----------------------+-------------------------------------+
                         | JSON (/api/*)        links: GET /go/{id}
                         v
  Docker container (non-root)  - uvicorn, 1 worker, 0.0.0.0 inside
  +------------------------------------------------------------+
  |  FastAPI                                                   |
  |   routers   (HTTP only: parse, validate, status codes)     |
  |      |                                                     |
  |   services  (rules, transactions: import, stages,          |
  |      |       bulk-stage, visits, pipelines, backup)        |
  |      |                                                     |
  |   repositories (parameterized SQL, sqlite3)                |
  |      |                                                     |
  |   static files: built SPA (dist/) + index.html fallback    |
  +------+-----------------------------+-----------------------+
         |                             |
   volume ./db                    volume ./data
   crm.sqlite (+ -wal/-shm,       Connections.csv
   backups/)                      copies of uploaded CSVs
```

- **React SPA**: all screens and client state (D7, D25–D29). It is static files, so it needs no Node at run time.
- **Routers**: HTTP only, so services can be tested without HTTP (D43).
- **Services**: own business rules and transaction boundaries (import, stage moves, bulk stage with staging tokens, pipelines, visits, backup) (D43).
- **Repositories**: the only place SQL is written (D20, D43).
- **SQLite file + volumes**: one database file on a host-mounted volume; the data folder is a second mount (D30) where copies of uploaded CSVs are written (D73).

## 3. Data Model

Entities follow PRD §7, plus pipeline templates (D35, D36) and bulk staging (D33). Timestamps are integer epoch seconds in UTC (D12), except `connected_on`, a `YYYY-MM-DD` text date (D47).

```
contacts            groups              group_members (PK group_id, contact_id)
-----------------   ----------------    ------------------------------------
id                  id                  group_id, contact_id
first_name          name (unique)       stage_id (nullable)  <- null if the
last_name           created_at                                   group has no pipeline
company                                 stage_changed_at
position            stages (per group)  next_follow_up_at
linkedin_url        ----------------    added_at
 (unique, normal-   id, group_id
 ized, D48)         name, position      stage_history
email               is_final            ------------------------------------
connected_on        UNIQUE(group,name)  id, group_id, contact_id
last_visited_at                         from_stage_id, to_stage_id
last_messaged_at    pipeline_templates  changed_at, source (manual|bulk)
created_at,         ----------------    batch_id (nullable), note
updated_at          id, name (new)
                    pipeline_template_  notes: id, contact_id, body, created_at
notes               stages (new)
                    ----------------    bulk_staging (new)
                    template_id, name,  ------------------------------------
                    position, is_final  token, group_id, stage_id (optional),
                                        rows_json, created_at (expires 30 min)
```

Ownership and key relationships:
- A **contact** owns visit and message timestamps, so they are the same from every group (FR-30).
- A **membership** owns stage, stage-change time and follow-up date, so one person can be at different stages in different groups.
- A **group owns its own stages**. A **template** is a separate saved list; applying it copies stages into the group, and the two are never linked afterward ([ADR-004](docs/adr/ADR-004-copy-on-apply-pipeline-templates.md), D35). Deleting a template never touches groups.
- A group may have no stages; its members then have a null stage (D39).
- **Foreign keys are on**; deleting a group removes its memberships and stages but never contacts (FR-23).

As built, beyond the sketch above (D60, D61):
- `groups.pipeline_epoch` (integer) is bumped whenever a group's pipeline changes structurally (apply a template, remove the pipeline, delete a stage). It is what lets bulk undo refuse safely (section 5.4).
- `stage_history` also stores `from_stage_name` / `to_stage_name` (so history survives stage deletion; the stage id columns are `ON DELETE SET NULL`) and `added_to_group` (marks members a bulk batch added).
- `bulk_batches (batch_id, group_id, epoch, created_at, undone_at)` records each applied bulk batch and the pipeline epoch it ran under. `bulk_staging` also keeps `problems_json` and `counts_json`.
- Migrations are `001_baseline` (empty) to `007_bulk`; each feature adds only its own tables.

## 4. Interfaces / APIs

JSON under `/api`, owned by FastAPI routers. Response models are Pydantic; TypeScript types are generated from the OpenAPI schema; errors use `{ "detail": ... }` (D44). Endpoints from PRD §10 are unchanged unless noted.

| Area | Endpoints |
|---|---|
| Import | `POST /api/import` (25 MB cap, D55; `mode=add` default, or `mode=fresh&confirm=RESET`, D75; optional `group=Name` puts everyone in the file into that group, created if missing, D80), `GET /api/import/stats`. The folder-import endpoint was removed (D73). `POST /api/restore/preview` and `POST /api/restore?confirm=RESTORE` replace the database from an uploaded `.sqlite` backup (D76). |
| Contacts | `GET /api/contacts` (boolean search in `q`, `company`, `position`, `group`, plus filters, sort, offset paging ~100, D11, D22, D79), `GET /api/contacts/ids` (ids of every contact matching the filters, for "select all N matching", D65), `POST /api/contacts/{id}/messaged`, `POST /api/contacts/messaged-bulk` (several ids), `GET /api/contacts/{id}`, `GET/POST /api/contacts/{id}/notes` |
| Visits | `GET /go/{contact_id}` (302, https LinkedIn hosts only; skips the update on prefetch headers, D23). There is no pending-visits endpoint and no return prompt: those were removed (D62, supersedes D24). |
| Groups | `GET/POST /api/groups` (create takes optional template id), `PATCH/DELETE /api/groups/{id}` |
| Members | `GET/POST /api/groups/{id}/members`, `DELETE /api/groups/{id}/members/{cid}`, `PATCH /api/groups/{id}/members/{cid}`, `GET /api/groups/{id}/stage-counts`, `POST /api/groups/{id}/members/csv` (add from a CSV with a URL column; `apply=false` previews, `apply=true` adds; D64). The board loads all members in one request (D46). |
| Stages | `GET/POST /api/groups/{id}/stages`, `PATCH/DELETE /api/stages/{id}` |
| Pipelines (new) | `GET/POST /api/pipelines` (templates; a group's stages can be saved as a template), `PATCH/DELETE /api/pipelines/{id}`, `POST /api/groups/{id}/pipeline` (apply a template, with preview), `DELETE /api/groups/{id}/pipeline` (remove, with confirmation) |
| Bulk stage | `POST /api/groups/{id}/bulk-stage?preview=true` returns counts and a **token**; `POST /api/groups/{id}/bulk-stage` applies by token; `POST /api/groups/{id}/bulk-stage/undo` (D10, D33, D34) |
| Export, backup, ops | `GET /api/export` (all contacts, `group_id`, `ids=1,2,3`, or the same filters as the contacts list, D65), `GET /api/backup` (download, via SQLite backup API, D49), `GET /api/health` (D57) |

Contract rules: unknown stage names are matched within the group, case-insensitive; the CSV `Stage` column overrides the chosen stage (D16). Every LinkedIn link in the UI points to `/go/{id}`, never directly to LinkedIn (FR-26).

## 5. Data Flow

### 5.1 Visit tracking (D23; the return prompt of D24 was removed, D62)

```
 Click link (new tab) --> GET /go/42
                            |-- stored URL host must be https linkedin.com
                            |-- prefetch header? --> skip update
                            |-- else UPDATE contacts SET last_visited_at = now
                            v
                       302 --> linkedin.com profile
```

Visits are counted on the server, so middle-click and open-in-new-tab work without JavaScript. The page refetches its list shortly after a click so "last visited" updates without a reload. Last messaged is only ever set by the user (per-row button, past-date picker, or the selection bar's bulk action); nothing prompts for it.

### 5.2 Import (FR-4 to FR-11, FR-72, D48, D55, D73)

```
 Upload (<= 25 MB)   -> copy saved to /data/import-add|import-fresh-<time>-<name>.csv (best effort, D73)
        |
        v
 service.import(bytes): find header row by column names
        |
 BEGIN
   for each row: normalize URL (ADR-005)
        no URL    -> skipped list
        exists    -> UPDATE name/company/position/email/connected_on
        new       -> INSERT contact
 COMMIT (or ROLLBACK on any error: nothing changes)
        v
 summary: new / updated / skipped / errors
```

**Optional group** (D80): when `group` is given, the same transaction also finds or creates the group (case-insensitive name; a new group has no pipeline) and adds every person in the file with a valid URL, new or already known, as a member (first stage if the group has a pipeline); the response carries `group: {id, name, created, added, already_members}`. A failed import therefore creates no group and no memberships.

In **add mode** groups, memberships, stages, notes, last visited and last messaged are never touched; contacts missing from the file are kept (D17).

**Fresh mode** (D75) needs `confirm=RESET`. Order of events: parse the file (a bad file stops here, nothing deleted) -> write a backup to `db/backups/pre-fresh-import-*.sqlite` (last 5 kept) -> in ONE transaction delete `groups` (cascades members, stages, history, staging, batches) and `contacts` (cascades notes) and `pipeline_templates` (cascades template stages), re-create the default Starter template as migration 006 seeds it, then insert the file's rows -> commit. Any error rolls the whole thing back, templates included. This makes a fresh import a complete reset (D77).

### 5.3 Stage move (FR-43)

```
 dropdown / next / back / drag --> PATCH /api/groups/{gid}/members/{cid} {stage_id}
        BEGIN
         set group_members.stage_id, stage_changed_at = now
         insert stage_history (source = manual, optional note)
        COMMIT --> UI row updates; chip counts refetched
```

### 5.4 Bulk set stage (D10, D33, D34)

```
 Bulk set stage (CSV + stage)
     |
     v
 POST ...bulk-stage?preview=true
   match URLs (normalized) --> classify each row:
     in group, other stage -> will move      | in group, same stage -> no change
     contact, not in group -> will be added  | no contact -> skipped
     unknown stage name    -> skipped
   store parsed rows in bulk_staging (token, 30 min, single use)
     |
     v  counts shown (+ downloadable problem rows)
 POST ...bulk-stage {token}
   BEGIN
     re-classify the staged rows
     counts differ from preview? -> ROLLBACK, ask user to re-preview
     set stage, add missing members, write history rows with batch_id
     delete the token
   COMMIT
```

Only stage is replaced; notes, last visited, last messaged and follow-up dates never change. Undo restores the previous stages for the last un-undone batch and removes members the batch added (FR-60). It is refused with a message if the group's `pipeline_epoch` differs from the one recorded when the batch ran, i.e. the pipeline was applied, removed or had a stage deleted since (D60).

### 5.5 Applying or changing a pipeline (D38, D40, D53, D54)

```
 Create group --> pipeline dropdown (starter preselected, "No pipeline" available)
 Apply template to existing group --> preview:
     members with no stage       -> moved to the first stage
     members with a stage        -> mapped to same-named stage (case-insensitive);
                                    unmatched need a stage chosen in the preview
 Confirm --> copy template stages into the group, update memberships, write history
 Remove pipeline --> confirm "N members lose their stage" --> stages cleared, history kept
```

### 5.6 Adding people to a group (FR-17, FR-20, FR-69, FR-70; D64, D65)

```
 Contacts list: tick rows (or "Select all N matching" -> GET /api/contacts/ids)
      -> POST /api/groups/{id}/members {contact_ids}          (idempotent, one transaction)

 Group page "Add members" / create-group form with a CSV:
      CSV (URL column) -> POST /api/groups/{id}/members/csv?apply=false   preview:
          match by normalized URL (ADR-005)  -> to_add / already_members / not_found (+ problem rows)
      confirm -> POST ...?apply=true  -> same matching, then add_members()  (one transaction)
```

No contacts are created; unmatched URLs are only reported. New members of a group with a pipeline start at its first stage; in a group without one their stage is null. The preview is stateless: apply re-reads the file, so there is no token.

## 6. Storage & Persistence

- **One SQLite file** on the `./db` volume (D20, D30). Foreign keys on, WAL mode, one worker, one short-lived connection per request (D21, D42).
- **Migrations**: numbered `.sql` files in `migrations/`, applied at startup in a transaction with the version in `PRAGMA user_version`. If one is pending, the app first backs up the database with SQLite's backup API into `db/backups/` and keeps the last 5 ([ADR-002](docs/adr/ADR-002-raw-sqlite3-sql-migrations.md), D41, D56).
- **Restore** (D76): an uploaded `.sqlite` is written to a temp file next to the database and validated (SQLite header, `integrity_check`, `app_meta.created_by = linkedin-mini-crm`, schema version 4 to latest; a newer version is refused). The current database is first backed up to `db/backups/pre-restore-*.sqlite` (last 5 kept). The swap is `source.backup(live_connection)`, which is atomic for the destination, so a failure leaves current data intact; an older backup is then upgraded by running the pending migrations. Limit 500 MB.
- **Backup**: a "Download backup" action and a CLI command use the backup API for a consistent single file. Copying files by hand is documented only with the app stopped (D49).
- **Staging rows** live in `bulk_staging` and are purged when used, or on the next preview or apply after expiry (D33, D34).
- **Uploaded CSV copies** (D73): every uploaded CSV (`import`, `group-members`, `bulk-stage`) is also written to the data folder as `<kind>-<YYYYMMDD-HHMMSS>-<sanitised name>.csv`, never overwriting a file; best effort, so a write failure is logged and the request still succeeds.
- **Retention**: contacts and history are kept indefinitely. Nothing is deleted automatically except expired staging rows and backups beyond the last 5. Uploaded CSV copies also accumulate until the user deletes them.
- **Search**: case-insensitive `LIKE` (no FTS index, D22). Since D79 the search, company, position and group inputs are parsed as boolean queries by `backend/app/search.py` (a small recursive-descent parser: OR < AND < NOT, parentheses, quoted phrases, `field:term`) that compiles to a parameterised SQL condition; terms are bound parameters with `%`/`_` escaped, so user text is never interpolated. Group terms compile to `EXISTS (... group_members JOIN groups ... name LIKE ?)`, so `NOT` also matches contacts in no group. Syntax errors raise a 400 with a plain message. `/api/contacts`, `/api/contacts/ids` and `/api/export` share the same filter code.

## 7. Non-Functional Requirements

| Area | Target | Notes |
|---|---|---|
| Performance | Contacts and group pages under 1 s at 10,000 contacts; import of 10,000 rows under 10 s; bulk preview of 1,000 rows under 3 s | From PRD §12. Offset paging (~100 rows) and `LIKE` search are expected to meet this on local SQLite. Measured on a laptop with synthetic data (D72): 10,000-row import 0.30 s, contacts list/search about 0.012 s, 1,000-row bulk preview 0.03 s. Real-data timing is still unmeasured. |
| Scale | One user, up to a few thousand connections (tested to 10,000) | PRD §4 |
| Availability | Local app; container restarts automatically (`restart: unless-stopped`) and has a health check (D57) | No uptime target |
| Reliability | Import, stage move, bulk apply and migrations are transactional; concurrent edits are last-write-wins (D58) | History records every change |
| Portability | macOS, Windows, Linux with Docker | One command: `docker compose up` |
| Accessibility | Keyboard-operable controls (headless components); board drag has a dropdown alternative (D27, D28) | |

## 8. Security & Compliance

- **Boundary**: no authentication. The only protection is that the port is published on `127.0.0.1` only, with uvicorn on `0.0.0.0` inside the container and a non-root user. The README warns against changing the mapping, and hosting beyond localhost requires adding auth first ([ADR-003](docs/adr/ADR-003-docker-loopback-publish.md), D31, D18).
- **Redirects**: `/go/{id}` redirects only to https `linkedin.com` or `www.linkedin.com` (FR-29, [ADR-005](docs/adr/ADR-005-linkedin-url-normalization-key.md)).
- **Injection and uploads**: all SQL is parameterized; uploaded CSVs are parsed as data only; uploads over 25 MB are rejected (D55).
- **Privacy**: data stays on the user's machine; no analytics, telemetry or third-party calls at run time.
- **Compliance**: uses only the user's own official LinkedIn export; no scraping or automation of LinkedIn.
- **Sensitivity**: contact names, companies, positions, emails and notes are personal data about third parties; protect the `./db` folder, backups and the uploaded CSV copies in `./data` accordingly.

## 9. Deployment & Operability

- **Ship**: a multi-stage Dockerfile (Node builds the React app, Python runs `uv sync` and uvicorn). Compose mounts `./data` and `./db`, publishes `127.0.0.1:8000:8000`, and adds the health check and restart policy (D30, D31, D57).
- **Develop**: native `uv run` for the backend plus the Vite dev server (D32). `./start.sh` starts both (dev mode, with auto-reload) or `./start.sh --built` serves the built UI from the backend alone (D69).
- **Observe**: logs go to stdout (`docker compose logs`), with no telemetry. Import and bulk errors appear in the UI summary, and failed transactions are logged with the row number (D50).
- **Rollback**: a bad deploy is undone by running the previous image. A failed migration is covered by the automatic pre-migration backup (D56). A bad bulk update is undone with "Undo last bulk change". A bad import is undone by restoring a backup.
- **Tests**: pytest against a real temporary SQLite file per test with fixture CSVs (preamble, BOM, quoting, non-Latin names) for parsing, URL normalization, upsert, stage-move and bulk flows, and the `/go/{id}` redirect. Frontend: Vitest with React Testing Library plus Playwright flows against the real backend on a throwaway database (D29, D59; currently 5 flows).

## 10. Failure Modes

| Dependency / event | Behavior |
|---|---|
| Uploaded file lacks the expected columns | Clear error; nothing changes (FR-4, FR-9); the file is still kept in the data folder |
| Import or bulk apply fails midway | Transaction rolls back; no partial data (FR-9, FR-58) |
| Stale bulk preview (data changed) or expired token | Apply aborts and asks the user to re-preview (D34) |
| Migration fails at startup | Backup taken first; the app does not start with a half-migrated schema (D41, D56) |
| SQLite file volume missing or read-only | Hard dependency: the app fails its health check and logs the error |
| Data folder not mounted, missing or read-only | Saving the copy of an upload fails quietly (a warning is logged); the upload itself still works (D73) |
| LinkedIn unreachable or a profile has changed | Not a dependency: `/go/{id}` records the visit and redirects regardless |
| Link prefetch | Detected prefetch requests skip the visit update; undetectable ones can still count (known limit, D23) |
| Two tabs edit the same member | Last write wins; history shows both changes (D58) |
| Docker port mapping changed to non-loopback | Contacts exposed on the network; guarded only by documentation (ADR-003) |

## 11. Open Risks / Deferred Decisions

Settled since the first draft (see the decision log): bulk undo after a pipeline change (D60), the template management screen (D66), the folder-import path (D67, since removed by D73), the staging token format and error wording (D68), and the performance numbers for synthetic data (D72). Still open or deliberately limited:

- **Copy-on-apply (ADR-004) was a default**, taken because that question went unanswered; it was not explicitly confirmed. The owner's wording ("two groups can use the same pipeline") fits both copy and shared pipelines.
- **Real-data performance** has not been measured; only synthetic 10,000-row data has (D72).
- **Docker image** was written but never built or run during implementation (the daemon was down); `docker compose config` validates.
- **Touch drag-and-drop** on the board (native HTML5 drag, D71) is untested; the dropdown is the alternative.
- **Later PRD items** not built: message templates (FR-66), keyboard shortcuts (FR-47), `.zip` import (FR-12).
- **Only the most recent bulk batch** can be undone.

## 12. Decisions & ADRs

The complete decision record lives in [decision-log.md](decision-log.md) (59 decisions). Decisions that cleared the three-part ADR bar have a standalone record under `docs/adr/`, written by the `adr-generator` skill:

| ADR | Title |
|-----|-------|
| [docs/adr/ADR-001-react-spa-frontend.md](docs/adr/ADR-001-react-spa-frontend.md) | Use a React SPA for the frontend |
| [docs/adr/ADR-002-raw-sqlite3-sql-migrations.md](docs/adr/ADR-002-raw-sqlite3-sql-migrations.md) | Use raw sqlite3 with numbered SQL migrations |
| [docs/adr/ADR-003-docker-loopback-publish.md](docs/adr/ADR-003-docker-loopback-publish.md) | Run in Docker with the port published on loopback only |
| [docs/adr/ADR-004-copy-on-apply-pipeline-templates.md](docs/adr/ADR-004-copy-on-apply-pipeline-templates.md) | Model pipelines as copy-on-apply templates, and let groups have none |
| [docs/adr/ADR-005-linkedin-url-normalization-key.md](docs/adr/ADR-005-linkedin-url-normalization-key.md) | Use an aggressively normalized LinkedIn URL as the contact key |
