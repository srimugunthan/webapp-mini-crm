# Phase 6: Bulk set stage

**Depends on:** `phase5-pipelines-and-stage-moves.md`
**Status:** Implemented — see [phase report](../../docs/phase-reports/phase6.md)

## Design components touched

§3 bulk_staging, §4 Bulk stage, §5.4 Bulk set stage, §10 Failure modes

## Objective

The user can set stages for many people from a CSV with a safe preview/apply flow and undo.

## Independently testable when

Preview shows correct counts; apply is atomic and aborts when stale; undo restores the last batch or refuses if the pipeline changed.

## Tasks

Each task is a thin vertical slice through every layer it touches, demoable or verifiable on its own. Design refs point to [system-design.md](../../system-design.md); PRD refs to [the PRD](../../linkedin-mini-crm-PRD.md).

### 6.1 Bulk preview and staging token

- **Type:** AFK
- **Blocked by:** Phase 5 (5.3), Phase 2 (2.5)
- **PRD reference:** FR-48, FR-49, FR-51, FR-55, FR-57
- **System design reference:** §5.4, §6

**Scope:** `bulk_staging` migration; `POST /api/groups/{id}/bulk-stage?preview=true` classifies rows (move, no change, add, URL not found), stores a 30-min single-use token; UI with counts and downloadable problem rows; expired staging rows purged. Preview of 1,000 rows < 3 s.

**Acceptance criteria:**
- [x] Counts match PRD example categories
- [x] Problem rows downloadable
- [x] Preview of 1,000 rows < 3 s
- [x] The uploaded bulk CSV is saved in the data folder (kind `bulk-stage`)
- [x] Verifiable via API tests

### 6.2 Bulk apply by token

- **Type:** AFK
- **Blocked by:** 6.1
- **PRD reference:** FR-52–FR-54, FR-58, FR-59
- **System design reference:** §5.4, §10

**Scope:** `POST .../bulk-stage {token}`: re-classify; abort with rollback if counts differ or token expired/used; set stages, add missing members, write history with `batch_id` and source=bulk; other fields untouched.

**Acceptance criteria:**
- [x] Same-stage members' `stage_changed_at` not reset
- [x] Stale preview or expired token aborts with re-preview message
- [x] All-or-nothing (rollback test)
- [x] Verifiable via API tests

### 6.3 Stage column override and unknown stages

- **Type:** AFK
- **Blocked by:** 6.1
- **PRD reference:** FR-50, FR-56
- **System design reference:** §4 Contract rules

**Scope:** Optional CSV `Stage` column overrides the dropdown (case-insensitive within group); unknown names skipped and reported.

**Acceptance criteria:**
- [x] Per-row override works
- [x] Unknown stage reported in preview and problem rows
- [x] Verifiable via API tests

### 6.4 Undo last bulk change

- **Type:** AFK
- **Blocked by:** 6.2
- **PRD reference:** FR-60
- **System design reference:** §5.4, §11

**Scope:** `POST .../bulk-stage/undo` restores previous stages and removes members the batch added. Refused with a clear message if the group's pipeline changed after the batch (decision 60): the batch records the group's `pipeline_epoch` in `bulk_batches` and undo compares it. Only the latest un-undone batch can be undone.

**Acceptance criteria:**
- [x] Undo restores prior stages and removes added members
- [x] Refused with message after a pipeline change
- [x] Verifiable via API tests

