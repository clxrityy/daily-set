---
name: "Feature: Track Sets Found + Per-user View"
about: "Persist found sets; let users review theirs and view others' from leaderboard"
title: "feat: track sets found & per-user set viewer"
labels: [feature, frontend, backend]
assignees: []
---

## Summary

Persist each found set per player per day; show a viewer post-game and from leaderboard (click username).

## Scope

- BE: `foundset` table, record on submit; list API by date/player
- FE: store/show your sets; modal/route for other users' sets from leaderboard

## Acceptance Criteria

- [ ] Each valid submit logs a 3-card set under the session
- [ ] "Found Sets" panel shows your sets after completion
- [ ] Leaderboard username click opens that user's sets for the selected date
- [ ] Rate-limited and validated; tests in place

## Tasks

- [ ] BE: model + migration + CRUD + list endpoint
- [ ] BE: record set on submit
- [ ] FE: UI for your sets & modal for others
- [ ] Tests: unit + API
