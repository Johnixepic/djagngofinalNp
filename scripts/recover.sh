#!/usr/bin/env bash
# Restore a PostgreSQL custom-format backup.
# Usage: ./scripts/recover.sh <backup_file.dump> [target_db]
# Prefer restoring to a disposable database first to verify a backup.

set -euo pipefail

BACKUP_FILE="${1:?Usage: ./scripts/recover.sh <backup_file.dump> [target_db]}"
DB_HOST="${POSTGRES_HOST:-${DB_HOST:-localhost}}"
DB_PORT="${POSTGRES_PORT:-${DB_PORT:-5432}}"
DB_NAME="${POSTGRES_DB:-notepad_db}"
DB_USER="${POSTGRES_USER:-}"
DB_PASSWORD="${POSTGRES_PASSWORD:-}"
TARGET_DB="${2:-${DB_NAME}}"

if [[ ! -s "${BACKUP_FILE}" ]]; then
    echo "ERROR: Backup file not found or empty: ${BACKUP_FILE}" >&2
    exit 1
fi
if [[ -z "${DB_USER}" ]]; then
    echo "ERROR: Set POSTGRES_USER in the environment." >&2
    exit 1
fi
if [[ ! "${TARGET_DB}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
    echo "ERROR: Target database name may contain only letters, digits, and underscores, and cannot start with a digit." >&2
    exit 1
fi

echo "WARNING: This will restore '${BACKUP_FILE}' into database '${TARGET_DB}'."
echo "Existing objects in that target database may be replaced."
read -r -p "Type the target database name to continue: " confirmation
if [[ "${confirmation}" != "${TARGET_DB}" ]]; then
    echo "Aborted."
    exit 0
fi

export PGPASSWORD="${DB_PASSWORD}"
if ! psql --host="${DB_HOST}" --port="${DB_PORT}" --username="${DB_USER}" \
    --dbname=postgres --tuples-only --no-align \
    --command="SELECT 1 FROM pg_database WHERE datname = '${TARGET_DB}'" | grep -q '^1$'; then
    createdb --host="${DB_HOST}" --port="${DB_PORT}" --username="${DB_USER}" "${TARGET_DB}"
fi

echo "Restoring into ${TARGET_DB}..."
pg_restore --host="${DB_HOST}" --port="${DB_PORT}" \
    --username="${DB_USER}" --dbname="${TARGET_DB}" \
    --clean --if-exists --no-owner --no-privileges "${BACKUP_FILE}"

echo "Restore completed. Verify the application and data before using this database."
