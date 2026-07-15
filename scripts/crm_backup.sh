#!/bin/bash
# CRM Postgres kunlik backup — gzip, rotatsiyali (oxirgi KEEP ta saqlanadi).
# Cron misoli (serverda `crontab -e`):
#   0 3 * * * /home/ubuntu/crm_telegram_bot/scripts/crm_backup.sh >> /home/ubuntu/backups/backup.log 2>&1
set -euo pipefail

PROJECT_DIR="${CRM_DIR:-/home/ubuntu/crm_telegram_bot}"
BACKUP_DIR="${CRM_BACKUP_DIR:-/home/ubuntu/backups}"
KEEP="${CRM_BACKUP_KEEP:-7}"
DB_USER="${POSTGRES_USER:-crm_bot}"
DB_NAME="${POSTGRES_DB:-crm_bot}"

mkdir -p "$BACKUP_DIR"
cd "$PROJECT_DIR"

TS="$(date +%Y%m%d_%H%M%S)"
OUT="$BACKUP_DIR/crm_${TS}.sql.gz"

# Postgres konteyneridan dump olib, gzip qilamiz.
docker compose exec -T postgres pg_dump -U "$DB_USER" -d "$DB_NAME" | gzip > "$OUT"

# Eski backuplarni tozalash (eng yangi KEEP ta qoldiriladi).
ls -1t "$BACKUP_DIR"/crm_*.sql.gz 2>/dev/null | tail -n +"$((KEEP + 1))" | xargs -r rm -f

echo "$(date '+%Y-%m-%d %H:%M:%S') backup OK: $OUT ($(du -h "$OUT" | cut -f1)); jami: $(ls -1 "$BACKUP_DIR"/crm_*.sql.gz 2>/dev/null | wc -l)"
