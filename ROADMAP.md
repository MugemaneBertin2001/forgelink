# ForgeLink Roadmap

**Last updated:** 2026-04-22
**Current release:** v1.0.0 (2026-03-23)
**Next release:** v1.1.0 (target: 2026-06-03)

## Philosophy

Tagged releases are coherent increments, not arbitrary cutoffs. Each release is scoped around a theme that answers one question: *what did this cycle make operable that wasn't before?* Items that don't fit the theme are publicly deferred rather than silently dropped — deferred scope is a first-class decision, documented so the next cycle starts from evidence instead of reconstruction. Every release cycle produces a retrospective in `docs/_meta/` and updates this file in the commit that opens the next cycle.

## v1.1.0 — "Operable Posture" (target 2026-06-03)

The theme: convert deployed-but-not-wired infrastructure into operable systems. Close the Zero Trust skeleton, land the observability stack in production, stand up a live demo.

### Must-ship

1. **Docs heal — already in motion.** `zero-trust.md`, `kubernetes.md`, `graphql-schema.md`, `aveva-pi-to-tdengine.md` per the Phase 2 plan + post-heal audit.
2. **NetworkPolicy allow-list.** Make the default-deny operable. One allow-list policy per service tier. Without this, the NetworkPolicy we ship is demo-only.
3. **Observability bring-up in k8s.** Minimum: Prometheus deployment + ServiceMonitor for Django + IDP, `django-prometheus` wired, Spring Actuator `/actuator/prometheus` enabled, one Grafana dashboard committed (telemetry throughput + alert rate + API p95). Not OTel tracing — that's v1.2.0.
4. **Live Oracle Cloud demo.** Deploy v1.1.0 to OCI using the already-committed Terraform + Ansible. Update README demo badge to point at the live URL. This is the single biggest outside-facing credibility move.
5. **cert-manager + Let's Encrypt for ingress.** The ingress manifest references TLS secrets that don't exist in base — cert-manager fills that gap with one ClusterIssuer. This is also the foundation mTLS work will build on in v1.2.0.

### Nice-to-have

- **SPIRE workload registration for one service.** A ClusterSPIFFEID for Spring IDP, IDP fetches its own SVID (even if it doesn't yet use it for transport). Converts SPIRE from "deployed" to "partially wired."
- **EMQX TLS listener uncommented.** Depends on cert-manager landing first. Adds MQTT-over-TLS on port 8883 alongside the existing 1883 cleartext.
- **Email channel in Spring Notification Service.** Add `EmailNotificationService.java` alongside `SlackNotificationService.java`, an `alerts.notifications` consumer branch for `notify_email`. Un-strikes the "email on roadmap" README line.
- **Delete `slack-bot/` directory.** Retires a stale placeholder.
- **`ROADMAP.md` in root.** Commits the v1.0.0 retrospective's Section 3 as a real planning artefact so v1.2.0 doesn't have to reconstruct it. *(This file satisfies that item.)*

### Explicitly deferred to v1.2.0+

- **mTLS service-to-service.** Real mTLS requires SPIRE workload consumption in every service — multi-week effort across three runtimes (Python, Java, Dart).
- **OTel distributed tracing.** Instrumentation in Django + Spring + Flutter is real work; Jaeger receives nothing today and will keep receiving nothing through v1.1.0.
- **Loki log aggregation.** No scaffolding, no urgency.
- **HashiCorp Vault.** Likely replaced with External Secrets Operator rather than built. Needs a design decision first.
- **Django `ai/` app (predictive maintenance).** README claim already removed. Bring back when there's real ML, not a scaffolded app.
- **MinIO integration.** Ship when a feature needs it (AI models, backup export).
- **Slack Bot as a standalone service.** Covered by Spring Notification Service.

## v1.2.0 — provisional theme: "Mutual Authentication"

Scope not yet committed. Candidate items:

- Service-to-service mTLS (gated on SPIRE SVID consumption)
- OTel distributed tracing instrumentation (Django + Spring + Flutter)
- Ingress mTLS (client-cert verify at nginx)
- Loki log aggregation
- Secrets operator decision (External Secrets Operator vs. Vault)

The theme assumes v1.1.0 lands cert-manager and at least one SPIRE workload registration; without those, mTLS is not a credible v1.2.0 theme.

## How this roadmap updates

Every release cut produces (a) a retrospective doc in `docs/_meta/` and (b) an update to this file. The release retrospective is authoritative for "what shipped"; this file is authoritative for "what's next." The commit that tags a release updates this file in the same commit.

## Related docs

- [v1.0.0 release retrospective](docs/_meta/release-retrospective-v1.0.md)
- [Architecture overview](docs/architecture/overview.md)
- [Zero Trust architecture](docs/architecture/zero-trust.md) *(in progress)*
