#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# Rafeeq Kernel v2.3.0 — One-Click Setup Script
# ═══════════════════════════════════════════════════════════════════

set -e

echo "🐺 Rafeeq Kernel v2.3.0 — Setup"
echo "================================"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose first."
    exit 1
fi

echo "✅ Docker & Docker Compose found"

# Create .env if not exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cat > .env << 'EOF'
# Rafeeq Kernel Environment
POSTGRES_PASSWORD=rafeeq_secure_2026
SECRET_KEY=change-this-in-production-now
GITHUB_TOKEN=your_github_token_here
GITHUB_USER=omarlhlbwy441-netizen
GITHUB_REPO=omarlhlbwy441-netizen/dtr-n-fixed
GRAFANA_USER=admin
GRAFANA_PASSWORD=rafeeq_grafana_2026
EOF
    echo "⚠️  Please edit .env and set your actual values!"
fi

# Create required directories
mkdir -p logs
mkdir -p nginx/ssl
mkdir -p grafana/dashboards
mkdir -p grafana/datasources

# Generate self-signed SSL cert for local dev
if [ ! -f nginx/ssl/fullchain.pem ]; then
    echo "🔐 Generating self-signed SSL certificate..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048         -keyout nginx/ssl/privkey.pem         -out nginx/ssl/fullchain.pem         -subj "/C=EG/ST=Cairo/L=Cairo/O=Rafeeq/OU=Dev/CN=localhost"
    echo "✅ SSL certificate generated"
fi

# Pull images
echo "📦 Pulling Docker images..."
docker-compose pull

# Start services
echo "🚀 Starting services..."
docker-compose up -d

# Wait for database
echo "⏳ Waiting for PostgreSQL..."
sleep 10

# Run migrations
echo "🗄️  Running database migrations..."
docker-compose exec -T postgres psql -U rafeeq -d rafeeq -f /docker-entrypoint-initdb.d/init.sql

echo ""
echo "✅ Rafeeq is ready!"
echo ""
echo "📍 Access Points:"
echo "   🌐 App:       https://localhost"
echo "   📊 Grafana:   http://localhost:3000 (admin/rafeeq_grafana_2026)"
echo "   📈 Prometheus: http://localhost:9090"
echo "   🔌 API Docs:  https://localhost/api/docs"
echo ""
echo "📋 Useful Commands:"
echo "   docker-compose logs -f app     # View app logs"
echo "   docker-compose ps              # Check status"
echo "   ./scripts/health-check.sh      # Run health check"
echo "   ./scripts/backup.sh            # Run backup"
echo ""
