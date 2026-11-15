# LinkedIn Mini CRM v1

Spec-driven implementation plan for LinkedIn Mini CRM, generated from the PRD and system-design.md. This folder is the source of truth for implementation — each phase file is self-contained and independently testable.

## Contents

- **`overview.md`** — goal, scope, non-goals, and a one-line summary of each phase.
- **`implementation-order.md`** — the phase dependency order and why. Read this before starting.
- `phase1-foundation-scaffold.md` — Foundation and scaffold
- `phase2-contacts-and-import.md` — Contacts and import
- `phase3-visit-tracking-and-messages.md` — Visit tracking and message log
- `phase4-groups-and-membership.md` — Groups and membership
- `phase5-pipelines-and-stage-moves.md` — Pipelines and stage moves
- `phase6-bulk-set-stage.md` — Bulk set stage
- `phase7-board-export-backup.md` — Board, export, backup and E2E

## How to use this folder

1. Read `overview.md` for context, then `implementation-order.md` for the sequence.
2. Open `phase1-foundation-scaffold.md` and implement its tasks in the order listed.
3. Verify the phase against its "Independently testable when" section before moving on.
4. Repeat for each subsequent phase file, in order. Do not skip ahead.

## Provenance

- PRD: [linkedin-mini-crm-PRD.md](../../linkedin-mini-crm-PRD.md)
- System design: [system-design.md](../../system-design.md)
- Generated: 2026-11-08
