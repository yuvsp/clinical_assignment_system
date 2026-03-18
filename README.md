# Clinical Assignment System

This project is a web application for assigning clinical instructors to students based on their preferred fields and practice areas.

## Setup

1. Clone the repository.
2. Create and activate a virtual environment.
3. Install dependencies with `pip install -r requirements.txt`.
4. Copy `.env.example` to `.env`.
5. Configure Google OAuth for Gmail sending:
   - Create a Google Cloud project.
   - Enable the Gmail API.
   - Configure the OAuth consent screen and add scopes: **Gmail send** and **Gmail metadata** (metadata is required so the app can read the connected account email via `users.getProfile`).
   - Create a Web application OAuth client.
   - Add your callback URL, such as `http://localhost:5000/api/gmail/callback`.
   - Copy the client ID and client secret into `.env`.

## Required environment variables

- `DATABASE_URL`
- `SECRET_KEY`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI`

The app stores the Gmail OAuth token encrypted using `SECRET_KEY`, so keep that value stable across restarts and deployments.

## Usage

1. Run the application.
2. Open the assignments page.
3. Click `חיבור Gmail` and grant consent.
4. Use the `שלח אימייל` button to send the assignment email through Gmail API.

## Notes

- The app no longer uses Gmail SMTP or app passwords for sending mail.
- If the Gmail connection is revoked, reconnect through the assignments page.
- If you change OAuth scopes, disconnect Gmail and connect again so Google re-authorizes.

## Deployment (Koyeb + Supabase)

- **Web:** Deploy as a Koyeb Web Service from GitHub (Buildpack, use the Procfile). Enable Auto-Deploy on your production branch for CD.
- **Database:** Create a Supabase project and use its PostgreSQL connection string as `DATABASE_URL`.
- **Env vars on Koyeb:** Set `DATABASE_URL`, `SECRET_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REDIRECT_URI`. Make sure the redirect URI exactly matches the one registered in Google Cloud.
- **Local:** Use default SQLite, or set `DATABASE_URL` in a `.env` file (e.g. to a Supabase URI for testing).

