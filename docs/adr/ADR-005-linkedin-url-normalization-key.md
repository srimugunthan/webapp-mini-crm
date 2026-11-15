# ADR-005: Use an aggressively normalized LinkedIn URL as the contact key

**Status:** Accepted
**Date:** 2026-11-08
**Deciders:** Srimugunthan

---

## Context

Contacts are identified by normalized LinkedIn profile URL (PRD §5, §7). That key drives import upserts (FR-6), bulk stage matching (FR-51) and visit tracking (FR-29). The PRD normalizes only host case, trailing slash and query string, but exports and bulk CSVs often differ by `www`, `http` versus `https`, or case. A re-import or bulk update that creates duplicates or misses matches would break the "re-import preserves 100% of groups and stages" success metric. The decision was settled in Q32.

---

## Decision

We will store `contacts.linkedin_url` as a unique value in normalized form: lowercase the whole URL including the path, drop query and fragment, strip the trailing slash, treat `linkedin.com` and `www.linkedin.com` as the same host, and force https. The same function is used by import, bulk-stage matching and the `/go/{id}` redirect (https `linkedin.com` hosts only).

---

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| PRD rules only (host case, trailing slash, no query) | Minimal; fewest assumptions about LinkedIn URLs | Misses `www`, `http` and path-case differences, so duplicates and missed matches |
| **Aggressive normalization (chosen)** | Robust matching across exports and bulk CSVs; no duplicate contacts | Hard to change later; distinct case-sensitive slugs, if any existed, would merge |

---

## Consequences

**Positive:**
- Re-import and bulk CSV matching are robust to case, `www` and `http` differences.
- One normalization function is shared by all entry points, so behavior is identical.

**Negative / Accepted Tradeoffs:**
- Changing the rules later means rewriting the key for every contact and resolving collisions.
- LinkedIn profile paths are treated as case-insensitive, and case-sensitive slugs are not expected.

---

## Follow-up Actions

- [x] Cover the normalization function with tests for `www`, `http`, case, fragments, query strings and trailing slashes.

---

## Implementation notes (2026-11-08)

Built as decided in `backend/app/urlnorm.py`: lowercased, query and fragment dropped, trailing slash stripped, https forced, and `linkedin.com` and `www.linkedin.com` stored as the single canonical host `www.linkedin.com`. The same function is used by import, bulk-stage matching, and the new add-members-from-CSV flow (decision 64); the `/go/{id}` redirect uses a separate check that only allows https `linkedin.com` or `www.linkedin.com`. The follow-up action is done: 8 tests cover `www`, `http`, case, fragments, query strings, trailing slashes, empty input and redirect host rules.
