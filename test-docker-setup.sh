#!/bin/bash

# Test script for Docker setup
# Verifies that the Chat API is running correctly in Docker

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Function to run a test
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -n "Testing: $test_name... "
    
    if eval "$test_command" > /dev/null 2>&1; then
        print_success "PASSED"
        ((TESTS_PASSED++))
        return 0
    else
        print_error "FAILED"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Start tests
print_header "Chat API Docker Setup Tests"

# Test 1: Check if Docker is installed
print_info "Checking prerequisites..."
run_test "Docker installed" "command -v docker"
run_test "Docker Compose installed" "command -v docker-compose"

# Test 2: Check if container is running
print_header "Container Status"
if docker ps | grep -q "influencer-chat-api"; then
    print_success "Container is running"
    ((TESTS_PASSED++))
else
    print_error "Container is not running"
    print_info "Start with: ./docker-start.sh start"
    ((TESTS_FAILED++))
    exit 1
fi

# Test 3: Check container health
print_header "Health Checks"
HEALTH_STATUS=$(docker inspect --format='{{.State.Health.Status}}' influencer-chat-api 2>/dev/null || echo "unknown")
if [ "$HEALTH_STATUS" = "healthy" ]; then
    print_success "Container health status: $HEALTH_STATUS"
    ((TESTS_PASSED++))
else
    print_error "Container health status: $HEALTH_STATUS"
    ((TESTS_FAILED++))
fi

# Test 4: Check if port is accessible
print_header "Network Connectivity"
run_test "Port 5001 is accessible" "nc -z localhost 5001"

# Test 5: Test API endpoints
print_header "API Endpoint Tests"

# Test health endpoint
if curl -s -f http://localhost:5001/health > /dev/null; then
    print_success "Health endpoint responding"
    ((TESTS_PASSED++))
else
    print_error "Health endpoint not responding"
    ((TESTS_FAILED++))
fi

# Test health endpoint response
HEALTH_RESPONSE=$(curl -s http://localhost:5001/health)
if echo "$HEALTH_RESPONSE" | grep -q "status"; then
    print_success "Health endpoint returns valid JSON"
    ((TESTS_PASSED++))
else
    print_error "Health endpoint response invalid"
    ((TESTS_FAILED++))
fi

# Test 6: Check volumes
print_header "Volume Mounts"

# Check if database file exists
if docker exec influencer-chat-api test -f /app/messaging.db; then
    print_success "Database file exists in container"
    ((TESTS_PASSED++))
else
    print_error "Database file not found in container"
    ((TESTS_FAILED++))
fi

# Check if uploads directory exists
if docker exec influencer-chat-api test -d /app/uploads; then
    print_success "Uploads directory exists in container"
    ((TESTS_PASSED++))
else
    print_error "Uploads directory not found in container"
    ((TESTS_FAILED++))
fi

# Test 7: Check Firebase configuration
print_header "Firebase Configuration"

if docker exec influencer-chat-api test -f /app/serviceAccountKey.json; then
    print_success "Firebase service account key mounted"
    ((TESTS_PASSED++))
else
    print_error "Firebase service account key not found"
    print_info "Make sure serviceAccountKey.json exists in the chatAPI directory"
    ((TESTS_FAILED++))
fi

# Test 8: Check Python dependencies
print_header "Python Dependencies"

run_test "Flask installed" "docker exec influencer-chat-api python3 -c 'import flask'"
run_test "Firebase Admin installed" "docker exec influencer-chat-api python3 -c 'import firebase_admin'"
run_test "PIL installed" "docker exec influencer-chat-api python3 -c 'from PIL import Image'"
run_test "OpenCV installed" "docker exec influencer-chat-api python3 -c 'import cv2'"

# Test 9: Check logs for errors
print_header "Log Analysis"

ERROR_COUNT=$(docker logs influencer-chat-api 2>&1 | grep -i "error" | wc -l)
if [ "$ERROR_COUNT" -eq 0 ]; then
    print_success "No errors found in logs"
    ((TESTS_PASSED++))
else
    print_error "Found $ERROR_COUNT error(s) in logs"
    print_info "View logs with: docker-compose logs -f chat-api"
    ((TESTS_FAILED++))
fi

# Test 10: Check resource usage
print_header "Resource Usage"

MEMORY_USAGE=$(docker stats --no-stream --format "{{.MemPerc}}" influencer-chat-api | sed 's/%//')
CPU_USAGE=$(docker stats --no-stream --format "{{.CPUPerc}}" influencer-chat-api | sed 's/%//')

print_info "Memory usage: ${MEMORY_USAGE}%"
print_info "CPU usage: ${CPU_USAGE}%"

if (( $(echo "$MEMORY_USAGE < 80" | bc -l) )); then
    print_success "Memory usage is within limits"
    ((TESTS_PASSED++))
else
    print_error "Memory usage is high"
    ((TESTS_FAILED++))
fi

# Summary
print_header "Test Summary"

TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))
echo -e "Total tests: $TOTAL_TESTS"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}✓ All tests passed! Docker setup is working correctly.${NC}\n"
    exit 0
else
    echo -e "\n${RED}✗ Some tests failed. Please check the errors above.${NC}\n"
    print_info "Common fixes:"
    print_info "  - Restart container: ./docker-start.sh restart"
    print_info "  - View logs: ./docker-start.sh logs"
    print_info "  - Rebuild: ./docker-start.sh rebuild"
    exit 1
fi
