# Django Notepad

A full-featured web-based notepad application built with Django.

## Features

- **Create, edit, and delete notes** — Plain text (TXT) and Markdown (MD) formats
- **Live Markdown preview** — Split-pane editor with real-time HTML rendering
- **File import/export** — Import TXT/MD files (up to 1 MiB), safely create numbered copies for duplicate names, and download notes as raw content
- **Search** — Find notes by title and content
- **Save As** — Duplicate notes with a new name
- **Keyboard shortcuts** — Quick access to common actions
- **Unsaved changes tracking** — Warning when leaving with unsaved edits
- **Responsive design** — Accessible mobile navigation and desktop layouts

## Technical Details

- **Usage scope**: Single-user app; it does not include login or account isolation. Keep it on a trusted network unless authentication and authorization are added.

- **Backend**: Django 6.1 with SQLite (local development) or PostgreSQL 17 (Docker)
- **Frontend**: Vanilla JavaScript, CSS Grid/Flexbox
- **Markdown**: Python `markdown` library with extensions (extra, codehilite, tables)
- **Security**: XSS sanitization, CSRF protection, secure file handling

## Project Structure

```
FinalProj/
├── config/          # Django project settings
├── notepad/         # Main Django app
│   ├── models.py    # Note model
│   ├── views.py     # View logic
│   ├── urls.py      # URL routing
│   ├── forms.py     # Forms (including Save As)
│   ├── tests.py     # Django regression test suite
│   └── templates/   # HTML templates
├── static/          # CSS and JS assets
├── docker-compose.yml  # Docker deployment
├── INSTALL.md       # Installation guide
└── browser_test.js  # E2E browser tests
```

## LAN Access

For phone testing on the same trusted Wi-Fi, run `bash scripts/enable-lan.sh` from the repository root, then `docker compose up -d --force-recreate web`. The helper adds the laptop's current LAN IP to Django's allowed hosts and, when UFW is active, allows TCP port 8081 only from the detected local subnet. Open the printed `http://LAN-IP:8081` address on your phone. PostgreSQL and pgAdmin host ports remain bound to localhost. This app has no login; do not forward port 8081 to the public internet.

## Quick Start

1. Clone the repository
2. Create a virtual environment: `python -m venv .venv`
3. Activate and install dependencies: `pip install -r requirements.txt`
4. Run migrations: `python manage.py migrate`
5. Start the dev server: `python manage.py runserver`
6. Open http://127.0.0.1:8000/

## Testing

- **Unit tests**: `python manage.py test notepad -v 2`
- **E2E browser tests**: `node browser_test.js` (requires the app to be running on the configured test URL)
- **Deployment checks**: `python manage.py check --deploy` with production environment variables configured

## NP Reports

- [NP-010: E2E Browser Verification](NP-010_report.md) — 25/25 passed
- [NP-011: Security Audit](NP-011_report.md) — All issues addressed

## License

MIT
