#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# Rafeeq Kernel v2.3.0 — Health Check Script
# ═══════════════════════════════════════════════════════════════════

set -e

API_URL="${API_URL:-http://localhost:8000}"
TIMEOUT=10

echo "🏥 Rafeeq Health Check — $(date)"
echo "=================================="

# Check API
echo -n "🌐 API Health... "
if curl -fs -m $TIMEOUT "$API_URL/api/health" > /dev/null 2>&1; then
    echo "✅ OK"
else
    echo "❌ FAIL"
    exit 1
fi

# Check Database
echo -n "🗄️  Database... "
if curl -fs -m $TIMEOUT "$API_URL/api/health/db" > /dev/null 2>&1; then
    echo "✅ OK"
else
    echo "❌ FAIL"
fi

# Check Redis
echo -n "⚡ Redis... "
if curl -fs -m $TIMEOUT "$API_URL/api/health/redis" > /dev/null 2>&1; then
    echo "✅ OK"
else
    echo "❌ FAIL"
fi

# Check GitHub
echo -n "🐙 GitHub... "
if curl -fs -m $TIMEOUT "$API_URL/api/health/github" > /dev/null 2>&1; then
    echo "✅ OK"
else
    echo "❌ FAIL"
fi

# System resources
echo ""
echo "📊 System Resources:"
echo "  CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
echo "  Memory: $(free -h | awk '/^Mem:/ {print $3 "/" $2}')"
echo "  Disk: $(df -h / | awk 'NR==2 {print $3 "/" $2 " (" $5 ")"}')"

echo ""
echo "✅ All checks completed at $(date)"
