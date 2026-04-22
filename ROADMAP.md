# ForgeLink Roadmap

**Last updated:** 2026-04-22
**Current release:** v1.0.0 (2026-03-23)
**Next release:** v1.1.0 (target: 2026-06-03, demo-live checkpoint)
**Target release:** v2.0.0 (target: 2026-10-14, productization cut)

## Philosophy

Tagged releases are coherent increments, not arbitrary cutoffs. Each release is scoped around a theme that answers one question: *what did this cycle make operable or demonstrable that wasn't before?* Items that don't fit the theme are publicly deferred rather than silently dropped — deferred scope is a first-class decision, documented so the next cycle starts from evidence instead of reconstruction. Every release cycle produces a retrospective in `docs/_meta/` and updates this file in the commit that opens the next cycle.

**As of 2026-04-22, the overall trajectory is governed by [`docs/_meta/v2.0.0-productization-plan.md`](docs/_meta/v2.0.0-productization-plan.md).** That plan takes ForgeLink from scaffold-with-honest-labels (v1.0.0) to fully productized consulting credibility substrate (v2.0.0) across four six-week milestones (M1–M4). v1.1.0 is the M1 public checkpoint; v2.0.0 is the M4 release.

## v1.1.0 — "Live" (target 2026-06-03)

The theme: public demo URL reachable, end-to-end data flow visible, honest scope labels on every surface. v1.1.0 is public-worthy — it is the earliest release a reviewer can encounter and draw a fair conclusion from.

### Must-ship (all items demo-visible)

1. **Delete list executed.** Removes `slack-bot/`, empty `apps/ai/`, vestigial `mobile/flutter-app/`, MinIO and RabbitMQ from compose, all SPIRE manifests, Vault references. See productization plan § 8.
2. **NetworkPolicy allow-list.** 8+ policies per service tier, Calico CNI on k3s, `scripts/test-networkpolicy.sh` verifies allow + deny matrix.
3. **cert-manager + Let's Encrypt.** `https://forgelink.mugemanebertin.com` serves a real LE cert with auto-renewal.
4. **Observability in k8s.** Prometheus + Grafana deployed; `django-prometheus` + Spring Actuator exposing metrics; one committed dashboard showing telemetry ingest rate, alert rate, API p95.
5. **OCI Always Free live deploy.** Demo URL reachable 24/7; three seeded demo accounts (viewer / operator / admin); nightly reset CronJob keeps the demo clean.
6. **Mobile APK public download.** Signed APK in GitHub Releases, QR code in README, sideload guide.
7. **Simulator hardened for continuous operation.** Runs 30+ days without manual intervention; backoff-and-retry on transient disconnects.
8. **Docs rewritten to match running reality.** README + zero-trust.md + overview.md reflect the post-delete-list state; no SPIRE claim; no RabbitMQ/MinIO/Vault mentions.

### Exit criteria (v1.1.0 does not tag until all are true)

- Visit URL → login → see live data within 10 minutes.
- APK QR code → mobile login → receive test alert notification.
- `kubectl get networkpolicy -n forgelink` shows ≥8 allow-list policies; test script passes.
- Grafana panel shows non-zero `forgelink_telemetry_records_per_second`.

## v2.0.0 — "Productized" (target 2026-10-14)

The theme: every claim in the README is backed by running behavior a reviewer can observe in 10 minutes. No `DEPLOYED-NOT-WIRED`. No `PARTIAL`. No `NOT STARTED that was in the original claim`.

### Must-ship (delivered across M2, M3, M4)

1. **Service-to-service mTLS via internal PKI (not SPIRE).** cert-manager-issued certs from a self-signed ClusterIssuer; Spring access logs show client DN; cleartext probes rejected at handshake.
2. **EMQX TLS listener active on 8883.** Cert-manager-issued server cert; `mosquitto_pub --cafile ... -p 8883` works; cleartext rejected.
3. **Email notification channel.** Alert rule with `notify_email=true` dispatches SMTP within 30s to a public demo inbox.
4. **Performance characterization.** `docs/performance/v2.0.0-characterization.md` reports measured numbers from a week of live demo traffic (telemetry ingest, alert latency, API p95).
5. **Runbooks.** 5 runbooks, each tested by running it against the demo.
6. **ADRs.** 5 ADRs covering the major architectural decisions + the SPIRE-delete + scope-cut calls.
7. **Demo guide + external review pass.** 3 external reviewers confirm the 10-minute reviewer journey completes successfully.
8. **Docs in present tense.** Every feature-describing doc describes running behavior; "target state" language moves to ROADMAP only.

### Breaking changes (justifies the major bump)

- NetworkPolicy allow-list enforcement breaks deploys assuming flat reachability.
- Service-to-service mTLS breaks clients that don't present a cert.
- Delete list removes `slack-bot`, `apps/ai`, MinIO, RabbitMQ, SPIRE, Vault references — any downstream tooling depending on these must adapt.

## v2.1.0+ — reopened questions

Not committed. Items whose exclusion from v2.0.0 is deliberate:

- **SPIFFE/SPIRE reintroduction** — if a consulting engagement specifically requires SPIFFE. The v2.0.0 delete is reversible.
- **iOS TestFlight distribution** — requires Apple Developer account ($99/yr). Decision cost, not scope cost.
- **Loki log aggregation** — revisit alongside OTel tracing (below).
- **OTel distributed tracing.** Full instrumentation in Django + Spring + Flutter. Jaeger already deployed; replace with Tempo or Grafana Cloud if the operational cost of self-hosted tracing is not justified.
- **External Secrets Operator.** Cloud-adjacent deployments benefit; on-prem don't. Revisit when a deployment context demands it.

## How this roadmap updates

Every release cut produces (a) a retrospective doc in `docs/_meta/` and (b) an update to this file. The release retrospective is authoritative for "what shipped"; this file is authoritative for "what's next." The commit that tags a release updates this file in the same commit.

Mid-cycle, the productization plan (`docs/_meta/v2.0.0-productization-plan.md`) is the working-document source of truth for M1–M4 milestone detail; this file carries only the release-facing summary.

## Related docs

- [v2.0.0 productization plan](docs/_meta/v2.0.0-productization-plan.md) — full milestone-by-milestone breakdown
- [v1.0.0 release retrospective](docs/_meta/release-retrospective-v1.0.md) — diagnosis that motivated v2.0.0 scope
- [Architecture overview](docs/architecture/overview.md)
- [Zero Trust architecture](docs/architecture/zero-trust.md) — will be rewritten in M2 to reflect the PKI-based mTLS approach
