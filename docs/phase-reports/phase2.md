# Phase 2 report: Contacts and import

Spec: [phase2-contacts-and-import.md](../../specs/linkedin-mini-crm-v1/phase2-contacts-and-import.md) — tasks 2.1–2.6.

## Files touched (new)
- `backend/migrations/002_contacts.sql`
- `backend/app/urlnorm.py`, `csvparse.py`
- `backend/app/repositories/contacts.py`; `services/importer.py`, `services/contacts.py` (list part)
- `backend/app/routers/imports.py`, `routers/contacts.py` (list/get)
- `frontend/src/pages/Import.tsx`, `pages/Contacts.tsx`
- Tests: `backend/tests/test_urlnorm.py`, `test_phase2_import_contacts.py`, `fixtures/{Connections.csv,bom.csv,bad_columns.csv}`; `frontend/src/util.test.ts`

## How to test by hand
**Start the app for manual testing** (once, reuse for later phases): `cd frontend && npm install && npm run build`, then `cd backend && uv sync && uv run uvicorn app.asgi:app` and open http://127.0.0.1:8000 (data goes to `./db/crm.sqlite`; delete that folder to start fresh). For live UI edits use `npm run dev` in `frontend/` and open http://localhost:5173.
1. **Import → Upload**: choose `backend/tests/fixtures/Connections.csv` → *Upload and import*. Expect "4 new · 0 updated · 1 skipped · 0 errors" and "Row 7 (Ravi Kumar): missing URL" (the row has no URL).
2. Upload it again → "0 new · 4 updated".
3. Look in the `data/` folder: a copy was saved, e.g. `import-20261108-153000-Connections.csv`. Upload again: a second file appears (nothing is overwritten). *(Updated 2026-11-08: the "Import from folder" button was removed, decision 73.)*
4. Upload `backend/tests/fixtures/bad_columns.csv` → red error about the header row.
5. **Contacts** page: 4 contacts incl. 李 雷 / Ünal Çelik. Click column headers to sort (▲/▼); type in Search (name/company/position), try the Company, Position, Year boxes and the three checkboxes. Filters are in the URL (reload keeps them).
6. Large test: the pytest perf test seeds 10,000 contacts (see below); to try it in the UI generate a CSV of your own and import it.

## Testing done
- `pytest tests/test_urlnorm.py` → **8 passed** (www/http/case/query/fragment/trailing slash collapse to one key; redirect host rules).
- `pytest tests/test_phase2_import_contacts.py` → **21 passed**: fixture import (preamble, quoting, non-Latin, no-URL skipped, date parsing); BOM; missing columns → 400 and nothing changes;
  optional columns missing OK; 25 MB cap → 413; mid-import failure rolls back everything; re-import updates but keeps timestamps and absent contacts;
  uploaded copy saved in the data folder (byte-identical, never overwritten, unsafe names sanitised, import still works if the folder is unwritable, bulk and group CSVs saved too), folder endpoint gone; paging + sort; search, each filter, LIKE-wildcard escaping.
- **Measured at 10,000 contacts** (this machine): import 0.30 s (budget 10 s), list/search page avg 0.012 s (budget 1 s). The design's unmeasured assumption in §7 is now measured for these paths.
- Vitest `util.test.ts` (dates, query-string helper) → passes.

## Added 2026-11-08: add vs fresh import
- Import page has **Upload and add to contacts** (the original upsert) and **Upload and Fresh import** (red; confirmation dialog with live counts, type `RESET`). Fresh is a complete reset: it deletes contacts, groups, memberships, stages, history, notes and all pipeline templates (the default Starter is re-created; decision 77), and writes `db/backups/pre-fresh-import-*.sqlite` first.
- Manual test: import the fixture, make a group, add a note; then fresh-import a different CSV → dialog shows the counts, the button stays disabled until `RESET` (case sensitive) → afterwards only the new file's people exist, no groups, only the default Starter template remains (custom or renamed ones are gone), and the backup file holds the old data. A bad CSV or a failed import deletes nothing.
- Tests: 6 new pytest (confirmation required, wipe + load, backup content, bad file, rollback midway, add mode default) and Playwright flow 7.

## Notes / choices
- `connected_on` is parsed from LinkedIn's "02 Nov 2024" into `YYYY-MM-DD`; unparseable values are stored as typed.
- Ascending sort puts never-visited / never-messaged first ("oldest first").
- Duplicate URLs inside one file count as new then updated.
- "Not in any group" filter was re-verified after groups existed in Phase 4's tests.
- Import `errors` list is always empty in practice: any fatal error aborts and rolls back with an error message.

## Added 2026-11-08: boolean search and the Group box
- Contacts page: new **Group** filter, and all text boxes (Search, Company, Position, Group) accept `AND`, `OR`, `NOT`/`-`, parentheses, `"phrases"` and `field:term`; **Search help** shows the syntax. Code: `backend/app/search.py`, `repositories/contacts.py`, `routers/contacts.py`, `routers/ops.py`, `pages/Contacts.tsx`.
- Manual test (with a few groups): Group box `ML OR HR`; `Hot AND NOT ML`; `NOT Hot`; Search `data AND (google OR acme) NOT manager`; `company:acme AND group:ml`. Type `(data` to see the syntax message. Tick rows or use "Select all N matching" and export: the same filter applies.
- Tests: 17 pytest in `test_boolean_search.py` (operators, precedence, fields, groups incl. NOT, bad syntax, limits, injection-safety, ids/export) and Playwright flow 10.

## Added 2026-11-09: optional group name on import
- Import → Upload and add to contacts has an optional **Group name** (suggestions from existing groups). With a name, everyone in the file is also put in that group (created if missing, no pipeline). Empty = no group.
- Manual test: upload a CSV with group `Following` → summary says the group was created and N people added, with an *Open group* link; Contacts shows connections + followed people; Group box `Following` shows only the followed ones; `NOT Following` the rest. Upload another file with the field empty: no group is created. Upload again as `following`: group reused, no duplicates.
- Tests: 6 new pytest (create + add, no name unchanged, case-insensitive reuse and idempotence, already-known people, first stage in a pipelined group, rollback and validation) and Playwright flow 11. Code: `services/importer.py`, `routers/imports.py`, `repositories/groups.py`, `pages/Import.tsx`.
