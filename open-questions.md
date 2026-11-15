# Open Questions (Round 3): LinkedIn Mini CRM system design

Fill in the **Your answer** column and send the file back. Write a letter or number for a choice, "accept" to take my recommendation, or free text. Blank answers will take my recommendation.

| # | Question (options) and my recommendation | Your answer |
|---|---|---|
| Q35 | **Default pipeline for a new group.** You said some groups have no pipeline. On the "create group" form: (a) the pipeline dropdown is preselected to the starter template, with "No pipeline" and your own templates one click away, (b) preselected to "No pipeline", (c) force a choice with no preselection. *Recommend (a): matches the PRD's starter pipeline (FR-34) while keeping "No pipeline" easy.* | |
| Q36 | **What a no-pipeline group looks like.** Members have no stage. Confirm: the group page hides stage chips, the stage dropdown, next/back buttons and the board; "Bulk set stage" is disabled; members are still listed with last visited, last messaged and follow-up date; and the group can still be filtered by visited and messaged dates. *Recommend yes.* | |
| Q37 | **Applying a pipeline to a group whose members have no stage.** (a) Put all of them at the pipeline's first stage, shown in a preview you confirm, with a stage-history row for each, (b) leave them without a stage until you set one, (c) choose in the preview. *Recommend (a): consistent with "new members start at the first stage" (decision 13).* | |
| Q38 | **Removing a pipeline from a group** (back to no pipeline). (a) Allowed with a confirmation that states how many members will lose their stage; stage history is kept, (b) not allowed once members have stages. *Recommend (a): keeps the history and matches the delete-confirmation pattern (FR-23).* | |
| Q39 | **Upload size limit for CSV imports.** (a) Reject files over 25 MB with a clear error, (b) no limit. A 10,000-row connections export is well under 5 MB. *Recommend (a): protects against a wrong file being uploaded by accident (the PRD's "wrong file" risk).* | |
| Q40 | **Automatic backup before migrations.** On startup, if a migration is pending: (a) copy the database file using SQLite's backup API to `db/backups/` first, and keep the last 5, (b) migrate with no automatic backup. *Recommend (a): a failed migration is the main way to lose data, and the backup is cheap.* | |
| Q41 | **Container health and restart.** (a) A `/api/health` endpoint, a Compose `healthcheck`, and `restart: unless-stopped`, (b) no healthcheck and no restart policy. *Recommend (a): small and keeps the app available after a Docker restart or laptop reboot.* | |
| Q42 | **Concurrent edits (two browser tabs).** (a) Last write wins, no version checks, (b) optimistic locking with a version column and a conflict message. *Recommend (a): one user, and the stage history already records every change.* | |
| Q43 | **Backend test approach.** (a) pytest against a real temporary SQLite file per test (no database mocks), with fixture CSVs for the odd cases in the PRD (preamble, BOM, quoting, non-Latin names), (b) mock the repository layer. *Recommend (a): the PRD's riskiest behavior is transactional SQL, which mocks can't check.* | |

## Notes

- Q35–Q38 follow from your Q23 answer that groups can have no pipeline. They also change decision 13: members start at the first stage only when the group has a pipeline.
- Q39–Q43 are the deployment and failure-mode questions I said were coming. They don't depend on any open answer.
- I did not hear a switch to shared pipelines in Q23, so decision 38 keeps copy-on-apply. Tell me here if that's wrong.
- All round 2 answers (Q23–Q34, blanks defaulted) are logged as decisions 38–50 in `decision-log.md`.
- If this round settles cleanly, I expect the frontier to be empty. Next would come the ADR check on the decision log.
