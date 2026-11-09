# Installation Guide — Django Notepad Application

## Overview

A full-featured web-based notepad application supporting plain text (TXT) and Markdown (MD) notes.

**Features:** Create, edit, delete, import/export notes with live Markdown preview, search, and keyboard shortcuts.

---

## Prerequisites

### Local Development (SQLite)
- Python 3.11+
- pip (Python package manager)

### Docker
- Docker Desktop or Docker Engine
- Docker Compose v2+

---

## Quick Start — Local Development (SQLite)

### 1. Clone and navigate
```bash
git clone <repo-url>
cd FinalProj
```

### 2. Create virtual environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment
```bash
cp .env.example .env
# Edit .env — keep DB_HOST empty for SQLite, set DJANGO_SECRET_KEY
```

### 5. Run migrations and start server
```bash
python manage.py migrate
python manage.py runserver
```

**Access:** http://localhost:8000

---

## Docker Compose Development (PostgreSQL)

The Compose setup is intended for local development. It runs Django's development server; do not expose it as a production deployment. Use a production WSGI/ASGI server, secure proxy/TLS, production settings, and a separately managed database before deploying publicly.

### 1. Configure environment variables
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```bash
POSTGRES_DB=notepad_db
POSTGRES_USER=notepad_user
POSTGRES_PASSWORD=your_secure_password
DJANGO_SECRET_KEY=your_cryptographically_random_secret
DJANGO_DEBUG=false
PGADMIN_EMAIL=admin@example.com
PGADMIN_PASSWORD=admin_password
```

### 2. Start services
```bash
docker compose up --build -d
```

### 3. Apply migrations
```bash
docker compose exec web python manage.py migrate
```

### 4. Access services
| Service | URL | Credentials |
|---------|-----|-------------|
| Django App | http://localhost:8081 | — |
| pgAdmin | http://localhost:5051 | Email/password from `.env` |

### 5. Stop services
```bash
docker compose down          # Keeps volumes (data preserved)
docker compose down -v       # Removes volumes (DESTRUCTIVE)
```

### 6. View logs
```bash
docker compose logs -f web   # Django logs
docker compose logs -f db    # PostgreSQL logs
```

---

## User Guide

### Creating Notes
1. Click **+ New Note** or navigate to `/notes/new/`
2. Enter a filename (without extension) in the title field
3. Select format: **Plain Text** or **Markdown**
4. Type your content
5. Click **Save** or press `Ctrl+S` / `Cmd+S`

### Editing Notes
1. Click any note in the sidebar
2. Edit title or content
3. Save changes with **Save** button or keyboard shortcut

### Save As
1. In the editor, click **Save As**
2. Enter a new filename
3. Click **Save As** to create a copy
4. Original note remains unchanged

### Deleting Notes
1. Click the note to open it
2. Click **Delete** button
3. Confirm deletion in the modal dialog

### Searching
1. Use the search box in the sidebar and submit your query.
2. Search checks titles and content using case-insensitive partial matching.
3. If no notes match, use **Clear search** in the empty state to return to all notes.

### Importing Files
1. Open **Import Notes** in the sidebar or choose **Import a file** on the empty notes screen.
2. Select a `.txt` or `.md` file. The picker displays its filename and size.
3. Click **Import note**. The server accepts files up to 1 MiB and rejects unsupported or binary files.
4. The imported note is saved and opens automatically.
5. If a note with the same filename and format already exists, a numbered copy is created (for example, `meeting (2).md`). The original note is not overwritten.

### Downloading Notes
1. Open any note
2. Click **Download** button
3. File saves with correct extension (`.txt` or `.md`)

### Markdown Preview
- Existing Markdown notes open with a live preview on the right.
- On a new note, select **Markdown** to reveal the preview control.
- Toggle the pane with **Show preview** / **Hide preview**.
- Sanitized HTML prevents XSS attacks

### Keyboard Shortcuts
| Shortcut | Action |
|----------|--------|
| `Ctrl+S` / `Cmd+S` | Save |
| `Ctrl+Shift+S` / `Cmd+Shift+S` | Save As |
| `Escape` | Close Save As modal |

### Unsaved Changes
- Browser warns when leaving with unsaved edits
- Warning clears after successful save

---

## Troubleshooting

### Port Already in Use
```bash
# Find and kill process on port 8000
lsof -ti:8000 | xargs kill -9
# Or use different port
python manage.py runserver 0.0.0.0:8001
```

### Database Connection Failed
- Ensure PostgreSQL is running: `docker compose ps`
- Verify `.env` has correct credentials
- Check `DB_HOST` is set to `db` for Docker

### Migration Errors
```bash
python manage.py migrate --run-syncdb
```

### Container Won't Start
```bash
docker compose logs db    # Check database logs
docker compose logs web   # Check Django logs
docker compose down -v    # Reset volumes (LOSES DATA)
docker compose up --build -d
```

### Browser Preview Not Working
- Ensure JavaScript is enabled
- Check browser console for CSP errors
- Clear browser cache

---

## Project Structure

```
FinalProj/
├── config/              # Django project settings
│   ├── settings.py      # Configuration
│   ├── urls.py          # URL routing
│   └── wsgi.py          # WSGI entry point
├── notepad/             # Main application
│   ├── models.py        # Note model
│   ├── views.py         # View logic
│   ├── urls.py          # URL patterns
│   ├── forms.py         # Forms (including Save As)
│   ├── tests.py         # Test suite
│   ├── templates/       # HTML templates
│   └── static/          # CSS and JS assets
├── scripts/             # Utility scripts
│   ├── backup.sh        # Database backup
│   └── recover.sh       # Database recovery
├── docker-compose.yml   # Docker services
├── INSTALL.md           # This file
├── USER_GUIDE.md        # User documentation
├── BACKUP_GUIDE.md      # Backup procedures
└── browser_test.js      # E2E test suite
```

---

## Testing

### Unit Tests
```bash
python manage.py test notepad -v2
```

### E2E Browser Tests
```bash
# Start dev server first
python manage.py runserver 127.0.0.1:8765
node browser_test.js
```

### Django Check
```bash
python manage.py check
python manage.py check --deploy
```

---

## Security Notes

- **Never commit `.env`** — it contains secrets
- Use cryptographically random `DJANGO_SECRET_KEY` in production
- PostgreSQL credentials externalized to environment variables
- Content Security Policy (CSP) enabled with nonces
- Markdown output sanitized against XSS
- CSRF protection on all forms

---

## Backup and Recovery

See [BACKUP_GUIDE.md](BACKUP_GUIDE.md) for detailed procedures.

```bash
# Create backup
./scripts/backup.sh

# List backups
ls -lt backups/notepad_backup_*.dump

# Restore (to same database)
./scripts/recover.sh backups/notepad_backup_YYYYMMDD_HHMMSS.dump
```

---

## License

MIT
