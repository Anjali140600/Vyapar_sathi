# Google Authentication Setup

The application uses Google Identity Services in the browser and verifies the
returned ID token in the FastAPI backend. The first successful sign-in links
the local user to Google's stable account identifier in `user_identities`.

## 1. Create a Google Web Client

In Google Cloud Console, configure the OAuth consent screen and create an
OAuth 2.0 Client ID with application type **Web application**.

Add these Authorized JavaScript origins:

```text
http://localhost:5173
http://127.0.0.1:5173
https://transcendent-gaufre-4c2d77.netlify.app
```

Copy the generated client ID. A client secret is not required by this flow.

## 2. Configure the Backend

Add the client ID to the root `.env` file:

```dotenv
GOOGLE_CLIENT_ID=your_google_web_client_id.apps.googleusercontent.com
```

Install dependencies and restart FastAPI:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## 3. Configure the Local Frontend

Create `frontend/.env` and add the same public client ID:

```dotenv
VITE_GOOGLE_CLIENT_ID=your_google_web_client_id.apps.googleusercontent.com
```

Then restart the Vite development server.

```powershell
npm --prefix frontend run dev
```

If FastAPI will serve the built frontend on port 8000, rebuild it after setting
the client ID:

```powershell
npm --prefix frontend run build
```

## 4. Configure Netlify

In the Netlify site's environment variables, set:

```text
VITE_GOOGLE_CLIENT_ID = your Google Web client ID
VITE_API_BASE_URL = your public FastAPI backend origin
```

Redeploy the frontend after changing either build-time environment variable.
