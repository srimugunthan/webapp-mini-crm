# ADR-001: Use a React SPA for the frontend

**Status:** Accepted
**Date:** 2026-11-08
**Deciders:** Srimugunthan

---

## Context

The PRD (§13) proposed server-rendered HTML with HTMX or vanilla JavaScript, chosen to keep packaging at "one command, one file". During the design interview (Q2) HTMX was the recommended option, but the owner chose React. The app has interactive flows beyond simple click-and-save: a drag-and-drop board (FR-46), bulk stage preview and apply (FR-57), a return prompt on tab focus (FR-62), and bookmarkable filters (FR-41), at a scale of up to 10,000 contacts for one local user.

---

## Decision

We will build the UI as a React single-page app (TypeScript, Vite, TanStack Query, React Router, Tailwind with headless components, dnd-kit) and serve the built files as static assets from FastAPI.

---

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Jinja2 + HTMX | No build step; Python-only toolchain; URL filters come free; simplest packaging | Multi-step stateful flows (bulk preview, board) are clunkier; less app-like feel |
| Jinja2 + vanilla JS | Fewest dependencies | Hand-rolled state handling for the board and bulk flows |
| **React SPA (chosen)** | Smooth board and bulk flows; typed API contract via OpenAPI; optimistic updates | Node build stage; JSON API and client state to maintain; npm dependency churn |

The PRD goal of "no build step" is dropped. React's main advantage here is the board and stateful flows, which are P1 and arrive last (milestone M5).

---

## Consequences

**Positive:**
- Richer board, bulk preview and stateful flows.
- Typed API contract: TypeScript types are generated from the FastAPI OpenAPI schema.
- Keyboard-accessible components through headless UI primitives.

**Negative / Accepted Tradeoffs:**
- A Node build stage is required, so packaging depends on the Docker multi-stage build (ADR-003).
- A JSON API contract and client-side state have to be maintained alongside the backend.
- Frontend tests are needed (Vitest plus a few Playwright flows).
- Dependency upgrades will be needed over time, which is a cost for a personal tool left idle.

---

## Implementation notes (2026-11-08)

The decision stands and was built as written: Vite, React, TypeScript, React Router and TanStack Query, with the built `dist/` served by FastAPI and an `index.html` fallback for client routes. Differences from the surrounding decisions, none of which change this ADR: the board uses native HTML5 drag-and-drop instead of `dnd-kit` (decision 71), styling is one plain CSS file instead of Tailwind (decision 70), and TypeScript types are generated from the OpenAPI schema only for request models (decision 70). Verified by 11 Vitest tests and 5 Playwright flows. Related changes this session: decisions 62 (return prompt removed), 64 and 65 (add members, selection bar).
