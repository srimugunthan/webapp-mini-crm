# Phase 7: Board, export, backup and E2E

**Depends on:** `phase6-bulk-set-stage.md`
**Status:** Implemented — see [phase report](../../docs/phase-reports/phase7.md)

## Design components touched

§2 SPA, §4 Export/backup, §6 Backup, §9 Tests

## Objective

Visual pipeline board, hide final stages, CSV export, backup and README, and end-to-end tests.

## Independently testable when

Dragging a card changes stage with history; export CSV round-trips; downloaded backup opens as valid SQLite; Playwright flows pass.

## Tasks

Each task is a thin vertical slice through every layer it touches, demoable or verifiable on its own. Design refs point to [system-design.md](../../system-design.md); PRD refs to [the PRD](../../linkedin-mini-crm-PRD.md).

### 7.1 Board view

- **Type:** AFK
- **Blocked by:** Phase 5 (5.4)
- **PRD reference:** FR-46
- **System design reference:** §2, §7

**Scope:** Board with one column per stage, drag-and-drop between columns (native HTML5 drag-and-drop, decision 71, not dnd-kit), dropdown alternative retained.

**Acceptance criteria:**
- [x] Drag moves stage and writes history
- [x] Dropdown works as alternative
- [x] Verifiable in UI

### 7.2 Hide final-stage members

- **Type:** AFK
- **Blocked by:** Phase 5 (5.3)
- **PRD reference:** FR-45
- **System design reference:** §4

**Scope:** Toggle hiding final-stage members from the default group view.

**Acceptance criteria:**
- [x] Default view hides them; toggle reveals
- [x] Verifiable in UI

### 7.3 CSV export

- **Type:** AFK
- **Blocked by:** Phase 4 (4.3)
- **PRD reference:** FR-67
- **System design reference:** §4

**Scope:** `GET /api/export` for all contacts, a group (`group_id`), an explicit selection (`ids=1,2,3`), or whatever the contacts filters match (same parameters as the contacts list); the contacts selection bar gets **Export N selected CSV** (and uses the filters when 'all N matching' is selected), and with nothing ticked the link reads 'Export all N matching CSV'. `GET /api/contacts/ids` supports select-all-matching (task 4.2).

**Acceptance criteria:**
- [x] CSV includes expected columns and honors group scope
- [x] Export honors a selection of ids and the contacts filters; filenames are safe
- [x] A group export with `ids` includes only the ticked members of that group (decision 74)
- [x] Re-importable by the importer
- [x] Verifiable via API test

### 7.4 Backup, CLI and README

- **Type:** AFK
- **Blocked by:** Phase 1 (1.4)
- **PRD reference:** FR-68
- **System design reference:** §6, §9

**Scope:** `GET /api/backup` and CLI via the SQLite backup API; README covering LinkedIn export, where uploaded copies go, backup/restore (manual copy only with app stopped), loopback warning.

**Acceptance criteria:**
- [x] Downloaded backup opens and matches data
- [x] CLI produces equivalent file
- [x] README steps verified by following them
- [x] Verifiable manually

### 7.5 Playwright E2E flows

- **Type:** AFK
- **Blocked by:** 7.1, 6.4
- **PRD reference:** §13 Tests
- **System design reference:** §9

**Scope:** Playwright flows against the real backend: import → group → stage move; bulk preview/apply/undo; board drag and a no-pipeline group; add people to a group (CSV on create, Add members); contacts filter + selection bar. As built: 5 flows.

**Acceptance criteria:**
- [x] Flows pass against a built container or dev server
- [x] Verifiable by running Playwright

### 7.6 Restore the database from an uploaded .sqlite backup

> Added 2026-11-08 (decision 76).

- **Type:** AFK
- **Blocked by:** 7.4
- **PRD reference:** FR-76 (extends FR-68)
- **System design reference:** §6 Storage (Restore), §4 Export, backup, ops

**Scope:** `POST /api/restore/preview` and `POST /api/restore?confirm=RESTORE`; Import page panel 'Restore database from a .sqlite backup' with a preview dialog and typed confirmation.

**Acceptance criteria:**
- [x] Restore brings back the backed-up contacts, groups, members and notes and the app works normally afterwards
- [x] Missing or wrong confirmation phrase is rejected and writes no safety backup
- [x] Preview describes the file and changes nothing
- [x] Rejected: non-SQLite files, SQLite files not made by this app, damaged files, backups from a newer schema; current data is untouched
- [x] An older backup is restored and then upgraded by the migrations
- [x] The pre-restore state is saved to `db/backups/pre-restore-*.sqlite`
- [x] UI dialog shows counts in the file versus current data and keeps the button disabled until `RESTORE` is typed
