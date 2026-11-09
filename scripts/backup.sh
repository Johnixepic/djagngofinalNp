#!/usr/bin/env bash
# PostgreSQL custom-format backup for Django Notepad.
# Run inside the web container (DB_HOST=db), or provide POSTGRES_HOST/POSTGRES_PORT.
# Usage: ./scripts/backup.sh [backup_dir]

set -euo pipefail

BACKUP_DIR="${1:-$(pwd)/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/notepad_backup_${TIMESTAMP}.dump"

DB_HOST="${POSTGRES_HOST:-${DB_HOST:-localhost}}"
DB_PORT="${POSTGRES_PORT:-${DB_PORT:-5432}}"
DB_NAME="${POSTGRES_DB:-}"
DB_USER="${POSTGRES_USER:-}"
DB_PASSWORD="${POSTGRES_PASSWORD:-}"

for var_name in DB_NAME DB_USER; do
    if [[ -z "${!var_name}" ]]; then
        echo "ERROR: Set POSTGRES_DB and POSTGRES_USER in the environment." >&2
        exit 1
    fi
done

mkdir -p "${BACKUP_DIR}"
echo "Creating PostgreSQL custom-format backup: ${BACKUP_FILE}"
PGPASSWORD="${DB_PASSWORD}" pg_dump \
    --host="${DB_HOST}" --port="${DB_PORT}" \
    --username="${DB_USER}" --dbname="${DB_NAME}" \
    --format=custom --file="${BACKUP_FILE}"

if [[ ! -s "${BACKUP_FILE}" ]]; then
    echo "ERROR: Backup file was not created or is empty." >&2
    exit 1
fi

echo "Backup completed successfully."
du -h "${BACKUP_FILE}"
echo
echo "Recent backups:"
find "${BACKUP_DIR}" -maxdepth 1 -type f -name 'notepad_backup_*.dump' -printf '%T@ %p\n' \
    | sort -rn | head -5 | cut -d' ' -f2-
