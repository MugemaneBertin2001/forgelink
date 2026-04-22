# Kubernetes Deployment

**Last updated:** 2026-04-22

This document describes how ForgeLink deploys onto Kubernetes and labels every control as `IMPLEMENTED`, `PARTIAL`, or `TARGET (v1.1.0+)` per the convention established in [zero-trust.md](../architecture/zero-trust.md). We prefer to quote committed manifests over prose descriptions — paths to the authoritative files are inline.

## Scope

The deployment targets a vanilla Kubernetes distribution (k3s for the demo and home-lab path, any managed Kubernetes for cloud). We do not use cloud-provider-specific resources (no AWS ALB Ingress, no GKE Autopilot-only features, no OCI Native Ingress). Anything that works on k3s works on every cloud.

## Namespace strategy — IMPLEMENTED

One namespace per environment. The base Kustomization sets `namespace: forgelink`; overlays rewrite it per environment.

| Overlay | Namespace | Path |
|---|---|---|
| base | `forgelink` | `k8s/base/kustomization.yaml` |
| dev | `forgelink-dev` | `k8s/overlays/dev/kustomization.yaml` |
| staging | `forgelink-staging` | `k8s/overlays/staging/kustomization.yaml` |
| production | `forgelink-prod` (via rename in overlay) | `k8s/overlays/production/kustomization.yaml` |
| demo | `forgelink` (single-namespace demo) | `k8s/overlays/demo/kustomization.yaml` |

Each overlay uses `nameSuffix` (`-dev`, `-staging`, `-prod`) so resource names are distinct when multiple environments share a cluster. SPIRE lives in its own `spire` namespace (`k8s/base/spire/spire-server.yaml:1-7`).

## Deployment topology

### Infrastructure (StatefulSets) — IMPLEMENTED

Every stateful component is a StatefulSet with a PersistentVolumeClaim template. Replicas = 1 in base; overlays scale per environment.

| Component | Path | Replicas (base) | Volume |
|---|---|---|---|
| PostgreSQL | `k8s/base/deployments/postgresql.yaml` | 1 | `volumeClaimTemplates` |
| Redis | `k8s/base/deployments/redis.yaml` | 1 | — (in-memory, volume for append-only log) |
| Kafka (KRaft) | `k8s/base/deployments/kafka.yaml` | 1 | `volumeClaimTemplates` |
| TDengine | `k8s/base/deployments/tdengine.yaml` | 1 | `volumeClaimTemplates` |
| EMQX | `k8s/base/deployments/emqx.yaml` | 1 | `volumeClaimTemplates` |

Kafka runs in KRaft mode (no Zookeeper) — the StatefulSet is self-contained. TDengine requires its data volume for both the archive files and the write-ahead log.

**Not yet in k8s (PARTIAL):** RabbitMQ is in `docker-compose.yml` but has no k8s deployment. The current command/task queue scope is served by Celery-over-Redis and Kafka; RabbitMQ comes back when a feature needs it.

### Applications (Deployments) — IMPLEMENTED

Every stateless service is a `Deployment` with `replicas >= 1` in base, scaled per-overlay. The `forgelink-api.yaml` manifest carries four deployments that share the Django image — this is the pattern we use to avoid image duplication across roles.

| Deployment | Role | Replicas (base) | Health probes |
|---|---|---|---|
| `forgelink-api` | Gunicorn serving REST + GraphQL + Socket.IO | 2 | `/health/` liveness + readiness |
| `forgelink-celery-worker` | Celery worker (telemetry rollups, retention, anomaly detection) | 2 | `celery inspect ping` liveness |
| `forgelink-celery-beat` | Celery beat scheduler | 1 | — (single-instance, scheduler) |
| `forgelink-kafka-consumer` | Kafka → TDengine consumer (`consume_telemetry --type both`) | 2 | — (readiness via process) |
| `forgelink-idp` | Spring IDP (JWT issuer) | separate deployment | Spring Actuator `/actuator/health` |
| `forgelink-notification` | Spring Notification (Slack webhook consumer) | separate deployment | Spring Actuator `/actuator/health` |

The four Django roles each run the same container image with different `command` overrides. Example (API role):

```yaml
# k8s/base/deployments/forgelink-api.yaml:41-73
containers:
  - name: api
    image: forgelink-api:latest
    ports:
      - containerPort: 8000
        name: http
    envFrom:
      - configMapRef: { name: forgelink-config }
      - secretRef:    { name: forgelink-secrets }
    env:
      - name: DJANGO_SETTINGS_MODULE
        value: "apps.core.settings"
    livenessProbe:
      httpGet: { path: /health/, port: 8000 }
      initialDelaySeconds: 30
      periodSeconds: 10
    readinessProbe:
      httpGet: { path: /health/, port: 8000 }
      initialDelaySeconds: 10
      periodSeconds: 5
```

### Init containers — IMPLEMENTED

The `forgelink-api` pod uses two init containers: `wait-for-postgresql` (netcat probe) and `migrate` (runs `python manage.py migrate --noinput`). Migrations run once per pod start, which is safe because Django's migration runner is idempotent.

### SPIRE — DEPLOYED-NOT-WIRED

SPIRE server and agent manifests (`k8s/base/spire/`) are present and deployable but no workload is registered. Status and roadmap tracked in [zero-trust.md § SPIRE](../architecture/zero-trust.md#spire-server-and-agent--deployed-not-wired).

## Networking

### Ingress — IMPLEMENTED (TLS termination), TARGET v1.1.0 (cert-manager)

One nginx Ingress for HTTP/WebSocket traffic, one for EMQX dashboard and MQTT-over-WebSocket.

- `api.forgelink.local` → `forgelink-api:8000`
- `idp.forgelink.local` → `forgelink-idp:8080`
- `forgelink.local` → path-based routing (`/api`, `/graphql`, `/socket.io` → API; `/auth` → IDP)
- `mqtt.forgelink.local` → EMQX dashboard + MQTT-over-WebSocket

TLS is terminated at nginx with `secretName: forgelink-tls` and `secretName: forgelink-mqtt-tls`. Those secrets must be provided out-of-band today; [ROADMAP.md](../../ROADMAP.md) schedules cert-manager + Let's Encrypt for v1.1.0.

### NetworkPolicy — IMPLEMENTED (skeleton), TARGET v1.1.0 (allow-list)

Default-deny is in (`k8s/base/network-policies/default-deny.yaml`). Applied as-is, every pod is isolated except for kube-dns resolution. The allow-list that makes the cluster operable is tracked as a v1.1.0 must-ship item in the roadmap and documented in [zero-trust.md § NetworkPolicy allow-list](../architecture/zero-trust.md#networkpolicy-allow-list--target-v110).

## Autoscaling — IMPLEMENTED

`k8s/base/hpa/hpa.yaml` defines HorizontalPodAutoscalers for four deployments:

| HPA | Targets | Metrics |
|---|---|---|
| `forgelink-api-hpa` | `forgelink-api` | CPU + memory |
| `forgelink-idp-hpa` | `forgelink-idp` | CPU |
| `forgelink-celery-worker-hpa` | `forgelink-celery-worker` | CPU + memory |
| `forgelink-kafka-consumer-hpa` | `forgelink-kafka-consumer` | CPU |

No HPA for `forgelink-celery-beat` (single-instance by design) or for the infrastructure StatefulSets (scaled manually via overlay patches).

## Secrets strategy — IMPLEMENTED (baseline), TARGET v1.2.0+ (operator)

Secrets live in `k8s/base/secrets/secrets.example.yaml` as templates. The real values are provided at deploy time — the example file is committed, the filled-in file (`secrets.yaml`) is gitignored. Five secret groups:

| Secret | Consumed by |
|---|---|
| `forgelink-secrets` | Django API (DB URL, Redis URL, Kafka config, TDengine config) |
| `idp-secrets` | Spring IDP (DB URL, JWT private/public keys) |
| `notification-secrets` | Spring Notification Service (Slack webhook URL, Kafka config) |
| `postgresql-secrets` | PostgreSQL StatefulSet (admin password) |
| `emqx-secrets` | EMQX (dashboard admin password) |

**Known limitations:**
- Plain k8s Secrets are base64-encoded, not encrypted at rest unless the cluster enables etcd encryption.
- No rotation automation.
- No per-environment separation beyond Kustomize overlays.

**Roadmap:** External Secrets Operator (ESO) or HashiCorp Vault is a v1.2.0+ decision (see [ROADMAP.md](../../ROADMAP.md)). The choice depends on deployment context — cloud-adjacent environments favor ESO + a cloud secret backend; air-gapped environments favor self-hosted Vault.

## Kustomize overlays — IMPLEMENTED

The overlays use the same base and apply targeted patches:

- **dev** — `replicas: 1` for all app deployments, image tag `dev`.
- **staging** — similar with image tag `staging`.
- **production** — scales replicas up, sets resource limits for production workloads.
- **demo** — single-namespace deployment using GHCR-published images (`ghcr.io/mugemanebertin2001/forgelink-*:main`), tuned for resource-constrained hosts (Raspberry Pi, Oracle Cloud free tier). Used by `scripts/deploy.sh`.

Overlays never duplicate manifests — all changes are JSON-Patch ops against base resources. This keeps the base as the single source of truth.

## ArgoCD — IMPLEMENTED (optional)

`k8s/argocd/base/forgelink-app.yaml` defines an ArgoCD Application pointing at this repo. Teams that run ArgoCD can adopt the ForgeLink deployment as a GitOps-managed app without modifying the base Kustomization.

## Deployment modes

Two documented paths:

1. **`scripts/deploy.sh`** — single-command deploy to a local k3s cluster. Reads `k8s/overlays/demo/`, generates secrets, waits for pods, reports URLs. Used for Raspberry Pi and VPS demos.
2. **`infra/terraform/` + `infra/ansible/`** — provisions a VM (OCI Free Tier by default), installs k3s via Ansible, applies the same overlay. Used for the Oracle Cloud live-demo path planned for v1.1.0.

Both paths land the same manifests. The difference is only in how the cluster gets provisioned.

## What is proposed vs. implemented

Explicit status per component to avoid the "looks complete" trap:

| Component | State |
|---|---|
| Base manifests for API, IDP, Notification | IMPLEMENTED |
| StatefulSets for PostgreSQL, Redis, Kafka, TDengine, EMQX | IMPLEMENTED |
| Ingress (TLS terminate only) | IMPLEMENTED |
| HPA for four deployments | IMPLEMENTED |
| Overlays (dev, staging, production, demo) | IMPLEMENTED |
| ArgoCD app manifest | IMPLEMENTED |
| SPIRE server + agent manifests | DEPLOYED-NOT-WIRED (no workload registration) |
| Default-deny NetworkPolicy | IMPLEMENTED (skeleton only) |
| NetworkPolicy allow-list | TARGET (v1.1.0) |
| cert-manager + Let's Encrypt | TARGET (v1.1.0) |
| Prometheus / Grafana in k8s | TARGET (v1.1.0) |
| Jaeger / OTel instrumentation | TARGET (v1.2.0+) |
| RabbitMQ deployment | Deferred (not currently needed) |
| External Secrets Operator or Vault | TARGET (v1.2.0+, decision pending) |

---

## Related docs

- [ROADMAP.md](../../ROADMAP.md) — when each TARGET lands
- [v1.0.0 release retrospective](../_meta/release-retrospective-v1.0.md) — how the current state was reached
- [Zero Trust architecture](../architecture/zero-trust.md) — security posture these manifests implement
- [Local development setup](local-dev.md) — Docker Compose path (pre-Kubernetes)
- [Architecture overview](../architecture/overview.md) — system-level view
