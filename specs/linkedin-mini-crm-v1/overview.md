# LinkedIn Mini CRM v1 — Overview

> **Revised 2026-11-08** to reflect the built v1 and later changes: return prompt and visited list removed; add-members and the selection bar added; documents updated in step (PRD v0.3, system design, decision log rows 60–72, ADR implementation notes).

## Source documents

- **PRD:** [linkedin-mini-crm-PRD.md](../../linkedin-mini-crm-PRD.md) (v0.2)
- **System design:** [system-design.md](../../system-design.md), with [decision-log.md](../../decision-log.md) and [ADRs](../../docs/adr/)

## Goal

A private, single-user web app, run locally in Docker, that imports the LinkedIn connections export, organizes contacts into groups, records last visited and last messaged dates, and lets each group follow an optional stage pipeline. It covers PRD goals G1–G7 and keeps all data on the user's machine.

Where the PRD's technical approach (§13: HTMX, Alembic) differs from the system design (React SPA, raw sqlite3 SQL migrations), the design governs. Likewise pipelines are copy-on-apply templates and groups may have none (ADR-004).

## Scope

- Import by upload (a copy of every uploaded CSV is kept in the data folder) with upsert (FR-1, FR-4–11, FR-72); contacts list with search, filters, sort
- Groups (filled from the Contacts list, the group page, or a CSV), visit tracking via `/go/{id}`, last messaged logged by hand, notes, follow-ups
- Contacts selection bar: add to group, export selected, mark messaged, select all N matching
- Per-group pipelines from templates, stage moves with history, board view
- Bulk set stage from CSV with preview, apply and undo
- CSV export, backup, README

Decisions made while planning: bulk undo is refused if the group's pipeline changed since the batch; the template screen is minimal (list, create, rename, delete, save from group); the folder import planned at first was later removed in favour of keeping a copy of every uploaded CSV in `/data` (decision 73).

## Non-goals

- Scraping LinkedIn or unofficial APIs; sending messages or outreach automation; syncing messages
- Background jobs or folder watching; emails, notifications, reminders
- Logins, multi-user, sharing; enrichment; deal values; native mobile apps
- Dropped after v1 use (2026-11-08): the return prompt (FR-62) and the 'Visited, not logged' list (FR-63)
- Deferred PRD items: `.zip` import (FR-12), keyboard shortcuts (FR-47), message templates (FR-66)

## Phases

| Phase | File | Summary | Depends on |
|-------|------|---------|------------|
| 1 | `phase1-foundation-scaffold.md` | Backend skeleton, migration runner, SPA shell, Docker/Compose | None |
| 2 | `phase2-contacts-and-import.md` | Import (upload, copies kept in data folder), upsert, contacts list, search, filters | Phase 1 |
| 3 | `phase3-visit-tracking-and-messages.md` | /go redirect, mark messaged (single and bulk), notes | Phase 2 |
| 4 | `phase4-groups-and-membership.md` | Groups CRUD, membership, selection bar, group page, add members (pick or CSV) | Phase 3 |
| 5 | `phase5-pipelines-and-stage-moves.md` | Stage editor, templates, stage moves, chips, apply/remove pipeline, follow-ups | Phase 4 |
| 6 | `phase6-bulk-set-stage.md` | Bulk preview, apply, stage override, undo | Phase 5 |
| 7 | `phase7-board-export-backup.md` | Board, hide finals, export, backup/README, E2E | Phase 6 |

See `implementation-order.md` for the full dependency detail and `README.md` for how to work through this folder.
