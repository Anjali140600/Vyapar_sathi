# How to Start the Backend

Open PowerShell in the project root:

```text
C:\Users\Anjali\Desktop\Final_vyapar_sathi
```

Activate the virtual environment:

```powershell
.\venv\Scripts\Activate.ps1
```

Start the FastAPI backend:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open the application at:

```text
http://127.0.0.1:8000
```

Keep the PowerShell terminal open while using the application. Make sure the
MySQL service is running before starting the backend.

## If Virtual Environment Activation Is Blocked

Run the backend directly through the virtual environment's Python executable:

```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Press `Ctrl+C` in the terminal when you want to stop the backend.
