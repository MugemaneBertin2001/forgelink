# Architecture Decision Records

This directory holds the load-bearing decisions behind ForgeLink. Each ADR is short (one page), immutable once accepted, and written to answer the question *"why did we pick X instead of Y — and would we make the same call again?"*.

## When to write one

Write an ADR when a choice:

- Locks in a runtime dependency (database, broker, auth provider).
- Cuts across services (a contract everyone has to respect).
- Will be reasonably contested in code review six months from now.
- Was made with significant information the code alone can't convey (a failed spike, a vendor benchmark, a regulatory constraint).

**Don't** write one for:

- Easy-to-reverse choices (library versions, code style, file layout).
- Things already well-documented elsewhere (CLAUDE.md, READMEs).
- Decisions that are obvious from the code.

## Format

Shamelessly borrowed from Michael Nygard's original ADR template, trimmed to what we actually use:

```markdown
# ADR NNNN — Title

**Status:** accepted | superseded by ADR-NNNN
**Date:** YYYY-MM-DD

## Context

What forced this decision? Constraints, alternatives, the spike results.

## Decision

One paragraph. The thing we picked.

## Consequences

What this makes easy. What this makes hard. What we gave up.
```

Keep them under 200 lines. If an ADR needs more, the context is probably wrong.

## Index

| # | Title | Status |
|---|-------|--------|
| [0001](0001-django-spring-split.md) | Django + Spring split | accepted |
| [0002](0002-tdengine-for-timeseries.md) | TDengine for time-series | accepted |
| [0003](0003-uns-topic-design.md) | UNS topic design (ISA-95) | accepted |
| [0004](0004-cert-manager-over-spire.md) | cert-manager over SPIRE | accepted |
| [0005](0005-framing-a-scaffold-retention.md) | Framing-A scaffold retention | accepted |
