import os
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.schema import User

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key_needs_to_be_secure_and_long")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

# 🔥 Use Argon2 instead of bcrypt
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
VALID_ROLES = {"owner", "staff", "accountant"}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user or (user.role or "").strip().lower() not in VALID_ROLES:
        raise credentials_exception
    return user


def ensure_role(user: User, allowed_roles: set[str]) -> User:
    """Pure role check shared by FastAPI dependencies and unit tests."""
    role = (user.role or "").strip().lower()
    if role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This action requires one of these roles: {', '.join(sorted(allowed_roles))}",
        )
    return user


def require_roles(*roles: str) -> Callable:
    """Create a FastAPI dependency that permits only the supplied roles."""
    allowed = {role.strip().lower() for role in roles}
    invalid = allowed - VALID_ROLES
    if not allowed or invalid:
        raise ValueError(f"Invalid role configuration: {sorted(invalid)}")

    def role_dependency(current_user: User = Depends(get_current_user)) -> User:
        return ensure_role(current_user, allowed)

    return role_dependency


require_any_business_role = require_roles("owner", "staff", "accountant")
require_finance_role = require_roles("owner", "accountant")
require_owner = require_roles("owner")
