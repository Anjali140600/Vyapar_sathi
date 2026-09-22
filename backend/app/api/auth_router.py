from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.security import create_access_token, get_current_user, get_password_hash, verify_password
from backend.app.models.schema import User
from backend.app.schemas.schemas import CurrentUserResponse, UserCreate, UserResponse, Token
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
        password_hash=hashed_password,
        role="owner",
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
    return {
        "accessToken": access_token,
        "tokenType": "bearer",
        "role": user.role,
        "success": True,
    }


@router.get("/me", response_model=CurrentUserResponse)
def current_user_profile(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "fullName": current_user.full_name,
        "role": current_user.role,
        "success": True,
    }

@router.post("/logout")
def logout():
    return {"success": True}
