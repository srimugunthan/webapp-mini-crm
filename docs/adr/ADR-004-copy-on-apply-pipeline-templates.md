# ADR-004: Model pipelines as copy-on-apply templates, and let groups have none

**Status:** Accepted
**Date:** 2026-11-08
**Deciders:** Srimugunthan

---

## Context

The PRD (§5, §6.5) gives each group its own ordered stage list, with stage and stage-change time stored on the membership. During the design interview (Q1, Q22, Q23) the owner described multiple reusable pipelines, such as `shortlisted → reachout → messaged → closed`, where one pipeline is applied to a group, several groups can use the same pipeline, and some groups have no pipeline at all.

---

## Decision

We will treat a pipeline as a saved template (a starter template is seeded, and any group's stages can be saved as a new template). Applying a template copies its stages into the group's own `stages` rows, so later edits or deletion of the template never change groups that already copied it. A group may have no pipeline, in which case its members have a null stage. Applying a pipeline to null-stage members moves them to its first stage after a confirmed preview, changing pipelines maps members by same-named stage with a preview for unmatched ones, and removing a pipeline asks for confirmation and keeps stage history.

---

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Shared pipeline reference | One edit updates every group on it; no copies | Stages belong to the pipeline, not the group; one edit can reshuffle stages in groups you aren't viewing; history gets harder |
| Shared with edit lock and versioning | Safe shared edits | Most complex: versions, opt-in upgrades |
| **Copy on apply (chosen)** | Keeps the PRD's per-group `stages`, stage history and editor unchanged; no cross-group surprises | Copies can drift from the template; template edits don't propagate |

Copy on apply was taken as the default because the template-versus-sharing question was left unanswered; the owner's wording is consistent with it and no switch to shared pipelines was requested.

---

## Consequences

**Positive:**
- The schema from the PRD (per-group stages, per-membership stage) stays as it is.
- Stage history and FR-35 (the stage editor) are unaffected.
- Template edits and deletion are always safe.

**Negative / Accepted Tradeoffs:**
- Copies can drift from the template over time, and there is no "update groups from template" action.
- Null stages must be handled in the UI and queries: hidden stage controls, disabled bulk stage, and no days-in-stage.
- A pipeline change on a group with members needs a preview flow.

---

## Implementation notes (2026-11-08)

Built as decided, and still the unconfirmed default described above. Applying a template to an existing group replaces the group's stages with copies and re-points members (stage-less members go to the first stage, same-named stages map across case-insensitively, unmatched ones need a chosen target) in one transaction, writing a history row per member. Details added while building: each group has a `pipeline_epoch` that is bumped on apply, remove and stage deletion, and a bulk undo is refused if the epoch changed since the batch (decision 60, which resolves the open risk this ADR's negative consequences pointed at); history rows keep stage names so they survive stage deletion (decision 61); the template screen is minimal (decision 66). Covered by pytest.
