#!/usr/bin/env bash
set -euo pipefail

DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${DB_NAME:-knowledge_graphs}
DB_USER=${DB_USER:-postgres}

BACKUP_FILE=${1:?"Usage: $0 <backup-file>"}

pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" --clean "$BACKUP_FILE"
