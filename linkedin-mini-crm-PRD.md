# PRD: LinkedIn Mini CRM

| | |
|---|---|
| **Status** | Draft v0.3 (v1 implemented) |
| **Date** | 2026-11-08 |
| **Owner** | Srimugunthan |
| **Type** | Personal, single-user webapp with a local backend |

**Changes from v0.2 (2026-11-08, after building and using v1):** the "Did you message…?" return prompt (FR-62) and the "Visited, not logged" list (FR-63) were **dropped** because they added noise without helping; last messaged is logged by hand (FR-61). People can now be added to a group from the group page, by picking from contacts or by CSV (FR-69, FR-70). The Contacts list has a selection bar: add to group, export the selection, mark messaged, and "select all N matching" (FR-17, FR-71). Export respects filters and selections (FR-67).

**Also changed in v0.3 (later the same day):** the **Import from folder** button and the folder-import endpoint (FR-2, FR-3) were removed as redundant. Instead, every CSV the user uploads (imports, group member lists, bulk stage files) is saved as a copy in the `data/` folder (FR-72).

**Changes from v0.1:** backend is required (FastAPI + SQLite); two import paths (upload and "Import from folder" button, no file watching); per-group pipelines with a stage filter; bulk stage update from CSV; "last messaged" tracking; simplified backend scope.

---

## 1. Overview

LinkedIn Mini CRM is a lightweight personal CRM built on top of the user's LinkedIn connections export. The user imports their connections, organizes them into named groups (for example `school-friends`, `consulting-clients`, `job-search-consultants`), tracks when they last opened each person's LinkedIn profile and last messaged them, and moves people through a pipeline defined separately for each group.

It is deliberately small. It does not scrape LinkedIn, automate outreach, or sync messages. It is a private, free tool that runs on the user's own machine and answers three questions:

1. Who is in this group, and at which stage?
2. When did I last look at or message them?
3. Who needs follow-up next?

## 2. Problem statement

LinkedIn's own interface is poor for relationship management: no custom groups of connections, no "last visited" memory, no notes, no follow-up reminders, and no pipeline view. Existing tools fill this gap but are cloud-hosted, paid, aimed at sales teams, and often rely on browser extensions or automation that carry LinkedIn terms-of-service risk. The user wants a private, personal tool that handles groups, visit tracking, and a per-group pipeline without those trade-offs.

## 3. Goals and non-goals

### Goals
- G1. Import the LinkedIn connections CSV by uploading it in the webapp, without losing groups or history. A copy of each uploaded file is kept in the data folder.
- G2. Create named groups and fill them with a chosen subset of connections.
- G3. Show each group's members with name, title, company, LinkedIn URL, last visited date, last messaged date, and stage.
- G4. Record "last visited" automatically when the user clicks a person's LinkedIn link from the app.
- G5. Let each group have its own ordered pipeline stages, move people between them, and list the people in any one stage.
- G6. Bulk-set the stage for many people at once from a CSV.
- G7. Keep all data on the user's machine.

### Non-goals (v1)
- Scraping LinkedIn or using unofficial LinkedIn APIs.
- Sending messages or any outreach automation. The user sends messages on LinkedIn themselves.
- Reading or syncing LinkedIn messages automatically.
- Watching folders or running background jobs. Imports happen only when the user clicks a button.
- Emails, push notifications or scheduled reminders.
- Logins, multi-user accounts, teams or sharing.
- Automatic contact enrichment.
- Deal values and revenue tracking.
- Native mobile apps.

## 4. User and use cases

**Primary user:** one person managing a professional network of up to a few thousand connections, split across relationship types.

| # | Use case |
|---|---|
| UC1 | Upload my connections export in the app (a copy is kept in the data folder). |
| UC2 | Create a group called `consulting-clients` and add 25 connections from a search for "CTO". |
| UC3 | Define a different pipeline for `job-search` than for `consulting-clients`. |
| UC4 | Open a group and see everyone currently at `coldreached`. |
| UC5 | Click someone's LinkedIn link and have "last visited" update without any extra step. |
| UC6 | Come back from LinkedIn and record that I messaged the person. |
| UC7 | Upload a CSV of 40 people and set them all to `warmth-and-trustbuilding` in one action, adding any who are not yet in the group. |
| UC8 | Move a person to the next stage with one click and record a short note. |
| UC9 | Re-import a fresh export next month without duplicating contacts or losing groups, stages or history. |
| UC10 | See who in a group has not been visited or messaged for a long time. |

## 5. Core concepts

- **Contact:** a person from the LinkedIn export, identified by normalized LinkedIn profile URL.
- **Group:** a user-defined named collection of contacts. A contact can belong to many groups.
- **Pipeline:** the ordered list of stages belonging to one group. Every group has its own.
- **Stage:** one step in a group's pipeline (for example `connected → coldreached → warmth-and-trustbuilding → offer-given → negotiation → closed`). A stage can be marked **final** (for example `closed`, `closed-won`, `closed-lost`). A group may have more than one final stage.
- **Membership:** the link between a contact and a group. The stage, stage-change time and follow-up date live here, so the same person can be at different stages in different groups.
- **Last visited:** timestamp updated when the user opens the person's LinkedIn profile through the app.
- **Last messaged:** timestamp the user records when they send a LinkedIn message. Visiting a profile is not the same as messaging someone.

Example pipelines:

```
 job-search                          consulting-clients
 ----------                          ------------------
 connected                           connected
 coldreached                         coldreached
 warmth-and-trustbuilding            warmth-and-trustbuilding
 referral-asked                      offer-given
 interview                           negotiation
 closed                              closed
```

## 6. Functional requirements

Priority: **P0** = required for v1, **P1** = should have, **P2** = later.

### 6.1 Import connections

Two entry points share one import function, so behavior is identical.

| ID | Requirement | Priority |
|---|---|---|
| FR-1 | **Upload:** a file picker in the webapp sends a LinkedIn connections CSV to the backend. | P0 |
| FR-2 | ~~**Import from folder:** a button reads `Connections.csv` from a configured folder.~~ **Dropped in v0.3:** redundant with upload; the endpoint and button were removed. | Dropped |
| FR-3 | ~~Folder-file error handling.~~ **Dropped with FR-2.** A file that lacks the expected columns is still rejected with a clear error and changes nothing (FR-4, FR-9). | Dropped |
| FR-4 | The parser skips the notes lines before the header row and finds the header by column names. | P0 |
| FR-5 | Expected columns: First Name, Last Name, URL, Email Address, Company, Position, Connected On. Extra columns are ignored. Missing optional columns do not fail the import. | P0 |
| FR-6 | Import upserts by normalized LinkedIn URL: new contacts are added and existing ones are updated. Groups, memberships, stages, notes, last visited and last messaged are never overwritten or lost. | P0 |
| FR-7 | Rows without a URL are skipped and listed. | P0 |
| FR-8 | Show an import summary: new, updated, skipped, and error rows. | P0 |
| FR-9 | Each import runs in one database transaction. A failed import changes nothing. | P0 |
| FR-10 | Handle UTF-8 with BOM, quoted fields, commas, and non-Latin names. | P0 |
| FR-11 | Contacts missing from a newer export are kept and not deleted. | P0 |
| FR-12 | Accept LinkedIn's `.zip` archive and extract the connections file. | P2 |

### 6.2 Contacts list

| ID | Requirement | Priority |
|---|---|---|
| FR-13 | Show all contacts with name, position, company, LinkedIn link, connected-on date, last visited, last messaged, and group badges. | P0 |
| FR-14 | Free-text search across name, company and position (boolean operators supported, FR-77). | P0 |
| FR-15 | Filters: company, position keyword, group name, connected year, never visited, never messaged, not in any group. Company, position and group accept boolean queries (FR-77). | P1 |
| FR-16 | Sort by any column, including last visited and last messaged (oldest first). | P0 |
| FR-17 | Multi-select on the contacts list. Once rows are ticked a selection bar shows how many are selected and offers **Add to group**, **Export selected CSV** and **Mark messaged**, plus "Select all N matching" to extend the selection to every filtered result across pages. Changing a filter clears the selection. | P0 |
| FR-18 | Stays responsive at 10,000 contacts (pagination or virtual scrolling). | P0 |

### 6.3 Groups

| ID | Requirement | Priority |
|---|---|---|
| FR-19 | Create, rename and delete groups. Names are unique. | P0 |
| FR-20 | Add contacts to a group in bulk from the contacts list. | P0 |
| FR-21 | Remove contacts from a group. This does not delete the contact. | P0 |
| FR-22 | A contact can belong to any number of groups. | P0 |
| FR-23 | Deleting a group asks for confirmation and states how many members it has. Contacts are not deleted. | P0 |
| FR-24 | Group page lists members with name, title, company, LinkedIn URL, last visited, last messaged, stage, days in stage, and next follow-up date. | P0 |
| FR-25 | Group page sorting and filters: by stage, not visited in N days, not messaged in N days, follow-up overdue. | P0 |

### 6.4 Visit tracking

| ID | Requirement | Priority |
|---|---|---|
| FR-26 | Every LinkedIn link shown in the app points to `GET /go/{contact_id}` on the backend, not directly to LinkedIn. | P0 |
| FR-27 | The endpoint sets `last_visited_at = now()` for that contact and responds with an HTTP 302 redirect to the stored LinkedIn URL. | P0 |
| FR-28 | The link opens in a new tab and works for left-click, middle-click and "open in new tab", without relying on JavaScript. | P0 |
| FR-29 | The endpoint redirects only to `linkedin.com` or `www.linkedin.com` over https. Any other host returns an error. | P0 |
| FR-30 | `last_visited_at` is stored on the contact and is the same from every group. | P0 |
| FR-31 | The page updates the "last visited" cell after a click without a full reload. | P1 |
| FR-32 | Link prefetch or preview must not count as a visit where it can be detected. | P1 |

### 6.5 Pipelines and stages (per group)

| ID | Requirement | Priority |
|---|---|---|
| FR-33 | Each group has its own ordered list of stages. Stage names are unique within a group. | P0 |
| FR-34 | A new group is created with a starter pipeline (`Connected → Reached out → In conversation → Closed`) that the user can edit, or the user can paste a comma-separated list to define the whole pipeline at creation or later. | P0 |
| FR-35 | Stage editor on the group page: add, rename, reorder and delete stages, and mark a stage as final. A group can have several final stages. | P0 |
| FR-36 | Deleting a stage that has members requires choosing a stage to move them to, or clearing their stage. | P0 |
| FR-37 | A person added to a group starts at the group's first stage. | P0 |
| FR-38 | **Dropdown:** each member row has a stage dropdown that saves on change. | P0 |
| FR-39 | **Next / back buttons:** one click moves a member to the next or previous stage in order. Moving into a final stage asks for confirmation. | P0 |
| FR-40 | **Stage chips with counts** at the top of the group page, for example `All 40 · connected 22 · coldreached 8 · warmth 5`. Clicking a chip filters the list to people in that stage. | P0 |
| FR-41 | The stage filter is part of the URL (for example `/groups/3?stage=coldreached`) so it can be bookmarked. | P1 |
| FR-42 | Rows show "days in current stage" and can be sorted by it. | P0 |
| FR-43 | Moving a member sets `stage_changed_at` and writes a stage history record in one transaction. | P0 |
| FR-44 | On a stage move, offer an optional one-line note that can be skipped with one keystroke. | P1 |
| FR-45 | Final-stage members can be hidden from the default group view. | P1 |
| FR-46 | **Board view:** one column per stage with cards, and drag-and-drop between columns. The dropdown remains available as an alternative. | P1 |
| FR-47 | Keyboard shortcuts on a selected member: `]` next stage, `[` previous stage. | P2 |

### 6.6 Bulk stage update from CSV

Set the stage for many people in one group from a CSV.

| ID | Requirement | Priority |
|---|---|---|
| FR-48 | On the group page, a **Bulk set stage** action accepts a CSV file and a stage chosen from a dropdown of the group's stages. | P0 |
| FR-49 | The only required CSV column is the LinkedIn URL. A LinkedIn connections export can be used as is. | P0 |
| FR-50 | An optional `Stage` column sets a different stage per row. When present, it overrides the dropdown. Stage names are matched within the group, ignoring case. | P1 |
| FR-51 | People are matched to contacts by normalized LinkedIn URL. | P0 |
| FR-52 | **Overwrite means replace only the stage.** Each matched person's stage is replaced with the new one. Nothing else about them changes (notes, last visited, last messaged, follow-up date). Anyone not in the CSV is left untouched. | P0 |
| FR-53 | **People in the CSV who are not yet in the group are added to the group** at the chosen stage. | P0 |
| FR-54 | People already at the target stage are left unchanged, and their stage-change time is not reset. | P0 |
| FR-55 | URLs that match no contact are skipped and reported. The bulk update does not create new contacts. | P0 |
| FR-56 | Rows with an unknown stage name are skipped and reported. | P1 |
| FR-57 | **Preview before apply:** show counts (moved, already at stage, added to group, URL not found, unknown stage) and let the user download the problem rows, then confirm. | P0 |
| FR-58 | Apply runs in one transaction. It either fully succeeds or changes nothing. | P0 |
| FR-59 | Each changed person gets a stage history record tagged with a batch id, marked as a bulk update. | P0 |
| FR-60 | **Undo last bulk change** restores the previous stages for that batch, and removes anyone the batch added to the group. | P1 |

Example preview:

```
 Bulk set stage: coldreached
   32 will be moved to coldreached
    5 already at coldreached (no change)
    6 not in this group yet (will be added)
    2 URLs not found in your contacts (skipped)
    1 row with unknown stage (skipped)
   [Download problem rows]   [Cancel]   [Apply]
```

### 6.7 Last messaged, notes and follow-ups

The user sends messages on LinkedIn themselves. The app helps record that they did.

| ID | Requirement | Priority |
|---|---|---|
| FR-61 | `last_messaged_at` is stored on the contact. A **Mark messaged** button sets it to now, and a small date picker allows a past date. | P0 |
| FR-62 | ~~After the user clicks through to LinkedIn and returns to the app tab, show a prompt "Did you message {name}?"~~ **Dropped in v0.3:** the prompt appeared on every page open and was noise. The user logs messages manually (FR-61). | Dropped |
| FR-63 | ~~A **Visited, not logged** list.~~ **Dropped in v0.3:** it did not help the workflow. "Last visited" is still recorded and shown (FR-27). | Dropped |
| FR-64 | Free-text notes per contact, with timestamps. | P1 |
| FR-65 | A next follow-up date per membership, with an overdue filter and highlight. | P1 |
| FR-66 | Message templates with the person's first name filled in, and a "Copy template and open profile" action. The user pastes and sends on LinkedIn. | P2 |

### 6.8 Data portability

| ID | Requirement | Priority |
|---|---|---|
| FR-67 | Export to CSV: all contacts, a group, the contacts that match the current filters, or an explicit selection of ticked contacts. The export can be re-imported (it uses the LinkedIn column names plus extra columns). | P1 |
| FR-68 | Backup and restore by copying the single SQLite file, documented in the README. | P0 |
| FR-69 | **Add members from the group page.** An **Add members** button opens a dialog with two ways in: pick from contacts (search, tick, add) or upload a CSV with a URL column (preview of will be added / already in the group / URL not found, then confirm). Matching is by normalized URL; no new contacts are created; repeating it is safe. People added to a group with a pipeline start at its first stage. | P0 |
| FR-70 | The **create group** form has an optional CSV (URL column) so a group can be filled in one step. A failed CSV does not block creating the group. | P1 |
| FR-71 | **Mark messaged** is available for a whole selection on the contacts list (sets last messaged to now), besides the per-row button and date picker (FR-61). | P1 |
| FR-72 | **Keep uploaded files.** Every CSV uploaded in the app (connections import, group member list, bulk stage file) is also saved in the data folder as `<kind>-<YYYYMMDD-HHMMSS>-<original name>.csv` (kinds: `import`, `group-members`, `bulk-stage`). Names are sanitised and never overwrite an existing file; rejected files are kept too; the copy is best effort (a write failure is logged and does not fail the request). | P1 |
| FR-73 | **Selection on the group page.** The members table has checkboxes; ticked rows are highlighted. A selection bar offers **Export N selected CSV** (only ticked members of this group, with the Stage column), **Mark N messaged**, **Remove N from group** (confirms; contacts are kept) and Clear selection. Changing a filter clears the selection. Each member row also has **Mark messaged** (now) and a date box with **Set** (past date), the same as on the contacts list (FR-61); the per-row remove is a small ✕. The contacts table highlights ticked rows the same way and both tables are compact enough to show Name, Position, Company and LinkedIn without sideways scrolling. | P1 |
| FR-74 | **Two import modes.** The Import page offers (a) **Upload and add to contacts**: adds new people and updates existing ones by URL, deleting nothing (this is FR-6), and (b) **Upload and Fresh import**: replaces everything. | P0 |
| FR-75 | **Fresh import** deletes all contacts, groups, memberships, stages, stage history, notes, bulk-update state, batches and all pipeline templates (the default Starter template is re-created, as in a new install), then loads the file as the only connections. It needs a confirmation dialog that states what will be deleted (live counts) and requires typing `RESET`; the API also requires `confirm=RESET`. A backup of the database is written to `db/backups/pre-fresh-import-*.sqlite` first (the last 5 are kept). The file is validated before anything is deleted, and the wipe and the load are one transaction, so a failed import leaves the old data untouched. | P0 |
| FR-76 | **Restore from a .sqlite backup in the app.** The Import page lets the user upload a backup file (from *Download backup*, the CLI, or `db/backups/`) to replace the whole database. The file is validated first (SQLite header, integrity check, made by this app, not from a newer schema version) and previewed (counts in the file versus current data); the user must type `RESTORE`; the API requires `confirm=RESTORE`. The current database is saved to `db/backups/pre-restore-*.sqlite` first (last 5 kept); the swap uses SQLite's backup API so a failure keeps the current data; an older backup is upgraded by the migrations. The uploaded `.sqlite` is not copied into `data/`. Extends FR-68 (manual file copy still works with the app stopped). | P1 |
| FR-77 | **Boolean search on the contacts list.** The Search, Company, Position and new **Group** boxes all accept the same query language: `AND`, `OR`, `NOT` (uppercase; so lowercase "and" stays an ordinary word), `-word`, parentheses, `"exact phrase"`, implicit AND between words, and `field:word` for `name`, `company`, `position`/`title` or `group`. Every term is a case-insensitive contains match. The Search box defaults to name, company and position; the Group box matches group names, and `NOT` there includes contacts who are in no group. The boxes combine with AND. Invalid syntax (missing parenthesis, dangling operator, unclosed quote, over 300 characters or 30 terms) shows a clear message instead of results. The same filters drive "select all N matching" and the CSV export. A collapsible **Search help** explains the syntax with examples. | P1 |
| FR-78 | **Optional group name on import.** "Upload and add to contacts" has an optional **Group name** field (with suggestions from existing groups). When filled, everyone in the file who has a valid URL, whether new or already in the contacts, is also put in that group: the group is created without a pipeline if it does not exist, an existing one is reused (name match is case-insensitive), and people already in it are counted but not duplicated; members of an existing pipelined group start at its first stage. Blank means no group, as before. The group is created and filled in the same transaction as the import, so a failed import creates nothing. The summary shows the group name, whether it was created, how many were added, and a link to it. Typical use: a CSV of people you follow uploaded as group `Following`, while a CSV of new connections is uploaded with no group; Contacts shows both sets. Name limit 100 characters. | P1 |

## 7. Data model

```
contacts                      groups                    group_members
------------------------      -------------------       ----------------------------
id (PK)                       id (PK)                   group_id (FK)
first_name                    name (unique)             contact_id (FK)
last_name                     created_at                stage_id (FK, nullable)
company                                                 stage_changed_at
position                      stages                    next_follow_up_at
linkedin_url (unique,         -------------------       added_at
  normalized)                 id (PK)                   PK (group_id, contact_id)
email                         group_id (FK)
connected_on                  name                      stage_history
last_visited_at               position (int)            ----------------------------
last_messaged_at              is_final (bool)           id (PK)
created_at                    UNIQUE (group_id, name)   group_id, contact_id
updated_at                                              from_stage_id, to_stage_id
                                                        changed_at
notes                                                   source ('manual' | 'bulk')
------------------------                                batch_id (nullable)
id, contact_id (FK),                                    note
body, created_at
```

Design notes:
- `linkedin_url` is normalized (lowercase host, no trailing slash, no query string) before use as the unique key.
- Stage, stage-change time and follow-up date are per membership, so the same person can be at different stages in different groups.
- `last_visited_at` and `last_messaged_at` live on the contact.
- `batch_id` groups the history rows from one bulk update so it can be undone.
- All timestamps are stored in UTC and displayed in local time.

## 8. Key flows

### 8.1 Visit tracking and message logging

```
 Click link in app
        |
        v
 GET /go/42
        |
        +--> validate stored URL host is linkedin.com
        +--> UPDATE contacts SET last_visited_at = now() WHERE id = 42
        |
        v
 302 Redirect --> https://www.linkedin.com/in/someone   (new tab)

 ... user reads profile, sends the message on LinkedIn themselves ...

 Later, in the app: [Mark messaged] (or pick a past date, or tick several rows)
        |
        v
 POST /api/contacts/42/messaged --> last_messaged_at = now()   (no automatic prompt, see FR-62)
```

### 8.2 Moving a stage

```
 User action (dropdown / next button / drag)
        |
        v
 PATCH /api/groups/{gid}/members/{cid}  { stage_id }
        |
        +--> BEGIN
        +--> set group_members.stage_id, stage_changed_at = now()
        +--> insert stage_history row (+ optional note)
        +--> COMMIT
        |
        v
 UI updates the row; days-in-stage resets to 0
```

### 8.3 Import

```
 [Upload CSV]   (a copy is saved in data/)
        |
        v
 import_csv(bytes)
   locate header row --> for each row:
      normalize URL
      exists?  yes --> update name/company/position/email/connected_on
               no  --> insert new contact
 Groups, memberships, stages, notes, last visited, last messaged: untouched
 Return summary: new / updated / skipped (or an error, with no changes)
```

### 8.4 Bulk set stage

```
 Group page --> [Bulk set stage] --> choose CSV + stage
        |
        v
 POST /api/groups/{gid}/bulk-stage?preview=true
   match URLs --> classify each row:
     in group, other stage  --> will move
     in group, same stage   --> no change
     contact, not in group  --> will be added at that stage
     no contact found       --> skipped
     unknown stage name     --> skipped
        |
        v
 Show preview counts --> [Apply]
        |
        v
 POST /api/groups/{gid}/bulk-stage  (one transaction, batch_id assigned)
   set stage, stage_changed_at, write history rows, add missing members
```

## 9. Backend responsibilities

The backend (FastAPI + SQLite) holds the data and does the work the page asks for:

1. Imports connections from an uploaded CSV, and keeps a copy of every uploaded CSV in the data folder.
2. Serves the contacts list with search, filters, sorting and paging.
3. Manages groups: create, rename, delete, add and remove members (including adding from a CSV).
4. Tracks visits through `/go/{id}`, redirecting only to LinkedIn.
5. Runs each group's pipeline: stage CRUD, moving people, history, stage counts and the stage filter.
6. Applies bulk stage updates from CSV, with preview and undo.
7. Records last messaged dates, notes and follow-up dates.
8. Exports CSV (all, a group, filtered, or selected) and serves the web pages so one command starts the whole app.

It does not talk to LinkedIn, watch folders, send emails or reminders, or handle logins.

## 10. API outline

```
POST   /api/restore/preview                 validate an uploaded .sqlite backup and describe it (changes nothing)
POST   /api/restore                         replace the database with an uploaded backup; ?confirm=RESTORE
POST   /api/import                          upload connections CSV; ?mode=add (default) or ?mode=fresh&confirm=RESET; optional ?group=Name
GET    /api/import/stats                    counts shown in the fresh-import confirmation
GET    /api/contacts                        list, search, filter (q, company, position, group: boolean queries), sort, paginate
GET    /go/{contact_id}                     record visit, then 302 to LinkedIn
POST   /api/contacts/{id}/messaged          set last_messaged_at (now or given date)
POST   /api/contacts/messaged-bulk          set last_messaged_at for several contacts { ids, date? }
GET    /api/contacts/ids                    ids of every contact matching the filters (select all N matching)
GET    /api/contacts/{id}/notes             list notes
POST   /api/contacts/{id}/notes             add note

GET    /api/groups                          list groups with member counts
POST   /api/groups                          create group (with starter or pasted stages)
PATCH  /api/groups/{id}                     rename
DELETE /api/groups/{id}                     delete group (not contacts)

GET    /api/groups/{id}/members             members; filters: stage_id, not_visited_days,
                                            not_messaged_days, overdue
POST   /api/groups/{id}/members             bulk add { contact_ids: [...] }
POST   /api/groups/{id}/members/csv        add from a CSV (URL column); ?apply=false previews
DELETE /api/groups/{id}/members/{cid}       remove from group
PATCH  /api/groups/{id}/members/{cid}       change stage / follow-up date
GET    /api/groups/{id}/stage-counts        counts per stage for the chips

GET    /api/groups/{id}/stages              list stages
POST   /api/groups/{id}/stages              create stage (or paste list)
PATCH  /api/stages/{id}                     rename / reorder / mark final
DELETE /api/stages/{id}                     delete (requires reassignment)

POST   /api/groups/{id}/bulk-stage          CSV + stage; ?preview=true to preview only
POST   /api/groups/{id}/bulk-stage/undo     undo the last bulk batch

GET    /api/export                          CSV export; ?group_id=, ?ids=1,2,3, or the contacts filters
GET    /api/backup                          download a consistent SQLite backup
```

## 11. UX outline

**Screens**
1. **Import:** "Upload and add to contacts", "Upload and Fresh import" (red, typed confirmation), "Upload and restore database" from a .sqlite backup (red, preview and typed confirmation), result summary, backup download.
2. **Contacts:** searchable, filterable table with checkboxes. A selection bar appears when rows are ticked (Add to group, Export selected CSV, Mark messaged, Select all N matching); when nothing is ticked it offers "Export all N matching CSV".
3. **Groups:** list of groups with member counts.
4. **Group page:** **Add members**, stage chips with counts, table and board views, stage editor, bulk set stage, filters.
6. **Pipelines:** minimal template list (create, rename, delete).
5. **Contact detail (drawer or page):** profile fields, group memberships and stages, notes, history.

**Group page, table view**

```
 consulting-clients     [Table] [Board]     [Edit stages] [Bulk set stage]

 [All 40] [connected 22] [coldreached 8] [warmth 5] [offer-given 2] [negotiation 2] [closed 1]

 Name       Title     Company  LinkedIn         Visited  Messaged  Stage            In stage
 ---------  --------  -------  ---------------  -------  --------  ---------------  --------
 A. Rao     CTO       X Corp   linkedin.com/..  2 Nov    1 Nov     [coldreached  v]  3d  [<][>]
 P. Nair    VP Eng    Y Ltd    linkedin.com/..  28 Oct   --        [connected    v]  9d  [<][>]
```

**Group page, board view**

```
 connected        coldreached       warmth...         closed
+-----------+    +-----------+     +-----------+    +-----------+
| P. Nair   |    | A. Rao    |     | S. Iyer   |    | K. Menon  |
| VP Eng, Y |    | CTO, X    |     | Dir, Z    |    |           |
| 9d        |    | 3d        |     | 21d       |    |           |
+-----------+    +-----------+     +-----------+    +-----------+
```

**UX principles:** every common action is one click; destructive and bulk actions show a preview or confirmation; the table works at phone width; the dropdown remains available wherever drag-and-drop is.

## 12. Non-functional requirements

| Area | Requirement |
|---|---|
| Performance | Contacts list and group pages load in under 1 second at 10,000 contacts. Import of 10,000 rows completes in under 10 seconds. Bulk stage update of 1,000 rows previews in under 3 seconds. |
| Storage | Single SQLite file. No external services. |
| Privacy | All data stays on the user's machine. No analytics, telemetry or third-party calls at runtime. |
| Security | Binds to `127.0.0.1` by default. `/go/{id}` restricts redirects to LinkedIn hosts. All SQL parameterized. Uploaded files are parsed as data only. Hosting beyond localhost requires adding authentication first. |
| Compliance | Uses only the user's own official LinkedIn data export. No scraping or automation of LinkedIn. |
| Reliability | Imports, stage moves and bulk updates are transactional. Backup is a file copy. |
| Portability | Runs on macOS, Windows and Linux with a single start command. |
| Accessibility | Keyboard-operable dropdowns and buttons. Board drag-and-drop has a non-drag alternative. |

## 13. Technical approach

- **Backend:** FastAPI (Python) with raw `sqlite3` and numbered SQL migrations (ADR-002; supersedes the Alembic suggestion in v0.2).
- **Frontend:** React single-page app with TypeScript and Vite (ADR-001; supersedes the HTMX suggestion in v0.2). The board uses native browser drag-and-drop with a dropdown alternative.
- **Uploaded files:** each uploaded CSV is also written to the data folder (`DATA_DIR`, default `data/`, `/data` in Docker) as `<kind>-<YYYYMMDD-HHMMSS>-<original name>.csv`. Existing files are never overwritten, and a failure to write only logs a warning.
- **Packaging:** one command to start, one file for data, and a README covering the LinkedIn export steps, where uploaded copies go, and backup.
- **Tests:** CSV parsing (preamble, BOM, odd quoting), URL normalization, upsert behavior that preserves groups and stages, stage-move transactions, bulk-stage preview and apply (including adding missing members and undo), and an integration test for `/go/{id}` that checks the timestamp update and redirect target.

## 14. Milestones

| Milestone | Scope | Outcome |
|---|---|---|
| M1: Foundation | Schema, upload import with upsert, contacts list with search and sort | Network visible and searchable |
| M2: Groups and tracking | Groups CRUD, bulk add, group page, `/go/{id}` visit tracking | Core idea working |
| M3: Per-group pipelines | Per-group stages, stage editor with pasted list, dropdown, next/back, stage chips and filter, history | Pipeline usable |
| M4: Bulk stage and messaging | Bulk set stage from CSV with preview and undo, last messaged (logged by hand), notes, follow-up dates | Daily-use readiness |
| M5: Board and export | Board view with drag-and-drop, hide final stages, CSV export | Visual pipeline |
| Later | Message templates, keyboard shortcuts, `.zip` import | Polish |

## 15. Success metrics

- Import of a real export, with groups and pipelines set up, takes under 30 minutes.
- Last visited updates correctly on every click path (left, middle, new tab) in manual testing.
- Re-import by upload preserves 100% of groups, stages and notes.
- A bulk stage update of 50 people takes under a minute from file to applied.
- Answering "who in `consulting-clients` is at `coldreached`?" takes under 5 seconds.
- The user is still opening the app weekly after one month.

## 16. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| LinkedIn changes the export format | Import breaks | Detect header by column names, tolerate missing columns, show clear errors |
| Bulk update overwrites the wrong stages | Pipeline data wrong | Mandatory preview, one transaction, history with batch id, undo |
| Wrong file uploaded | Bad import | Validate columns before touching data, show the summary, 25 MB cap |
| Visiting a profile is mistaken for contact | Misleading signal | Separate `last_messaged_at`, clear labels; the user logs messages by hand |
| Link prefetch triggers false visits | Inaccurate dates | Ignore prefetch requests where detectable |
| Open-redirect abuse of `/go/{id}` | Security issue | Allow only LinkedIn hosts over https |
| Contact data leaks if later hosted | Privacy harm | Localhost-only default; require auth before any hosting |
| Scope creep toward a full CRM | Tool becomes heavy | Non-goals list; revisit only when a real need appears |

## 17. Assumptions and open questions

**Decided**
- Backend required: FastAPI + SQLite.
- One import path: upload in the app. (v0.2 also had "Import from folder"; removed in v0.3.) No file watching.
- Stages are defined per group. Stage is stored on the membership.
- Bulk stage update adds people who are not yet in the group, and replaces only the stage.
- No deal values in v1.
- (v0.3) No automatic "did you message?" prompt and no "Visited, not logged" list.
- (v0.3) Groups can have no pipeline; a pipeline is a reusable template copied into a group on apply (ADR-004).
- (v0.3) Undoing a bulk stage change is refused if the group's pipeline changed after the batch.
- (v0.3) Every uploaded CSV is saved to the data folder (`/data` in the container, mounted from `./data`).

**Assumed, please confirm**
1. A person added to a group starts at the group's **first stage**, rather than "no stage."
2. A group can have **more than one final stage** (for example `closed-won` and `closed-lost`), and using just one is fine.
3. When the bulk CSV has a `Stage` column, it overrides the stage chosen in the dropdown.
4. If someone disappears from a newer export, they are **kept**, not deleted.
5. The app stays **local-only**. Any hosting later would need authentication added first.
6. ~~The folder import reads one fixed file name.~~ Moot: there is no folder import any more.

## 18. Out of scope for now, candidates for later

- Browser extension that detects when a message is sent.
- Import of the LinkedIn messages export to backfill last messaged dates.
- Enrichment of email and company data.
- Reminders by email or notification.
- Deal and revenue tracking.
- Multi-device sync.
