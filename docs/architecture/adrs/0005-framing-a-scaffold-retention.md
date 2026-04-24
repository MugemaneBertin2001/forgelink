# ADR 0005 — Framing-A scaffold retention

**Status:** accepted
**Date:** 2026-04-10

## Context

During the v1 → v2 retrospective the team confronted a pile of partially-implemented features: the SPIRE manifests that never got wired up (see [ADR 0004](0004-cert-manager-over-spire.md)), the AI anomaly-detection app with only model stubs, the audit-log surface that ingests events but doesn't yet query them, several K8s overlays for environments we've never deployed.

Two framings were on the table:

### Framing B — "delete all unfinished code"

Argument: honesty through removal. A codebase that only contains working code is clearer to a new contributor; the git history preserves whatever was deleted. Unused scaffolds rot, confuse readers, and hide behind `TODO` comments that nobody prioritises.

### Framing A — "keep scaffolds, label them honestly"  *(chosen)*

Argument: the scaffolds encode design intent and survived earlier design reviews. Deleting them means re-deriving the intent from commit messages and re-justifying the choice to every future contributor who asks "why doesn't this have SPIRE?" The scaffold itself, clearly labelled as scaffold, is faster to reason about than an empty directory plus a 200-word comment explaining what used to be there.

**What tipped it:**

1. **Zero-trust SPIRE manifests.** Deleting them would require a new contributor asking about SPIFFE to re-derive the decision from [ADR 0004](0004-cert-manager-over-spire.md) and hope that ADR is current. With the manifests present-but-disabled, the decision is grep-able: the YAML says *"this was seriously considered and the decision was to not ship it yet."*
2. **AI app stubs.** The ML anomaly-detection serializers / task placeholders are shaped for the eventual integration. When the real model arrives, the code follows the existing shape rather than inventing one. Deleting the stubs would mean rediscovering that shape.
3. **The Retrospective.** Every unwired feature was a decision at the time. Deleting it deletes the decision; keeping it, labelled, preserves the *why*.

The cost of Framing A is real: a new contributor running `grep -r TODO services/django-api/apps/ai/` finds dozens of placeholders. The mitigation is labelling: every scaffold carries a module-level docstring that starts with `SCAFFOLD —` and links to either the ADR or the retrospective entry that explains why it's there. The CI never builds or ships scaffold code paths.

## Decision

**Retain scaffolds as first-class code**, labelled honestly. Every scaffold file opens with a `SCAFFOLD —` docstring; every scaffold K8s manifest has an `# SCAFFOLD` comment plus an `enabled: false` kustomize patch. Scaffold code participates in lint + type-check but is excluded from the coverage gate (because testing unwired code is pointless). Scaffolds get deleted only when:

1. The underlying decision is re-opened and resolved (in which case the scaffold becomes real code, not empty).
2. The scaffold has sat untouched for >180 days AND the motivating context is either stale or documented elsewhere.

## Consequences

**Good:**

- Future contributors see the decisions the team has already made without archaeology.
- When a scaffold turns into real code, the shape is already designed and reviewed.
- Deletions are intentional, not cleanup churn.

**Painful:**

- The repository is larger than its shipping surface. First impression on `cloc` is slightly misleading.
- A casual reader might mistake scaffold for working code despite the `SCAFFOLD —` prefix. We've accepted this and expect reviewers to call out any scaffold that isn't clearly labelled.
- Coverage gates exclude scaffold paths; reviewers have to spot-check that "scaffold" isn't being used as a shield against writing tests for code that actually ships.

**Won't change unless:**

- The scaffold-to-real-code ratio flips (more scaffold than working code). Then the project has a planning problem, not a documentation one.
- A stakeholder audit (security, compliance) requires only working code in the repository. Unlikely today; we'd negotiate selective labelling instead.
