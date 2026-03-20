#!/bin/bash
# ============================================
# ForgeLink Development Setup Script
# ============================================

set -e

echo "=========================================="
echo "ForgeLink Development Setup"
echo "=========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo -e "\n${YELLOW}Checking prerequisites...${NC}"

check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} $1 found"
        return 0
    else
        echo -e "  ${RED}✗${NC} $1 not found"
        return 1
    fi
}

MISSING=0
check_command docker || MISSING=1
check_command docker-compose || check_command "docker compose" || MISSING=1
check_command git || MISSING=1

if [ $MISSING -eq 1 ]; then
    echo -e "\n${RED}Please install missing prerequisites and try again.${NC}"
    exit 1
fi

# Setup environment
echo -e "\n${YELLOW}Setting up environment...${NC}"

if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "  ${GREEN}✓${NC} Created .env from .env.example"
else
    echo -e "  ${YELLOW}!${NC} .env already exists, skipping"
fi

# Create secrets directory
echo -e "\n${YELLOW}Setting up secrets...${NC}"
mkdir -p secrets

# Generate JWT keys if they don't exist
if [ ! -f secrets/jwt-private.pem ]; then
    echo "  Generating JWT keys..."
    openssl genrsa -out secrets/jwt-private.pem 2048 2>/dev/null
    openssl rsa -in secrets/jwt-private.pem -pubout -out secrets/jwt-public.pem 2>/dev/null
    echo -e "  ${GREEN}✓${NC} Generated JWT key pair"
else
    echo -e "  ${YELLOW}!${NC} JWT keys already exist, skipping"
fi

# Start Docker services
echo -e "\n${YELLOW}Starting Docker services...${NC}"
docker compose up -d

# Wait for services to be healthy
echo -e "\n${YELLOW}Waiting for services to be ready...${NC}"
sleep 10

# Check service health
echo -e "\n${YELLOW}Checking service health...${NC}"

check_service() {
    local name=$1
    local url=$2
    if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "200\|204"; then
        echo -e "  ${GREEN}✓${NC} $name is healthy"
    else
        echo -e "  ${YELLOW}!${NC} $name not ready yet (may still be starting)"
    fi
}

check_service "PostgreSQL" "localhost:5432" 2>/dev/null || true
check_service "Redis" "localhost:6379" 2>/dev/null || true
check_service "EMQX" "http://localhost:18083" 2>/dev/null || true

# Print summary
echo -e "\n=========================================="
echo -e "${GREEN}Setup complete!${NC}"
echo "=========================================="
echo ""
echo "Services:"
echo "  Django API:     http://localhost:8000"
echo "  Django Admin:   http://localhost:8000/admin"
echo "  GraphQL:        http://localhost:8000/graphql"
echo "  Spring IDP:     http://localhost:8080"
echo "  EMQX Dashboard: http://localhost:18083"
echo "  Grafana:        http://localhost:3000"
echo "  RabbitMQ:       http://localhost:15672"
echo ""
echo "Next steps:"
echo "  1. Run 'docker compose logs -f' to view logs"
echo "  2. Run 'python scripts/seed-factory-data.py' to seed test data"
echo "  3. Visit http://localhost:8000/admin to access the admin panel"
echo ""
