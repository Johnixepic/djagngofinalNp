#!/usr/bin/env bash
# Database Backup Script for Django Notepad
# Usage: ./scripts/backup.sh [backup_dir]
# Creates a timestamped PostgreSQL dump

set -euo pipefail

BACKUP_DIR="${1:-$(pwd)/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/notepad_backup_${TIMESTAMP}.sql.gz"

# Ensure backup directory exists
mkdir -p "${BACKUP_DIR}"

# Check environment variables
if [ -z "${POSTGRES_HOST:-}" ]; then
    echo "ERROR: POSTGRES_HOST not set" >&2
    exit 1
fi

if [ -z "${POSTGRES_DB:-}" ]; then
    echo "ERROR: POSTGRES_DB not set" >&2
    exit 1
fi

if [ -z "${POSTGRES_USER:-}" ]; then
    echo "ERROR: POSTGRES_USER not set" >&2
    exit 1
fi

# Create backup using pg_dump
echo "Creating backup: ${BACKUP_FILE}"
PGPASSWORD="${POSTGRES_PASSWORD:-}" pg_dump     -h "${POSTGRES_HOST}"     -U "${POSTGRES_USER}"     -d "${POSTGRES_DB}"     -F c     -f "${BACKUP_FILE}" 2>/dev/null

if [ -f "${BACKUP_FILE}" ]; then
    SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    echo "Backup completed successfully"
    echo "File: ${BACKUP_FILE}"
    echo "Size: ${SIZE}"
else
    echo "ERROR: Backup failed" >&2
    exit 1
fi

# List recent backups
echo ""
echo "Recent backups:"
ls -lt "${BACKUP_DIR}"/notepad_backup_*.sql.gz 2>/dev/null | head -5
