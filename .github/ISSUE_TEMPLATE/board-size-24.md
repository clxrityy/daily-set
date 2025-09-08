---
name: "Feature: 24-card Board Size"
about: "Double the board size to 24 with responsive layout and backend support"
title: "feat: 24-card board (daily)"
labels: [feature, frontend, backend]
assignees: []
---

## Summary

Double the visible board to 24 cards. Keep gameplay rules; ensure at least one valid set exists and all shapes appear.

## Scope

- Frontend responsive grid and selection logic for 24 cards
- Backend `daily_board(size=24)` support and validation
- Performance check (render, set search)

## Non-goals

- Changing core game rules

## Acceptance Criteria

- [ ] Toggle or config to serve a 24-card board for the daily game
- [ ] Mobile grid remains usable; desktop density looks balanced
- [ ] Submit/validation works with indices > 11
- [ ] Tests updated/passing

## Tasks

- [ ] FE: grid/layout updates for 24
- [ ] FE: selection and client validation for >12
- [ ] BE: allow variable board size; relax index validation
- [ ] BE: cache/daily board caching for different sizes
- [ ] Tests: unit + basic e2e
