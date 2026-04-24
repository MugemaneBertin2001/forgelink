# Recover from a lost Kubernetes cluster

## When to reach for this

The cluster is gone — hardware failure, accidental `terraform destroy`, a provider eating the control plane, or someone ran a wrong `kubectl delete`. You have:

- The repo at a known commit (you should; it's git).
- The most recent Postgres + TDengine backup archive.
- The sealed root private key for the IDP.

You do **not** have the live cluster. This runbook rebuilds from scratch.

If the cluster is up but one service is unhealthy, use [restart-all](restart-all.md).
If you want a clean slate without restoring data, use [full-stack-reinstall](full-stack-reinstall.md).

## Before you start

- The replacement cluster exists and `kubectl` can reach it. Provisioning the cluster itself is out of scope for this runbook — use Terraform / whatever your infra repo uses.
- You have the most recent backups:
  - `forgelink-pg-YYYY-MM-DD.sql.gz`
  - `forgelink-tdengine-YYYY-MM-DD.tar.gz`
  - `forgelink-idp-signing-private.pem` (sealed)
  - Copy of the production `.env` or equivalent secret dump
- Data loss window equals **"last backup → now"**. If the last backup was 6h ago, the last 6h of telemetry is gone. Alerts, assets, JWT refresh tokens — same.
- Expected recovery time: 45–90 minutes, mostly waiting for TDengine restore.

## Steps

### 1. Verify cluster readiness

```bash
kubectl version --short
# Server Version: v1.2x or higher
kubectl get nodes
# All nodes Ready.
kubectl get ns forgelink 2>&1 | tail -1
# Expect: NotFound. If it's not NotFound, you're on a live cluster — stop.
```

### 2. Deploy cert-manager (if not already in the new cluster)

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.yaml
kubectl -n cert-manager wait --for=condition=Available deployments --all --timeout=5m
```

### 3. Apply the forgelink namespace, secrets, and config

```bash
cd k8s/overlays/production
kubectl apply -k .
# Expect: all Deployments / StatefulSets / Services / ConfigMaps created.
# Pods will crash-loop until the next steps finish — that's fine.
```

### 4. Restore the IDP signing key

```bash
kubectl -n forgelink create secret generic forgelink-idp \
  --from-file=signing.key.pem=./forgelink-idp-signing-private.pem \
  --from-literal=signing.key.id=v1 \
  --dry-run=client -o yaml | kubectl apply -f -
# Without this, every JWT minted by a fresh IDP fails to validate against
# any user's existing refresh token — users would need to re-authenticate.
```

### 5. Restore Postgres

```bash
# Wait for Postgres to be ready.
kubectl -n forgelink wait --for=condition=Ready pod -l app=postgres --timeout=5m

# Copy the dump into the pod.
kubectl -n forgelink cp ./forgelink-pg-YYYY-MM-DD.sql.gz postgres-0:/tmp/dump.sql.gz

# Restore.
kubectl -n forgelink exec -it postgres-0 -- bash -c \
  "gunzip -c /tmp/dump.sql.gz | psql -U forgelink -d forgelink"
# Expect: hundreds of lines of CREATE TABLE / COPY output, exit code 0.
```

### 6. Restore TDengine

```bash
kubectl -n forgelink wait --for=condition=Ready pod -l app=tdengine --timeout=5m
kubectl -n forgelink cp ./forgelink-tdengine-YYYY-MM-DD.tar.gz tdengine-0:/tmp/dump.tar.gz
kubectl -n forgelink exec -it tdengine-0 -- bash -c \
  "cd / && tar -xzf /tmp/dump.tar.gz"
kubectl -n forgelink exec -it tdengine-0 -- taos -s "SHOW DATABASES;"
# Expect: forgelink_telemetry present.
```

This step is the long one — TDengine's restore is I/O-bound and scales with the retention window. 30 days of telemetry for 68 devices restores in ~30min on a fast disk.

### 7. Restart the application services

```bash
for dep in forgelink-api forgelink-idp forgelink-notification \
           forgelink-mqtt-bridge forgelink-edge-gateway \
           forgelink-opcua-simulator; do
  kubectl -n forgelink rollout restart deployment/$dep
  kubectl -n forgelink rollout status deployment/$dep --timeout=5m
done
```

### 8. Verify end-to-end

```bash
# 1. Login works (uses the restored IDP signing key).
TOKEN=$(kubectl -n forgelink exec deploy/forgelink-api -- \
  curl -fsS -X POST http://forgelink-idp:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@forgelink.local","password":"Admin@ForgeLink2026!"}' \
  | jq -r .access_token)

# 2. API returns restored assets.
kubectl -n forgelink exec deploy/forgelink-api -- \
  curl -fsS -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/assets/plants/ \
  | jq '.results | length'
# Expect: matches pre-disaster count.

# 3. Telemetry is readable.
kubectl -n forgelink exec deploy/forgelink-api -- \
  curl -fsS -H "Authorization: Bearer $TOKEN" \
    "http://localhost:8000/api/telemetry/data/latest/?area=melt-shop" | jq '.count'
# Expect: non-zero.

# 4. The simulator starts producing fresh telemetry (new data post-restore).
kubectl -n forgelink logs deploy/forgelink-mqtt-bridge --since=1m | grep MESSAGES_PROCESSED
# Expect: increasing counters.
```

## Rollback

There is no rollback from "cluster is gone → cluster is back with data." If the restore produces unusable state (schema mismatch, corrupt dump), your options are:

1. Restore the *previous* backup (one-generation-older dump). Repeat steps 5–6 with it.
2. Stand up the cluster anyway with an empty database, then replay the most recent Kafka `alerts.notifications` / `telemetry.*` if the Kafka cluster survived.

## Known pitfalls

- **Backup ordering matters.** Restore Postgres *before* starting Django — Django's startup will create tables if none exist, which then conflict with the SQL dump's `CREATE TABLE` statements. If you hit this, drop and recreate the database first:
  ```bash
  kubectl -n forgelink exec postgres-0 -- \
    psql -U forgelink -c "DROP DATABASE forgelink; CREATE DATABASE forgelink;"
  ```
- **IDP signing key is irreplaceable.** Without the original, every JWT validation against pre-disaster tokens fails permanently, and every refresh token in Redis is bricked. Store the sealed key at least in two locations; treat it like a root CA.
- **EMQX ACLs are in the EMQX volume, not Postgres.** A pure Postgres restore gives you assets and alerts but no MQTT auth. The backup archive should include `/etc/emqx/acl.conf` or the equivalent dashboard export.
- **Alert rules fire for "new" old data.** If telemetry is restored but the consumer re-ingests it as if fresh, alert rules will evaluate thresholds and potentially page. Either suppress alerts during restore (`kubectl scale deployment/forgelink-notification --replicas=0` until step 7.4) or accept the replay noise.
