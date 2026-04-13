#!/bin/bash
set -e

#############################################################################
# ForgeLink Single-Command Deployment Script
#
# Usage: ./scripts/deploy.sh [options]
#
# Options:
#   --local       Use local images (build from source)
#   --skip-k3s    Skip k3s installation (use existing cluster)
#   --uninstall   Remove ForgeLink and k3s completely
#
# This script:
#   1. Installs k3s (lightweight Kubernetes)
#   2. Installs ArgoCD
#   3. Generates secrets (JWT keys, passwords)
#   4. Deploys ForgeLink via ArgoCD (GitOps)
#
# Works on: Linux (AMD64/ARM64), macOS (for local testing)
#############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SECRETS_FILE="$PROJECT_ROOT/k8s/overlays/demo/secrets.yaml"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
USE_LOCAL_IMAGES=false
SKIP_K3S=false
UNINSTALL=false
SLACK_WEBHOOK="${SLACK_WEBHOOK_URL:-}"

while [[ $# -gt 0 ]]; do
    case $1 in
        --local)
            USE_LOCAL_IMAGES=true
            shift
            ;;
        --skip-k3s)
            SKIP_K3S=true
            shift
            ;;
        --uninstall)
            UNINSTALL=true
            shift
            ;;
        --slack-webhook)
            SLACK_WEBHOOK="$2"
            shift 2
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

log() {
    echo -e "${BLUE}[ForgeLink]${NC} $1"
}

success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[!]${NC} $1"
}

error() {
    echo -e "${RED}[✗]${NC} $1"
    exit 1
}

#############################################################################
# Uninstall
#############################################################################
if [ "$UNINSTALL" = true ]; then
    log "Uninstalling ForgeLink..."

    if command -v kubectl &> /dev/null; then
        kubectl delete namespace forgelink --ignore-not-found=true || true
        kubectl delete namespace argocd --ignore-not-found=true || true
    fi

    if [ -f /usr/local/bin/k3s-uninstall.sh ]; then
        log "Removing k3s..."
        /usr/local/bin/k3s-uninstall.sh
    fi

    success "ForgeLink uninstalled"
    exit 0
fi

#############################################################################
# System Detection
#############################################################################
detect_system() {
    OS="$(uname -s)"
    ARCH="$(uname -m)"

    case "$ARCH" in
        x86_64)  ARCH="amd64" ;;
        aarch64) ARCH="arm64" ;;
        arm64)   ARCH="arm64" ;;
    esac

    log "Detected: $OS ($ARCH)"

    # Check if Raspberry Pi
    if [ -f /proc/device-tree/model ]; then
        PI_MODEL=$(cat /proc/device-tree/model 2>/dev/null || echo "")
        if [[ "$PI_MODEL" == *"Raspberry Pi"* ]]; then
            log "Running on: $PI_MODEL"
        fi
    fi
}

#############################################################################
# Prerequisites
#############################################################################
check_prerequisites() {
    log "Checking prerequisites..."

    # Check for curl
    if ! command -v curl &> /dev/null; then
        error "curl is required but not installed"
    fi

    # Check for openssl (for key generation)
    if ! command -v openssl &> /dev/null; then
        error "openssl is required but not installed"
    fi

    success "Prerequisites satisfied"
}

#############################################################################
# Install k3s
#############################################################################
install_k3s() {
    if [ "$SKIP_K3S" = true ]; then
        log "Skipping k3s installation (--skip-k3s)"
        return
    fi

    if command -v k3s &> /dev/null; then
        success "k3s already installed"
        return
    fi

    # macOS - use colima or docker desktop
    if [ "$OS" = "Darwin" ]; then
        if command -v minikube &> /dev/null; then
            log "Using minikube on macOS..."
            if ! minikube status &> /dev/null; then
                log "Starting minikube..."
                minikube start --memory=4096 --cpus=2 --driver=docker
            fi
            success "minikube running"
            return
        elif command -v colima &> /dev/null; then
            log "Using colima on macOS..."
            if ! colima status &> /dev/null; then
                colima start --kubernetes --cpu 2 --memory 4
            fi
            success "colima running"
            return
        else
            error "macOS requires minikube or colima. Install with: brew install minikube"
        fi
    fi

    # Linux - install k3s
    log "Installing k3s..."
    curl -sfL https://get.k3s.io | sh -s - \
        --write-kubeconfig-mode 644 \
        --disable traefik \
        --disable servicelb

    # Wait for k3s to be ready
    log "Waiting for k3s to be ready..."
    sleep 10

    until kubectl get nodes &> /dev/null; do
        sleep 2
    done

    # Set up kubeconfig for non-root users
    mkdir -p ~/.kube
    sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
    sudo chown $(id -u):$(id -g) ~/.kube/config

    success "k3s installed and running"
}

#############################################################################
# Generate Secrets
#############################################################################
generate_secrets() {
    log "Generating secrets..."

    # Generate Django secret key
    DJANGO_SECRET=$(openssl rand -base64 32)

    # Generate JWT keys if not exists
    JWT_KEYS_DIR="$PROJECT_ROOT/.secrets"
    mkdir -p "$JWT_KEYS_DIR"

    if [ ! -f "$JWT_KEYS_DIR/jwt-private.pem" ]; then
        log "Generating JWT RSA keys..."
        openssl genrsa -out "$JWT_KEYS_DIR/jwt-private.pem" 2048
        openssl rsa -in "$JWT_KEYS_DIR/jwt-private.pem" -pubout -out "$JWT_KEYS_DIR/jwt-public.pem"
    fi

    JWT_PRIVATE=$(cat "$JWT_KEYS_DIR/jwt-private.pem")
    JWT_PUBLIC=$(cat "$JWT_KEYS_DIR/jwt-public.pem")

    # Prompt for Slack webhook if not set
    if [ -z "$SLACK_WEBHOOK" ]; then
        warn "No Slack webhook URL provided"
        read -p "Enter Slack webhook URL (or press Enter to skip): " SLACK_WEBHOOK
        if [ -z "$SLACK_WEBHOOK" ]; then
            SLACK_WEBHOOK="https://hooks.slack.com/services/PLACEHOLDER"
        fi
    fi

    # Create secrets file (strategic merge patch format for kustomize)
    cat > "$SECRETS_FILE" << EOF
# Strategic merge patch for demo secrets
# Generated by deploy.sh - DO NOT COMMIT
apiVersion: v1
kind: Secret
metadata:
  name: forgelink-secrets
stringData:
  DJANGO_SECRET_KEY: "$DJANGO_SECRET"
  DJANGO_DB_USER: "forgelink"
  DJANGO_DB_PASSWORD: "forgelink_demo_2024"
  DJANGO_TDENGINE_USER: "root"
  DJANGO_TDENGINE_PASSWORD: "taosdata"
  DJANGO_REDIS_PASSWORD: ""
  KAFKA_SASL_USERNAME: ""
  KAFKA_SASL_PASSWORD: ""

---
apiVersion: v1
kind: Secret
metadata:
  name: idp-secrets
stringData:
  SPRING_DATASOURCE_USERNAME: "idp"
  SPRING_DATASOURCE_PASSWORD: "idp_demo_2024"
  SPRING_REDIS_PASSWORD: ""
  JWT_PRIVATE_KEY: |
$(echo "$JWT_PRIVATE" | sed 's/^/    /')

---
apiVersion: v1
kind: Secret
metadata:
  name: notification-secrets
stringData:
  SLACK_WEBHOOK_URL: "$SLACK_WEBHOOK"

---
apiVersion: v1
kind: Secret
metadata:
  name: postgresql-secrets
stringData:
  POSTGRES_PASSWORD: "postgres_demo_2024"
  POSTGRES_FORGELINK_PASSWORD: "forgelink_demo_2024"
  POSTGRES_IDP_PASSWORD: "idp_demo_2024"

---
apiVersion: v1
kind: Secret
metadata:
  name: emqx-secrets
stringData:
  EMQX_DASHBOARD_PASSWORD: "emqx_demo_2024"
  MQTT_DEVICE_PASSWORD: "mqtt_demo_2024"
EOF

    success "Secrets generated"
}

#############################################################################
# Build Local Images (optional)
#############################################################################
build_local_images() {
    if [ "$USE_LOCAL_IMAGES" != true ]; then
        return
    fi

    log "Building local images..."

    # Configure docker to use k3s containerd
    if command -v k3s &> /dev/null; then
        export CONTAINERD_ADDRESS=/run/k3s/containerd/containerd.sock
        export DOCKER_HOST=unix:///run/k3s/containerd/containerd.sock
    fi

    # Use minikube's docker if on macOS
    if [ "$OS" = "Darwin" ] && command -v minikube &> /dev/null; then
        eval $(minikube docker-env)
    fi

    cd "$PROJECT_ROOT"

    # Build all images in parallel
    log "Building Django API..."
    docker build -t forgelink-api:local ./services/django-api &
    PID1=$!

    log "Building Spring IDP..."
    (cd ./services/spring-idp && mvn package -DskipTests -q && docker build -t forgelink-idp:local .) &
    PID2=$!

    log "Building Notification Service..."
    (cd ./services/spring-notification-service && mvn package -DskipTests -q && docker build -t forgelink-notification:local .) &
    PID3=$!

    # Wait for all builds
    wait $PID1 && success "API image built" || error "API build failed"
    wait $PID2 && success "IDP image built" || error "IDP build failed"
    wait $PID3 && success "Notification image built" || error "Notification build failed"

    # Update kustomization to use local images
    cd "$PROJECT_ROOT/k8s/overlays/demo"

    # Use sed to replace GHCR images with local images
    if [ "$OS" = "Darwin" ]; then
        # macOS sed requires empty string after -i
        sed -i '' 's|newName: ghcr.io/mugemanebertin/forgelink-api|newName: forgelink-api|g' kustomization.yaml
        sed -i '' 's|newName: ghcr.io/mugemanebertin/forgelink-idp|newName: forgelink-idp|g' kustomization.yaml
        sed -i '' 's|newName: ghcr.io/mugemanebertin/forgelink-notification|newName: forgelink-notification|g' kustomization.yaml
        sed -i '' 's|newTag: main|newTag: local|g' kustomization.yaml
    else
        sed -i 's|newName: ghcr.io/mugemanebertin/forgelink-api|newName: forgelink-api|g' kustomization.yaml
        sed -i 's|newName: ghcr.io/mugemanebertin/forgelink-idp|newName: forgelink-idp|g' kustomization.yaml
        sed -i 's|newName: ghcr.io/mugemanebertin/forgelink-notification|newName: forgelink-notification|g' kustomization.yaml
        sed -i 's|newTag: main|newTag: local|g' kustomization.yaml
    fi

    success "Local images built"
}

#############################################################################
# Install ArgoCD
#############################################################################
install_argocd() {
    log "Installing ArgoCD..."

    # Create namespace
    kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -

    # Install ArgoCD
    kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.13.0/manifests/install.yaml

    # Wait for ArgoCD to be ready
    log "Waiting for ArgoCD to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/argocd-server -n argocd

    # Patch ArgoCD to use NodePort for easy access
    kubectl patch svc argocd-server -n argocd -p '{"spec": {"type": "NodePort", "ports": [{"port": 443, "targetPort": 8080, "nodePort": 30443}]}}'

    success "ArgoCD installed"

    # Get initial admin password
    ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)

    echo ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}ArgoCD Credentials${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo -e "URL:      https://$(get_node_ip):30443"
    echo -e "Username: admin"
    echo -e "Password: $ARGOCD_PASSWORD"
    echo -e "${GREEN}============================================${NC}"
    echo ""
}

#############################################################################
# Deploy ForgeLink
#############################################################################
deploy_forgelink() {
    log "Deploying ForgeLink..."

    # Apply the namespace first
    kubectl create namespace forgelink --dry-run=client -o yaml | kubectl apply -f -

    # Apply secrets directly (not via ArgoCD for security)
    kubectl apply -f "$SECRETS_FILE"

    # Apply the ArgoCD Application
    kubectl apply -f "$PROJECT_ROOT/k8s/argocd/base/forgelink-app.yaml"

    # Wait for sync
    log "Waiting for ArgoCD to sync (this may take a few minutes)..."
    sleep 30

    # Check sync status
    kubectl get applications -n argocd

    success "ForgeLink deployment initiated"
}

#############################################################################
# Deploy ForgeLink Directly (without ArgoCD pulling from Git)
#############################################################################
deploy_forgelink_direct() {
    log "Deploying ForgeLink directly..."

    # Apply the namespace first
    kubectl create namespace forgelink --dry-run=client -o yaml | kubectl apply -f -

    # Apply secrets
    kubectl apply -f "$SECRETS_FILE"

    # Apply via kustomize
    kubectl apply -k "$PROJECT_ROOT/k8s/overlays/demo"

    success "ForgeLink deployed"
}

#############################################################################
# Get Node IP
#############################################################################
get_node_ip() {
    if [ "$OS" = "Darwin" ]; then
        if command -v minikube &> /dev/null; then
            minikube ip
            return
        fi
        echo "localhost"
        return
    fi

    # Try to get external IP
    EXTERNAL_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="ExternalIP")].address}' 2>/dev/null)
    if [ -n "$EXTERNAL_IP" ]; then
        echo "$EXTERNAL_IP"
        return
    fi

    # Fall back to internal IP
    kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}'
}

#############################################################################
# Print Access Info
#############################################################################
print_access_info() {
    NODE_IP=$(get_node_ip)

    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              ForgeLink Deployment Complete!                   ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Services:${NC}"
    echo -e "  ForgeLink API:    http://$NODE_IP:30080"
    echo -e "  ForgeLink IDP:    http://$NODE_IP:30081"
    echo -e "  ArgoCD:           https://$NODE_IP:30443"
    echo ""
    echo -e "${BLUE}Demo Credentials:${NC}"
    echo -e "  Email:    admin@forgelink.local"
    echo -e "  Password: Admin@ForgeLink2026!"
    echo ""
    echo -e "${BLUE}Useful Commands:${NC}"
    echo -e "  kubectl get pods -n forgelink      # Check pod status"
    echo -e "  kubectl logs -f -n forgelink <pod> # View logs"
    echo -e "  ./scripts/deploy.sh --uninstall    # Remove everything"
    echo ""

    # Show pod status
    log "Current pod status:"
    kubectl get pods -n forgelink 2>/dev/null || true
}

#############################################################################
# Main
#############################################################################
main() {
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║         ForgeLink Industrial IoT Platform Deployer            ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    detect_system
    check_prerequisites
    install_k3s
    generate_secrets
    build_local_images
    install_argocd

    # For local/demo, deploy directly instead of waiting for Git sync
    if [ "$USE_LOCAL_IMAGES" = true ]; then
        deploy_forgelink_direct
    else
        deploy_forgelink
    fi

    print_access_info
}

main "$@"
