# Phase 5 report: Pipelines and stage moves

Spec: [phase5-pipelines-and-stage-moves.md](../../specs/linkedin-mini-crm-v1/phase5-pipelines-and-stage-moves.md) — tasks 5.1–5.9.

## Files touched (new/changed)
- `backend/migrations/005_stages.sql` (stages, member stage/follow-up columns, stage_history, `groups.pipeline_epoch`), `006_templates.sql` (templates + Starter seed)
- `backend/app/repositories/stages.py`, `repositories/groups.py`; `services/pipelines.py`, `services/groups.py`; `routers/groups.py` (stages, member PATCH, stage-counts, pipeline apply/remove), `routers/pipelines.py`
- `frontend/src/components/{PipelineModal,StageNoteModal}.tsx`; `pages/Pipelines.tsx`, `pages/GroupPage.tsx`, `pages/Groups.tsx` (pipeline dropdown)
- Tests: `backend/tests/test_phase5_pipelines.py`, `frontend/src/components/components.test.tsx`, `frontend/src/util.test.ts` (stepStage)

## How to test by hand
**Start the app for manual testing** (once, reuse for later phases): `cd frontend && npm install && npm run build`, then `cd backend && uv sync && uv run uvicorn app.asgi:app` and open http://127.0.0.1:8000 (data goes to `./db/crm.sqlite`; delete that folder to start fresh). For live UI edits use `npm run dev` in `frontend/` and open http://localhost:5173.
1. **Groups**: the pipeline dropdown is preselected to *Starter* (Connected → Reached out → In conversation → Closed); create "Prospects". Create another with *No pipeline*.
2. Add contacts to Prospects (Contacts page). Open it: chips "All N · Connected N …"; click a chip to filter (the URL gets `?stage=<id>`, reload keeps it).
3. Change a member's **Stage dropdown**: a note box appears — type text and press **Enter** to save, or press **Esc** to move without a note. Use **< >** buttons; moving into *Closed* (final) asks for confirmation. "In stage" shows days and sorts. The contact drawer shows the history with notes.
4. Final-stage members are hidden by default; tick *show final-stage members*. Chips still count them.
5. *Edit stages*: rename (edit then click away), final checkbox, ↑/↓ reorder, add a stage, paste "a, b, c" and *Add list* (appends missing), delete a stage that has members (asks to move them or clear).
6. *Apply a template*: pick one → *Preview* (stage-less members → first stage, same-named stages map, others need you to choose) → *Confirm and apply*. *Save group's stages as template*. *Remove pipeline…* confirms and clears stages (history kept).
7. **No-pipeline group**: no chips, no stage column, no Board, Bulk set stage disabled; dates and filters still work.
8. **Pipelines** page: create (comma list), rename, delete a template; groups made from it are unaffected.
9. Follow-up date box per row; set a past date → row highlights; tick *follow-up overdue* to filter.

## Testing done
- `pytest tests/test_phase5_pipelines.py` → **11 passed**: stage CRUD/reorder/final/unique/pasted list; delete with members requires move-or-clear (+history); starter seed, copy-on-create independence and template delete doesn't touch groups; template CRUD + validation; save group as template; stage move writes history with note, days in stage + sort, same-stage no-op, cross-group stage rejected, **atomic rollback when history fails**; stage counts and filters; hide final; apply template (preview changes nothing, name mapping, unmatched must be chosen, history); remove pipeline needs confirm and keeps history; follow-up dates per membership and overdue filter.
- Vitest `components.test.tsx`: note modal (Enter saves / Esc skips), Board columns and dropdown alternative, No stage column. → part of **11 passed**.
- Playwright flow 1: dropdown move + Esc, next with Enter note, final confirmation, final hidden/shown, history in drawer. Flow 3 checks a no-pipeline group's UI.

## Notes / choices
- Adding the first stage manually to a group that already has stage-less members leaves them stage-less (use *Apply template* to put them on a first stage with history).
- "Pipeline changed" for undo purposes = apply template, remove pipeline, or delete stage (they bump `pipeline_epoch`); renames and reorders don't.
- Template screen is the minimal scope you chose (no stage reordering inside a template).
