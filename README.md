# VINNPRO Campus OS Pro

A responsive campus-management web app built with **Python, Flask, SQLite, HTML, CSS, and vanilla JavaScript**. No Node.js or Express.js.

## Features

- Public account registration, login, and logout
- Password hashing using Werkzeug
- Dark/light theme toggle saved in browser local storage
- Responsive layout for mobile, tablet, laptop, and desktop
- Database-driven overview metrics
- Student CRUD (create, list, delete)
- Faculty CRUD (create, list, delete)
- Attendance recording, duplicate prevention, and deletion
- Timetable create/list/delete
- Reports calculated from saved records
- Attendance CSV export
- Rule-based campus assistant that queries the live database
- Table search on student, faculty, and timetable pages

## Run locally (Windows PowerShell)

Open a terminal in the folder that contains `app.py` and `requirements.txt`:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

If PowerShell blocks activation, run this instead:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Then open `http://127.0.0.1:5000`. Create an account on the registration page; there is no hardcoded demo login.

## Run on macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Deploy to Render

1. Push the contents of this folder to a GitHub repository.
2. In Render, choose **New → Blueprint** and connect the repository, or create a Python web service manually.
3. The included `render.yaml` configures Gunicorn, a generated `SECRET_KEY`, and a 1 GB persistent disk mounted at `/var/data`.
4. If creating the service manually, use:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
   - Environment variable: `SECRET_KEY` (use a long random value)
   - For persistent SQLite storage, mount a disk at `/var/data` and set `DATABASE_PATH=/var/data/campus.db`.

**Plan note:** persistent disks may depend on your Render plan and billing. If you do not attach persistent storage, local SQLite files on hosted instances can be ephemeral. For larger multi-user production deployments, consider managed PostgreSQL and database migrations.

## Dynamic data and demo records

The dashboard numbers and reports are calculated from the SQLite database. The app does not ship with fake student/faculty/attendance records or a hardcoded demo account. After registration, add your own records through the UI. Static assets are limited to reusable design styles and interface structure, which is normal for a web application.

## Security and production notes

- Passwords are hashed, never stored as plain text.
- Set a strong `SECRET_KEY` in the deployment environment.
- This starter app does not yet include email verification, password reset, role-based permissions, or full CSRF protection. Add these before using it for sensitive institutional records.
- Public signup means anyone can create an account. In this starter version, authenticated users share the same campus data. For real multi-tenant usage, add per-workspace data ownership and authorization before deploying with sensitive data.
- The included campus assistant is rule-based and database-backed, not an external generative AI model.
