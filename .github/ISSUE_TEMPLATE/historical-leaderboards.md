---
name: "Feature: Historical, Weekly, Monthly Leaderboards"
about: "Navigate previous days and see weekly/monthly aggregates"
title: "feat: historical & aggregated leaderboards"
labels: [feature, frontend, backend]
assignees: []
---

## Summary

Add daily history navigation and weekly/monthly aggregated leaderboards.

## Scope

- BE: daily by date param, weekly/monthly aggregation endpoints (with caching)
- FE: tabs or routes to switch between Daily / Weekly / Monthly; date picker for Daily

## Acceptance Criteria

- [ ] Daily leaderboard can be viewed for arbitrary date
- [ ] Weekly/monthly leaderboards show aggregates (e.g., best time, average, total sets)
- [ ] Performance acceptable with indexes and caching
- [ ] Tests updated

## Tasks

- [ ] BE: endpoints + queries + indexes + cache
- [ ] FE: UI & state
- [ ] Tests
