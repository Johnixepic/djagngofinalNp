# NP-011 — Application Security and Configuration Audit Report

**Project:** `/mnt/WorkDisk/3rd Year School/Integrative Prog/FinalProj` (Notepad Clone)  
**Date:** 2026-11-01  
**Priority:** P1  
**Auditor:** Automated security audit agent

---

## 1. Findings

### Critical — None

No critical vulnerabilities were identified. The application has no authentication layer and is designed as a local-only tool; there are no exposed user credentials or data-access flaws.

---

### High — None

No high-severity issues found. CSRF protection, input validation, and HTML sanitization all operate correctly.

---

### Medium — 1 finding (fixed)

**MEDIUM-01: XSS via unescaped note title in JavaScript context**  
- **Severity:** Medium  
- **Status:** ✅ Fixed  
- **File:** `notepad/templates/notepad/editor.html`, line 156  
- **Evidence:** The template rendered `note.title` directly into a JavaScript string literal without escaping:
  ```html
  saveasTitle.value = '{{ note.title|default:"Untitled" }}_copy';
  ```
  While Django auto-escapes HTML entities, it does not escape JavaScript control characters. A title containing a single quote (e.g., `foo's note`) would produce invalid JS syntax (`'foo's note_copy'`), and a title with backslash sequences could cause unintended string interpretation.  
- **Fix applied:** Added Django's `|escapejs` filter:
  ```html
  saveasTitle.value = '{{ note.title|default:"Untitled"|escapejs }}_copy';
  ```
- **Verification:** All 145 existing tests pass; the fix was verified with a targeted check that no other `{{ note.* }}` variables remain unescaped in JS contexts across all templates.

---

### Low — None

No low-severity issues requiring code changes were found.

---

### Informational — 6 findings

**INFO-01: .env file contains committed SECRET_KEY**  
- **Severity:** Informational  
- **File:** `.env` (untracked by git)  
- **Evidence:** The `.env` file contains `DJANGO_SECRET_KEY=django-insecure-...`. It is not tracked by git (confirmed via `git ls-files .env`), but no `.gitignore` exists in the project root, so it could be accidentally committed.  
- **Recommendation:** Add `.env` to a new `.gitignore` file to prevent accidental inclusion in version control.

**INFO-02: Hardcoded PostgreSQL credentials in docker-compose.yml**  
- **Severity:** Informational  
- **File:** `docker-compose.yml`, lines 9–10  
- **Evidence:** `POSTGRES_PASSWORD: secret` is hardcoded in plain text. The docker-compose file is also untracked by git.  
- **Recommendation:** Move credentials to `.env` and reference via `${POSTGRES_PASSWORD}` interpolation, consistent with the web service's existing pattern for `DJANGO_SECRET_KEY`.

**INFO-03: pgadmin exposed with default credentials**  
- **Severity:** Informational  
- **File:** `docker-compose.yml`, lines 24–25  
- **Evidence:** `PGADMIN_DEFAULT_PASSWORD: admin123` uses a weak default password. The pgadmin service is bound to host port 5051.  
- **Recommendation:** Move pgadmin credentials to `.env` and use strong passwords in production.

**INFO-04: No Content-Security-Policy (CSP) header**  
- **Severity:** Informational  
- **File:** `config/settings.py`  
- **Evidence:** Django's deployment check (`check --deploy`) does not flag missing CSP, and none is configured. Adding a CSP would provide defense-in-depth against XSS.  
- **Recommendation:** Consider adding `content-security-policy` via a middleware or the `django-csp` package when the application moves to a hosted environment.

**INFO-05: No HSTS enforcement (local dev tool)**  
- **Severity:** Informational / Expected  
- **File:** `config/settings.py`  
- **Evidence:** `SECURE_HSTS_SECONDS = 0` by default; `check --deploy` warns about this. For a local-only development tool served over HTTP, HSTS is neither applicable nor desirable.  
- **Status:** No action needed for local use. Set `DJANGO_HSTS_SECONDS` in production deployment.

**INFO-06: SECURE_SSL_REDIRECT not set**  
- **Severity:** Informational / Expected  
- **File:** `config/settings.py`  
- **Evidence:** Django's `check --deploy` warns about missing `SECURE_SSL_REDIRECT`. For a local dev tool, SSL termination is handled by the user's browser or proxy, not by Django.  
- **Status:** No action needed for local use. Set in production deployment configuration.

---

## 2. Evidence and Affected Files

| File | Relevance |
|------|-----------|
| `config/settings.py` | Django security settings (DEBUG, SECRET_KEY, ALLOWED_HOSTS, cookies, HSTS) |
| `docker-compose.yml` | Docker service config, exposed ports, credentials |
| `.env` | Local secrets (SECRET_KEY, DB creds) |
| `notepad/views.py` | View logic, markdown sanitization, import handling, download |
| `notepad/forms.py` | Input validation (title, file upload) |
| `notepad/templates/notepad/editor.html` | Template rendering, JS context (fixed) |
| `notepad/templates/notepad/preview.html` | Sanitized HTML output |
| `requirements.txt` | Dependencies (bleach, markdown, Django) |

---

## 3. Fixes Implemented

| # | Change | File | Description |
|---|--------|------|-------------|
| 1 | Added `\|escapejs` filter | `notepad/templates/notepad/editor.html:156` | Prevents JS context breakout from user-controlled note titles in the Save As modal initialization |

No database changes, no Docker configuration changes, and no credentials were rotated.

---

## 4. Issues Requiring Executive Approval

### 4a. .gitignore file creation (INFO-01)
- **Issue:** No `.gitignore` exists; `.env` is untracked but could be accidentally committed.
- **Proposed fix:** Create `.gitignore` with `*.env` and `db.sqlite3`.
- **Impact:** Low risk; prevents accidental secret leakage.
- **Approval needed:** Yes — requires user confirmation to create a new file in the project root.

### 4b. docker-compose.yml credential externalization (INFO-02, INFO-03)
- **Issue:** PostgreSQL and pgadmin credentials are hardcoded in `docker-compose.yml`.
- **Proposed fix:** Move all credentials to `.env` and use `${VAR}` interpolation in `docker-compose.yml`.
- **Impact:** Requires updating `.env` and `docker-compose.yml`; no functional change to the running app.
- **Approval needed:** Yes — changes deployment configuration files.

### 4c. CSP middleware addition (INFO-04)
- **Issue:** No Content-Security-Policy header is set.
- **Proposed fix:** Install and configure `django-csp` with a restrictive policy.
- **Impact:** Moderate risk; a misconfigured CSP can break existing functionality. Requires testing.
- **Approval needed:** Yes — adds a new dependency and middleware.

---

## 5. Test Results

| Command | Result |
|---------|--------|
| `python manage.py test notepad.tests --verbosity=2` | **145 tests, 0 failures, 0 errors** ✅ |
| `python manage.py check` | **0 issues** ✅ |
| `python manage.py check --deploy` | **6 warnings** (see §6 below) |
| `python manage.py makemigrations --check --dry-run` | **No changes detected** ✅ |

---

## 6. Remaining Security Limitations

The following are **expected for a local development tool** and do not require fixes under the current constraints:

| Item | Detail | Rationale |
|------|--------|-----------|
| `security.W004` (HSTS) | `SECURE_HSTS_SECONDS = 0` | Local dev over HTTP; HSTS would lock users out |
| `security.W008` (SSL redirect) | `SECURE_SSL_REDIRECT` not set | No SSL termination in Docker compose |
| `security.W009` (SECRET_KEY strength) | Key prefixed with `django-insecure-` when DEBUG=true | Local dev only; production requires a strong key via env var |
| `security.W012` (SESSION_COOKIE_SECURE) | False when DEBUG=true | Cookies sent over HTTP in local dev; enforced to True when DEBUG=false |
| `security.W016` (CSRF_COOKIE_SECURE) | False when DEBUG=true | Same as above; enforced when DEBUG=false |
| `security.W018` (DEBUG=True) | Default for local SQLite workflow | Intentional; production Docker sets `DJANGO_DEBUG=false` |

These 6 warnings are **expected and acceptable** for a local development environment. They become actionable only when deploying to a production context with HTTPS.

---

## 7. Summary

| Category | Count |
|----------|-------|
| Critical | 0 |
| High | 0 |
| Medium (fixed) | 1 |
| Low | 0 |
| Informational | 6 |
| Require approval | 3 |

**Overall assessment:** The Notepad clone is in good security shape for a local-only application. CSRF protection, input validation, and HTML sanitization are all correctly implemented. One medium-severity XSS vector was identified and fixed. Three informational items require executive approval before implementation. All 145 existing tests continue to pass.
