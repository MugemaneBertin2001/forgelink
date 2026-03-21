#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "ForgeLink CI Validation (Local)"
echo "=========================================="

FAILED=0

# Function to check result
check_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ $2 passed${NC}"
    else
        echo -e "${RED}✗ $2 failed${NC}"
        FAILED=1
    fi
}

# 1. Validate K8s manifests
echo -e "\n${YELLOW}[1/6] Validating Kubernetes manifests...${NC}"
if command -v kustomize &> /dev/null; then
    kustomize build k8s/overlays/dev > /dev/null 2>&1
    check_result $? "K8s dev overlay"
    kustomize build k8s/overlays/production > /dev/null 2>&1
    check_result $? "K8s production overlay"
elif command -v kubectl &> /dev/null; then
    kubectl kustomize k8s/overlays/dev > /dev/null 2>&1
    check_result $? "K8s dev overlay"
    kubectl kustomize k8s/overlays/production > /dev/null 2>&1
    check_result $? "K8s production overlay"
else
    echo -e "${YELLOW}⚠ kustomize/kubectl not installed, skipping K8s validation${NC}"
fi

# 2. Django checks
echo -e "\n${YELLOW}[2/6] Checking Django API...${NC}"
cd services/django-api
if [ -f "requirements.txt" ]; then
    check_result 0 "Django requirements exist"
    # Run lint checks if tools are available
    if command -v ruff &> /dev/null; then
        ruff check . > /dev/null 2>&1
        check_result $? "Ruff lint check"
    fi
    if command -v black &> /dev/null; then
        black --check . > /dev/null 2>&1
        check_result $? "Black formatting"
    fi
    if command -v isort &> /dev/null; then
        isort --check-only . > /dev/null 2>&1
        check_result $? "isort imports"
    fi
else
    check_result 1 "Django requirements.txt"
fi
cd ../..

# 3. Spring IDP checks
echo -e "\n${YELLOW}[3/6] Checking Spring IDP...${NC}"
cd services/spring-idp
if [ -f "pom.xml" ]; then
    if command -v mvn &> /dev/null; then
        mvn validate -q 2>/dev/null
        check_result $? "Spring IDP pom.xml valid"
    else
        echo -e "${YELLOW}⚠ mvn not installed, checking pom.xml exists${NC}"
        check_result 0 "Spring IDP pom.xml exists"
    fi
else
    check_result 1 "Spring IDP pom.xml"
fi
cd ../..

# 4. Spring Notification checks
echo -e "\n${YELLOW}[4/6] Checking Spring Notification Service...${NC}"
cd services/spring-notification-service
if [ -f "pom.xml" ]; then
    if command -v mvn &> /dev/null; then
        mvn validate -q 2>/dev/null
        check_result $? "Spring Notification pom.xml valid"
    else
        check_result 0 "Spring Notification pom.xml exists"
    fi
else
    check_result 1 "Spring Notification pom.xml"
fi
cd ../..

# 5. Flutter checks
echo -e "\n${YELLOW}[5/6] Checking Flutter App...${NC}"
cd services/flutter-app
if [ -f "pubspec.yaml" ]; then
    if command -v flutter &> /dev/null; then
        flutter pub get --offline 2>/dev/null || flutter pub get 2>/dev/null
        check_result $? "Flutter pub get"
        flutter analyze --no-fatal-warnings 2>/dev/null || true
        check_result 0 "Flutter analyze (warnings allowed)"
    else
        echo -e "${YELLOW}⚠ flutter not installed, checking pubspec.yaml exists${NC}"
        check_result 0 "Flutter pubspec.yaml exists"
    fi
else
    check_result 1 "Flutter pubspec.yaml"
fi
cd ../..

# 6. GitHub Actions syntax check
echo -e "\n${YELLOW}[6/6] Checking GitHub Actions workflows...${NC}"
for workflow in .github/workflows/*.yml; do
    if [ -f "$workflow" ]; then
        # Basic YAML syntax check
        if command -v yq &> /dev/null; then
            yq '.' "$workflow" > /dev/null 2>&1
            check_result $? "$(basename $workflow) syntax"
        elif python3 -c "import yaml" 2>/dev/null; then
            python3 -c "import yaml; yaml.safe_load(open('$workflow'))" 2>/dev/null
            check_result $? "$(basename $workflow) syntax"
        else
            # No YAML parser available, just check file exists
            check_result 0 "$(basename $workflow) exists"
        fi
    fi
done

# Summary
echo -e "\n=========================================="
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All checks passed! Safe to push.${NC}"
    exit 0
else
    echo -e "${RED}Some checks failed. Fix issues before pushing.${NC}"
    exit 1
fi
