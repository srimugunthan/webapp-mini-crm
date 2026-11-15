# Phase 4: Groups and membership

**Depends on:** `phase3-visit-tracking-and-messages.md`
**Status:** Implemented — see [phase report](../../docs/phase-reports/phase4.md)

## Design components touched

§3 groups and group_members, §4 Groups and Members

## Objective

The user can create groups, put contacts into them (from the Contacts list, from the group page, or from a CSV), and view a group's members with dates and filters. Stages arrive in Phase 5.

> **Revised 2026-11-08:** task 4.2 gained the selection bar and 'Select all N matching'; new task 4.4 adds 'Add members' on the group page and CSV adding, including an optional CSV on the create-group form (decisions 64, 65).

## Independently testable when

Create/rename/delete groups; add selected contacts from the contacts list, the Add members dialog, or a CSV; the group page lists members with working visit links and filters; deleting a group keeps contacts.

## Tasks

Each task is a thin vertical slice through every layer it touches, demoable or verifiable on its own. Design refs point to [system-design.md](../../system-design.md); PRD refs to [the PRD](../../linkedin-mini-crm-PRD.md).

### 4.1 Groups CRUD

- **Type:** AFK
- **Blocked by:** Phase 1
- **PRD reference:** FR-19, FR-23
- **System design reference:** §3, §4

**Scope:** Groups and group_members migration, `GET/POST /api/groups`, `PATCH/DELETE /api/groups/{id}`, groups list with member counts, unique names, delete confirmation stating member count. Pipeline selection on create comes in Phase 5.

**Acceptance criteria:**
- [x] Duplicate names rejected
- [x] Delete confirmation shows member count; contacts are not deleted
- [x] Verifiable via API tests and UI

### 4.2 Add contacts to groups and the selection bar

- **Type:** AFK
- **Blocked by:** 4.1, 3.2
- **PRD reference:** FR-17, FR-20–FR-22, FR-71
- **System design reference:** §4, §5.6

**Scope:** Multi-select on the contacts list with a **selection bar**: when rows are ticked it shows the count and offers Add to group, Mark N messaged (`messaged-bulk`, task 3.2) and Clear selection; 'Select all N matching' (`GET /api/contacts/ids`) extends the selection across pages; changing a filter clears the selection; with nothing ticked the bar explains what ticking does. Group badges; `POST/DELETE` members; a contact may be in many groups. (Export selected is added in task 7.3.)

**Acceptance criteria:**
- [x] Bulk add works and is idempotent
- [x] Remove from group keeps the contact
- [x] Badges and the 'not in any group' filter reflect membership
- [x] Selection bar appears only with a selection; 'Select all N matching' selects across pages; a filter change clears the selection
- [x] Demoable or verifiable in isolation

### 4.3 Group page members table

- **Type:** AFK
- **Blocked by:** 4.2, 3.1
- **PRD reference:** FR-24, FR-25
- **System design reference:** §4

**Scope:** (Revised 2026-11-08: members table has checkboxes, highlighted ticked rows and a selection bar with Export N selected, Mark N messaged and Remove N from group; compact layout, decision 74.) Members table (name, title, company, `/go` link, last visited, last messaged, follow-up placeholder) with sort and filters: not visited in N days, not messaged in N days.

**Acceptance criteria:**
- [x] Links use `/go/{id}` and update last visited in place
- [x] Filters and sorts return correct members
- [x] Each row has Mark messaged (now) and a past-date picker with Set, like the contacts list; the table fits laptop widths (1280, 1366, 1536 px) without sideways scrolling (decision 78)
- [x] Ticked rows are highlighted; the selection bar exports only the ticked members of the group, marks them messaged, or removes them from the group; a filter change clears the selection
- [x] Verifiable via API tests and UI

### 4.4 Add members from the group page and from a CSV

- **Type:** AFK
- **Blocked by:** 4.1, 4.2
- **PRD reference:** FR-69, FR-70
- **System design reference:** §5.6, §4 Members, ADR-005

**Scope:** `POST /api/groups/{id}/members/csv` (URL column; `apply=false` previews, `apply=true` adds). Group page **Add members** dialog with two tabs: pick from contacts (search, tick, add) and upload CSV (preview of will be added / already in the group / not found, then confirm). Optional CSV file on the create-group form, applied right after creation; a bad CSV does not stop the group being created and the message says so. Matching is by normalized URL; no contacts are created. Pipelined groups put new members at their first stage once Phase 5 exists.

**Acceptance criteria:**
- [x] Preview changes nothing; apply adds only matched contacts; repeating it adds nobody
- [x] Unmatched URLs and a file without a URL column are reported (400 for the latter); unknown group is 404
- [x] Search-and-pick adds the ticked contacts and says how many were already members
- [x] Create-group CSV fills the group and reports added and not-found counts
- [x] The uploaded CSV is saved in the data folder when the add is applied (kind `group-members`)
- [x] Verifiable via API tests and the Playwright flow 'add people to a group'
