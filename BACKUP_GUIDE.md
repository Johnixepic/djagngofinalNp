# Database Backup and Recovery

## PostgreSQL (Docker Compose)

The Compose application uses the `web` service and PostgreSQL `db` service. Inside the web container, the database host is `db` (from `DB_HOST`). The scripts create PostgreSQL **custom-format** archives with the `.dump` extension; these are not gzip-compressed SQL files.

### Create a backup

Run from the project root:

```bash
mkdir -p backups
docker compose exec web ./scripts/backup.sh /app/backups
```

The backup is written to the host's `./backups` directory because the project folder is mounted at `/app`.

You can also run the script outside Docker by supplying connection variables, for example:

```bash
POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=5433 \
POSTGRES_DB=notepad_db POSTGRES_USER=notepad_user \
POSTGRES_PASSWORD='your-password' ./scripts/backup.sh
```

### Restore safely

**Do not test a backup by restoring over your working database.** First restore to a disposable database:

```bash
docker compose exec -it web ./scripts/recover.sh /app/backups/notepad_backup_TIMESTAMP.dump notepad_verify
```

The script requires you to type the target database name before it proceeds. Check the restored data:

```bash
docker compose exec web python manage.py shell -c \
  "from notepad.models import Note; print('Restored notes:', Note.objects.using('default').count())"
```

After verification, remove the disposable database only when you are certain it is the test database:

```bash
docker compose exec web dropdb --host=db --username="$POSTGRES_USER" notepad_verify
```

To restore to the configured application database, pass its exact name as the target. This can replace existing database objects and should only be done after confirming a separate current backup exists.

### Manual PostgreSQL commands

```bash
pg_dump -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -F c -f backup.dump
pg_restore -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$TARGET_DB" --clean --if-exists --no-owner --no-privileges backup.dump
```

## Local SQLite development

Stop the local server before copying the SQLite database:

```bash
mkdir -p backups
cp db.sqlite3 "backups/db_$(date +%Y%m%d_%H%M%S).sqlite3"
```

## Operational notes

- Keep `.env` out of Git; it contains database credentials and the Django secret key.
- Store backup copies somewhere separate from the development machine.
- Periodically perform a restore into a disposable database and verify the result.
- The Compose PostgreSQL data volume is persistent. Do not use `docker compose down -v` unless intentionally deleting database data.
