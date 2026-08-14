from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth_router, chat_router, multimodal_router, transaction_router
from app.core.database import Base, engine
import os
from pathlib import Path

# Create tables if not exists so a fresh local setup can boot without
# requiring a separate init step before the API becomes usable.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Vyapar Sathi Unified API", version="1.0.0")
BASE_DIR = Path(__file__).resolve().parent.parent
PUBLIC_DIR = BASE_DIR / "frontend" / "public"

ALLOWED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]

# Add deployed frontend origins through a comma-separated environment variable.
# Origins must include the scheme and must not include a trailing slash.
ALLOWED_ORIGINS.extend(
    origin.strip().rstrip("/")
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print(f"DEBUG: 422 Validation Error at {request.url}")
    print(f"DEBUG: Error details: {exc.errors()}")
    # We use await request.json() instead of .body() for prettier printing
    try:
        body = await request.json()
        print(f"DEBUG: Request body: {body}")
    except:
        print("DEBUG: Could not parse body as JSON")
    return JSONResponse(
        status_code=422,
        content={"success": False, "detail": exc.errors()},
    )

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth_router.router)
app.include_router(chat_router.router)
app.include_router(multimodal_router.router)
app.include_router(transaction_router.router)

# Mount Static Files (Frontend)
from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory=str(PUBLIC_DIR), html=True), name="static")

@app.get("/api/health")
def health_check():
    return {"success": True, "message": "Vyapar Sathi Backend is healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
