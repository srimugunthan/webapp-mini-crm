# Phase 3: Visit tracking and message log

**Depends on:** `phase2-contacts-and-import.md`
**Status:** Implemented — see [phase report](../../docs/phase-reports/phase3.md)

## Design components touched

§3 contact timestamps and notes, §4 Visits and Contacts, §5.1 Visit tracking, §8 Redirects

## Objective

Clicking any LinkedIn link in the app records a visit and redirects; the user logs messages by hand (now, a past date, or for a whole selection) and keeps notes per contact.

> **Revised 2026-11-08:** the return prompt (old task 3.3, FR-62) and the 'Visited, not logged' list (old task 3.4, FR-63) were **removed** after use showed they added noise (decision 62). Old task 3.5 (notes) is now 3.3. The pending-visits API was deleted.

## Independently testable when

Integration test of `/go/{id}` (timestamp and redirect target), manual left/middle-click check, Mark messaged (now and past date), notes on the contact drawer. Nothing prompts for messaging.

## Tasks

Each task is a thin vertical slice through every layer it touches, demoable or verifiable on its own. Design refs point to [system-design.md](../../system-design.md); PRD refs to [the PRD](../../linkedin-mini-crm-PRD.md).

### 3.1 Visit tracking via /go/{id}

- **Type:** AFK
- **Blocked by:** Phase 2 (2.4)
- **PRD reference:** FR-26–FR-32
- **System design reference:** §5.1, §8, ADR-005

**Scope:** `GET /go/{contact_id}`: only https `linkedin.com`/`www.linkedin.com`, skip update on prefetch headers, 302; UI links open in a new tab; last-visited cell updates in place after click.

**Acceptance criteria:**
- [x] Redirect and `last_visited_at` update asserted in an integration test
- [x] Non-LinkedIn or non-https stored URL returns an error
- [x] Left-click, middle-click and open-in-new-tab all count without JS dependence
- [x] Prefetch-header requests don't update
- [x] Demoable or verifiable in isolation

### 3.2 Mark messaged

- **Type:** AFK
- **Blocked by:** Phase 2 (2.4)
- **PRD reference:** FR-61
- **System design reference:** §4

**Scope:** `POST /api/contacts/{id}/messaged` (now or a given past date, stored as local noon), per-row **Mark messaged** button plus a date box with **Set** on the contacts list, and `POST /api/contacts/messaged-bulk` (used by the selection bar's **Mark N messaged**, added in task 4.2).

**Acceptance criteria:**
- [x] Button sets last messaged to now; picker sets a past date
- [x] Value is the same from every view (stored on contact)
- [x] Bulk endpoint sets several contacts at once
- [x] Verifiable via API test and UI

### 3.3 Contact notes and detail drawer

- **Type:** AFK
- **Blocked by:** Phase 2 (2.4)
- **PRD reference:** FR-64
- **System design reference:** §3, §4

**Scope:** Notes table migration, `GET/POST /api/contacts/{id}/notes`, contact detail drawer with profile fields and timestamped notes. Memberships and history are added in later phases.

**Acceptance criteria:**
- [x] Add and list notes with timestamps
- [x] Notes survive re-import
- [x] Verifiable via API tests and drawer

