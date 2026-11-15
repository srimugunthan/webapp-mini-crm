# Phase 2: Contacts and import

**Depends on:** `phase1-foundation-scaffold.md`
**Status:** Implemented — see [phase report](../../docs/phase-reports/phase2.md)

## Design components touched

§3 contacts table, §4 Import and Contacts endpoints, §5.2 Import flow, §6 search, §7 performance, ADR-005

## Objective

The user can import a LinkedIn connections CSV (upload; a copy is kept in the data folder), re-import safely, and browse, search, filter and sort their contacts at 10,000-row scale.

## Independently testable when

Fixture CSVs (preamble, BOM, quoting, non-Latin names) import by upload; re-import updates without losing data; the contacts page lists, sorts, searches and filters; the 10k-contact budget test passes.

## Tasks

Each task is a thin vertical slice through every layer it touches, demoable or verifiable on its own. Design refs point to [system-design.md](../../system-design.md); PRD refs to [the PRD](../../linkedin-mini-crm-PRD.md).

### 2.1 Upload import for new contacts

- **Type:** AFK
- **Blocked by:** Phase 1
- **PRD reference:** FR-1, FR-4, FR-5, FR-7–FR-10
- **System design reference:** §3, §5.2, §8, ADR-005

**Scope:** Contacts migration (incl. nullable `last_visited_at`, `last_messaged_at`), URL normalization per ADR-005, CSV parser (header found by column names; BOM, quoting, non-Latin), `POST /api/import` with 25 MB cap, single-transaction insert, summary (new/updated/skipped/errors), Import screen. Updating existing contacts is the next task.

**Acceptance criteria:**
- [x] Header row found after preamble lines; extra columns ignored; missing optional columns do not fail
- [x] Rows without a URL are skipped and listed; summary shows counts
- [x] Any error rolls back and changes nothing; files over 25 MB are rejected
- [x] Verifiable with fixture CSV tests and the Import screen

### 2.2 Re-import upserts and preserves data

- **Type:** AFK
- **Blocked by:** 2.1
- **PRD reference:** FR-6, FR-11
- **System design reference:** §5.2

**Scope:** Existing contacts (matched by normalized URL) have name/company/position/email/connected_on updated; contacts absent from the new file are kept. Never touches visit/message timestamps (and later groups, stages, notes).

**Acceptance criteria:**
- [x] Re-importing a changed file updates fields and reports `updated` counts
- [x] Timestamps set on a contact survive re-import
- [x] Contacts missing from the file remain
- [x] Verifiable with pytest

### 2.3 Keep uploaded CSVs in the data folder

> **Revised 2026-11-08:** this task was 'Import from folder'. The folder import (FR-2, FR-3) was removed as redundant with upload (decision 73) and replaced by this smaller task.

- **Type:** AFK
- **Blocked by:** 2.1
- **PRD reference:** FR-72 (FR-2 and FR-3 dropped)
- **System design reference:** §5.2, §6, §10 (D73)

**Scope:** Every uploaded CSV is also written to the data folder (`DATA_DIR`, `/data` in Docker) as `<kind>-<YYYYMMDD-HHMMSS>-<sanitised name>.csv` by a shared helper (`services/uploads.py`). This task wires it into connections import (`kind = import`); tasks 4.4 (`group-members`, saved on apply) and 6.1 (`bulk-stage`, saved on preview) reuse it. `POST /api/import/folder` and the Import-from-folder button do not exist.

**Acceptance criteria:**
- [x] A successful upload leaves a copy in the data folder with identical bytes
- [x] A second upload never overwrites the first (timestamp and counter), and a rejected file is kept too
- [x] Unsafe file names (`../`, spaces, symbols) are sanitised and cannot escape the data folder
- [x] A missing, unwritable or read-only data folder does not fail the import
- [x] The folder-import endpoint is gone; the Import page has no folder button and says copies are kept in `data/`
- [x] Verifiable with pytest and the Playwright flows (files appear in the data folder)

### 2.4 Contacts list with paging and sort

- **Type:** AFK
- **Blocked by:** 2.1
- **PRD reference:** FR-13, FR-16, FR-18
- **System design reference:** §4, §6

**Scope:** `GET /api/contacts` with offset paging (~100) and sort by any column (nulls handled for last visited/messaged, oldest first); table UI with the PRD's columns. Group badges appear in Phase 4.

**Acceptance criteria:**
- [x] Table shows name, position, company, LinkedIn link, connected-on, last visited, last messaged
- [x] Sorting any column works server-side across pages
- [x] Verifiable via API tests and UI

### 2.5 Contacts search and filters

- **Type:** AFK
- **Blocked by:** 2.4
- **PRD reference:** FR-14, FR-15
- **System design reference:** §4, §6

**Scope:** `LIKE` search over name/company/position; filters: company, position keyword, connected year, never visited, never messaged, not in any group.

**Acceptance criteria:**
- [x] Search matches across the three fields
- [x] Each filter narrows results correctly and combines with search and sort
- [x] 'Not in any group' returns all contacts until groups exist (Phase 4 re-verifies)
- [x] Verifiable with API tests

### 2.6 Performance check at 10,000 contacts

- **Type:** AFK
- **Blocked by:** 2.2, 2.5
- **PRD reference:** §12 Performance, FR-18
- **System design reference:** §7

**Scope:** Seed 10,000 contacts and assert the budgets: list/search page < 1 s, import of 10,000 rows < 10 s. Records measured numbers, replacing the design's unmeasured assumptions.

**Acceptance criteria:**
- [x] Import of 10,000 rows < 10 s
- [x] Contacts list and search < 1 s
- [x] Results recorded in the phase file or a test report
- [x] Verifiable by running the benchmark test

### 2.7 Two import modes: add and fresh import

> Added 2026-11-08 (decision 75).

- **Type:** AFK
- **Blocked by:** 2.1, 2.2, 2.3
- **PRD reference:** FR-74, FR-75
- **System design reference:** §5.2, §6 (backups)

**Scope:** `POST /api/import?mode=add` (default; the existing upsert) and `?mode=fresh&confirm=RESET`; `GET /api/import/stats`. Fresh import writes a backup first, then deletes contacts, groups and pipeline templates (cascades), re-creates the default Starter template and loads the file in one transaction (a complete reset, decision 77). Import page: 'Upload and add to contacts' and 'Upload and Fresh import' with a confirmation dialog (live counts, typed `RESET`).

**Acceptance criteria:**
- [x] Missing or wrong confirmation phrase is rejected (400) and nothing changes; an unknown mode is 422
- [x] Fresh import deletes contacts, groups, memberships, stages, history, notes and all pipeline templates, then re-creates the default Starter template (custom and renamed templates are gone)
- [x] A bad file is rejected before any deletion; a failure midway rolls the wipe back
- [x] A backup holding the old data is written to `db/backups/pre-fresh-import-*.sqlite`
- [x] Add mode keeps everything; saved copies are named `import-add-` / `import-fresh-`
- [x] The UI dialog states what will be deleted and keeps the button disabled until `RESET` is typed (case sensitive)

### 2.8 Boolean search and group filter on the contacts list

> Added 2026-11-08 (decision 79); builds on 2.5 and needs groups from Phase 4 for the group terms.

- **Type:** AFK
- **Blocked by:** 2.5, 4.2
- **PRD reference:** FR-77 (extends FR-14, FR-15)
- **System design reference:** §6 Search, §4 Contacts

**Scope:** `backend/app/search.py` parser and SQL builder; `group` filter on `GET /api/contacts`, `/api/contacts/ids` and `/api/export`; Group box and a Search help panel on the Contacts page.

**Acceptance criteria:**
- [x] AND, OR, NOT, `-word`, parentheses, quoted phrases, implicit AND and `field:term` work in every box; lowercase `and`/`or` are plain words
- [x] Group box: `ML OR HR`, `Hot AND NOT ML`, `NOT Hot` (includes people in no group)
- [x] Boxes combine with AND; select-all-matching and export honour the same filters
- [x] Syntax errors (missing paren, dangling operator, unclosed quote, too long or too many terms) return a clear 400 and the UI shows it
- [x] `%`, `_` and quotes are literal and cannot inject SQL
- [x] Playwright flow checks the UI end to end

### 2.9 Optional group name on add-mode import

> Added 2026-11-09 (decision 80).

- **Type:** AFK
- **Blocked by:** 2.7, 4.1
- **PRD reference:** FR-78
- **System design reference:** §5.2, §5.6, §4 Import

**Scope:** Optional `group` parameter on `POST /api/import`; Group name field with suggestions on the Import page; summary shows the group result. Group creation and membership run inside the import transaction.

**Acceptance criteria:**
- [x] With a name, every person with a valid URL (new or already known) is added; the group is created without a pipeline when missing
- [x] An existing group is reused case-insensitively; re-uploading is idempotent (already-members are counted, not duplicated); pipelined groups put members at the first stage
- [x] Blank or no name behaves exactly as before and creates no group; the field clears after each upload
- [x] A failed import or a bad file creates no group; a name over 100 characters is rejected (422)
- [x] Contacts lists everyone and the Group filter finds the group's members
- [x] Playwright flow covers upload with and without a group name
