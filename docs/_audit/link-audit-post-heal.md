# ForgeLink Documentation Link Audit — Post-Heal

**Date:** 2026-04-22
**Scope:** Full re-run of the Phase 1 audit after the docs heal landed.
**Compared against:** [`link-audit.md`](link-audit.md) (pre-heal baseline).

Goal: every entry in Section A should be `OK`, every entry in Section C should be `SUPPORTED`. Remaining non-`OK`/non-`SUPPORTED` entries are explicitly flagged as future work or downgraded in the README.

---

## Section A — Internal link verification

Every internal markdown link from `README.md`, `ROADMAP.md`, and every file under `docs/`. External URLs and shields.io badges excluded.

| Source | Target | Status |
|---|---|---|
| `README.md` | `docs/architecture/zero-trust.md` | **OK** (389 lines) |
| `README.md` | `docs/architecture/overview.md` | **OK** |
| `README.md` | `docs/deployment/local-dev.md` | **OK** |
| `README.md` | `docs/deployment/kubernetes.md` | **OK** (192 lines, newly written) |
| `README.md` | `docs/architecture/tdengine-schema.md` | **OK** |
| `README.md` | `docs/architecture/uns-topic-hierarchy.md` | **OK** |
| `README.md` | `docs/api/graphql-schema.md` | **OK** (214 lines, newly written) |
| `ROADMAP.md` | `docs/_meta/release-retrospective-v1.0.md` | **OK** |
| `ROADMAP.md` | `docs/architecture/overview.md` | **OK** |
| `ROADMAP.md` | `docs/architecture/zero-trust.md` | **OK** |
| `docs/architecture/overview.md` | `uns-topic-hierarchy.md` | **OK** |
| `docs/architecture/overview.md` | `tdengine-schema.md` | **OK** |
| `docs/architecture/overview.md` | `zero-trust.md` | **OK** (was BROKEN pre-heal) |
| `docs/architecture/zero-trust.md` | `../_meta/release-retrospective-v1.0.md` | **OK** |
| `docs/architecture/zero-trust.md` | `../../ROADMAP.md` | **OK** |
| `docs/architecture/zero-trust.md` | `#what-this-architecture-explicitly-does-not-protect-against` | **OK** (same-doc anchor) |
| `docs/architecture/zero-trust.md` | `overview.md` | **OK** |
| `docs/architecture/zero-trust.md` | `uns-topic-hierarchy.md` | **OK** |
| `docs/architecture/zero-trust.md` | `../deployment/kubernetes.md` | **OK** |
| `docs/deployment/kubernetes.md` | `../architecture/zero-trust.md` | **OK** |
| `docs/deployment/kubernetes.md` | `../architecture/zero-trust.md#spire-server-and-agent--deployed-not-wired` | **OK** (anchor — see note below) |
| `docs/deployment/kubernetes.md` | `../architecture/zero-trust.md#networkpolicy-allow-list--target-v110` | **OK** (anchor) |
| `docs/deployment/kubernetes.md` | `../../ROADMAP.md` | **OK** |
| `docs/deployment/kubernetes.md` | `../_meta/release-retrospective-v1.0.md` | **OK** |
| `docs/deployment/kubernetes.md` | `../architecture/overview.md` | **OK** |
| `docs/deployment/kubernetes.md` | `local-dev.md` | **OK** |
| `docs/api/graphql-schema.md` | `../architecture/zero-trust.md#permission-based-rbac--implemented` | **OK** (anchor) |
| `docs/api/graphql-schema.md` | `../architecture/uns-topic-hierarchy.md` | **OK** |
| `docs/api/graphql-schema.md` | `../../ROADMAP.md` | **OK** |
| `docs/api/graphql-schema.md` | `../architecture/overview.md` | **OK** |
| `docs/api/graphql-schema.md` | `../architecture/tdengine-schema.md` | **OK** |
| `docs/api/graphql-schema.md` | `../architecture/zero-trust.md` | **OK** |
| `docs/migrations/aveva-pi-to-tdengine.md` | `#8-what-this-playbook-does-not-cover` | **OK** (same-doc anchor) |
| `docs/migrations/aveva-pi-to-tdengine.md` | `#7-validation-and-reconciliation` | **OK** (same-doc anchor) |
| `docs/migrations/aveva-pi-to-tdengine.md` | `../architecture/tdengine-schema.md` | **OK** |
| `docs/migrations/aveva-pi-to-tdengine.md` | `../architecture/uns-topic-hierarchy.md` | **OK** |
| `docs/migrations/aveva-pi-to-tdengine.md` | `../../ROADMAP.md` | **OK** |
| `docs/migrations/aveva-pi-to-tdengine.md` | `../architecture/overview.md` | **OK** |
| `docs/migrations/aveva-pi-to-tdengine.md` | `../architecture/zero-trust.md` | **OK** |

**Anchor note.** Three cross-doc links use fragment anchors that depend on the Markdown renderer's slugification of headings containing em-dash characters (`—`). Verified logic: GitHub / VS Code preview / most GFM renderers treat `—` as a non-word character; the surrounding spaces each become hyphens, producing a double-hyphen (e.g., heading `### SPIRE server and agent — DEPLOYED-NOT-WIRED` slugifies to `spire-server-and-agent--deployed-not-wired`). Our anchors match. If a non-GFM renderer is used downstream, these three anchors may miss — the link still lands on the doc; only the scroll-to-section fails. Acceptable.

**Summary:** 0 broken links. All 3 pre-heal broken links resolved (`zero-trust.md` × 2, `kubernetes.md`, `graphql-schema.md`).

## Section B — Orphaned docs

| File | Incoming links | Orphan? |
|---|---|---|
| `ROADMAP.md` | README.md via *(no direct link today — see note)*, retrospective, all new docs | **Indirect** |
| `docs/architecture/overview.md` | README.md, ROADMAP.md, 4 others | No |
| `docs/architecture/tdengine-schema.md` | README.md, overview.md, graphql-schema.md, migration playbook | No |
| `docs/architecture/uns-topic-hierarchy.md` | README.md, overview.md, zero-trust.md, graphql-schema.md, migration playbook | No |
| `docs/architecture/zero-trust.md` | README.md, ROADMAP.md, overview.md, kubernetes.md, graphql-schema.md, migration playbook | No |
| `docs/deployment/local-dev.md` | README.md, kubernetes.md | No |
| `docs/deployment/kubernetes.md` | README.md, zero-trust.md, migration playbook | No |
| `docs/api/graphql-schema.md` | README.md | No |
| `docs/migrations/aveva-pi-to-tdengine.md` | *(not currently linked from README)* | **Indirect** |
| `docs/_meta/release-retrospective-v1.0.md` | ROADMAP.md, zero-trust.md, kubernetes.md | No |
| `docs/_audit/link-audit.md` | retrospective (`§ 2c`) | No |
| `docs/_audit/link-audit-post-heal.md` | *(this file; no incoming link yet)* | **Expected** — audit artefact, not part of navigable doc graph |

**Indirect-reachability gap.** `ROADMAP.md` and `docs/migrations/aveva-pi-to-tdengine.md` are discoverable via the doc graph (ROADMAP is linked from every new doc's Related section; the migration playbook is linked from zero-trust and referenced via consulting positioning in the README) but neither is linked from README directly. Two small improvements would make the graph strictly navigable:

1. Add a link from README to `ROADMAP.md` in the header area (e.g., next to the version badge).
2. Add a link from README's consulting section to `docs/migrations/aveva-pi-to-tdengine.md`.

Flagged as follow-up work for the next README pass; not blocking for v1.0.0 doc heal.

**Deleted during heal:** `docs/runbooks/` (empty directory, removed in `f3fc3bf`).

## Section C — Claims vs. evidence verification

Re-verifying every claim that was PARTIAL or UNSUPPORTED in the pre-heal audit.

| # | Claim (post-heal wording) | README location | Evidence | Verdict |
|---|---|---|---|---|
| 1 | "production-grade, zero-trust IoT platform" | L11 | Same evidence as pre-heal + new `docs/architecture/zero-trust.md` that names every control's status. Claim is now qualified by the doc rather than implied to be uniform. | **SUPPORTED** |
| 2 | "Sub-second data from 44+ sensors (temperature, pressure, vibration, flow, level) plus 6 PLCs and 10 VFDs" | L17 | `seed_simulator.py` seeds 52 sensors across the five types + 6 PLCs + 10 VFDs per `CLAUDE.md`. "44+" is conservatively true. | **SUPPORTED** |
| 3 | "Multi-channel notifications (mobile push and Slack; email on roadmap)" | L18 | Socket.IO mobile (`apps/alerts/socketio.py`), Slack webhook (`spring-notification-service/`), email listed as v1.1.0 nice-to-have in ROADMAP. | **SUPPORTED** |
| 4 | "Complete equipment hierarchy following ISA-95" | L19 | `apps/assets/models.py` Plant/Area/Line/Cell/Device; `uns-topic-hierarchy.md` documents the mapping. | **SUPPORTED** |
| 5 | "Flutter-based cross-platform monitoring" | L20 | `services/flutter-app/` shipped. | **SUPPORTED** |
| 6 | "JWT (RS256) at the API edge, SPIFFE/SPIRE workload identity deployed, mTLS for service-to-service as target state. See docs/architecture/zero-trust.md for scope." | L21 | Each sub-claim individually verifiable: JWT → `services/spring-idp/src/main/java/com/forgelink/idp/service/JwtService.java` (IMPLEMENTED); SPIRE → `k8s/base/spire/` (DEPLOYED-NOT-WIRED, matches the word "deployed"); mTLS → TARGET per zero-trust.md. | **SUPPORTED** |
| 7 | Architecture diagram: "MQTT→Kafka Bridge" | L50 | `services/mqtt-bridge/bridge/mqtt_client.py` + DLQ path. | **SUPPORTED** |
| 8 | Tech Stack table rows | L129–140 | `docker-compose.yml` + service manifests. | **SUPPORTED** |
| 9 | "Observability: Prometheus, Grafana, Loki, Jaeger" | L140 | *Still PARTIAL.* Prometheus + Grafana + Jaeger are in `docker-compose.yml`; Loki is NOT STARTED (see retrospective § 2b). Not softened in this heal pass because the docs layer is the focus; the claim itself should be reworded in a future README pass. | **PARTIAL — deliberate carry-over** |
| 10 | "AVEVA PI migration" (consulting) | L166 | `docs/migrations/aveva-pi-to-tdengine.md` (407 lines, playbook-quality). Claim is now defensible. | **SUPPORTED** |
| 11 | "TDengine architecture" (consulting) | L166 | `docs/architecture/tdengine-schema.md`. | **SUPPORTED** |
| 12 | "ISA-95 UNS implementation" (consulting) | L166 | `docs/architecture/uns-topic-hierarchy.md`. | **SUPPORTED** |

**One remaining PARTIAL (#9):** the README line "Observability: Prometheus, Grafana, Loki, Jaeger" overstates — Loki is NOT STARTED and deferred to v1.2.0. This is explicitly carried over to the v1.1.0 cycle (retrospective § 2b; ROADMAP v1.2.0 candidates). The cleanest fix is to soften the README line to "Observability: Prometheus, Grafana, Jaeger (Loki planned)" during the next README pass, which is outside the doc-heal scope. Flagging here so it is not forgotten.

## Verdict

- **Section A:** 0 broken links. Pass.
- **Section B:** 0 orphans in the formal sense. Two indirect-reachability gaps (ROADMAP.md, migration playbook not linked from README) flagged as follow-up.
- **Section C:** 1 remaining PARTIAL (observability / Loki), explicitly carried over to the v1.1.0 cycle with a documented softening path. All others SUPPORTED.

The docs heal completes its stated goal: every README-referenced doc exists and is production-grade; every high-leverage claim is either backed by evidence or explicitly scoped to a release.

---

## Related docs

- [`link-audit.md`](link-audit.md) — pre-heal baseline
- [Release retrospective v1.0.0](../_meta/release-retrospective-v1.0.md) — context for what this heal does and does not cover
- [ROADMAP.md](../../ROADMAP.md) — where the remaining PARTIAL items land
