#!/bin/bash
# Rafeeq Kernel v2.3.0 — Deployment Script
# Supports: Docker Compose, K8s, Helm, Render

set -e

DEPLOY_TYPE="${1:-docker}"
ENV="${2:-production}"

echo "🐺 Rafeeq Kernel v2.3.0 — Deploy to $ENV via $DEPLOY_TYPE"
echo "=========================================================="

case $DEPLOY_TYPE in
  docker)
    echo "🐳 Deploying with Docker Compose..."
    docker-compose pull
    docker-compose up -d
    echo "✅ Docker deployment complete"
    ;;

  k8s)
    echo "☸️  Deploying to Kubernetes..."
    kubectl apply -k k8s/
    kubectl rollout status deployment/rafeeq-api -n rafeeq
    echo "✅ K8s deployment complete"
    ;;

  helm)
    echo "⛵ Deploying with Helm..."
    helm upgrade --install rafeeq ./helm/rafeeq       --namespace rafeeq       --create-namespace       --wait       --timeout 5m
    echo "✅ Helm deployment complete"
    ;;

  render)
    echo "🚀 Triggering Render deployment..."
    curl -X POST       -H "Authorization: Bearer $RENDER_API_KEY"       -H "Content-Type: application/json"       "https://api.render.com/v1/services/$RENDER_SERVICE_ID/deploys"       -d '{"clearCache": "do_not_clear"}'
    echo "✅ Render deployment triggered"
    ;;

  *)
    echo "❌ Unknown deployment type: $DEPLOY_TYPE"
    echo "Usage: ./deploy.sh [docker|k8s|helm|render] [environment]"
    exit 1
    ;;
esac

echo ""
echo "🏥 Running health check..."
sleep 10
./scripts/health-check.sh || echo "⚠️  Health check failed, check logs"
