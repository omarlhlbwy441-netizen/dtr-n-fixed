#!/bin/bash
# Rafeeq Kernel v2.3.0 — Database Migration Runner

set -e

echo "🗄️  Rafeeq Database Migration"
echo "============================="

# Detect environment
if [ -f .env ]; then
  export $(cat .env | grep -v '^#' | xargs)
fi

if [ -z "$DATABASE_URL" ]; then
  echo "❌ DATABASE_URL not set"
  exit 1
fi

echo "📋 Running migrations..."

# Run init script
if command -v psql &> /dev/null; then
  psql "$DATABASE_URL" -f scripts/init-db.sql
elif command -v docker-compose &> /dev/null; then
  docker-compose exec -T postgres psql -U rafeeq -d rafeeq -f /docker-entrypoint-initdb.d/init.sql
else
  echo "❌ Neither psql nor docker-compose available"
  exit 1
fi

echo "✅ Migrations complete"
