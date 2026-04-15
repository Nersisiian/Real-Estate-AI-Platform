#!/bin/bash
set -e

echo "=== RealEstate AI Platform Verification ==="
echo ""

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

API_URL="${API_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"

check_endpoint() {
    local url=$1
    local description=$2
    echo -n "Checking $description... "
    if curl -s -f -o /dev/null "$url"; then
        echo -e "${GREEN}OK${NC}"
        return 0
    else
        echo -e "${RED}FAILED${NC}"
        return 1
    fi
}

echo "Step 1: Service Health Checks"
echo "-----------------------------"
check_endpoint "$API_URL/api/v1/health" "Backend health" || exit 1
check_endpoint "$API_URL/api/v1/ready" "Backend readiness" || exit 1
check_endpoint "$FRONTEND_URL" "Frontend" || echo -e "${YELLOW}Frontend not available${NC}"
echo ""

echo "Step 2: Database & Vector Store"
echo "-------------------------------"
echo -n "Checking PostgreSQL connection... "
if docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC}"
    exit 1
fi

echo -n "Checking pgvector extension... "
if docker-compose exec -T postgres psql -U postgres -d realestate -c "SELECT 1 FROM pg_extension WHERE extname='vector'" | grep -q 1; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC}"
    exit 1
fi

echo -n "Checking property count... "
COUNT=$(docker-compose exec -T postgres psql -U postgres -d realestate -t -c "SELECT COUNT(*) FROM properties")
if [ "$COUNT" -gt 0 ]; then
    echo -e "${GREEN}$COUNT properties found${NC}"
else
    echo -e "${YELLOW}No properties found. Run: docker-compose exec backend python scripts/seed.py${NC}"
fi
echo ""

echo "Step 3: API End-to-End Test"
echo "---------------------------"
echo -n "Testing /chat endpoint... "
RESPONSE=$(curl -s -X POST "$API_URL/api/v1/chat" \
    -H "Content-Type: application/json" \
    -d '{"messages":[{"role":"user","content":"Hello"}],"stream":false}')

if echo "$RESPONSE" | grep -q '"response"'; then
    echo -e "${GREEN}OK${NC}"
    echo "Sample response:"
    echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"  Response: {data.get('response', '')[:50]}...\"); print(f\"  Session ID: {data.get('session_id')}\")"
else
    echo -e "${RED}FAILED${NC}"
    echo "Response: $RESPONSE"
    exit 1
fi
echo ""

echo "Step 4: Log Format Verification"
echo "-------------------------------"
echo "Recent backend logs:"
docker-compose logs --tail=3 backend | while read line; do
    if echo "$line" | python3 -c "import sys,json; json.loads(sys.stdin.read())" 2>/dev/null; then
        echo -e "${GREEN}✓ JSON log${NC}: $line"
    else
        echo "  $line"
    fi
done
echo ""

echo "=== Verification Complete ==="