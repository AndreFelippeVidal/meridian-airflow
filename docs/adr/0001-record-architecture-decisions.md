# 1. Record architecture decisions

- Status: Accepted
- Date: 2026-06-29

## Context
We need a lightweight, durable way to capture *why* design choices were made, so the
portfolio demonstrates architectural reasoning (not just working code) and so future-me
remembers the tradeoffs. This file is also the template for every later ADR.

## Decision
We use MADR-style ADRs, one markdown file per non-obvious decision in `docs/adr/`,
numbered sequentially. Each has Context, Decision, Consequences. Scaffold with `/adr`.

## Consequences
- Reviewers can read decisions in minutes.
- Slightly more discipline per decision; worth it for the signal it sends.
- ADRs become source material for blog posts and the vault.
