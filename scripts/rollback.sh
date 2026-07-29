#!/bin/bash
# Rafeeq Kernel v2.3.0 — Rollback Script

set -e

DEPLOY_TYPE="${1:-docker}"

echo "🔄 Rafeeq Kernel — Rollback"
echo "==========================="

case $DEPLOY_TYPE in
  docker)
    echo "🐳 Rolling back Docker..."
    docker-compose down
    docker-compose up -d --no-build
    ;;

  k8s)
    echo "☸️  Rolling back K8s..."
    kubectl rollout undo deployment/rafeeq-api -n rafeeq
    kubectl rollout status deployment/rafeeq-api -n rafeeq
    ;;

  helm)
    echo "⛵ Rolling back Helm..."
    helm rollback rafeeq 0 -n rafeeq
    ;;

  *)
    echo "❌ Unknown type: $DEPLOY_TYPE"
    exit 1
    ;;
esac

echo "✅ Rollback complete"
