# LinkedIn Mini CRM

A private, single-user web app that runs on your machine. Import your LinkedIn connections export, organise
people into groups, track last visited / last messaged dates, and move people through per-group stage pipelines.
All data stays in one SQLite file. See [linkedin-mini-crm-PRD.md](linkedin-mini-crm-PRD.md) and
[system-design.md](system-design.md); the phase-by-phase plan is in [specs/linkedin-mini-crm-v1/](specs/linkedin-mini-crm-v1/)
and what was built/tested per phase is in [docs/phase-reports/](docs/phase-reports/).

## Run it

### Quick start (start script)
```bash
sh ./start.sh                    # from the project root
```

### Docker (supported run path)
```bash
docker compose up --build        # then open http://127.0.0.1:8000
```
The port is published on **127.0.0.1 only** because the app has no login. Do not change the mapping to
`8000:8000` unless you add authentication first (ADR-003). Data lives in `./db/crm.sqlite`; a copy of every CSV you upload is saved in `./data`
(for example `import-20261108-153000-Connections.csv`).

> Note: the Dockerfile/Compose were written but **not built or run** in the environment that produced this code
> (the Docker daemon was not running). `docker compose config` validates; the same app was run natively (below).

### Native (development)
```bash
# backend (needs uv; Python 3.13 is fetched automatically)
cd backend && uv sync && uv run uvicorn app.asgi:app --reload      # API on :8000
# frontend dev server with proxy to :8000
cd frontend && npm install && npm run dev                           # UI on http://localhost:5173
# or serve the built UI from the backend:
cd frontend && npm run build && cd ../backend && uv run uvicorn app.asgi:app   # UI+API on :8000
```
Environment variables: `DB_PATH` (default `./db/crm.sqlite`), `DATA_DIR` (default `./data`; copies of uploaded CSVs are saved there; Docker uses `/data`), `STATIC_DIR` (built SPA).

## Importing with a group name
On **Import → Upload and add to contacts** the *Group name* field is optional. Upload a CSV of people you follow with the name `Following` and they are added to your contacts and put in a group called Following (created if needed); upload a CSV of new connections with the field empty and they are just added to your contacts. Contacts always shows everyone, and the Group box on the Contacts page (`Following`, or `NOT Following`) filters by it.

## Searching contacts
The Contacts page has Search, Company, Position and Group boxes, and all four understand boolean queries (click **Search help** on the page):
- `AND`, `OR`, `NOT` in uppercase, or `-word` to exclude; spaces mean AND; `( )` to group; `"exact phrase"`; `field:word` where field is `name`, `company`, `position` (or `title`) or `group`.
- Search: `data AND (google OR acme) NOT manager` · Group box: `HR OR ML`, `Hot AND NOT ML`, `NOT Hot` (includes people in no group).

## Get your LinkedIn data
LinkedIn → Settings & Privacy → Data privacy → *Get a copy of your data* → pick **Connections** → download and
unzip → use `Connections.csv` (unzip it yourself; `.zip` import is not built yet). Upload it on the **Import** page with **Upload and add to contacts** (a copy is kept in `data/`). Re-importing is safe: groups, stages, notes and
visit/message dates are never overwritten, and contacts missing from a newer file are kept.
To start over, use **Upload and Fresh import**: it is a complete reset: it deletes all contacts, groups, notes and pipeline templates (the default Starter template is re-created) after you type `RESET`, and saves a backup to `db/backups/` first.

## Backup and restore
- In the app: **Import → Download backup** (`GET /api/backup`), or CLI: `cd backend && uv run python -m app.cli backup [dest.sqlite]`
  (uses SQLite's backup API, so it is consistent while the app runs).
- The app also backs up automatically to `db/backups/` before applying a pending migration (keeps the last 5).
- Restore in the app: **Import → Upload and restore database**, choose a `.sqlite` backup (from *Download backup* or `db/backups/`). You see what it contains, type `RESTORE`, and your current data is saved to `db/backups/pre-restore-*.sqlite` first.
- Restore by hand: stop the app, replace `db/crm.sqlite` with the backup file (delete any `crm.sqlite-wal`/`-shm` next to it), start the app.
- Copying the `.sqlite` file by hand is only safe **with the app stopped**.

## Resetting outside the app
The command-line tool only has `backup` so far; reset and restore are done from the Import page or by hand as below.

**Reset the database by hand** (the same result as a brand-new install):
1. Stop the app (Ctrl+C on `./start.sh`, or `docker compose down`).
2. Optional safety copy: `cd backend && uv run python -m app.cli backup`.
3. Delete the database files:
   ```bash
   rm -f db/crm.sqlite db/crm.sqlite-wal db/crm.sqlite-shm
   ```
4. Start the app again. It creates a new empty database on startup and re-creates the default Starter pipeline template.

**Wipe everything the tool has stored.** Step 3 above only resets the database. Also delete:
- `db/backups/`: the automatic pre-migration, pre-fresh-import and pre-restore backups.
- `data/*.csv`: the copies of every CSV you uploaded.

**Docker:** `docker compose down`, delete the files in `./db` as above, then `docker compose up`.

**Restore a backup by hand:** stop the app, copy the backup over `db/crm.sqlite`, delete any `crm.sqlite-wal` and `crm.sqlite-shm` next to it, and start the app. A backup from an older version is upgraded automatically on startup. Only do this with the app stopped.

Inside the app, **Import → Upload and Fresh import** is a complete reset (contacts, groups, notes and pipeline templates, with the default Starter re-created) and **Import → Upload and restore database** loads a `.sqlite` backup. Both take a backup first and ask you to type a confirmation word.

## Tests
```bash
cd backend && uv run pytest                 # 104 tests (real temp SQLite per test)
cd frontend && npm test                     # Vitest + React Testing Library
cd frontend && npm run build && npx playwright test   # 11 end-to-end flows against the real backend
```
