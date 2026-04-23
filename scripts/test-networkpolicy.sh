#!/usr/bin/env bash
#
# Verify ForgeLink NetworkPolicy allow-list by running a netshoot pod
# and asserting which intra-cluster paths succeed vs. time out.
#
# Usage:
#   kubectl apply -k k8s/overlays/dev
#   bash scripts/test-networkpolicy.sh [namespace]
#
# Default namespace: forgelink-dev
# Exit 0 if every expected allow/deny pair matches; exit 1 otherwise.
#
# Requires: kubectl, a Kubernetes cluster with a NetworkPolicy-enforcing
# CNI (Calico, Cilium, or any cluster where "NetworkPolicy is enforced"
# is true — vanilla flannel does NOT enforce). k3s ships with flannel
# and requires --flannel-backend=none --disable-network-policy OR
# kube-flannel + calico-for-network-policy.
set -euo pipefail

NAMESPACE="${1:-forgelink-dev}"
NETSHOOT_NAME="netshoot-test"
NETSHOOT_IMAGE="nicolaka/netshoot:latest"

PASS=0
FAIL=0

pass() { printf '  ✅ %s\n' "$1"; PASS=$((PASS+1)); }
fail() { printf '  ❌ %s\n' "$1"; FAIL=$((FAIL+1)); }

cleanup() {
  kubectl -n "$NAMESPACE" delete pod "$NETSHOOT_NAME" --ignore-not-found --wait=false >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "━━━ NetworkPolicy verification — namespace: $NAMESPACE ━━━"

# Launch netshoot with NO ForgeLink labels — should be able to resolve
# DNS but not reach any in-cluster service.
cleanup
kubectl -n "$NAMESPACE" run "$NETSHOOT_NAME" \
  --image="$NETSHOOT_IMAGE" --restart=Never --command -- sleep 3600 >/dev/null
kubectl -n "$NAMESPACE" wait --for=condition=Ready "pod/$NETSHOOT_NAME" --timeout=60s >/dev/null

# Run a probe inside the netshoot pod. Succeeds when TCP handshake
# completes in <5s; counts as "denied" when it times out.
probe_deny() {
  local desc="$1"; local host="$2"; local port="$3"
  if kubectl -n "$NAMESPACE" exec "$NETSHOOT_NAME" -- \
      timeout 5 bash -c "echo > /dev/tcp/$host/$port" >/dev/null 2>&1; then
    fail "$desc ALLOWED (expected deny)"
  else
    pass "$desc blocked"
  fi
}

probe_allow() {
  local desc="$1"; local pod_label="$2"; local host="$3"; local port="$4"
  # Run from inside a pod with the matching label so the allow-list
  # applies. Uses kubectl debug ephemeral-container into an existing
  # pod of that label, via `kubectl exec`.
  local target_pod
  target_pod=$(kubectl -n "$NAMESPACE" get pod -l "app.kubernetes.io/name=$pod_label" \
                 -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
  if [[ -z "$target_pod" ]]; then
    fail "$desc (no $pod_label pod in namespace)"
    return
  fi
  if kubectl -n "$NAMESPACE" exec "$target_pod" -- \
      timeout 5 bash -c "echo > /dev/tcp/$host/$port" >/dev/null 2>&1; then
    pass "$desc"
  else
    fail "$desc denied (expected allow)"
  fi
}

echo
echo "▼ Expected DENY from an un-labelled probe pod"
probe_deny "netshoot → postgresql:5432" postgresql 5432
probe_deny "netshoot → redis:6379"      redis      6379
probe_deny "netshoot → kafka:9092"      kafka      9092
probe_deny "netshoot → tdengine:6041"   tdengine   6041

echo
echo "▼ Expected ALLOW between adjacent app tiers"
probe_allow "forgelink-api → postgresql:5432" forgelink-api postgresql 5432
probe_allow "forgelink-api → redis:6379"      forgelink-api redis      6379
probe_allow "forgelink-api → kafka:9092"      forgelink-api kafka      9092
probe_allow "forgelink-api → forgelink-idp:8080" forgelink-api forgelink-idp 8080

echo
printf '━━━ %d passed, %d failed ━━━\n' "$PASS" "$FAIL"
exit $FAIL
