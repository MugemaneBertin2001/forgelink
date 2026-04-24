# Rotate the IDP JWT signing key

## When to reach for this

- Scheduled quarterly rotation.
- The private key is suspected compromised (signing material exfiltrated).
- You're migrating to a stronger key (RSA-2048 → RSA-4096, or RSA → Ed25519 once Spring Security supports it).

## Before you start

- You have `kubectl` access to the `forgelink` namespace and can edit the `forgelink-idp` Secret.
- You have 5–10 minutes during which newly-issued tokens should rotate key — *existing* tokens keep validating until they expire (24h access, 30d refresh), because we publish the new key alongside the old in the JWKS.
- If the key is compromised, you want "both keys present" to be as short as possible — see the compromised path at the end.

## Mechanism (one paragraph)

The IDP signs with a single active private key and publishes public keys in the JWKS endpoint at `/auth/jwks`. Django caches the JWKS for 1 hour. Rotation is: add the new public key to JWKS **first**, wait for the cache to expire across all Django replicas, switch the IDP's active signing key, then retire the old public key after the longest-lived token (30d) expires.

## Steps (scheduled rotation)

### 1. Generate the new key pair

```bash
openssl genpkey -algorithm RSA -out idp-signing-v2.pem -pkeyopt rsa_keygen_bits:2048
openssl rsa -pubout -in idp-signing-v2.pem -out idp-signing-v2.pub
```

Expected: two files in the current directory. The `-----BEGIN PRIVATE KEY-----` header on the first, `-----BEGIN PUBLIC KEY-----` on the second.

### 2. Publish the NEW public key alongside the old (JWKS only)

Edit the IDP Secret to include both keys under `jwks.json`:

```bash
kubectl -n forgelink edit secret forgelink-idp
```

Under `data.jwks.json`, include both current (`kid=v1`) and new (`kid=v2`) public keys. The IDP rereads this on restart:

```bash
kubectl -n forgelink rollout restart deployment/forgelink-idp
kubectl -n forgelink rollout status deployment/forgelink-idp
```

### 3. Verify both keys are published

```bash
kubectl -n forgelink exec deploy/forgelink-idp -- \
  curl -fsS http://localhost:8080/auth/jwks | jq '.keys | length'
# Expect: 2
```

### 4. Wait for Django's JWKS cache to refresh

`IDP.JWKS_CACHE_TTL` is 3600s (settings.py). Either:

```bash
# Option A — wait 1h. Boring but safe.
sleep 3600

# Option B — force-refresh by restarting the API.
kubectl -n forgelink rollout restart deployment/forgelink-api
kubectl -n forgelink rollout status deployment/forgelink-api
```

### 5. Switch the IDP's active signing key

Edit the same Secret; set `signing.key.id` to `v2` and replace `signing.key.pem` with the new private key.

```bash
kubectl -n forgelink edit secret forgelink-idp
kubectl -n forgelink rollout restart deployment/forgelink-idp
kubectl -n forgelink rollout status deployment/forgelink-idp
```

From this point, every new login gets a token signed by `v2`.

### 6. Verify new tokens validate end-to-end

```bash
TOKEN=$(curl -fsS -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@forgelink.local","password":"Admin@ForgeLink2026!"}' \
  | jq -r .access_token)

curl -fsS -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/assets/plants/ | jq '. | length'
# Expect: a number > 0 — Django validated the v2-signed token.

echo $TOKEN | cut -d. -f1 | base64 -d 2>/dev/null | jq .
# Expect: {"alg":"RS256","kid":"v2","typ":"JWT"}
```

### 7. After 30 days — retire the old public key

Longest-lived token is the refresh token (30d). After the full window has passed, remove `v1` from JWKS:

```bash
kubectl -n forgelink edit secret forgelink-idp
# Remove the v1 entry from jwks.json.
kubectl -n forgelink rollout restart deployment/forgelink-idp
```

## Steps (compromised key — emergency)

Skip the "wait 30 days" and immediately invalidate all refresh tokens:

```bash
# 1. Generate new key pair (as above).
# 2. Replace jwks.json to contain ONLY the new public key — skip the two-key window.
# 3. Switch signing key.
# 4. Purge Redis DB1 (refresh tokens).
kubectl -n forgelink exec statefulset/forgelink-redis -- \
  redis-cli -n 1 FLUSHDB
```

Every user is logged out. They re-authenticate with password; new tokens signed by v2. Old v1 tokens fail validation because v1 is no longer in JWKS.

### Verify

```bash
# Confirm JWKS has only one key.
curl -fsS http://localhost:8080/auth/jwks | jq '.keys | length'
# 1

# Confirm old tokens fail (use a token you saved before rotation).
curl -i -H "Authorization: Bearer $OLD_TOKEN" http://localhost:8000/api/assets/plants/
# 401
```

## Rollback

If step 5 (activating v2) surfaces a signature validation problem:

```bash
# Revert the Secret to point signing.key.id back at v1 and restore v1's private key.
kubectl -n forgelink rollout restart deployment/forgelink-idp
```

This only works if you haven't yet removed v1 from JWKS. Keep the old private key in a sealed envelope / password manager for the 30d window; without it, rollback is impossible.

## Known pitfalls

- **Django's JWKS cache is process-local** in each replica. Scaling up mid-rotation gives you a cold-cache pod that pulls the NEW JWKS immediately. Scaling down can keep a stale cache alive. Sequencing (new JWKS → restart API to force refresh → activate new signing) avoids the failure mode where a new pod trusts v2 but an old pod only knows v1.
- **Kid in the JWT header matters.** Spring signs with `kid=v1` explicitly; Django reads `kid` and looks it up in JWKS. If your new keys don't set `kid`, Django falls back to "try every key" which works but is slow and hides rotation errors. Always set `kid`.
- **Refresh-token revocation is all-or-nothing.** We don't have per-user revocation. Purging Redis DB1 logs out everyone. If you only need to boot one user, delete their specific entry via `redis-cli -n 1 DEL refresh:<uuid>`.
