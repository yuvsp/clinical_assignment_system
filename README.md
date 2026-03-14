# Clinical Assignment System

This project is a web application for assigning clinical instructors to students based on their preferred fields and practice areas.

## Installation

1. Clone the repository
2. Create a virtual environment
3. Install dependencies

## Usage

1. Run the application
2. Access the application in your browser

## Deployment (Koyeb + Supabase)

- **Web:** Deploy as a Koyeb Web Service from GitHub (Buildpack, use the Procfile). Enable Auto-Deploy on your production branch for CD.
- **Database:** Create a Supabase project and use its PostgreSQL connection string as `DATABASE_URL`.
- **Env vars on Koyeb:** Set `DATABASE_URL` (Supabase URI), `SECRET_KEY`, and `FLASK_APP=app:create_app` so the Procfile’s `flask db upgrade` step runs before gunicorn.
- **Local:** Use default SQLite, or set `DATABASE_URL` in a `.env` file (e.g. to a Supabase URI for testing).

## Project Structure

clinical_assignment_system/
|
├── app/
│ ├── init.py
│ ├── models.py
│ ├── routes.py
│ ├── templates/
│ │ ├── base.html
│ │ ├── instructors.html
│ │ ├── students.html
│ │ ├── assign.html
│ └── static/
│ ├── css/
│ │ └── styles.css
│ └── js/
│ └── scripts.js
|
├── venv/
├── config.py
├── run.py
├── requirements.txt
└── README.md

