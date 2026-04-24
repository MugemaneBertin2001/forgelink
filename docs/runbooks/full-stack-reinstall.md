# Full-stack reinstall (clean slate)

## When to reach for this

- Spinning up a new customer site / lab environment.
- The local dev stack is so mangled that `docker compose down -v` is the fastest path forward.
- A major version upgrade where config migrations are easier done fresh.

**This wipes every stateful store.** If you need to keep data, this is the wrong runbook — use [restart-all](restart-all.md) for most problems or [recover-from-lost-cluster](recover-from-lost-cluster.md) if the cluster itself is gone.

## Before you start

- You have 30–60 minutes. Pulling images is the bulk of it on the first run.
- You're on a box with ≥16 GB RAM and ≥20 GB free disk. TDengine + Kafka + Postgres + EMQX under Docker is not lightweight.
- You have a `.env` at the repo root (`cp .env.example .env` if not). No secrets need to be real for local dev.
- **Production**: you have the SMTP creds, Slack webhook URL, and IDP signing key ready to drop into the Secrets at step 5.

## Local (docker compose) — clean slate

### 1. Nuke everything

```bash
cd /path/to/forgelink
docker compose down -v --remove-orphans
# `-v` drops named volumes (postgres-data, tdengine-data, kafka-data, emqx-data).
docker compose rm -fsv
docker system prune -f   # optional — reclaims dangling images / networks.
```

Verify:

```bash
docker volume ls | grep forgelink
# Expect: empty.
```

### 2. Pull current images

```bash
docker compose pull
```

### 3. Bring up the stateful layer first

```bash
docker compose up -d forgelink-postgres forgelink-tdengine \
                    forgelink-redis forgelink-kafka \
                    forgelink-zookeeper forgelink-emqx
docker compose ps --format "table {{.Service}}\t{{.Status}}" \
  | grep -E "postgres|tdengine|redis|kafka|zookeeper|emqx"
# Each should be "Up (healthy)" within ~60s.
```

### 4. Run init scripts

```bash
# Creates per-service databases (forgelink, idp) and applies GRANTS.
docker compose --profile init run --rm postgres-init

# Creates Kafka topics (telemetry.*, events.all, alerts.notifications, dlq.unparseable).
docker compose --profile init run --rm kafka-init
```

### 5. Start the application services

```bash
docker compose up -d
docker compose ps --format "table {{.Service}}\t{{.Status}}"
# Every service "Up (healthy)" within ~2 minutes.
```

### 6. Apply Django migrations + seed

```bash
docker compose exec forgelink-api python manage.py migrate
docker compose exec forgelink-api python manage.py seed_permissions
docker compose exec forgelink-api python manage.py seed_simulator
```

### 7. Verify

```bash
curl -fsS http://localhost:8000/health/ | jq .
# {"status":"healthy",...}

TOKEN=$(curl -fsS -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@forgelink.local","password":"Admin@ForgeLink2026!"}' \
  | jq -r .access_token)

curl -fsS -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/assets/plants/ | jq '.count'
# Expect: 1 (the seeded "steel-plant-kigali" plant).
```

## Cluster (K8s) — clean slate

### 1. Nuke the namespace

```bash
kubectl delete namespace forgelink --wait
# Waits for every resource — PVCs, Secrets, everything — to tear down.
```

This **is** destructive and will fail if the namespace has `finalizers` still held by a CRD. If that happens:

```bash
kubectl -n forgelink patch <stuck-resource> -p '{"metadata":{"finalizers":[]}}' --type=merge
```

### 2. Apply fresh from git

```bash
cd k8s/overlays/production    # or /dev, /staging
kubectl apply -k .
```

### 3. Seed secrets

For production, the Secrets from git are empty templates. Populate them:

```bash
kubectl -n forgelink create secret generic forgelink-idp \
  --from-file=signing.key.pem=./idp-signing-private.pem \
  --from-literal=signing.key.id=v1 \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n forgelink create secret generic forgelink-notification-smtp \
  --from-literal=SMTP_HOST=<host> --from-literal=SMTP_PORT=<port> \
  --from-literal=SMTP_USERNAME=<user> --from-literal=SMTP_PASSWORD=<pw> \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n forgelink create secret generic forgelink-notification-slack \
  --from-literal=SLACK_WEBHOOK_URL=<url> \
  --dry-run=client -o yaml | kubectl apply -f -
```

Restart deployments so they pick up the Secrets:

```bash
kubectl -n forgelink rollout restart deployment/forgelink-idp deployment/forgelink-notification
```

### 4. Run migrations + seed in-cluster

```bash
kubectl -n forgelink exec deploy/forgelink-api -- python manage.py migrate
kubectl -n forgelink exec deploy/forgelink-api -- python manage.py seed_permissions
# seed_simulator only on dev/staging — prod connects to real devices.
```

### 5. Verify

```bash
kubectl -n forgelink get pods -o wide
# Every pod Running 1/1.

kubectl -n forgelink port-forward svc/forgelink-api 8000:8000 &
curl -fsS http://localhost:8000/health/ | jq .
kill %1
```

## Rollback

A "rollback" from a clean-slate install is just... using the previous install's backups. Follow [recover-from-lost-cluster](recover-from-lost-cluster.md) with the pre-reinstall backup archive.

## Known pitfalls

- **`kubectl delete namespace` can hang on stuck finalizers.** Our charts don't set custom finalizers; if they start, delete them first, then the namespace.
- **Image pull rate limits.** Docker Hub throttles anonymous pulls at 100/6h. If the cold pull hits the limit, authenticate first:
  ```bash
  echo $DOCKERHUB_TOKEN | docker login -u <user> --password-stdin
  ```
- **Kafka's auto-create-topics is off in prod.** If you skip step 4 (kafka-init), producers succeed silently but no messages reach consumers. Always run the init profile.
- **TDengine supertables are created on first insert, not by init.** If the app stack comes up before any telemetry has arrived, the schema is bare; the first telemetry message creates tables. Not a problem unless a reader queries before the first writer.
- **Permission seeding is idempotent** but not fast on cold. Budget 20–30s for `seed_permissions` on first run.
