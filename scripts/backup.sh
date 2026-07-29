#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# Rafeeq Kernel v2.3.0 — Backup Script
# Backs up PostgreSQL + Redis + File uploads
# ═══════════════════════════════════════════════════════════════════

set -e

BACKUP_DIR="/backups/rafeeq"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

mkdir -p $BACKUP_DIR

echo "🔄 Starting backup at $(date)"

# PostgreSQL backup
PG_BACKUP="$BACKUP_DIR/postgres_$TIMESTAMP.sql.gz"
echo "💾 Backing up PostgreSQL..."
pg_dump "$DATABASE_URL" | gzip > "$PG_BACKUP"
echo "✅ PostgreSQL backup: $PG_BACKUP ($(du -h $PG_BACKUP | cut -f1))"

# Redis backup
REDIS_BACKUP="$BACKUP_DIR/redis_$TIMESTAMP.rdb"
echo "💾 Backing up Redis..."
redis-cli -u "$REDIS_URL" BGSAVE
# Wait for save to complete
sleep 2
cp /data/dump.rdb "$REDIS_BACKUP" 2>/dev/null || echo "⚠️ Redis backup skipped (no local Redis)"

# Application logs backup
LOGS_BACKUP="$BACKUP_DIR/logs_$TIMESTAMP.tar.gz"
echo "💾 Backing up logs..."
tar -czf "$LOGS_BACKUP" -C /app logs/ 2>/dev/null || echo "⚠️ Logs backup skipped"

# Upload to S3 if configured
if [ -n "$S3_BUCKET" ] && [ -n "$AWS_ACCESS_KEY_ID" ]; then
    echo "☁️ Uploading to S3..."
    aws s3 sync "$BACKUP_DIR/" "s3://$S3_BUCKET/rafeeq/backups/" --exclude "*" --include "postgres_*" --include "redis_*"
    echo "✅ S3 upload complete"
fi

# Cleanup old backups
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "*.rdb" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "✅ Backup completed at $(date)"
echo "📦 Files in backup directory:"
ls -lh "$BACKUP_DIR" | tail -5
