#!/usr/bin/env bash
# Database Recovery Script for Django Notepad
# Usage: ./scripts/recover.sh <backup_file> [target_db]
# Restores a backup to a PostgreSQL database

set -euo pipefail

BACKUP_FILE="${1:?Usage: ./scripts/recover.sh <backup_file> [target_db]}"
TARGET_DB="${2:-${POSTGRES_DB:-notepad_db}}"

# Verify backup file exists
if [ ! -f "${BACKUP_FILE}" ]; then
    echo "ERROR: Backup file not found: ${BACKUP_FILE}" >&2
    exit 1
fi

# Check environment variables
if [ -z "${POSTGRES_HOST:-}" ]; then
    echo "ERROR: POSTGRES_HOST not set" >&2
    exit 1
fi

if [ -z "${POSTGRES_USER:-}" ]; then
    echo "ERROR: POSTGRES_USER not set" >&2
    exit 1
fi
# Warn about data loss
echo "WARNING: This will restore '${BACKUP_FILE}' to database '${TARGET_DB}'"
echo "         Existing data in '${TARGET_DB}' will be overwritten!"
echo ""
read -p "Continue? (yes/no): " confirm
if [ "${confirm}" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

# Create target database if it doesn't exist
psql -h "${POSTGRES_HOST}" -U "${POSTGRES_USER}" -d postgres -tc \
    "SELECT 1 FROM pg_database WHERE datname = '${TARGET_DB}'" 2>/dev/null | grep -q 1 || \
    psql -h "${POSTGRES_HOST}" -U "${POSTGRES_USER}" -d postgres -c \
    "CREATE DATABASE ${TARGET_DB}" 2>/dev/null || true

# Restore from backup
echo "Restoring from: ${BACKUP_FILE}"
echo "Target database: ${TARGET_DB}"
PGPASSWORD="${POSTGRES_PASSWORD:-}" pg_restore     -h "${POSTGRES_HOST}"     -U "${POSTGRES_USER}"     -d "${TARGET_DB}"     --clean --if-exists     "${BACKUP_FILE}" 2>/dev/null

echo "Recovery completed."
