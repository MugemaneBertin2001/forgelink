# ADR 0004 — cert-manager over SPIRE

**Status:** accepted
**Date:** 2026-03-14

## Context

The zero-trust model calls for every workload-to-workload call inside the cluster to present an identity: Django talking to Postgres, Spring talking to Redis, the MQTT bridge talking to Kafka, and so on. That identity is a short-lived cert signed by something the peer trusts.

Two serious options in the Kubernetes ecosystem:

### SPIFFE / SPIRE

- **What it is:** workload attestation + SVID issuance. Pods get certs tied to a SPIFFE ID like `spiffe://forgelink.local/ns/forgelink/sa/django-api`.
- **Why it's attractive:** vendor-neutral standard, strong attestation story (Unix UID, K8s ServiceAccount, AWS instance identity), trust-bundle management solved.
- **Why we didn't pick it:** two moving parts in the cluster that someone has to operate (`spire-server` + `spire-agent` per node), and the SDK surface is still thin for our language mix (first-class Go; acceptable Java / Python with `go-spiffe`'s bindings; Flutter doesn't get SPIFFE at all). The security-real-estate we'd buy is significant, but the operator cost — for a platform whose target deployment is a single-site steel plant, not a multi-tenant SaaS — is disproportionate.

### cert-manager + K8s ServiceAccounts

- **What it is:** cert-manager issues certs from a cluster-internal CA (self-signed at bootstrap, swappable to Vault later); workload identity is the K8s ServiceAccount JWT that every pod already projects via the `kube-apiserver` TokenRequest API.
- **Why it wins for us:**
  - **One less thing to run.** cert-manager is likely already in the cluster (Ingress TLS, Let's Encrypt). SPIRE is an extra deploy.
  - **Rotation is declarative.** `Certificate` + `renewBefore` replaces cron jobs or custom controllers.
  - **Workload identity via SA token is K8s-native.** No new attestation path for contributors to understand; the auth boundary is the same thing they already use for RBAC.
  - **Vault is a non-forced upgrade.** When/if we need stronger identity attestation — HSM-backed CA, cross-cluster federation — `vault-issuer` swaps in under cert-manager without rewriting workload code.

**The security delta we consciously accepted:**

SPIRE's attestation ties a cert to a provable pod property (ServiceAccount + node identity + optional selectors), making it hard to smuggle an identity out of a compromised pod. cert-manager's issuance is authenticated at the CA level; once a pod has a cert, a pod-escape gives an attacker that cert. For a single-tenant single-site deployment where the blast radius of a compromised pod already includes the cluster's secrets, the practical difference is small. For a multi-tenant or regulated deployment, the calculus changes — see "Won't change unless" below.

## Decision

Use cert-manager as the workload-cert issuer. Self-signed internal CA at bootstrap; switch to `vault-issuer` when (a) the deployment expands past a single cluster or (b) a regulator asks for HSM-backed signing. Keep `k8s/base/spire/` manifests in the repo marked as Framing-A scaffold (see [ADR 0005](0005-framing-a-scaffold-retention.md)) — don't ship them, don't delete them.

## Consequences

**Good:**

- One cert-manager Helm release handles ingress TLS, inter-service mTLS, and the IDP's signing cert.
- Contributors don't learn a new attestation model.
- Renewal is `renewBefore: 360h` on a `Certificate` resource; nothing custom to monitor.

**Painful:**

- Workload-identity story in docs says "K8s ServiceAccount + cert-manager cert" which is correct but less marketable than "SPIFFE." We've accepted that the customer-facing pitch loses a sentence.
- If we ever need cross-cluster federation (factory + corp HQ), we rebuild this layer. cert-manager doesn't federate; Vault + PKI secrets engine or SPIRE does.

**Won't change unless:**

- We deploy to a shared cluster where pod-to-pod isolation needs attestation (multi-tenant).
- Regulatory requirement forces HSM-backed cert signing without going through Vault.
- cert-manager itself regresses badly enough that SPIRE becomes operationally cheaper (implausible today).
