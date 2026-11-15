# Phase 5: Pipelines and stage moves

**Depends on:** `phase4-groups-and-membership.md`
**Status:** Implemented — see [phase report](../../docs/phase-reports/phase5.md)

## Design components touched

§3 stages, templates, stage_history, §4 Stages and Pipelines, §5.3 Stage move, §5.5 Pipelines, ADR-004

## Objective

Groups can have an ordered stage pipeline, created from a template or none; members move through stages with history; the group page shows chips, days in stage and follow-up dates.

## Independently testable when

Create groups with/without pipelines, edit stages, apply/remove templates with previews, move members by dropdown and next/back with history rows, filter by chip, track follow-ups.

## Tasks

Each task is a thin vertical slice through every layer it touches, demoable or verifiable on its own. Design refs point to [system-design.md](../../system-design.md); PRD refs to [the PRD](../../linkedin-mini-crm-PRD.md).

### 5.1 Stage editor

- **Type:** AFK
- **Blocked by:** Phase 4 (4.3)
- **PRD reference:** FR-33, FR-35, FR-36
- **System design reference:** §3, §4

**Scope:** Stages migration; `GET/POST /api/groups/{id}/stages`, `PATCH/DELETE /api/stages/{id}`; editor to add, rename, reorder, mark final (several allowed), paste a comma-separated list; deleting a stage with members requires choosing a target or clearing.

**Acceptance criteria:**
- [x] Stage names unique per group
- [x] Delete-with-members requires move-or-clear
- [x] Reorder persists
- [x] Verifiable via API tests and UI

### 5.2 Pipeline templates and create-group dropdown

- **Type:** AFK
- **Blocked by:** 5.1
- **PRD reference:** FR-34
- **System design reference:** §3, §5.5, ADR-004

**Scope:** Templates migration and starter template seed (Connected, Reached out, In conversation, Closed); minimal management screen (list, create, rename, delete); create-group dropdown preselects starter with 'No pipeline' available; stages copied on create.

**Acceptance criteria:**
- [x] Deleting a template never alters groups
- [x] Group created from template has copied, independent stages
- [x] 'No pipeline' creates a stage-less group
- [x] Verifiable via API tests and UI

### 5.3 Member stage and moves

- **Type:** AFK
- **Blocked by:** 5.1
- **PRD reference:** FR-37, FR-38, FR-42, FR-43
- **System design reference:** §3, §5.3

**Scope:** Members added to a pipelined group start at the first stage; stage dropdown saves via `PATCH .../members/{cid}` setting `stage_changed_at` and writing stage_history in one transaction; days-in-stage column and sort.

**Acceptance criteria:**
- [x] Move and history row are atomic (rollback test)
- [x] Days in stage computed and sortable
- [x] Verifiable via API tests and UI

### 5.4 Stage chips and filter

- **Type:** AFK
- **Blocked by:** 5.3
- **PRD reference:** FR-40, FR-41
- **System design reference:** §4

**Scope:** `GET /api/groups/{id}/stage-counts`, chips with counts that filter the list, filter reflected in URL `?stage=`.

**Acceptance criteria:**
- [x] Counts match members
- [x] Chip click filters and URL is bookmarkable
- [x] Verifiable in UI

### 5.5 Next/back buttons with confirmation and note

- **Type:** AFK
- **Blocked by:** 5.3
- **PRD reference:** FR-39, FR-44
- **System design reference:** §5.3

**Scope:** One-click next/back; moving into a final stage asks for confirmation; optional one-line note skippable with one keystroke, stored on history.

**Acceptance criteria:**
- [x] Final-stage confirmation shown
- [x] Note saved to stage_history when given, skippable otherwise
- [x] Verifiable in UI and API tests

### 5.6 No-pipeline group UI

- **Type:** AFK
- **Blocked by:** 5.3
- **PRD reference:** FR-37 (derived), Q36
- **System design reference:** §5.5, D39

**Scope:** For groups without stages, hide chips, stage dropdown, next/back and board; disable Bulk set stage; members still show dates and date filters.

**Acceptance criteria:**
- [x] Stage UI absent for stage-less groups
- [x] Date filters still work
- [x] Verifiable in UI

### 5.7 Apply template to existing group; remove pipeline

- **Type:** AFK
- **Blocked by:** 5.2, 5.3
- **PRD reference:** FR-34
- **System design reference:** §5.5, D38, D40

**Scope (as built: each apply/remove/stage delete bumps the group's `pipeline_epoch`, used by bulk undo in 6.4; history rows keep stage names):** `POST /api/groups/{id}/pipeline` with preview: stage-less members go to the first stage, staged members map to same-named stages (case-insensitive), unmatched need a chosen stage; history rows written. `DELETE` removes pipeline after confirming N members lose their stage, history kept.

**Acceptance criteria:**
- [x] Preview counts match the applied result
- [x] Unmatched members require a choice before confirm
- [x] Remove keeps stage_history
- [x] Verifiable via API tests

### 5.8 Save group stages as template

- **Type:** AFK
- **Blocked by:** 5.2
- **PRD reference:** FR-34
- **System design reference:** §4 Pipelines

**Scope:** Action on a group to save its current stages as a new template.

**Acceptance criteria:**
- [x] Saved template matches the group's order and final flags
- [x] Later group edits don't alter the template
- [x] Verifiable via API test

### 5.9 Follow-up dates

- **Type:** AFK
- **Blocked by:** Phase 4 (4.3)
- **PRD reference:** FR-65, FR-25
- **System design reference:** §3

**Scope:** `next_follow_up_at` on membership editable on the group page, overdue filter and highlight.

**Acceptance criteria:**
- [x] Date editable per membership (differs across groups)
- [x] Overdue filter and highlight correct
- [x] Verifiable via API test and UI

