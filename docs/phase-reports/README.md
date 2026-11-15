# Phase reports

One report per phase of [specs/linkedin-mini-crm-v1](../../specs/linkedin-mini-crm-v1/): files touched, how to test by hand, and what was tested.

| Phase | Report | Automated tests (final run) |
|---|---|---|
| 1 Foundation | [phase1.md](phase1.md) | 7 pytest |
| 2 Contacts and import | [phase2.md](phase2.md) | 8 (URL normalization) + 44 pytest (incl. 17 boolean-search) |
| 3 Visit tracking and messages | [phase3.md](phase3.md) | 6 pytest |
| 4 Groups | [phase4.md](phase4.md) | 6 pytest |
| 5 Pipelines | [phase5.md](phase5.md) | 11 pytest + 11 Vitest (shared with P7) |
| 6 Bulk set stage | [phase6.md](phase6.md) | 10 pytest |
| 7 Board, export, backup, E2E | [phase7.md](phase7.md) | 11 pytest + 9 Playwright flows |

Totals: **104 pytest, 11 Vitest, 11 Playwright, all passing** (updated 2026-11-08).

> **Updated 2026-11-08:** the return prompt and "Visited, not logged" were removed; add-members, the selection bar and export scopes were added; the folder import was removed and uploaded CSVs are now saved to the data folder. The PRD (v0.3), system design, decision log (rows 60–72), ADR implementation notes and specs were revised to match.

## How the work was ordered (honest note)
I wrote the backend for all seven phases (each with its tests) first, then the frontend, then ran Playwright. So the
phase reports describe each phase's *final* files; the git-style "phase-by-phase" snapshots don't exist (the folder is not a git repo).
Frontend files were created after all backend phases, not interleaved.

## Deviations from the design / PRD (all phases)
- **Drag and drop** uses native HTML5 drag-and-drop, not `dnd-kit` (D28). The dropdown alternative works on every card.
- **Styling** is one plain CSS file; Tailwind and shadcn/Radix (D27) were not used.
- **API types:** `frontend/src/api-types.ts` is generated from the backend's OpenAPI schema (`npm run gen:api`), but most
  responses are plain dicts rather than Pydantic models, so response types in `frontend/src/types.ts` are hand-written
  (only the request body `GroupCreate` uses the generated type). D44 is only partly met.
- **Docker image was never built** (Docker daemon not running here). `docker compose config` validates. The same code path
  was exercised natively and through Playwright.
- **I did not look at the UI in a browser myself**; UI behaviour is verified only through the Vitest and Playwright tests.
  Please eyeball layout and phone width.
- Python 3.13 via `uv` (pinned in `backend/.python-version`).
