# Django Notepad

A full-featured web-based notepad application built with Django.

## Features

- **Create, edit, and delete notes** — Plain text (TXT) and Markdown (MD) formats
- **Live Markdown preview** — Split-pane editor with real-time HTML rendering
- **File import/export** — Import TXT/MD files, download notes as raw content
- **Search** — Filter notes by title
- **Save As** — Duplicate notes with a new name
- **Keyboard shortcuts** — Quick access to common actions
- **Unsaved changes tracking** — Warning when leaving with unsaved edits
- **Responsive design** — Works on mobile and desktop viewports

## Technical Details

- **Backend**: Django 4.x with SQLite (default) or PostgreSQL (Docker)
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
│   ├── tests.py     # Test suite (145+ tests)
│   └── templates/   # HTML templates
├── static/          # CSS and JS assets
├── docker-compose.yml  # Docker deployment
├── INSTALL.md       # Installation guide
└── browser_test.js  # E2E browser tests
```

## Quick Start

1. Clone the repository
2. Create a virtual environment: `python -m venv .venv`
3. Activate and install dependencies: `pip install -r requirements.txt`
4. Run migrations: `python manage.py migrate`
5. Start the dev server: `python manage.py runserver`
6. Open http://127.0.0.1:8000/

## Testing

- **Unit tests**: `python manage.py test notepad`
- **E2E browser tests**: `node browser_test.js` (requires dev server running)

## NP Reports

- [NP-010: E2E Browser Verification](NP-010_report.md) — 25/25 passed
- [NP-011: Security Audit](NP-011_report.md) — All issues addressed

## License

MIT
