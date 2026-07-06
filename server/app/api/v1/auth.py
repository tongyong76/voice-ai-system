from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ...core.database import get_db
from ...core.security import verify_password, get_password_hash, create_access_token

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Simple admin user (in production, use database)
ADMIN_USER = {
    "username": "admin",
    "hashed_password": get_password_hash("admin123"),  # Change in production!
}


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    if request.username != ADMIN_USER["username"] or not verify_password(
        request.password, ADMIN_USER["hashed_password"]
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    access_token = create_access_token(data={"sub": request.username})
    return TokenResponse(access_token=access_token)
