import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from google.auth.exceptions import GoogleAuthError
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import (
    GoogleAuthConfigurationError,
    create_access_token,
    get_password_hash,
    verify_google_id_token,
    verify_password,
)
from app.models.schema import User, UserIdentity
from app.schemas.schemas import (
    GoogleAuthResponse,
    GoogleCredential,
    Token,
    UserCreate,
    UserResponse,
)
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/register", response_model=UserResponse)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user_in.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user_in.password)
    new_user = User(
        full_name=user_in.fullName,
        email=user_in.email,
        password_hash=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"id": str(new_user.id), "email": new_user.email, "success": True}

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # form_data.username is the email
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"accessToken": access_token, "tokenType": "bearer", "success": True}


@router.post("/google", response_model=GoogleAuthResponse)
def google_auth(payload: GoogleCredential, db: Session = Depends(get_db)):
    try:
        claims = verify_google_id_token(payload.credential)
    except GoogleAuthConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid Google credential") from exc
    except GoogleAuthError as exc:
        raise HTTPException(
            status_code=503,
            detail="Google authentication is temporarily unavailable",
        ) from exc

    email = str(claims.get("email", "")).strip().lower()
    google_subject = str(claims.get("sub", "")).strip()
    if not email or claims.get("email_verified") is not True:
        raise HTTPException(status_code=401, detail="Google email is not verified")
    if not google_subject:
        raise HTTPException(status_code=401, detail="Google account identifier is missing")

    identity = db.query(UserIdentity).filter(
        UserIdentity.provider == "google",
        UserIdentity.provider_subject == google_subject,
    ).first()

    if identity:
        user = db.query(User).filter(User.id == identity.user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="Google account link is invalid")
        is_new_user = False
    else:
        user = db.query(User).filter(func.lower(User.email) == email).first()
        is_new_user = user is None

    if user and not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    if is_new_user:
        full_name = str(claims.get("name", "")).strip() or email.split("@", 1)[0]
        user = User(
            full_name=full_name[:150],
            email=email,
            password_hash=get_password_hash(secrets.token_urlsafe(32)),
        )
        db.add(user)
        db.flush()

    if not identity:
        db.add(
            UserIdentity(
                user_id=user.id,
                provider="google",
                provider_subject=google_subject,
                email=email,
            )
        )
        db.commit()
        db.refresh(user)

    access_token = create_access_token(data={"sub": str(user.id)})
    return {
        "accessToken": access_token,
        "tokenType": "bearer",
        "success": True,
        "email": user.email,
        "isNewUser": is_new_user,
    }

@router.post("/logout")
def logout():
    return {"success": True}
