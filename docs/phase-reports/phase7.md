# Phase 7 report: Board, export, backup and E2E

Spec: [phase7-board-export-backup.md](../../specs/linkedin-mini-crm-v1/phase7-board-export-backup.md) — tasks 7.1–7.5.

## Files touched (new/changed)
- `backend/app/services/ops.py`, `routers/ops.py`, `cli.py`
- `frontend/src/components/Board.tsx`, `pages/GroupPage.tsx` (Board toggle, hide-final), `pages/Import.tsx` (Download backup), export links in `Contacts.tsx`/`GroupPage.tsx`
- `frontend/e2e/flows.spec.ts`, `frontend/playwright.config.ts`
- `README.md` (export steps, where uploaded copies go, backup/restore, loopback warning)
- Tests: `backend/tests/test_phase7_ops.py`

## How to test by hand
**Start the app for manual testing** (once, reuse for later phases): `cd frontend && npm install && npm run build`, then `cd backend && uv sync && uv run uvicorn app.asgi:app` and open http://127.0.0.1:8000 (data goes to `./db/crm.sqlite`; delete that folder to start fresh). For live UI edits use `npm run dev` in `frontend/` and open http://localhost:5173.
1. Group with a pipeline → **Board**: one column per stage with cards. **Drag a card** to another column (note box appears: Enter/Esc); or use the dropdown on the card. Moves appear in the Table view and in history.
2. On Contacts, tick rows → **Export N selected CSV**; with nothing ticked the link exports everything matching your filters ("Export all N matching CSV"). **Export CSV** on a group page (adds a Stage column) and *Export all CSV* on Contacts. Import an export back: everything shows as "updated", nothing new.
3. **Import → Download backup** saves a `.sqlite` file; open it with any SQLite viewer or `sqlite3 file.sqlite "select count(*) from contacts"`.
4. CLI: `cd backend && uv run python -m app.cli backup /tmp/my-backup.sqlite` (uses `DB_PATH`, default `../db/crm.sqlite`).
5. Restore: stop the app, copy the backup over `db/crm.sqlite`, remove `-wal`/`-shm` files, start.

## Testing done
- `pytest tests/test_phase7_ops.py` → **5 passed**: export all round-trips through the importer; group export scope + Stage column + safe filename; backup download opens as valid SQLite (`integrity_check` ok, right row count); CLI backup + usage exit code.
- Playwright (`npm run build && npx playwright test`) → **5 passed** against the real backend on a throwaway DB: (1) import → group → add members → dropdown/next moves with notes, final confirm, hide/show final, link click via `/go`, return prompt, history in drawer; (2) bulk preview → apply → undo; (3) board drag-and-drop, and a no-pipeline group's hidden stage UI; (4) add people to a group (CSV on create, Add members search and CSV); (5) contacts filter, selection bar, export selected, mark messaged.
- Full final run: backend **65 passed**, Vitest **11 passed**, Playwright **5 passed** (after the 2026-11-08 changes).

## Added 2026-11-08: restore from an uploaded .sqlite
- Import page → **Upload and restore database**: choose a `.sqlite` (from *Download backup* or `db/backups/`) → dialog shows what the file contains versus your current data → type `RESTORE` → data replaced; your previous data is saved as `db/backups/pre-restore-*.sqlite`.
- Manual test: Download backup, add or delete some contacts, restore the file: the data from the backup is back. Try a random file renamed to `.sqlite`: clear error, nothing changes.
- Tests: 6 pytest in `test_phase7_restore.py` (round trip, confirmation required, preview, rejected files incl. damaged and newer-version, older backup upgraded) and Playwright flow 8. Files: `services/restore.py`, `routers/ops.py`, `pages/Import.tsx`.

## Notes / not done
- Export now also accepts `ids` and the contacts filters (decision 65). Native HTML5 drag-and-drop (not dnd-kit). Drag in a real touch device is not covered; use the dropdown there.
- Not built (per plan): `.zip` import, keyboard shortcuts `[ ]`, message templates.
- **Docker image build/run not verified** (daemon was down). Please run `docker compose up --build` and check the healthcheck.
