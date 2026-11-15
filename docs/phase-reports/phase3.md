# Phase 3 report: Visit tracking and message log

Spec: [phase3-visit-tracking-and-messages.md](../../specs/linkedin-mini-crm-v1/phase3-visit-tracking-and-messages.md) — tasks 3.1–3.3.

> **Updated 2026-11-08:** the return prompt and the "Visited, not logged" page/endpoint were built and then **removed** at the owner's request (decision 62). This report describes what remains.

## Files touched (new/changed)
- `backend/migrations/003_notes.sql`
- `backend/app/services/contacts.py` (visit, messaged, pending, notes), `repositories/contacts.py`, `routers/contacts.py` (`/go/{id}`, `messaged`, `messaged-bulk`, `notes`)
- `frontend/src/components/{LinkedInLink,ContactDrawer}.tsx`, `pages/Contacts.tsx` (link, Mark messaged, drawer)
- Tests: `backend/tests/test_phase3_visits_messages.py`

## How to test by hand
**Start the app for manual testing** (once, reuse for later phases): `cd frontend && npm install && npm run build`, then `cd backend && uv sync && uv run uvicorn app.asgi:app` and open http://127.0.0.1:8000 (data goes to `./db/crm.sqlite`; delete that folder to start fresh). For live UI edits use `npm run dev` in `frontend/` and open http://localhost:5173.
(Import the fixture first, see Phase 2.)
1. Contacts → click a **LinkedIn** link (left-click, then also middle-click another). A new tab opens linkedin.com; back in the app the **Last visited** cell updates within about a second.
2. Switch back to the app tab: nothing pops up (the prompt was removed).
3. There is no "Visited, not logged" page any more; log messages with **Mark messaged** (now), the date box + **Set** (past date), or tick rows on Contacts and use **Mark N messaged**.
4. **Mark messaged** button on a row sets now; the date box + *Set* sets a past date (stored as local noon).
5. Click a contact name → drawer: add notes (Enter or Add), they show newest first with dates; drawer also lists groups and stage history.
6. Safety check: edit a contact's stored URL to a non-LinkedIn host in the DB, click it: `/go/{id}` returns an error and doesn't redirect.

## Testing done
- `pytest tests/test_phase3_visits_messages.py` → **6 passed** (the pending-visits test was replaced by one confirming the endpoint is gone and bulk messaged works): `/go` sets `last_visited_at` and returns 302 to the stored URL; prefetch headers (Sec-Purpose, Purpose, X-Moz) don't count but still redirect; non-linkedin host → 400 and no update, unknown id 404;
  mark messaged now / past date / bad date / unknown contact; bulk messaged and the removed pending endpoint; notes add/list/empty rejected and survive re-import.
- Playwright flow 1 clicks the real link (LinkedIn stubbed), checks `last_visited_at` via the API, and checks that refocusing the tab shows no dialog.

## Notes / limits
- Visits can't be distinguished from prefetch unless the browser sends a prefetch header (known limit, D23).
