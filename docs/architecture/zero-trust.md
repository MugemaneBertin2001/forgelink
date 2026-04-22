# ForgeLink Zero Trust Architecture

**Last updated:** 2026-04-22
**Current state reference:** v1.0.0 (see [release retrospective](../_meta/release-retrospective-v1.0.md))
**Roadmap reference:** [ROADMAP.md](../../ROADMAP.md)

## Scope and honesty principle

This document describes the Zero Trust target architecture and the current implementation status of every control. Each control is labeled with one of:

- **IMPLEMENTED** — fully wired and operational
- **DEPLOYED-NOT-WIRED** — infrastructure present, integration pending
- **TARGET (v1.1.0)** — in scope for next release (see ROADMAP.md)
- **TARGET (v1.2.0+)** — in scope for a future release

The labels are not apologies. A platform that documents the maturity of each control is more trustworthy than a platform that claims uniform coverage — the labelling itself is the professionalism signal. We ship the skeleton now and close the integration gaps on an explicit cadence.

The architecture is comprehensive. The implementation is maturing.

---

## Zero Trust surface diagram

```
                         ╔═══════════════════════════════════╗
                         ║        IDENTITY BOUNDARY          ║
                         ║   Spring IDP — RS256 JWT + JWKS   ║
                         ║   Refresh tokens in Redis         ║
                         ║   Permission-based RBAC in Django ║
                         ╚══════════════╦════════════════════╝
                                        │ JWT (bearer)
                                        ▼
  ╔═══════════════════════════════════════════════════════════════════╗
  ║                        CLUSTER BOUNDARY                           ║
  ║                                                                   ║
  ║   ┌──────────────────┐      ┌───────────────────┐                 ║
  ║   │  Ingress (nginx) │──TLS─│  Django API       │                 ║
  ║   │  TLS terminate   │      │  JWT middleware   │                 ║
  ║   └──────────────────┘      └─────────┬─────────┘                 ║
  ║                                       │                           ║
  ║   NetworkPolicy: default-deny         │ (allow-list target v1.1)  ║
  ║   across forgelink namespace          │                           ║
  ║                                       ▼                           ║
  ║   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐   ║
  ║   │ Postgres │   │  Redis   │   │  Kafka   │   │   TDengine   │   ║
  ║   └──────────┘   └──────────┘   └──────────┘   └──────────────┘   ║
  ║                                                                   ║
  ║   ┌────────────────────────────────────────────────┐              ║
  ║   │ SPIRE Server + Agent DaemonSet                 │              ║
  ║   │ Trust domain: forgelink.local                  │              ║
  ║   │ Workload registration: TARGET (v1.1.0)         │              ║
  ║   └────────────────────────────────────────────────┘              ║
  ╚════════════════════════════╦══════════════════════════════════════╝
                               │ MQTT (QoS 0/1)
                               ▼
                    ╔══════════════════════════════╗
                    ║   OT↔IT BOUNDARY (EMQX)      ║
                    ║   Password auth + ACL        ║
                    ║   TLS listener commented out ║
                    ║   → TARGET (v1.1.0)          ║
                    ╚══════════════╦═══════════════╝
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │  Field devices (PLCs, VFDs,  │
                    │  sensors, OPC-UA adapters)   │
                    │  — outside our trust boundary│
                    └──────────────────────────────┘
```

---

## Threat model

Threats we design against, in order of likely blast radius:

1. **Lateral movement after a pod compromise.** An attacker who gains code execution in one pod (via a vulnerable dependency, a leaked credential, or a misconfigured volume) attempts to reach other services — Postgres, TDengine, Kafka, the Spring IDP — and exfiltrate data or pivot further. Primary control: NetworkPolicy segmentation. Secondary: workload identity via SPIRE once wired.
2. **Compromised MQTT device publishing outside its ISA-95 subtree.** A device credentialed for `melt-shop` attempts to publish to `finishing` or `$SYS/#`. Primary control: EMQX ACL with per-area topic wildcards and `no_match=deny` (see `config/emqx/acl.conf`). Secondary (future): mTLS client certs scoped per area.
3. **Credential theft at the API edge.** A stolen JWT is replayed against the REST, GraphQL, or Socket.IO surface. Primary control: short-lived (24h) access tokens, RS256 signature verification via JWKS, refresh-token blacklist in Redis. The IDP can revoke a refresh token without requiring all downstream services to coordinate.
4. **Privilege escalation via over-broad role.** An authenticated user with a lower-tier role attempts an admin action (e.g., creating alert rules, managing users, exporting raw telemetry). Primary control: atomic permission-based RBAC in Django — every REST viewset, GraphQL mutation, and Socket.IO event is gated on specific permissions (e.g., `alerts.create_rule`, not just "role=admin").
5. **Exfiltration via Slack webhook.** The Spring Notification Service holds a Slack webhook URL and posts alert payloads outbound. A compromised pod could abuse the webhook for data exfiltration. Primary control (target): egress NetworkPolicy restricting the notification service to the Slack API IP range only.
6. **Secret sprawl from plain k8s Secrets.** RSA private keys, DB passwords, and Slack webhook URLs live in k8s Secrets. Anyone with namespace-level `get secrets` RBAC in the `forgelink` namespace can read them. Primary control (target v1.2.0+): External Secrets Operator or Vault integration.
7. **Supply-chain compromise of base images.** A malicious update to an upstream image (Python, OpenJDK, Alpine) introduces a backdoor. Primary control: Trivy scans in CI, Dependabot-driven updates. Not in scope for this document.

The threat model does not include physical access to PLCs, nation-state SIGINT, or insider threats at the admin role — see the [explicit non-scope section](#what-this-architecture-explicitly-does-not-protect-against).

---

## Identity layer

### JWT (RS256) at the API edge — IMPLEMENTED

Every request that hits the Django API surface (REST, GraphQL, Socket.IO) is validated against an RS256-signed JWT issued by Spring IDP.

- **Signing:** `services/spring-idp/src/main/java/com/forgelink/idp/service/JwtService.java` (162 lines). Private key loaded from `/run/secrets/jwt-private.pem`. Issuer: `forgelink-idp`. Access token lifetime: 24h. Refresh token lifetime: 30d.
- **Verification:** Django middleware at `services/django-api/apps/core/middleware.py` (284 lines) fetches the JWKS from `https://idp.forgelink.local/auth/jwks` and caches it. Each request resolves the `role_code` claim to the user's active permission set.
- **Refresh flow:** refresh tokens are stored in Redis (not the JWT) so revocation is constant-time and does not require distributed coordination. `LogoutRequest` deletes the refresh token; subsequent refresh attempts fail.
- **Socket.IO:** the WebSocket handshake carries the JWT in the auth payload (`services/django-api/apps/alerts/socketio.py`). A failed verification closes the connection before namespace join.

Config reference:

```yaml
# services/spring-idp/src/main/resources/application.yml
jwt:
  privateKeyPath: /run/secrets/jwt-private.pem
  publicKeyPath: /run/secrets/jwt-public.pem
  accessTokenExpiryHours: 24
  refreshTokenExpiryDays: 30
  issuer: forgelink-idp
  keyId: forgelink-key-1
```

### Permission-based RBAC — IMPLEMENTED

Authorization is atomic-permission, not role-label. The IDP stores the user's `role_code` (a string) in the JWT; Django resolves the role to a permission set at request time.

- **Permission enumeration:** 20+ permissions across five modules (assets, alerts, telemetry, simulator, admin). Examples: `alerts.acknowledge`, `alerts.create_rule`, `telemetry.export`, `admin.manage_roles`.
- **Default roles:** `FACTORY_ADMIN` (all), `PLANT_OPERATOR`, `TECHNICIAN`, `VIEWER`.
- **Custom roles:** administrators can create new roles via the Django Unfold admin and assign arbitrary permission combinations.
- **Enforcement:** `services/django-api/apps/core/permissions.py` (293 lines) provides DRF permission classes; `decorators.py` provides function-view decorators; the Socket.IO namespaces check permissions on subscribe.

This design means the IDP can issue tokens for custom roles without knowing what those roles allow — the permission mapping lives in Django and changes without requiring IDP redeploys.

### SPIRE server and agent — DEPLOYED-NOT-WIRED

SPIRE infrastructure is deployed to the cluster but no workload currently registers for or consumes an SVID.

- **Server:** `k8s/base/spire/spire-server.yaml` (180 lines). StatefulSet with SQLite data store, k8s_psat node attestor, disk key manager, 1h X.509 SVID TTL, 5m JWT SVID TTL. Trust domain: `forgelink.local`.
- **Agent:** `k8s/base/spire/spire-agent.yaml` (145 lines). DaemonSet with k8s workload attestor, Unix workload attestor, Unix domain socket at `/run/spire/sockets/agent.sock`.
- **Workload side:** no Java `spire-api-sdk` dependency in `services/spring-idp/pom.xml`; no Python `py-spiffe` in any `requirements.txt`; no `spiffe://` reference in any workload code (`grep -r 'spiffe://' services/` returns zero hits). No `ClusterSPIFFEID` CRD applied.

Config excerpt (server trust domain):

```hcl
# k8s/base/spire/spire-server.yaml:46-62
server {
  bind_address = "0.0.0.0"
  bind_port    = "8081"
  trust_domain = "forgelink.local"
  data_dir     = "/run/spire/data"
  ca_key_type  = "rsa-2048"
  default_x509_svid_ttl = "1h"
  default_jwt_svid_ttl  = "5m"
  ca_subject = {
    country      = ["RW"]
    organization = ["ForgeLink"]
    common_name  = "ForgeLink SPIRE CA"
  }
}
```

### SPIRE workload registration — TARGET (v1.1.0)

First ClusterSPIFFEID will be issued to Spring IDP. The minimal viable target is a `ClusterSPIFFEID` resource that maps pods with `app.kubernetes.io/name: forgelink-idp` to the SPIFFE ID `spiffe://forgelink.local/ns/forgelink/sa/forgelink-idp`, plus the pod fetching the SVID via the agent socket — no transport change yet, just identity acquisition.

### SPIRE SVID consumption in app code — TARGET (v1.2.0+)

Full mTLS handshake using SPIRE-issued SVIDs requires each service to link against a SPIFFE Workload API client library and replace its HTTP/gRPC transport with an X.509-SVID-authenticated one. This is multi-week work across three runtimes (Python, Java, Dart) and is a v1.2.0 theme, not a v1.1.0 item.

---

## Network layer

### Default-deny NetworkPolicy — IMPLEMENTED (skeleton)

Every pod in the `forgelink` namespace is isolated by default.

```yaml
# k8s/base/network-policies/default-deny.yaml:1-32
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: forgelink
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: forgelink
spec:
  podSelector: {}
  policyTypes: [Egress]
  egress:
    - to:
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - {protocol: UDP, port: 53}
        - {protocol: TCP, port: 53}
```

Applied as-is, nothing reaches anything except kube-dns. The allow-list that makes the cluster operable is the next control.

### NetworkPolicy allow-list — TARGET (v1.1.0)

Per-service-tier allow rules. Minimum viable set:

- `forgelink-api` → `forgelink-idp` (HTTPS 8080 for JWKS, auth)
- `forgelink-api` → `postgresql` (5432)
- `forgelink-api` → `redis` (6379)
- `forgelink-api` → `kafka` (9092)
- `forgelink-api` → `tdengine` (6030, 6041)
- `forgelink-api` → `emqx` (1883 → 8883 once TLS listener lands)
- `forgelink-notification` → `kafka` (9092)
- `forgelink-notification` → `0.0.0.0/0:443` (egress for Slack webhook)
- `ingress-nginx/*` → `forgelink-api` and `forgelink-idp`
- `spire:spire-agent` (DaemonSet) → `spire:spire-server` (8081)

Delivered as one file per tier under `k8s/base/network-policies/` with namespace- and label-selectors, no IP literals.

### Ingress TLS termination — IMPLEMENTED (user-provided secrets)

```yaml
# k8s/base/ingress/ingress.yaml:17-23
spec:
  ingressClassName: nginx
  tls:
    - hosts: [forgelink.local, api.forgelink.local, idp.forgelink.local]
      secretName: forgelink-tls
```

The `forgelink-tls` and `forgelink-mqtt-tls` secrets are not in `k8s/base/secrets/` — the deployer is expected to provide them. That's workable for a closed demo but unacceptable as a production posture.

### cert-manager + Let's Encrypt — TARGET (v1.1.0)

One `ClusterIssuer` (ACME HTTP-01) plus `Certificate` resources for `api.forgelink.local`, `idp.forgelink.local`, and `mqtt.forgelink.local`. Replaces the user-provided secrets with automated issuance and renewal. Precondition for EMQX TLS listener (next row) and for future ingress mTLS.

### Service-to-service mTLS — TARGET (v1.2.0+)

Gated on SPIRE SVID consumption. The target is every intra-cluster call (Django → Spring IDP, Notification → Kafka, API → Postgres with `sslmode=verify-full`) using SVID-presented client certs. Partial delivery via cert-manager-issued intermediate certs is possible but not preferred — SPIRE-issued SVIDs carry workload identity, and identity-bound certs are the point of mTLS in a Zero Trust context.

### Ingress mTLS — TARGET (v1.2.0+)

Nginx `nginx.ingress.kubernetes.io/auth-tls-verify-client: on` with a trusted CA bundle. Scope limited to specific hosts (e.g., an administrative subdomain for admin operations) — we do not expect every mobile client to present a cert.

---

## Messaging layer

### EMQX password authentication — IMPLEMENTED

```hcl
# config/emqx/emqx.conf:52-62
authentication = [
  {
    mechanism = "password_based"
    backend   = "built_in_database"
    user_id_type = "username"
    password_hash_algorithm {
      name = "sha256"
      salt_position = "suffix"
    }
  }
]
```

Users are seeded by `config/emqx/init-users.sh`. One user per ISA-95 area (`device-melt-shop`, `device-continuous-casting`, `device-rolling-mill`, `device-finishing`) plus internal `bridge`, admin `operator`, and `admin` accounts.

### EMQX ACL default-deny — IMPLEMENTED

```hcl
# config/emqx/emqx.conf:64-84
authorization {
  sources = [
    { type = "built_in_database", enable = true },
    { type = "file", enable = true, path = "/opt/emqx/etc/acl.conf" }
  ]
  no_match     = "deny"
  deny_action  = "disconnect"
  cache { enable = true, max_size = 32, ttl = "1m" }
}
```

The ACL file (`config/emqx/acl.conf`, 65 lines) binds each area-specific user to its ISA-95 subtree and closes with `{deny, all, all, ["#"]}.`. A `melt-shop` device cannot publish to `finishing`.

Excerpt:

```erlang
# config/emqx/acl.conf:22-25
{allow, {user, "device-melt-shop"}, publish,
    ["forgelink/steel-plant-kigali/melt-shop/+/+/+/telemetry"]}.
{allow, {user, "device-melt-shop"}, subscribe,
    ["forgelink/steel-plant-kigali/melt-shop/+/+/+/commands"]}.
```

### EMQX TLS listener — TARGET (v1.1.0)

The listener is scaffolded in `config/emqx/emqx.conf:40-49` with the literal comment `## SSL/TLS Listener (for production with mTLS)` and is currently commented out:

```hcl
# config/emqx/emqx.conf:40-49 (commented out)
# listeners.ssl.default {
#   bind = "0.0.0.0:8883"
#   ssl_options {
#     keyfile   = "/opt/emqx/etc/certs/server.key"
#     certfile  = "/opt/emqx/etc/certs/server.crt"
#     cacertfile = "/opt/emqx/etc/certs/ca.crt"
#     verify    = verify_peer
#     fail_if_no_peer_cert = true
#   }
# }
```

v1.1.0 uncomments this, mounts certs issued by cert-manager, and keeps the cleartext 1883 listener for local-dev and simulator traffic only. `verify_peer` + `fail_if_no_peer_cert` is mTLS — devices must present a client cert. Per-device client certs, scoped per area, are the long-term direction; the v1.1.0 target is a single per-environment device-fleet CA.

---

## Secrets layer

### k8s Secrets (baseline) — IMPLEMENTED

Secrets are declared per-service in `k8s/base/secrets/secrets.example.yaml`:

- `forgelink-secrets` (Django settings)
- `idp-secrets` (JWT keys, DB URL)
- `notification-secrets` (Slack webhook URL)
- `postgresql-secrets`
- `emqx-secrets`

RSA keys for JWT signing live in `secrets/jwt-private.pem` and `secrets/jwt-public.pem` and are mounted into the Spring IDP pod. The example file is committed; real values are supplied at deploy time.

**Known limitation:** anyone with namespace-level `get secrets` RBAC can read them in plaintext. k8s Secret encryption-at-rest depends on cluster-level etcd encryption configuration, which we do not manage here.

### External Secrets Operator or Vault — TARGET (v1.2.0+, decision pending)

The original CLAUDE.md named HashiCorp Vault. Operationally, External Secrets Operator (ESO) plus a cloud secret backend (OCI Vault, AWS Secrets Manager, GCP Secret Manager) is lighter to run than a self-hosted Vault HA pair. ESO also integrates natively with Kustomize overlays.

**Decision required before v1.2.0 implementation:**

- If ForgeLink targets air-gapped / on-prem-only deployments → self-hosted Vault.
- If ForgeLink targets cloud-adjacent deployments (including the Oracle Cloud live demo) → ESO + OCI Vault.

No code is committed to either path in v1.0.0 or v1.1.0.

---

## What this architecture explicitly does not protect against

Controls we have chosen not to implement, with stated reasoning. An honest Zero Trust posture names these rather than omits them.

1. **Compromised OT devices upstream of the MQTT bridge.** If a PLC or edge gateway is physically compromised, it can publish valid-looking telemetry within its ACL scope. We detect anomalous values (threshold alerts, simulator-derived learned ranges in future ML work) but do not validate data integrity cryptographically. Per-device signing is out of scope.
2. **Physical access to field devices.** Tampering with a thermocouple to report false temperatures is an OT-plant security concern, not an IT-platform concern. Facility access controls are out of scope.
3. **Insider threats at the admin role.** A compromised or malicious `FACTORY_ADMIN` can do anything the platform allows, including creating roles, exporting data, and deleting records. We rely on audit logs (`apps/audit/`) for detection, not prevention.
4. **Supply-chain compromise of base container images.** Trivy scans in CI are a partial mitigation; we do not use reproducible builds, image attestations, or SLSA provenance. This is common practice, not an acceptable stopping point forever — it is a v2.x concern.
5. **Nation-state signals intelligence.** Traffic analysis of MQTT topic patterns, timing side channels, and similar threats are outside the design envelope. The relevant mitigation (traffic padding, mixnets) imposes latency unsuitable for real-time control telemetry.
6. **DDoS at the ingress.** We rate-limit at the application layer (60 req/min/user, 600 req/min global per endpoint) and at EMQX (100 msg/s per client, 1000 msg/s broker). Transport-layer DDoS mitigation relies on the hosting provider (OCI, GCP, AWS) or an upstream CDN/WAF.
7. **Secrets exposure via Docker image layers.** We mount secrets as files or env vars at runtime, never COPY them into images, and Trivy fails builds with hardcoded credentials. But we do not run a secret-scanning policy on pushed images — relying instead on CI enforcement at source.

This list is not exhaustive. The principle is: we protect against operationally likely attacks on an IIoT platform, and we document the remaining threat surface rather than claim coverage we don't have.

---

## Control status summary

| Layer | Control | Status |
|---|---|---|
| Identity | JWT (RS256) at API edge | IMPLEMENTED |
| Identity | Permission-based RBAC | IMPLEMENTED |
| Identity | Refresh-token blacklist (Redis) | IMPLEMENTED |
| Identity | SPIRE server + agent | DEPLOYED-NOT-WIRED |
| Identity | SPIRE workload registration | TARGET (v1.1.0) |
| Identity | SPIRE SVID consumption | TARGET (v1.2.0+) |
| Network | Default-deny NetworkPolicy | IMPLEMENTED (skeleton) |
| Network | NetworkPolicy allow-list | TARGET (v1.1.0) |
| Network | Ingress TLS termination | IMPLEMENTED (user-provided secrets) |
| Network | cert-manager + Let's Encrypt | TARGET (v1.1.0) |
| Network | Service-to-service mTLS | TARGET (v1.2.0+) |
| Network | Ingress mTLS | TARGET (v1.2.0+) |
| Messaging | EMQX password auth | IMPLEMENTED |
| Messaging | EMQX ACL default-deny | IMPLEMENTED |
| Messaging | EMQX TLS listener | TARGET (v1.1.0) |
| Secrets | k8s Secrets (baseline) | IMPLEMENTED |
| Secrets | External Secrets Operator / Vault | TARGET (v1.2.0+, decision pending) |

---

## Related docs

- [ROADMAP.md](../../ROADMAP.md) — when each TARGET control lands
- [v1.0.0 release retrospective](../_meta/release-retrospective-v1.0.md) — how we arrived at this posture
- [Architecture overview](overview.md) — system-level view
- [UNS topic hierarchy](uns-topic-hierarchy.md) — what the EMQX ACL secures
- [Kubernetes deployment](../deployment/kubernetes.md) — where these controls ship
