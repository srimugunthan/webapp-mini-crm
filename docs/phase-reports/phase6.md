# Phase 6 report: Bulk set stage

Spec: [phase6-bulk-set-stage.md](../../specs/linkedin-mini-crm-v1/phase6-bulk-set-stage.md) — tasks 6.1–6.4.

## Files touched (new/changed)
- `backend/migrations/007_bulk.sql` (`bulk_staging`, `bulk_batches`)
- `backend/app/services/bulk.py`, `routers/bulk.py`, `repositories/stages.py` (staging/batch functions)
- `frontend/src/components/BulkModal.tsx`, `pages/GroupPage.tsx` (button + Undo)
- Tests: `backend/tests/test_phase6_bulk.py`

## How to test by hand
**Start the app for manual testing** (once, reuse for later phases): `cd frontend && npm install && npm run build`, then `cd backend && uv sync && uv run uvicorn app.asgi:app` and open http://127.0.0.1:8000 (data goes to `./db/crm.sqlite`; delete that folder to start fresh). For live UI edits use `npm run dev` in `frontend/` and open http://localhost:5173.
Use a group with the Starter pipeline and some members (Phase 5).
1. Make a CSV, e.g. `URL,Stage` rows using URLs from your contacts (the import fixture has `https://www.linkedin.com/in/asha-rao`, `.../priya-nair`, `.../unal-celik`, `.../lilei`), plus one made-up URL and one row with a bogus stage name.
2. Group page → *Bulk set stage* → choose file (and a default stage, or leave "(use Stage column only)") → *Preview*. You get counts: will be moved / already at stage / will be added / URL not found / unknown stage, and *Download problem rows* (CSV).
3. *Apply*: members move, missing ones are added to the group at that stage, the contact drawer shows history marked "bulk". Notes, last visited/messaged and follow-up dates are unchanged.
4. *Undo last bulk change*: stages restored and people the batch added are removed. A second undo says there is nothing to undo.
5. Change the pipeline (apply another template) after a bulk update, then *Undo last bulk change* → refused with a message.
6. Preview, then change someone's stage in another tab, then Apply → "Your data changed since the preview. Please preview again." Applying the same preview twice, or after 30 min, says it expired.

## Testing done
- `pytest tests/test_phase6_bulk.py` → **10 passed**: preview categories and duplicate-URL collapse, problem rows CSV, preview changes nothing; `Stage` column override + unknown stage; apply adds/moves, leaves other fields, doesn't reset time for same-stage; token single-use + 30 min expiry + bogus token; **stale preview aborts with nothing applied**; **atomic apply** (history failure rolls everything back); disabled for no-pipeline group (400); undo restores + removes added, second undo 404; undo refused after pipeline change; preview of 1,000 rows.
- **Measured:** 1,000-row preview 0.03 s (budget 3 s).
- Playwright flow 2: upload CSV → preview counts → problem-rows link → apply → chips → undo.

## Notes
- Only the most recent un-undone batch can be undone.
- If neither a dropdown stage nor a Stage column value is present, the row is reported as a problem ("No stage given").
- The token is a 22-char URL-safe random string; error wording is mine (design left both open).
