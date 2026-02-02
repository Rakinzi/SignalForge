"""
Authentication utilities and dependencies

Shared auth functions to avoid circular imports.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
JWT_ALG = "HS256"
JWT_EXPIRE_MIN = int(os.getenv("JWT_EXPIRE_MIN", "60"))

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# Scope definitions
SCOPE_FLOWS_READ = "flows:read"
SCOPE_ALERTS_READ = "alerts:read"
SCOPE_ALERTS_ACK = "alerts:ack"
SCOPE_DETECTIONS_READ = "detections:read"
SCOPE_BASELINES_READ = "baselines:read"
SCOPE_AUDIT_READ = "audit:read"
SCOPE_METRICS_READ = "metrics:read"
SCOPE_REPORTS_READ = "reports:read"
SCOPE_CONFIG_READ = "config:read"
SCOPE_SSE_READ = "sse:read"

ROLE_SCOPES: Dict[str, set[str]] = {
    "admin": {
        SCOPE_FLOWS_READ,
        SCOPE_ALERTS_READ,
        SCOPE_ALERTS_ACK,
        SCOPE_DETECTIONS_READ,
        SCOPE_BASELINES_READ,
        SCOPE_AUDIT_READ,
        SCOPE_METRICS_READ,
        SCOPE_REPORTS_READ,
        SCOPE_CONFIG_READ,
        SCOPE_SSE_READ,
    },
    "analyst": {
        SCOPE_FLOWS_READ,
        SCOPE_ALERTS_READ,
        SCOPE_ALERTS_ACK,
        SCOPE_DETECTIONS_READ,
        SCOPE_BASELINES_READ,
        SCOPE_METRICS_READ,
        SCOPE_REPORTS_READ,
        SCOPE_SSE_READ,
    },
    "viewer": {
        SCOPE_FLOWS_READ,
        SCOPE_ALERTS_READ,
        SCOPE_BASELINES_READ,
        SCOPE_METRICS_READ,
        SCOPE_SSE_READ,
    },
}


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, str]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        username = payload.get("sub")
        role = payload.get("role")
        if not username or not role:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")
        return {"username": username, "role": role}
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token") from exc


def require_role(*roles: str):
    def checker(user: Dict[str, str] = Depends(get_current_user)) -> Dict[str, str]:
        if user["role"] not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        return user

    return checker


def require_scope(scope: str):
    def checker(user: Dict[str, str] = Depends(get_current_user)) -> Dict[str, str]:
        scopes = ROLE_SCOPES.get(user["role"], set())
        if scope not in scopes:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        return user

    return checker
