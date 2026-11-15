# Implementation Order

Phases must be implemented in this order. Order is derived from the system design's technical dependency graph (schema before service, service before UI, shared infra before features that consume it) — NOT from PRD feature priority. Each phase is independently testable in isolation before moving to the next.

| Order | Phase file | Depends on | Design components | Independently testable when |
|-------|-----------|------------|--------------------|------------------------------|
| 1 | `phase1-foundation-scaffold.md` | None | Backend layers, migrations, SPA shell, Docker | `docker compose up` starts the app |
| 2 | `phase2-contacts-and-import.md` | Phase 1 | contacts, import, contacts list | Fixture CSVs (preamble, BOM, quoting, non-Latin names) import by upload and from `/data` |
| 3 | `phase3-visit-tracking-and-messages.md` | Phase 2 | contact timestamps, `/go`, notes | Integration test of `/go/{id}` (timestamp and redirect target), manual left/middle-click check, Mark messaged  |
| 4 | `phase4-groups-and-membership.md` | Phase 3 | groups, group_members, group page | Create/rename/delete groups; add members by selection, search-and-pick or CSV |
| 5 | `phase5-pipelines-and-stage-moves.md` | Phase 4 | stages, templates, stage_history | Create groups with/without pipelines, edit stages, apply/remove templates with previews, move members by dropd |
| 6 | `phase6-bulk-set-stage.md` | Phase 5 | bulk_staging, bulk-stage API | Preview shows correct counts |
| 7 | `phase7-board-export-backup.md` | Phase 6 | board, export, backup, E2E | Dragging a card changes stage with history |

## Dependency notes

- Task 4.2's 'Mark N messaged' uses the bulk endpoint from task 3.2; task 7.3 (export) adds 'Export N selected' to the selection bar built in 4.2.
- Task 1.5 (start script) was added after the first build and has no dependents.
- Visit tracking (Phase 3) precedes groups (Phase 4) because the group page links through `/go/{id}`. Phase 3 needs only contacts from Phase 2.
- Phase 3 could in principle run in parallel with the groups CRUD and membership tasks (4.1, 4.2); it is sequenced first for review simplicity, and task 4.3 needs 3.1.
- Task 7.4 (backup and README) needs only Phase 1, so it can be pulled forward if wanted. Otherwise the phases are strictly sequential.

## Do not reorder

Do not start a phase before its listed dependencies are complete and verified. If a later phase reveals that an earlier phase's design assumption was wrong, stop and flag it — don't silently patch it forward.
