# Database Backup and Recovery

## Overview

This project uses PostgreSQL in production (Docker) and SQLite for local development.
Backup procedures are documented below for each environment.

## Production (PostgreSQL/Docker)

### Prerequisites

Ensure these environment variables are set:
- `POSTGRES_HOST` - Database host (e.g., `db` when using Docker, or `localhost` locally)
- `POSTGRES_DB` - Database name
- `POSTGRES_USER` - Database user
- `POSTGRES_PASSWORD` - Database password

### Creating a Backup

```bash
# Using the backup script
./scripts/backup.sh [backup_directory]

# Or manually with pg_dump
pg_dump -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -F c -f backup.sql.gz
```

Backups are stored as gzip-compressed PostgreSQL custom-format dumps.
Files are timestamped to prevent overwrites: `notepad_backup_YYYYMMDD_HHMMSS.sql.gz`

### Restoring from Backup

```bash
# Using the recovery script
./scripts/recover.sh <backup_file> [target_db]

# Or manually with pg_restore
pg_restore -h $POSTGRES_HOST -U $POSTGRES_USER -d $TARGET_DB --clean --if-exists backup.sql.gz
```

**Warning:** Restoration overwrites existing data in the target database.

### Verification Procedure

1. Create a backup of the current database
2. Restore to a temporary database:
   ```bash
   ./scripts/recover.sh backup.sql.gz temp_verify_db
   ```
3. Verify data integrity:
   ```bash
   psql -h $POSTGRES_HOST -U $POSTGRES_USER -d temp_verify_db -c "SELECT COUNT(*) FROM notepad_note;"
   ```
4. Drop the temporary database when satisfied:
   ```bash
   dropdb -h $POSTGRES_HOST -U $POSTGRES_USER temp_verify_db
   ```

## Local Development (SQLite)

For local SQLite development, use Django's built-in backup or copy the database file:

```bash
# Copy the database file
cp db.sqlite3 backups/db_$(date +%Y%m%d_%H%M%S).sqlite3
```

**Note:** SQLite does not support concurrent writes. Stop the server before backing up.

## Docker Service Configuration

The `docker-compose.yml` includes:
- `db` service: PostgreSQL 17 with persistent volume
- `web` service: Django application
- `pgadmin` service: Database management interface

### Persistent Volume

Database data is stored in the `postgres_data` Docker volume. Do not delete this volume
unless you intend to lose all database contents.

```bash
# List volumes
docker volume ls | grep postgres

# View volume contents (requires container access)
docker exec -it notepad_postgres ls -la /var/lib/postgresql/data
```

## Operational Checklist

- [ ] Verify backup script works in staging environment
- [ ] Document backup schedule (daily/weekly)
- [ ] Test restoration procedure quarterly
- [ ] Monitor backup file sizes and retention policy
- [ ] Store backups off-server (S3, Azure Blob, etc.)
