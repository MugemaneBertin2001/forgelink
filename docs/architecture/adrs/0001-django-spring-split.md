# ADR 0001 — Django + Spring split

**Status:** accepted
**Date:** 2026-03-14

## Context

ForgeLink's server-side footprint is split across three services written in two languages: Django (Python) for the REST + GraphQL + Socket.IO API and every business-data owner (assets, alerts, telemetry, simulator), and Spring Boot (Java) for the identity provider and the Slack / email notification dispatcher.

This looks inconsistent. Two obvious alternatives:

- **All-Django.** Replace Spring IDP with django-oauth-toolkit / dj-rest-auth; write Kafka → Slack in Python with confluent-kafka.
- **All-Spring.** Rebuild the business API on Spring Boot + Spring Data JPA + GraphQL Java.

We debated both before Phase 2. Neither won.

**What made us keep the split:**

1. **The IDP is a security product, not a business service.** Spring Security is the industry standard for RS256 + JWKS + refresh-token flows; it ships with years of CVE history, a mature extension surface (OIDC if we ever need it), and audit-ready default behavior. Reimplementing that in Django would mean either using django-oauth-toolkit (less battle-tested for our exact flow) or writing signing / key-rotation / JWKS endpoints by hand. Neither was worth the risk of getting token handling wrong.
2. **The notification service is a pure Kafka consumer with no DB.** Spring's `@KafkaListener` + at-least-once commit pattern is roughly 20 lines. The equivalent in Python (confluent-kafka's manual commit loop) is fine but not obviously better; Spring's built-in actuator + metrics surface came for free.
3. **Django owns the domain.** The business objects (ISA-95 hierarchy, alerts, telemetry batching, simulator) are CRUD-heavy and benefit from Django's admin (Unfold), ORM, migrations, and DRF permission wiring. Rebuilding those in Spring would be a large, low-value port.
4. **Our audience knows both.** The target engineer for this project can read Spring and Django. Forcing one language would shrink the contributor pool by less than the increased cost of the port.

The cross-language boundary is narrow: Spring IDP writes a JWT; Django validates it via JWKS. Spring Notification reads Kafka; Django produces to Kafka. Both contracts are pinned by tests (`test_jwt_contract.py`, `AlertEventConsumerTest.java`), which caught two real integration bugs (role / roles mismatch, Redis serialization) before they hit production.

## Decision

Keep the split. Django owns the business API. Spring owns identity and notification dispatch. Every cross-boundary contract — JWT payload shape, Kafka event envelope, correlation header — is versioned and covered by a test on both sides.

## Consequences

**Good:**

- Spring Security handles token issuance; we never wrote a JWKS endpoint.
- Django Unfold + DRF + django-graphql give us admin, REST, and GraphQL for the domain with almost no boilerplate.
- The notification service can be replaced (Go, Rust, anything that reads Kafka and POSTs to Slack) without touching Django.

**Painful:**

- Two language toolchains in CI (Python + Java). CI time is ~2× what all-Django would be.
- A contributor fixing a cross-service bug needs both mental models.
- Shared concerns (correlation IDs, structured logging, metrics) have to be reimplemented on each side. We've accepted this: the JWT role bug, the Redis `Instant` serializer bug, and the `StatusCode_` kwarg bug were all instances of this cost.

**Won't change unless:**

- Spring Security starts forcing a design we can't live with.
- The notification service grows stateful requirements (then Django makes sense).
- Contributor volume collapses to one person who refuses to write Java (then all-Django).
