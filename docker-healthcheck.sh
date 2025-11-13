#!/bin/bash

# Health check script for LLM Camera Tracker Docker containers

check_port() {
    local port=$1
    local service=$2
    if curl -f "http://localhost:${port}/health" >/dev/null 2>&1; then
        echo "✅ $service on port $port is healthy"
        return 0
    else
        echo "❌ $service on port $port is not responding"
        return 1
    fi
}

# Check which service this container is running based on exposed port
if netstat -tuln 2>/dev/null | grep -q ':8080 '; then
    echo "Checking llama-server health..."
    if curl -f "http://localhost:8080/v1/models" >/dev/null 2>&1; then
        echo "✅ llama-server is healthy"
        exit 0
    else
        echo "❌ llama-server is not responding"
        exit 1
    fi
elif netstat -tuln 2>/dev/null | grep -q ':8081 '; then
    echo "Checking scene-graph-server health..."
    check_port 8081 "scene-graph-server"
    exit $?
elif netstat -tuln 2>/dev/null | grep -q ':8000 '; then
    echo "Checking web-server health..."
    if curl -f "http://localhost:8000/index.html" >/dev/null 2>&1; then
        echo "✅ web-server is healthy"
        exit 0
    else
        echo "❌ web-server is not responding"
        exit 1
    fi
else
    echo "❌ No recognized service port found"
    exit 1
fi 