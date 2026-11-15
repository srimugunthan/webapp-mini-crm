# Phase 4 report: Groups and membership

Spec: [phase4-groups-and-membership.md](../../specs/linkedin-mini-crm-v1/phase4-groups-and-membership.md) — tasks 4.1–4.4.

> **Updated 2026-11-08:** added the Contacts selection bar with "Select all N matching" (4.2) and "Add members" / CSV adding (4.4) at the owner's request (decisions 64, 65).

## Files touched (new)
- `backend/migrations/004_groups.sql`
- `backend/app/repositories/groups.py`, `services/groups.py`, `routers/groups.py` (groups + members parts)
- `frontend/src/pages/Groups.tsx`, `pages/GroupPage.tsx`; `pages/Contacts.tsx` (multi-select, Add to group, badges)
- Added later: `frontend/src/components/AddMembersModal.tsx`, CSV field in `pages/Groups.tsx`, `GET /api/contacts/ids`, `POST /api/groups/{id}/members/csv` (in `services/groups.py`, `routers/groups.py`, `routers/contacts.py`)
- Tests: `backend/tests/test_phase4_groups.py` (6 tests now), `tests/helpers.py`

## How to test by hand
**Start the app for manual testing** (once, reuse for later phases): `cd frontend && npm install && npm run build`, then `cd backend && uv sync && uv run uvicorn app.asgi:app` and open http://127.0.0.1:8000 (data goes to `./db/crm.sqlite`; delete that folder to start fresh). For live UI edits use `npm run dev` in `frontend/` and open http://localhost:5173.
1. **Groups** → enter a name, choose *No pipeline*, *Create group*. Duplicate name (any case) shows an error. *Rename*; *Delete* asks and states the member count.
2. **Contacts** → tick rows (or the header checkbox), choose the group, *Add to group*: "Added N, M already in the group". Group badges appear on rows; the "not in any group" filter excludes them.
3. Open the group: members table with LinkedIn links (visit tracking works here too), Visited/Messaged dates, search box, "not visited in N days", "not messaged in N days", column sorting. *Remove* takes someone out of the group but they stay in Contacts.
4. Deleting the group leaves all contacts.
5. **Selection bar** (Contacts): tick rows → bar shows "N selected" with Add to group, Export N selected CSV, Mark N messaged, Clear. With more matches than one page, "Select all N matching" appears. Changing a filter clears the selection.
6. **Add members** (group page): *Pick from contacts* (search, tick, "Add N selected") or *Upload CSV* (URL column → Preview → "Add N people"). The create-group form also has an optional CSV; a CSV problem doesn't block creating the group.

## Testing done
- `pytest tests/test_phase4_groups.py` → **6 passed**: CRUD + unique names (case-insensitive) + empty name; bulk add idempotency, many groups per contact, unknown contact 404; remove member keeps contact and group delete cascades without deleting contacts; group member table sort, search and visited/messaged day filters (time faked).
- New: add from CSV previews then applies, is idempotent, never creates contacts, starts members at the first stage in a pipelined group, rejects a file with no URL column, and 404s an unknown group.
- Covered end-to-end in Playwright flow 1 and the "add people to a group" flow (create group, add 4 contacts from list).

## Notes
- Pipeline selection on create is available from the start of Phase 5 (the API already accepts `template_id`; the UI dropdown came with the templates).

## Added 2026-11-08: Mark messaged on the group page and compact tables
- Group rows now have **Mark messaged**, a date box and **Set** (same as Contacts); per-row remove is a small ✕. Dates show as `8 Nov 26` (hover for the full date).
- Tables are compact (smaller font, wrapped Title/Company, shortened LinkedIn text). Playwright checks there is no sideways scroll at 1280, 1366 and 1536 px for both the Contacts and group tables (flow 9). Very long names or wide dropdown labels on a narrower window could still scroll.
