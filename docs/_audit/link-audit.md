# ForgeLink Documentation Link Audit

**Date:** 2026-04-22
**Scope:** `README.md` + every file under `docs/`
**Purpose:** Identify broken links, orphaned docs, and README claims that are not backed by the codebase, before we heal the docs surface.

EMPTY threshold: a file counts as EMPTY (treated as broken) if it is under 50 lines. The audit applies that rule only to the internal docs set; the `LICENSE` file is short by nature and excluded.

---

## Section A — Broken internal links

Every internal markdown link from `README.md` and `docs/**/*.md`. External URLs (https://...) and shields.io badges are excluded because they are not part of the internal docs graph.

| Source | Target | Resolved path | Status |
|---|---|---|---|
| `README.md` | `docs/architecture/overview.md` | `docs/architecture/overview.md` (87 lines) | **OK** |
| `README.md` | `docs/deployment/local-dev.md` | `docs/deployment/local-dev.md` (151 lines) | **OK** |
| `README.md` | `docs/deployment/kubernetes.md` | *(missing)* | **BROKEN** |
| `README.md` | `docs/architecture/tdengine-schema.md` | `docs/architecture/tdengine-schema.md` (266 lines) | **OK** |
| `README.md` | `docs/architecture/uns-topic-hierarchy.md` | `docs/architecture/uns-topic-hierarchy.md` (216 lines) | **OK** |
| `README.md` | `docs/api/graphql-schema.md` | *(missing; `docs/api/` exists but is empty)* | **BROKEN** |
| `docs/architecture/overview.md` | `uns-topic-hierarchy.md` | `docs/architecture/uns-topic-hierarchy.md` | **OK** |
| `docs/architecture/overview.md` | `tdengine-schema.md` | `docs/architecture/tdengine-schema.md` | **OK** |
| `docs/architecture/overview.md` | `zero-trust.md` | *(missing)* | **BROKEN** |
| `docs/architecture/tdengine-schema.md` | *(no internal links)* | — | — |
| `docs/architecture/uns-topic-hierarchy.md` | *(no internal links)* | — | — |
| `docs/deployment/local-dev.md` | *(no internal links)* | — | — |

**Summary:** 3 broken internal links. All three are doc files that the README or overview promises but the repo never shipped:

1. `docs/deployment/kubernetes.md` — the Kubernetes deployment guide (referenced from README).
2. `docs/api/graphql-schema.md` — GraphQL schema reference (referenced from README; the `docs/api/` directory is empty).
3. `docs/architecture/zero-trust.md` — zero-trust architecture doc (referenced from `overview.md#next-steps`).

No EMPTY files were found in the existing docs set — every shipped doc clears the 50-line bar.

---

## Section B — Orphaned docs

Every file under `docs/` cross-referenced against every internal link in the repo (README + all markdown under docs/).

| File | Incoming links | Orphan? |
|---|---|---|
| `docs/architecture/overview.md` | README.md | No |
| `docs/architecture/tdengine-schema.md` | README.md, overview.md | No |
| `docs/architecture/uns-topic-hierarchy.md` | README.md, overview.md | No |
| `docs/deployment/local-dev.md` | README.md | No |

**Empty directories that exist but hold nothing:**

- `docs/api/` — created but empty. README links into it (`graphql-schema.md`) — effectively a broken link, not an orphan.
- `docs/runbooks/` — created but empty. Nothing references it.

**Summary:** No orphaned files. Two empty directories. `docs/runbooks/` is a dead-end placeholder that should be deleted or populated during heal; `docs/api/` becomes non-orphan once we write `graphql-schema.md`.

Service-level READMEs (`services/*/README.md`, `slack-bot/README.md`, `mobile/flutter-app/README.md`) were not audited for graph membership — they are local READMEs that describe a component, not part of the central docs graph, and tooling (`cd services/<x> && cat README.md`) finds them without needing an inbound link.

---

## Section C — Claims vs. evidence gaps

Every technical claim in `README.md` that a reader could reasonably fact-check. For each claim, I located the backing evidence (or the absence of it) in the codebase.

| # | Claim | README location | Evidence in repo | Verdict |
|---|---|---|---|---|
| 1 | "production-grade, zero-trust IoT platform" | L11 | `k8s/base/network-policies/default-deny.yaml` (default-deny ingress/egress + allow-dns), `k8s/base/spire/spire-server.yaml`, `k8s/base/spire/spire-agent.yaml`. No `docs/architecture/zero-trust.md`. No mTLS manifests or configs in any service. | **PARTIAL** |
| 2 | "Sub-second data from 68+ sensors across the plant" | L17 | `services/django-api/apps/simulator/management/commands/seed_simulator.py` seeds four area-create methods (melt_shop, continuous_casting, rolling_mill, finishing). `CLAUDE.md` breakdown: 20 temp + 8 pressure + 12 vibration + 8 flow + 4 level + 6 PLCs + 10 VFDs = 68. That total includes PLCs and VFDs, which are controllers/drives, not sensors. | **PARTIAL** — 68 devices is correct; "sensors" conflates sensors with controllers. Either change to "68+ devices" or drop PLC/VFD from the count. |
| 3 | "Alert Management — Multi-channel notifications (mobile, Slack, email)" | L18 | Slack: `services/spring-notification-service/` consumes `alerts.notifications` and posts to Slack webhook. Mobile: `apps/alerts/socketio.py` broadcasts over Socket.IO. Email: no `EMAIL_BACKEND`, no `django.core.mail`, no `send_mail` call anywhere. Alert model tracks `notified_slack` only — no `notified_email` field. | **PARTIAL** — email is unimplemented. |
| 4 | "Asset Registry — Complete equipment hierarchy following ISA-95" | L19 | `apps/assets/models.py` defines Plant → Area → Line → Cell → Device. `docs/architecture/uns-topic-hierarchy.md` documents the ISA-95 mapping. | **SUPPORTED** |
| 5 | "Mobile App — Flutter-based cross-platform monitoring" | L20 | `services/flutter-app/` exists with login, dashboard, alerts, assets, telemetry, settings screens. `mobile/flutter-app/README.md` also present. | **SUPPORTED** |
| 6 | "Zero Trust Security — mTLS, JWT, SPIFFE/SPIRE throughout" | L21 | **JWT**: `services/spring-idp/src/main/java/com/forgelink/idp/config/JwtConfig.java` + `JwtService` implement RS256; Django middleware validates via JWKS. **SPIFFE/SPIRE**: manifests for spire-server and spire-agent exist; no workload registration entries, no services consume SVIDs. **mTLS**: no TLS termination config between services, no cert-manager or ingress mTLS config, no `ssl_client_certificate`, no Spring `server.ssl.*` setup. | **PARTIAL** — JWT is real; SPIRE is deployed but not wired into workloads; mTLS is a claim without implementation. "Throughout" is the specific overreach. |
| 7 | Architecture diagram: "MQTT→Kafka Bridge" | L50 | `services/mqtt-bridge/` exists with its own README. | **SUPPORTED** |
| 8 | Tech Stack table rows: TDengine 3.x, PostgreSQL 16, Redis 7, Kafka (Confluent), RabbitMQ, EMQX 5.x, Django 5.1 + Graphene, Spring Boot 3.3, Flutter 3.19+ | L129–140 | `docker-compose.yml` and k8s StatefulSets include all listed services; service `pom.xml`/`requirements.txt` and `CLAUDE.md` confirm versions. | **SUPPORTED** |
| 9 | "Observability: Prometheus, Grafana, Loki, Jaeger" | L140 | Grafana + Jaeger referenced in `local-dev.md` and `docker-compose.yml`. Prometheus/Loki: need to verify in compose. Not a blocker for docs healing. | **PARTIAL** — accept as-is unless blocked later. |
| 10 | Consulting positioning: "AVEVA PI migration" | L166 | No AVEVA/OSIsoft/PI references anywhere in the repo (grep across `*.md`, `*.py`, `*.yaml`, `*.yml` returns only the README itself). | **UNSUPPORTED** — a consulting claim with no backing doc. Needs `docs/migrations/aveva-pi-to-tdengine.md`. |
| 11 | Consulting positioning: "TDengine architecture" | L166 | `docs/architecture/tdengine-schema.md` (266 lines: database config, supertables, retention, query patterns). | **SUPPORTED** |
| 12 | Consulting positioning: "ISA-95 UNS implementation" | L166 | `docs/architecture/uns-topic-hierarchy.md` (216 lines: topic grammar, QoS strategy, examples). | **SUPPORTED** |

### Additional finding (not a README claim, but adjacent hygiene)

- `docs/deployment/local-dev.md:17` contains a stale `https://github.com/your-org/forgelink.git` clone URL. The README was already patched; this doc was missed.

---

## What heals in Phase 2

If the audit is approved, Phase 2 must produce:

1. **Write in full** (consulting positioning, must be defensible):
   - `docs/architecture/zero-trust.md` — heals broken link from `overview.md`, backs the "zero-trust" claim from README.
   - `docs/migrations/aveva-pi-to-tdengine.md` — backs the AVEVA PI consulting claim (new directory).

2. **Write minimal but honest** (secondary, referenced from README):
   - `docs/deployment/kubernetes.md` — heals broken link; scope: namespace + deployment + NetworkPolicy + HPA + secrets strategy, labeled what's implemented vs. proposed against the actual `k8s/` manifests.
   - `docs/api/graphql-schema.md` — heals broken link; scope: top-level queries and mutations from `apps/api/schema.py`, generated from the Graphene schema rather than hand-rolled.

3. **Soften the README** to match reality:
   - L17 "68+ sensors" → "68+ devices" (or list the sensor subset explicitly).
   - L18 "mobile, Slack, email" → "mobile and Slack" until email is implemented, or mark email as roadmap.
   - L21 "mTLS, JWT, SPIFFE/SPIRE throughout" → soften "throughout": the honest claim is that SPIRE is deployed, JWT is enforced at the API edge, and mTLS is the target for service-to-service. The `zero-trust.md` doc should make that scope explicit.

4. **Delete or populate** empty directories:
   - `docs/runbooks/` — empty and unreferenced. Delete unless Phase 4 chooses to seed it.

5. **Fix remaining stale URLs**:
   - `docs/deployment/local-dev.md:17` clone URL.

---

*This audit stops here. No docs are written until the audit is reviewed.*
