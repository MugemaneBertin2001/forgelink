# Rotate SMTP credentials for the notification service

## When to reach for this

- Scheduled rotation (Postmark / Mailgun / SES tokens expire on the provider's cadence).
- The SMTP password is suspected leaked.
- You're moving providers (e.g. Mailhog → Postmark for the first prod push).

## Before you start

- You have the new SMTP credentials in hand (host, port, username, password).
- `kubectl` access to the `forgelink` namespace.
- You accept a ~30-second window where the notification service has no active SMTP connection — during that window, outgoing email alerts queue in Kafka (un-acked) and replay automatically.

## Mechanism

Spring's `JavaMailSender` is configured from environment variables (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`). They're loaded at startup. Rotation is: update the Secret, restart the deployment, verify.

## Steps

### 1. Update the Secret

```bash
kubectl -n forgelink create secret generic forgelink-notification-smtp \
  --from-literal=SMTP_HOST=<new-host> \
  --from-literal=SMTP_PORT=<new-port> \
  --from-literal=SMTP_USERNAME=<new-username> \
  --from-literal=SMTP_PASSWORD=<new-password> \
  --dry-run=client -o yaml | kubectl apply -f -
```

Expected: `secret/forgelink-notification-smtp configured`.

### 2. Rolling-restart the notification deployment

```bash
kubectl -n forgelink rollout restart deployment/forgelink-notification
kubectl -n forgelink rollout status deployment/forgelink-notification --timeout=2m
```

### 3. Verify the new creds work end-to-end

Trigger a test alert and confirm the email arrives:

```bash
# Get a FACTORY_ADMIN token.
TOKEN=$(curl -fsS -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@forgelink.local","password":"Admin@ForgeLink2026!"}' \
  | jq -r .access_token)

# Fire a test alert (replace the rule ID with one that has notify_email=true).
RULE_ID=$(curl -fsS -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/alerts/rules/ \
  | jq -r '.results[] | select(.notify_email==true) | .id' | head -1)

curl -fsS -H "Authorization: Bearer $TOKEN" \
  -X POST http://localhost:8000/api/alerts/rules/$RULE_ID/test/
# Expect: {"status":"queued","alert_id":"..."}
```

Then confirm it landed:

```bash
kubectl -n forgelink logs deploy/forgelink-notification --since=2m \
  | grep "Email dispatched"
# Expect: a line like "Email dispatched: alertId=... severity=... recipients=..."
```

Check the recipient mailbox (or Mailhog at http://localhost:8025 for local dev).

## Rollback

Keep the old credentials for 10 minutes after rotation so you can revert if the new ones don't work:

```bash
kubectl -n forgelink create secret generic forgelink-notification-smtp \
  --from-literal=SMTP_HOST=<OLD-host> \
  --from-literal=SMTP_PORT=<OLD-port> \
  --from-literal=SMTP_USERNAME=<OLD-username> \
  --from-literal=SMTP_PASSWORD=<OLD-password> \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n forgelink rollout restart deployment/forgelink-notification
```

## Known pitfalls

- **Don't put creds in git** — not even "temporarily." If you accidentally commit the Secret YAML, rotate immediately (this runbook, again, with new creds) and rewrite history; GitGuardian will page either way.
- **Kafka messages in flight are safe.** If the notification service restarts with bad creds, `EmailNotificationService.sendAlert` throws, the Kafka message is NOT acked, and redelivery replays after you fix the creds. Worst case: 1–2 duplicate emails if the old creds happened to succeed on the first attempt but we didn't ack fast enough.
- **Mailhog vs real SMTP.** Local dev points at Mailhog (SMTP_AUTH=false, SMTP_STARTTLS=false). Production must set SMTP_AUTH=true and usually STARTTLS=true. Double-check those two booleans when moving environments — a true → false drift here silently disables TLS.
