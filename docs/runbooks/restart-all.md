# Restart the full stack

## When to reach for this

The stack is in a weird state — one or more services reporting unhealthy, or you just pulled a new image set and want a deterministic restart. This runbook is safe to run during a shift; it does *not* drop data.

If you need to wipe state, use [full-stack-reinstall](full-stack-reinstall.md) instead.

## Before you start

- You're on a box with `docker compose` (local) **or** `kubectl` (cluster). This runbook covers both.
- For the K8s path: you have `forgelink` namespace access and permission to restart deployments.
- The stateful stores (Postgres, TDengine, Redis, Kafka, EMQX) **are not restarted here**. If you need to bounce one of those, do it deliberately — see "Known pitfalls" below.

## Local (docker compose)

```bash
cd /path/to/forgelink
docker compose ps
# Expect: list of services with STATUS "Up (healthy)". Note any that are
# "Up (unhealthy)" or "Exited" — those are what we're fixing.
```

Restart only the stateless services:

```bash
docker compose restart \
  forgelink-api forgelink-idp forgelink-notification \
  forgelink-mqtt-bridge edge-gateway opcua-simulator
```

Expected: each container prints `Restarted` within ~15s.

### Verify

```bash
docker compose ps --format "table {{.Service}}\t{{.Status}}" | grep -vE "healthy|NAME"
# Expect: zero lines. Anything listed is still not healthy.

curl -fsS http://localhost:8000/health/ && echo
# Expect: {"status": "healthy", ...}

curl -fsS http://localhost:8080/actuator/health && echo
# IDP. Expect: {"status":"UP",...}

curl -fsS http://localhost:8082/actuator/health && echo
# Notification. Expect: {"status":"UP",...}
```

### Rollback

Nothing to roll back — `restart` is idempotent.

## Cluster (kubectl)

```bash
kubectl -n forgelink get pods -o wide
# Expect: every pod Running 1/1.
```

Rolling restart of the stateless deployments:

```bash
for dep in forgelink-api forgelink-idp forgelink-notification \
           forgelink-mqtt-bridge forgelink-edge-gateway \
           forgelink-opcua-simulator; do
  kubectl -n forgelink rollout restart deployment/$dep
done

# Wait for each to finish.
for dep in forgelink-api forgelink-idp forgelink-notification \
           forgelink-mqtt-bridge forgelink-edge-gateway \
           forgelink-opcua-simulator; do
  kubectl -n forgelink rollout status deployment/$dep --timeout=5m
done
```

Expected: each `rollout status` line ends with `successfully rolled out`.

### Verify

```bash
kubectl -n forgelink get pods
# Every pod Running with 0 restart count deltas.

kubectl -n forgelink exec deploy/forgelink-api -- \
  curl -fsS http://localhost:8000/health/
# {"status":"healthy",...}
```

### Rollback

```bash
kubectl -n forgelink rollout undo deployment/<name>
```

Only use if a restart surfaced a bad image that was *already running*. If you just pulled new images, rolling back here lands you on the previous tag — make sure that's what you want.

## Known pitfalls

- **Don't restart stateful stores here.** A `docker compose restart forgelink-kafka` without draining consumers first causes offset thrash; a Postgres restart under load can leave connection pools stuck. Use the per-store runbooks.
- **Socket.IO clients disconnect.** Flutter reconnects automatically within ~5s. External subscribers (if any) may need a nudge.
- **Celery scheduled beats fire late.** Restarts within the beat interval miss one tick; acceptable for the aggregation / retention jobs we run, but audit anything time-sensitive against `docker compose logs forgelink-api | grep celery-beat`.
