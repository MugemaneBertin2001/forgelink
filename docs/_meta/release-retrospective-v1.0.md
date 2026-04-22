# ForgeLink Release Retrospective — v1.0.0

**Date prepared:** 2026-04-22
**Covering:** initial scaffold (2026-03-20) → v1.0.0 tag (2026-03-23) → HEAD (2026-04-22)
**Purpose:** Three-way comparison of original plan vs. v1.0.0 shipped vs. v1.1.0 proposed, to ground v1.1.0 scoping in evidence rather than vibes.

## 0. Preliminary finding — planning artefact gap

The project has **no dedicated planning document** on disk. There is no `ROADMAP.md`, no `PLAN.md`, no `docs/vision.md`, no scope statement. "Original plan" had to be reconstructed from:

1. The initial commit `75becf2` (2026-03-20, "chore: initial project scaffold") — the directory structure it created is the de-facto scope statement.
2. The initial `CLAUDE.md` at that commit — it lists the stack decisions and device topology, and is the closest thing to a vision statement.
3. The initial `README.md` at that commit — feature bullets and architecture diagram.
4. Commit messages of the two large feature commits (`c784a1d` zero-trust identity; `a3d44c9` phases 3-8) — these announce what was added, which lets us back into the sequencing.

**Finding:** for v1.1.0 onward, committing a `ROADMAP.md` is itself a worthwhile task. Reconstructing "the plan" from commits is fine for one retrospective but becomes painful at v1.5.0.

---

## 1. Subsystem-by-subsystem comparison

Evidence citations: commit SHAs in `()`, paths in backticks.

| Subsystem | Original plan | v1.0.0 status | v1.1.0 target |
|---|---|---|---|
| **Django API — core (REST + GraphQL + Admin + Celery)** | Full integration hub (`75becf2`: apps/ scaffolded with 7 apps) | **SHIPPED** — GraphQL schema at `apps/api/schema.py` (737 lines), REST viewsets, Celery broker+beat, Unfold admin. Kafka consumer wired at `apps/telemetry/kafka_consumer.py:198` with DLQ fallback. | No new core work; focus v1.1.0 on observability integration. |
| **Django `apps/ai/` — predictive maintenance** | README L12 at v1.0.0 claimed "AI-powered anomaly detection and failure prediction" | **NOT STARTED** — `apps/ai/` contains only `__init__.py` + `apps.py`. No models, no services, no ML code. Claim already removed from README in `b67e1f0`. | Stay DEFERRED to v1.2.0+. |
| **Spring IDP (JWT, JWKS, refresh, RBAC)** | Planned in `75becf2`: scaffolded with `IdpApplication.java`, empty `SecurityConfig.java` | **SHIPPED** — RS256 JWT (`JwtService.java:162 lines`), JWKS endpoint, refresh tokens in Redis with blacklist, Flyway migrations, 4 seeded demo users, unit tests (`c784a1d`) | No changes needed; IDP is the most mature subsystem. |
| **Spring Asset Service** | Planned in `75becf2`: `services/spring-asset-service/` scaffolded | **DEFERRED** — deleted in `2464221` ("replaced by Django apps/assets"). Data ownership consolidated to Django. | Stay DEFERRED — architectural decision, not scope cut. |
| **Spring Alert Service** | Planned in `75becf2`: `services/spring-alert-service/` scaffolded | **DEFERRED** — deleted in `2464221`. Rule engine moved to Django `apps/alerts/`; notification dispatch moved to new Spring Notification Service. | Stay DEFERRED. |
| **Spring Notification Service** | **Not in original plan** | **ADDED** — emerged in `a3d44c9` to replace Spring Alert Service. Consumes `alerts.notifications` Kafka topic, POSTs to Slack webhook (`SlackNotificationService.java`, 119 lines). Stateless. | Add email channel (v1.1.0 nice-to-have). |
| **MQTT Bridge (MQTT → Kafka, DLQ)** | Planned in `75becf2`: `services/mqtt-bridge/` scaffolded (5 files, Kafka client stub) | **SHIPPED** — full MQTT client (`mqtt_client.py:219 lines`), DLQ at `mqtt_client.py:200` publishes to `dlq.unparseable`, health probe. | No changes. |
| **EMQX (auth + ACL)** | Planned in CLAUDE.md: "EMQX 5.x — MQTT 5.0, mTLS, ACL" | **SHIPPED (partial)** — password auth + ACL file + `no_match=deny` (`config/emqx/emqx.conf:52-84`). TLS listener present but **commented out** (`emqx.conf:40-49`, literal comment: `## SSL/TLS Listener (for production with mTLS)`). | Uncomment TLS listener, bootstrap CA (v1.1.0 candidate, depends on cert-manager). |
| **TDengine (supertables, retention, aggregation)** | Planned in CLAUDE.md (stack table) + `docs/architecture/tdengine-schema.md` authored early | **SHIPPED** — supertables `telemetry` and `device_status` defined (`tdengine-schema.md`), TDengine client (`apps/telemetry/tdengine.py`), batch insert rule (500 records or 1s), Celery rollup tasks (1m/1h/1d). Continuous aggregation runs via Celery beat, not native TDengine stream. | No changes; the doc surface is the v1.1.0 deliverable. |
| **PostgreSQL / Redis / Kafka (KRaft) / RabbitMQ** | All planned | **SHIPPED** — Postgres 16 (forgelink + idp schemas), Redis 7 (3 logical DBs), Kafka in KRaft mode (no Zookeeper), RabbitMQ 3.13 mgmt. | No changes. |
| **Flutter mobile app** | Planned in `75becf2`: `mobile/flutter-app/README.md` only | **SHIPPED** — full app at `services/flutter-app/` (moved from `mobile/`): Riverpod, Go Router, Dio, Socket.IO. Screens: login, dashboard, alerts, assets, telemetry, settings (`a3d44c9` + `e667e40` API wiring). Pinned to Flutter 3.24.0 (`bfac393`). | Minor: align theming, add APK release artefact wiring verification. |
| **Slack Bot (standalone)** | Planned in `75becf2`: `slack-bot/README.md` created | **NOT STARTED** — `slack-bot/` directory still contains only `README.md`. No code. Slack integration shipped instead as part of Spring Notification Service. | Delete `slack-bot/` directory OR commit to building it in v1.1.0. Recommendation: **delete** — the functionality is in Spring Notification Service and the standalone bot is redundant. |
| **Prometheus** | Planned | **PARTIAL** — in `docker-compose.yml` with `config/prometheus/prometheus.yml`. **Not in k8s/** — zero k8s manifests for Prometheus. Django services do not expose `/metrics`. | v1.1.0 must-ship: add k8s manifest + `django-prometheus` + Spring Actuator Prometheus endpoint. |
| **Grafana** | Planned | **PARTIAL** — in `docker-compose.yml`, `config/grafana/provisioning/datasources/datasources.yml` has datasource stub. **No dashboards committed**, **not in k8s/**. | v1.1.0 must-ship: one operational dashboard (telemetry throughput + alert rate). |
| **Jaeger** | Planned | **PARTIAL** — in `docker-compose.yml`. **No OTel SDK instrumentation** in Django or Spring services. Jaeger runs but receives nothing. | Defer to v1.2.0; tracing instrumentation is a weeks-long task. |
| **Loki** | Planned in CLAUDE.md | **NOT STARTED** — zero references in `docker-compose.yml`, `k8s/`, or any config. Grep returns nothing. | Defer to v1.2.0. |
| **HashiCorp Vault** | Planned in CLAUDE.md ("Secrets: HashiCorp Vault — self-hosted") | **NOT STARTED** — zero references. Secrets are plain k8s Secrets (`k8s/base/secrets/secrets.example.yaml`) with `.secrets/` and `secrets/` directories holding RSA keys in PEM. | Defer to v1.2.0 (replacement with External Secrets Operator or Sealed Secrets is the likely path — Vault adds operational cost). |
| **MinIO** | Planned | **PARTIAL** — in `docker-compose.yml`. **Not used** by any service code; grep for `minio` / `boto3` / `S3` returns only config mentions. Provisioned but not integrated. | Ship when a feature needs it (backup job, AI model storage). Not v1.1.0. |
| **Default-deny NetworkPolicy** | Planned in `75becf2`: `k8s/base/network-policies/default-deny.yaml` (31 lines) | **SHIPPED (skeleton only)** — default-deny + allow-dns only. **No allow-list policies** for actual service-to-service traffic. Applied as-is, nothing reaches anything. | v1.1.0 must-ship: allow-list per service tier (API ↔ IDP, API ↔ Postgres, API ↔ Redis, API ↔ Kafka, API ↔ TDengine, Notification ↔ Kafka, Notification ↔ Slack egress). |
| **SPIRE server + agent** | Planned (CLAUDE.md: Phase 2 "SPIFFE/SPIRE K8s manifests") | **SHIPPED (deployed, not wired)** — `k8s/base/spire/spire-server.yaml` (180 lines: StatefulSet + ConfigMap + RBAC), `spire-agent.yaml` (DaemonSet). Trust domain `forgelink.local`. Added in `c784a1d`. | v1.1.0 nice-to-have: add first ClusterSPIFFEID + wire Spring IDP to fetch its SVID. |
| **SPIRE workload registration** | Implied by "SPIFFE/SPIRE throughout" | **NOT STARTED** — grep for `spiffe://` outside the SPIRE server/agent configs returns 0 hits. No ClusterSPIFFEID CRD, no `spire-server entry create` bootstrap. | v1.1.0 nice-to-have (just one service). |
| **SPIRE SVID consumption (in app code)** | Implied | **NOT STARTED** — no Java `spire-api-sdk` dep, no Python `py-spiffe` dep, no Dart spiffe client. | Defer. |
| **Service-to-service mTLS** | Claimed in v1.0.0 README ("mTLS, JWT, SPIFFE/SPIRE throughout") | **NOT STARTED** — no `server.ssl.*` in Spring, no cert-manager, no TLS in any inter-service call. | Keep target state; defer implementation to v1.2.0 unless SPIRE workload wiring lands. |
| **Ingress TLS termination** | Planned | **SHIPPED (scaffolded)** — `k8s/base/ingress/ingress.yaml` declares `secretName: forgelink-tls` and `forgelink-mqtt-tls`. These secrets are not in the base (user must provide). Nginx terminates TLS; backend is cleartext. | Wire cert-manager for auto-cert (v1.1.0 candidate). |
| **CI/CD** | Planned in CLAUDE.md Phase 8 | **SHIPPED** — 4 workflows: `ci.yml`, `build.yml`, `deploy.yml`, `release.yml`. Trivy + Bandit scans, Dependabot config, git-cliff changelog, multi-arch Docker builds. Post-v1.0.0 hardening in `3115b86`, `bfac393`. | No changes. |
| **Terraform + Ansible infra** | **Not in original plan** | **ADDED post-v1.0.0** (`d1ff6e2`, 2026-04-14) — OCI Terraform, Ansible roles for common/k3s/hardening/forgelink. | Exercise it: deploy to Oracle Cloud in v1.1.0 for the live demo. |
| **Single-command deploy script** | Not in original plan | **ADDED post-v1.0.0** (`c719e5d` + `714a71d`). | Keep. |
| **Documentation (arch/deploy/API/migrations)** | Planned — scaffolded: `overview.md`, `local-dev.md` at `75becf2` | **PARTIAL** — 4 docs shipped (overview, tdengine-schema, uns-topic-hierarchy, local-dev). 3 broken links (zero-trust.md, kubernetes.md, graphql-schema.md). `docs/migrations/` didn't exist. Empty `docs/api/` and `docs/runbooks/`. Audit at `docs/_audit/link-audit.md` (`85bd74c`). | v1.1.0 must-ship: heal the audit (already in motion). |

---

## 2. Variance analysis

### 2a. What we shipped that wasn't in the original plan

| Addition | Rationale (from commits) |
|---|---|
| **Spring Notification Service** | Emerged from the Phase 5 simplification — Django took ownership of all business data, so Spring Alert Service had no domain left. Replaced with a stateless Slack-only consumer. |
| **Django `simulator/` app** | Needed for phase 3 — without real PLCs, a domain-faithful simulator (`seed_simulator.py` seeds 68 devices across 4 areas) is what makes telemetry/alerts demoable. |
| **OPC-UA simulator + Edge Gateway** | Two services (`opcua-simulator/`, `edge-gateway/`) added in `a3d44c9` to simulate the OT boundary. Not in scaffold — emerged to give the architecture a realistic southbound edge. |
| **Django `apps/audit/`** | Scaffolded early but populated during phase 4. Captures mutation events for compliance posture. |
| **ArgoCD GitOps app manifest** | `k8s/argocd/` directory added during phase 7. Not in original plan. |
| **Terraform + Ansible infra** (post-v1.0.0) | Added `d1ff6e2` to support deploy-anywhere (Pi, VPS, OCI). Drove by desire to ship a live Oracle Cloud demo. |

### 2b. What was in the original plan but didn't ship in v1.0.0

| Missing / under-delivered | Why |
|---|---|
| **Django `ai/` app (predictive maintenance)** | Scoped in initial README bullet; never implemented. Anomaly detection got a stub in `apps/telemetry/services.py` (threshold-based, not ML). ML was too much scope for the initial cut. |
| **Slack Bot (standalone)** | Slack integration was delivered through Spring Notification Service instead. The standalone bot in `slack-bot/` is redundant and should be retired. |
| **Loki** | No scaffolding effort made. Deferred without explicit decision. |
| **HashiCorp Vault** | Same — scoped in stack table, never implemented. PEM-based secret provisioning and k8s Secrets were "good enough" for v1.0.0. |
| **Observability end-to-end (Prom/Grafana/Jaeger in k8s)** | Compose has Prometheus + Grafana + Jaeger; k8s has none of them. Dashboards never committed. Instrumentation never added. |
| **SPIRE workload registration + SVID consumption** | Infrastructure landed (`c784a1d`) but integration never followed. Classic "deployed but not wired" gap. |
| **Service-to-service mTLS** | Not started. EMQX TLS listener is commented out, Spring has no `server.ssl.*`, cert-manager absent. |
| **NetworkPolicy allow-list** | Default-deny landed; follow-through allow-list never did. |

### 2c. What we claimed in v1.0.0 that wasn't fully wired

Pulled directly from the link audit at `docs/_audit/link-audit.md`. At v1.0.0 (before `b67e1f0` and the softening amendments approved during the doc heal), the README claimed:

| Claim | Reality at v1.0.0 | Status |
|---|---|---|
| "Sub-second data from 68+ sensors" | 68 is total devices including 6 PLCs + 10 VFDs. Sensor-only count is 52. | PARTIAL — miscategorised |
| "Multi-channel notifications (mobile, Slack, email)" | Mobile (Socket.IO) ✓; Slack ✓; email — no `EMAIL_BACKEND`, no `send_mail`, no `notified_email` field | UNSUPPORTED on email |
| "Predictive Maintenance — AI-powered anomaly detection and failure prediction" | `apps/ai/` is empty | UNSUPPORTED |
| "Zero Trust Security — mTLS, JWT, SPIFFE/SPIRE throughout" | JWT real; SPIRE deployed not wired; mTLS absent | PARTIAL on "throughout" |
| "AVEVA PI migration" (consulting positioning, added post-v1.0.0 in `b67e1f0`) | No AVEVA references anywhere in repo | UNSUPPORTED — needs `docs/migrations/aveva-pi-to-tdengine.md` |

Three of those five have already been patched in the amendments approved during the doc heal; two are v1.1.0 deliverables.

---

## 3. v1.1.0 proposed scope

### 3a. v1.1.0 must-ship items (the release's reason to exist)

Five items. These close the biggest credibility gaps from v1.0.0.

1. **Docs heal — already in motion.** `zero-trust.md`, `kubernetes.md`, `graphql-schema.md`, `aveva-pi-to-tdengine.md` per the Phase 2 plan + post-heal audit.
2. **NetworkPolicy allow-list.** Make the default-deny operable. One allow-list policy per service tier. Without this, the NetworkPolicy we ship is demo-only.
3. **Observability bring-up in k8s.** Minimum: Prometheus deployment + ServiceMonitor for Django + IDP, `django-prometheus` wired, Spring Actuator `/actuator/prometheus` enabled, one Grafana dashboard committed (telemetry throughput + alert rate + API p95). Not OTel tracing — that's v1.2.0.
4. **Live Oracle Cloud demo.** Deploy v1.1.0 to OCI using the already-committed Terraform + Ansible. Update README demo badge to point at the live URL. This is the single biggest outside-facing credibility move.
5. **cert-manager + Let's Encrypt for ingress.** The ingress manifest references TLS secrets that don't exist in base — cert-manager fills that gap with one ClusterIssuer. This is also the foundation mTLS work will build on in v1.2.0.

### 3b. v1.1.0 nice-to-have items (ship if time permits)

- **SPIRE workload registration for one service.** A ClusterSPIFFEID for Spring IDP, IDP fetches its own SVID (even if it doesn't yet use it for transport). Converts SPIRE from "deployed" to "partially wired."
- **EMQX TLS listener uncommented.** Depends on cert-manager landing first. Adds MQTT-over-TLS on port 8883 alongside the existing 1883 cleartext.
- **Email channel in Spring Notification Service.** Add `EmailNotificationService.java` alongside `SlackNotificationService.java`, an `alerts.notifications` consumer branch for `notify_email`. Un-strikes the "email on roadmap" README line.
- **Delete `slack-bot/` directory.** Retires a stale placeholder.
- **`ROADMAP.md` in root.** Commits the output of this retrospective's Section 3 as a real planning artefact so v1.2.0 doesn't have to reconstruct it.

### 3c. Explicitly DEFERRED to v1.2.0+ (not in v1.1.0)

Calling these out so v1.1.0 doesn't creep:

- **mTLS service-to-service.** Real mTLS requires SPIRE workload consumption in every service — multi-week effort across three runtimes (Python, Java, Dart).
- **OTel distributed tracing.** Instrumentation in Django + Spring + Flutter is real work; Jaeger receives nothing today and will keep receiving nothing through v1.1.0.
- **Loki log aggregation.** No scaffolding, no urgency.
- **HashiCorp Vault.** Likely replaced with External Secrets Operator rather than built. Needs a design decision first.
- **Django `ai/` app (predictive maintenance).** README claim already removed. Bring back when there's real ML, not a scaffolded app.
- **MinIO integration.** Ship when a feature needs it (AI models, backup export).
- **Slack Bot as a standalone service.** Covered by Spring Notification Service.

---

## 4. Zero Trust specifically

| Control | Original plan | v1.0.0 | v1.1.0 target |
|---|---|---|---|
| JWT (RS256) at API edge | Planned (CLAUDE.md Phase 2) | **SHIPPED** — `JwtService.java`, JWKS endpoint, Django middleware validates | No change |
| Permission-based RBAC | Planned | **SHIPPED** — 20+ permissions, 4 default roles, custom roles via Django admin, enforced on REST/GraphQL/Socket.IO | No change |
| Default-deny NetworkPolicy | Planned | **SHIPPED (skeleton)** — `default-deny.yaml` + `allow-dns` only | No change (covered by row below) |
| NetworkPolicy allow-list | Implied ("no cross-service direct DB access") | **NOT STARTED** | **Must-ship** — one allow-list per service tier |
| EMQX auth + ACL | Planned | **SHIPPED** — password auth + file ACL, `no_match=deny` | No change |
| EMQX TLS listener | Planned ("mTLS, ACL" in stack table) | **NOT STARTED** — commented out in `emqx.conf:40-49` | **Nice-to-have** — uncomment after cert-manager lands |
| SPIRE server + agent | Planned Phase 2 | **SHIPPED (deployed)** — `c784a1d` | No change |
| SPIRE workload registration | Implied | **NOT STARTED** — zero `spiffe://` references in workload code | **Nice-to-have** — one ClusterSPIFFEID for Spring IDP |
| SPIRE SVID consumption | Implied | **NOT STARTED** | Defer to v1.2.0 |
| Service-to-service mTLS | Claimed in v1.0.0 README | **NOT STARTED** — no `server.ssl.*` in Spring, no inter-service TLS | Defer to v1.2.0 (gated on SPIRE workload consumption) |
| cert-manager | Not explicitly planned | **NOT STARTED** | **Must-ship** — foundation for ingress TLS and future mTLS |
| Ingress mTLS | Not in plan | **NOT STARTED** — ingress terminates plain TLS, no client-cert verify | Defer to v1.2.0 |

### Zero-Trust recommendation

**v1.1.0 closes:** NetworkPolicy allow-list (must), cert-manager (must), and either EMQX TLS OR one SPIRE workload wired (pick one, not both). That moves the Zero Trust posture from "skeleton + identity" to "skeleton + identity + operable network segmentation + auto-TLS." It is a believable 4–6 week increment.

**v1.1.0 does not close:** service-to-service mTLS, SPIRE SVID consumption in app code, ingress mTLS. These are honest v1.2.0 items and the zero-trust.md doc should label them as such.

The zero-trust.md doc should use this framing: each control gets an `IMPLEMENTED` / `DEPLOYED-NOT-WIRED` / `TARGET (v1.1.0)` / `TARGET (v1.2.0+)` tag, with the relevant manifest or config line cited. That is more defensible than a generic "we do Zero Trust" doc.

---

## 5. Release cadence recommendation

v1.0.0 was an architectural scaffold release — scope-cut for coherent tagging, not for production-parity feature completeness. The 8 post-v1.0.0 commits are deployability fixes (Flutter pin, k8s deploy repair, CI repair, Terraform+Ansible, README, audit) rather than net-new features. The cadence discipline starts with v1.1.0.

**Recommended v1.1.0 target: 6 weeks from today (2026-06-03).**

The must-ship list (docs heal + NetworkPolicy allow-list + observability + cert-manager + OCI live demo) is realistic in 4 weeks if nothing else happens, but 6 weeks gives room for the nice-to-haves (especially SPIRE workload wiring, which is the single highest-leverage credibility item) and for the AVEVA PI doc to land properly rather than as a rushed artefact. 8 weeks would be too long — the outside-facing gap (no live demo, no updated docs) starts to cost credibility faster than v1.1.0 scope grows. 4 weeks sacrifices the nice-to-haves and leaves Zero Trust at the same "skeleton + identity" level it sits at today.

**Going forward:** commit a `ROADMAP.md` at the top of v1.1.0 that publishes the 3a/3b/3c split above. Every subsequent release cycle should update it in the same commit that opens the cycle, so the retrospective half of this report is a 30-minute exercise, not a multi-hour forensic dig through git.

---

## Summary

- v1.0.0 is best understood as **a comprehensive architectural scaffold**, not a production release. Most subsystems are either SHIPPED (Django core, Spring IDP, MQTT bridge, TDengine, Flutter, CI/CD) or PARTIAL (EMQX TLS, NetworkPolicies, observability, SPIRE). A handful are NOT STARTED (ai/, Slack bot standalone, Loki, Vault, mTLS).
- The big credibility gap is **deployed-but-not-wired infrastructure**: SPIRE, Prometheus/Grafana/Jaeger, NetworkPolicies, EMQX TLS. The manifests exist and look complete at a glance; the integration is the work.
- **v1.1.0 in 6 weeks** is the right target, focused on closing the deployed-but-not-wired gaps rather than adding new subsystems.
- **A standing `ROADMAP.md`** is the cheapest process improvement available and should land with v1.1.0.

---

## Related docs

- `ROADMAP.md` — canonical planning surface going forward
- `docs/_audit/link-audit.md` — source for Section 2c
- `docs/architecture/overview.md` — the system surface this retrospective reviews
