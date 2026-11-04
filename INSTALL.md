# Installation Guide — Notepad Application

## Quick Start (Local Development — SQLite)

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd FinalProj
   ```

2. **Create a virtual environment and install dependencies**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env — ensure DB_HOST is empty for SQLite, set DJANGO_SECRET_KEY to a real value
   ```

4. **Run migrations and start the server**
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

The app will be available at `http://localhost:8000`.

## Docker Compose (PostgreSQL)

1. **Ensure `.env` has PostgreSQL credentials set:**
   ```bash
   POSTGRES_DB=notepad_db
   POSTGRES_USER=<your_user>
   POSTGRES_PASSWORD=<your_password>
   DJANGO_SECRET_KEY=<a-long-random-secret>
   DJANGO_DEBUG=false
   ```

2. **Start the stack:**
   ```bash
   docker compose up --build -d
   ```

   Services will be available at:
   - Django API: `http://localhost:8081`
   - pgAdmin: `http://localhost:5051` (default email: `admin@example.com`, password from `.env`)

3. **Stop the stack:**
   ```bash
   docker compose down
   ```

## Security Notes

- Never commit your `.env` file — it is listed in `.gitignore`.
- The `.env.example` file contains only placeholders and is safe to commit.
- For production, always set `DJANGO_SECRET_KEY` to a cryptographically random value.
- PostgreSQL credentials in `docker-compose.yml` are read from environment variables — no hardcoded secrets remain.
