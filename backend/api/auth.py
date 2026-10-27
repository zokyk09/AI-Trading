import secrets
from fastapi import Header, HTTPException
from backend.config import settings

def require_api_token(authorization: str | None = Header(default=None)):
    expected = settings.api_token
    supplied = authorization.removeprefix("Bearer ") if authorization else ""
    if expected == "change-me-before-use" or not secrets.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Valid bearer token required")
