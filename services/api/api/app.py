import json
import os
import secrets
import time
import asyncio
import uuid
import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Set, AsyncGenerator, Mapping, Any
from urllib.parse import quote

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse, PlainTextResponse
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    func,
    select,
    update,
)

DATABASE_URL = os.getenv("DATABASE_URL", "")
from .auth import (
    JWT_ALG,
    JWT_EXPIRE_MIN,
    JWT_SECRET,
    ROLE_SCOPES,
    SCOPE_ALERTS_ACK,
    SCOPE_ALERTS_READ,
    SCOPE_AUDIT_READ,
    SCOPE_BASELINES_READ,
    SCOPE_CONFIG_READ,
    SCOPE_DETECTIONS_READ,
    SCOPE_FLOWS_READ,
    SCOPE_METRICS_READ,
    SCOPE_REPORTS_READ,
    SCOPE_SSE_READ,
    get_current_user,
    pwd_context,
    require_role,
    require_scope,
    verify_password,
)
from .auth_email import EmailService, build_reset_email, build_verification_email

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL must be set")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
metadata = MetaData()

flows = Table(
    "flows",
    metadata,
    Column("id", String, primary_key=True),
    Column("start_time", DateTime, nullable=False),
    Column("end_time", DateTime, nullable=False),
    Column("src_ip", String, nullable=False),
    Column("dst_ip", String, nullable=False),
    Column("src_port", Integer, nullable=False),
    Column("dst_port", Integer, nullable=False),
    Column("protocol", String, nullable=False),
    Column("packet_count", Integer, nullable=False),
    Column("byte_count", Integer, nullable=False),
    Column("duration_ms", Integer, nullable=False),
    Column("packet_rate", Float, nullable=False),
    Column("fwd_packets", Integer, nullable=False),
    Column("bwd_packets", Integer, nullable=False),
    Column("fwd_bytes", Integer, nullable=False),
    Column("bwd_bytes", Integer, nullable=False),
    Column("raw", Text, nullable=False),
)

detections = Table(
    "detections",
    metadata,
    Column("id", String, primary_key=True),
    Column("flow_id", String, nullable=False),
    Column("created_at", DateTime, nullable=False),
    Column("rules_triggered", Text, nullable=False),
    Column("anomaly_score", Float, nullable=False),
    Column("baseline", Text, nullable=False),
    Column("explanation", Text, nullable=False),
)

alerts = Table(
    "alerts",
    metadata,
    Column("id", String, primary_key=True),
    Column("detection_id", String, nullable=False),
    Column("created_at", DateTime, nullable=False),
    Column("severity", String, nullable=False),
    Column("status", String, nullable=False),
    Column("summary", Text, nullable=False),
)

baselines = Table(
    "baselines",
    metadata,
    Column("id", String, primary_key=True),
    Column("key", String, nullable=False),
    Column("count", Integer, nullable=False),
    Column("mean", Float, nullable=False),
    Column("m2", Float, nullable=False),
    Column("ewma", Float, nullable=False),
    Column("updated_at", DateTime, nullable=False),
)

audit_logs = Table(
    "audit_logs",
    metadata,
    Column("id", String, primary_key=True),
    Column("event", String, nullable=False),
    Column("actor", String, nullable=False),
    Column("occurred_at", DateTime, nullable=False),
    Column("metadata", Text, nullable=False),
)

evaluations = Table(
    "evaluations",
    metadata,
    Column("id", String, primary_key=True),
    Column("created_at", DateTime, nullable=False),
    Column("flow_count", Integer, nullable=False),
    Column("alert_count", Integer, nullable=False),
    Column("high_severity", Integer, nullable=False),
    Column("notes", Text, nullable=False),
)

detection_jobs = Table(
    "detection_jobs",
    metadata,
    Column("id", String, primary_key=True),
    Column("created_at", DateTime, nullable=False),
    Column("actor", String, nullable=False),
    Column("job_type", String, nullable=False),
    Column("status", String, nullable=False),
    Column("input_meta", Text, nullable=False),
    Column("result_json", Text, nullable=True),
    Column("error", Text, nullable=True),
)

users = Table(
    "users",
    metadata,
    Column("id", String, primary_key=True),
    Column("username", String, nullable=False, unique=True),
    Column("email", String, nullable=False, unique=True),
    Column("hashed_password", String, nullable=False),
    Column("role", String, nullable=False),
    Column("is_active", Integer, nullable=False, default=1),
    Column("created_at", DateTime, nullable=False),
)

auth_tokens = Table(
    "auth_tokens",
    metadata,
    Column("id", String, primary_key=True),
    Column("user_id", String, nullable=False),
    Column("email", String, nullable=False),
    Column("purpose", String, nullable=False),  # verify_email | reset_password
    Column("token", String, nullable=False, unique=True),
    Column("expires_at", DateTime, nullable=False),
    Column("used_at", DateTime, nullable=True),
    Column("created_at", DateTime, nullable=False),
)

user_security = Table(
    "user_security",
    metadata,
    Column("user_id", String, primary_key=True),
    Column("email_verified", Integer, nullable=False, default=0),
    Column("verified_at", DateTime, nullable=True),
    Column("updated_at", DateTime, nullable=False),
)

metadata.create_all(engine)

app = FastAPI(title="SignalForge API")
START_TIME = time.time()

# Include detection endpoints
from .detection_endpoints import router as detection_router
app.include_router(detection_router)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.time()
    response = await call_next(request)
    duration_ms = int((time.time() - start) * 1000)
    response.headers["X-Request-Id"] = request_id
    log_json(
        "api_request",
        {
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
            "request_id": request_id,
        },
    )
    return response


def build_users() -> Dict[str, Dict[str, str]]:
    users = {}
    for username, role, env in [
        ("admin", "admin", "ADMIN_PASSWORD"),
        ("analyst", "analyst", "ANALYST_PASSWORD"),
        ("viewer", "viewer", "VIEWER_PASSWORD"),
    ]:
        password = os.getenv(env, username)
        users[username] = {
            "username": username,
            "hashed_password": pwd_context.hash(password),
            "role": role,
        }
    return users


USERS = build_users()
email_service = EmailService()
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:8089").rstrip("/")
AUTH_REQUIRE_EMAIL_VERIFIED = os.getenv("AUTH_REQUIRE_EMAIL_VERIFIED", "false").lower() == "true"




def authenticate_user(username: str, password: str) -> Optional[Dict[str, str]]:
    # Try database first
    user = get_user_from_db(username)
    if user and verify_password(password, user["hashed_password"]):
        return {"username": user["username"], "role": user["role"]}

    # Fall back to hardcoded users (for backwards compatibility)
    user = USERS.get(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user


def create_access_token(data: Dict[str, str], expires_delta: timedelta) -> str:
    expire = datetime.now(timezone.utc) + expires_delta
    payload: Dict[str, object] = {**data, "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    with engine.begin() as conn:
        row = conn.execute(select(users).where(users.c.email == email)).mappings().first()
        if row:
            return dict(row)
    return None


def is_email_verified(user_id: str) -> bool:
    with engine.begin() as conn:
        row = conn.execute(select(user_security).where(user_security.c.user_id == user_id)).mappings().first()
        if not row:
            return False
        return bool(row["email_verified"])


def mark_email_verified(user_id: str) -> None:
    with engine.begin() as conn:
        existing = conn.execute(
            select(user_security).where(user_security.c.user_id == user_id)
        ).mappings().first()
        now = datetime.now(timezone.utc)
        if existing:
            conn.execute(
                update(user_security)
                .where(user_security.c.user_id == user_id)
                .values(email_verified=1, verified_at=now, updated_at=now)
            )
        else:
            conn.execute(
                user_security.insert().values(
                    user_id=user_id,
                    email_verified=1,
                    verified_at=now,
                    updated_at=now,
                )
            )


def create_auth_token_record(
    user_id: str,
    email: str,
    purpose: str,
    expires_in_minutes: int,
) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    with engine.begin() as conn:
        conn.execute(
            auth_tokens.insert().values(
                id=f"tok-{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                email=email,
                purpose=purpose,
                token=token,
                expires_at=now + timedelta(minutes=expires_in_minutes),
                used_at=None,
                created_at=now,
            )
        )
    return token


def consume_auth_token(token: str, purpose: str) -> Optional[Dict[str, Any]]:
    now = datetime.now(timezone.utc)
    with engine.begin() as conn:
        row = conn.execute(
            select(auth_tokens).where(
                (auth_tokens.c.token == token)
                & (auth_tokens.c.purpose == purpose)
                & (auth_tokens.c.used_at.is_(None))
            )
        ).mappings().first()
        if not row:
            return None
        if row["expires_at"] < now:
            return None

        conn.execute(
            update(auth_tokens)
            .where(auth_tokens.c.id == row["id"])
            .values(used_at=now)
        )
        return dict(row)


def send_verification_email(username: str, email: str, token: str) -> tuple[bool, str]:
    verify_url = f"{FRONTEND_BASE_URL}/verify-email?token={quote(token)}"
    subject, html, text = build_verification_email(username=username, verify_url=verify_url)
    return email_service.send_email(to_email=email, subject=subject, html_body=html, text_body=text)


def send_password_reset_email(username: str, email: str, token: str) -> tuple[bool, str]:
    reset_url = f"{FRONTEND_BASE_URL}/reset-password?token={quote(token)}"
    subject, html, text = build_reset_email(username=username, reset_url=reset_url)
    return email_service.send_email(to_email=email, subject=subject, html_body=html, text_body=text)




@app.post("/auth/token")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        write_audit(
            event="auth_failed",
            actor=form_data.username,
            metadata={"reason": "invalid_credentials"},
            request_id=get_request_id(request),
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")

    if AUTH_REQUIRE_EMAIL_VERIFIED:
        db_user = get_user_from_db(user["username"])
        if db_user and not is_email_verified(db_user["id"]):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="email_not_verified")

    token = create_access_token(
        {"sub": user["username"], "role": user["role"]},
        expires_delta=timedelta(minutes=JWT_EXPIRE_MIN),
    )
    write_audit(
        event="auth_token_issued",
        actor=user["username"],
        metadata={"role": user["role"]},
        request_id=get_request_id(request),
    )
    return {"access_token": token, "token_type": "bearer"}


@app.post("/auth/register")
def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form("viewer"),
):
    """Register a new user"""
    # Validate role
    if role not in ROLE_SCOPES:
        raise HTTPException(status_code=400, detail="invalid_role")

    # Check if username or email already exists
    with engine.begin() as conn:
        existing = conn.execute(
            select(users).where((users.c.username == username) | (users.c.email == email))
        ).first()

        if existing:
            raise HTTPException(status_code=400, detail="user_already_exists")

        # Create user
        user_id = f"user-{int(time.time() * 1000)}"
        hashed_password = pwd_context.hash(password)

        conn.execute(
            users.insert().values(
                id=user_id,
                username=username,
                email=email,
                hashed_password=hashed_password,
                role=role,
                is_active=1,
                created_at=datetime.now(timezone.utc),
            )
        )
        conn.execute(
            user_security.insert().values(
                user_id=user_id,
                email_verified=0,
                verified_at=None,
                updated_at=datetime.now(timezone.utc),
            )
        )

    verify_token = create_auth_token_record(
        user_id=user_id,
        email=email,
        purpose="verify_email",
        expires_in_minutes=60 * 24,
    )
    email_sent, email_status = send_verification_email(username=username, email=email, token=verify_token)

    write_audit(
        event="user_registered",
        actor=username,
        metadata={"role": role, "email": email, "verification_email_sent": email_sent, "email_status": email_status},
        request_id=get_request_id(request),
    )

    return {
        "status": "registered",
        "username": username,
        "role": role,
        "verification_email_sent": email_sent,
        "email_delivery_status": email_status,
    }


@app.get("/auth/verify-email")
def verify_email(token: str, request: Request):
    token_data = consume_auth_token(token=token, purpose="verify_email")
    if not token_data:
        raise HTTPException(status_code=400, detail="invalid_or_expired_token")

    mark_email_verified(token_data["user_id"])
    write_audit(
        event="email_verified",
        actor=token_data["email"],
        metadata={"user_id": token_data["user_id"]},
        request_id=get_request_id(request),
    )
    return {"status": "verified"}


@app.post("/auth/resend-verification")
def resend_verification(request: Request, email: str = Form(...)):
    user = get_user_by_email(email)
    if not user:
        return {"status": "ok"}

    if is_email_verified(user["id"]):
        return {"status": "already_verified"}

    token = create_auth_token_record(
        user_id=user["id"],
        email=user["email"],
        purpose="verify_email",
        expires_in_minutes=60 * 24,
    )
    email_sent, email_status = send_verification_email(username=user["username"], email=user["email"], token=token)
    write_audit(
        event="verification_resent",
        actor=user["username"],
        metadata={"email": user["email"], "email_sent": email_sent, "email_status": email_status},
        request_id=get_request_id(request),
    )
    return {"status": "sent" if email_sent else "queued", "email_delivery_status": email_status}


@app.post("/auth/forgot-password")
def forgot_password(request: Request, email: str = Form(...)):
    user = get_user_by_email(email)
    if user:
        token = create_auth_token_record(
            user_id=user["id"],
            email=user["email"],
            purpose="reset_password",
            expires_in_minutes=30,
        )
        email_sent, email_status = send_password_reset_email(
            username=user["username"],
            email=user["email"],
            token=token,
        )
        write_audit(
            event="password_reset_requested",
            actor=user["username"],
            metadata={"email_sent": email_sent, "email_status": email_status},
            request_id=get_request_id(request),
        )

    # Don't leak user existence.
    return {"status": "ok"}


@app.post("/auth/reset-password")
def reset_password(request: Request, token: str = Form(...), new_password: str = Form(...)):
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="password_too_short")

    token_data = consume_auth_token(token=token, purpose="reset_password")
    if not token_data:
        raise HTTPException(status_code=400, detail="invalid_or_expired_token")

    with engine.begin() as conn:
        conn.execute(
            update(users)
            .where(users.c.id == token_data["user_id"])
            .values(hashed_password=pwd_context.hash(new_password))
        )

    write_audit(
        event="password_reset_completed",
        actor=token_data["email"],
        metadata={"user_id": token_data["user_id"]},
        request_id=get_request_id(request),
    )
    return {"status": "password_updated"}


def get_user_from_db(username: str) -> Optional[Dict[str, Any]]:
    """Get user from database"""
    with engine.begin() as conn:
        row = conn.execute(
            select(users).where(users.c.username == username)
        ).mappings().first()

        if row:
            return dict(row)
    return None


@app.get("/auth/me")
def me(user: Dict[str, str] = Depends(get_current_user)):
    db_user = get_user_from_db(user["username"])
    if not db_user:
        return user
    return {
        **user,
        "email": db_user["email"],
        "is_email_verified": is_email_verified(db_user["id"]),
    }


@app.get("/scopes")
def scopes(user: Dict[str, str] = Depends(get_current_user)):
    return {
        "role": user["role"],
        "scopes": sorted(ROLE_SCOPES.get(user["role"], set())),
    }


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@app.get("/ready")
def ready():
    return {"status": "ready"}


@app.get("/version")
def version():
    return {"version": "0.1.0"}


@app.get("/flows")
def list_flows(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    cursor: Optional[str] = None,
    src_ip: Optional[str] = None,
    dst_ip: Optional[str] = None,
    protocol: Optional[str] = None,
    min_rate: Optional[float] = None,
    max_rate: Optional[float] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    user: Dict[str, str] = Depends(require_scope(SCOPE_FLOWS_READ)),
):
    filters = []
    if src_ip:
        filters.append(flows.c.src_ip == src_ip)
    if dst_ip:
        filters.append(flows.c.dst_ip == dst_ip)
    if protocol:
        filters.append(flows.c.protocol == protocol)
    if min_rate is not None:
        filters.append(flows.c.packet_rate >= min_rate)
    if max_rate is not None:
        filters.append(flows.c.packet_rate <= max_rate)
    if start_time:
        filters.append(flows.c.start_time >= parse_time(start_time))
    if end_time:
        filters.append(flows.c.end_time <= parse_time(end_time))
    if cursor:
        filters.append(flows.c.end_time < parse_time(cursor))

    with engine.begin() as conn:
        total = None
        if not cursor:
            total = conn.execute(select(func.count()).select_from(flows).where(*filters)).scalar_one()
        rows = (
            conn.execute(
                select(flows).where(*filters).order_by(flows.c.end_time.desc()).limit(limit).offset(0 if cursor else offset)
            )
            .mappings()
            .all()
        )
    next_cursor = rows[-1]["end_time"].isoformat() if rows else None
    write_audit(
        event="flows_read",
        actor=user["username"],
        metadata={"count": len(rows)},
        request_id=get_request_id(request),
    )
    return {
        "items": list(rows),
        "limit": limit,
        "offset": 0 if cursor else offset,
        "cursor": cursor,
        "next_cursor": next_cursor,
        "total": total,
    }


@app.get("/flows/{flow_id}")
def get_flow(request: Request, flow_id: str, user: Dict[str, str] = Depends(require_scope(SCOPE_FLOWS_READ))):
    with engine.begin() as conn:
        row = conn.execute(select(flows).where(flows.c.id == flow_id)).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="flow_not_found")
    write_audit(
        event="flow_read",
        actor=user["username"],
        metadata={"flow_id": flow_id},
        request_id=get_request_id(request),
    )
    return row


@app.get("/alerts")
def list_alerts(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    cursor: Optional[str] = None,
    severity: Optional[str] = None,
    status_filter: Optional[str] = None,
    user: Dict[str, str] = Depends(require_scope(SCOPE_ALERTS_READ)),
):
    filters = []
    if severity:
        filters.append(alerts.c.severity == severity)
    if status_filter:
        filters.append(alerts.c.status == status_filter)
    if cursor:
        filters.append(alerts.c.created_at < parse_time(cursor))
    with engine.begin() as conn:
        total = None
        if not cursor:
            total = conn.execute(select(func.count()).select_from(alerts).where(*filters)).scalar_one()
        rows = (
            conn.execute(
                select(alerts).where(*filters).order_by(alerts.c.created_at.desc()).limit(limit).offset(0 if cursor else offset)
            )
            .mappings()
            .all()
        )
    next_cursor = rows[-1]["created_at"].isoformat() if rows else None
    write_audit(
        event="alerts_read",
        actor=user["username"],
        metadata={"count": len(rows)},
        request_id=get_request_id(request),
    )
    return {
        "items": list(rows),
        "limit": limit,
        "offset": 0 if cursor else offset,
        "cursor": cursor,
        "next_cursor": next_cursor,
        "total": total,
    }


@app.post("/alerts/{alert_id}/ack")
def ack_alert(request: Request, alert_id: str, user: Dict[str, str] = Depends(require_scope(SCOPE_ALERTS_ACK))):
    with engine.begin() as conn:
        res = conn.execute(update(alerts).where(alerts.c.id == alert_id).values(status="acknowledged"))
    if res.rowcount == 0:
        raise HTTPException(status_code=404, detail="alert_not_found")
    write_audit(
        event="alert_ack",
        actor=user["username"],
        metadata={"alert_id": alert_id},
        request_id=get_request_id(request),
    )
    return {"status": "acknowledged", "alert_id": alert_id}


@app.get("/detections")
def list_detections(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    cursor: Optional[str] = None,
    flow_id: Optional[str] = None,
    min_score: Optional[float] = None,
    user: Dict[str, str] = Depends(require_scope(SCOPE_DETECTIONS_READ)),
):
    filters = []
    if flow_id:
        filters.append(detections.c.flow_id == flow_id)
    if min_score is not None:
        filters.append(detections.c.anomaly_score >= min_score)
    if cursor:
        filters.append(detections.c.created_at < parse_time(cursor))

    with engine.begin() as conn:
        total = None
        if not cursor:
            total = conn.execute(select(func.count()).select_from(detections).where(*filters)).scalar_one()
        rows = (
            conn.execute(
                select(detections).where(*filters).order_by(detections.c.created_at.desc()).limit(limit).offset(
                    0 if cursor else offset
                )
            )
            .mappings()
            .all()
        )
    next_cursor = rows[-1]["created_at"].isoformat() if rows else None
    write_audit(
        event="detections_read",
        actor=user["username"],
        metadata={"count": len(rows)},
        request_id=get_request_id(request),
    )
    return {
        "items": list(rows),
        "limit": limit,
        "offset": 0 if cursor else offset,
        "cursor": cursor,
        "next_cursor": next_cursor,
        "total": total,
    }


@app.get("/baselines")
def list_baselines(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    cursor: Optional[str] = None,
    entity_type: Optional[str] = None,
    min_confidence: Optional[float] = None,
    user: Dict[str, str] = Depends(require_scope(SCOPE_BASELINES_READ)),
):
    filters = []
    if cursor:
        filters.append(baselines.c.updated_at < parse_time(cursor))
    if entity_type:
        if entity_type == "ip":
            filters.append(baselines.c.key.like("dst:%"))
        else:
            filters.append(baselines.c.key.like(f"{entity_type}:%"))

    with engine.begin() as conn:
        total = None
        if not cursor:
            total = conn.execute(select(func.count()).select_from(baselines).where(*filters)).scalar_one()
        rows = (
            conn.execute(
                select(baselines).where(*filters).order_by(baselines.c.updated_at.desc()).limit(limit).offset(
                    0 if cursor else offset
                )
            )
            .mappings()
            .all()
        )

    items = []
    for row in rows:
        entity_id, inferred_type = parse_baseline_key(row["key"])
        confidence = min(row["count"] / 100.0, 1.0)
        if min_confidence is not None and confidence < min_confidence:
            continue
        items.append(
            {
                "entity_id": entity_id,
                "entity_type": inferred_type,
                "avg_packet_rate": row["mean"],
                "avg_byte_rate": row["ewma"],
                "connection_count": row["count"],
                "last_seen": row["updated_at"].isoformat(),
                "baseline_confidence": confidence,
            }
        )

    next_cursor = rows[-1]["updated_at"].isoformat() if rows else None
    write_audit(
        event="baselines_read",
        actor=user["username"],
        metadata={"count": len(items)},
        request_id=get_request_id(request),
    )
    return {
        "items": items,
        "limit": limit,
        "offset": 0 if cursor else offset,
        "cursor": cursor,
        "next_cursor": next_cursor,
        "total": total,
    }


@app.get("/audit")
def list_audit_logs(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    cursor: Optional[str] = None,
    event: Optional[str] = None,
    actor: Optional[str] = None,
    user: Dict[str, str] = Depends(require_scope(SCOPE_AUDIT_READ)),
):
    filters = []
    if event:
        filters.append(audit_logs.c.event == event)
    if actor:
        filters.append(audit_logs.c.actor == actor)
    if cursor:
        filters.append(audit_logs.c.occurred_at < parse_time(cursor))

    with engine.begin() as conn:
        total = None
        if not cursor:
            total = conn.execute(select(func.count()).select_from(audit_logs).where(*filters)).scalar_one()
        rows = (
            conn.execute(
                select(audit_logs)
                .where(*filters)
                .order_by(audit_logs.c.occurred_at.desc())
                .limit(limit)
                .offset(0 if cursor else offset)
            )
            .mappings()
            .all()
        )
    next_cursor = rows[-1]["occurred_at"].isoformat() if rows else None
    write_audit(
        event="audit_read",
        actor=user["username"],
        metadata={"count": len(rows)},
        request_id=get_request_id(request),
    )
    return {
        "items": list(rows),
        "limit": limit,
        "offset": 0 if cursor else offset,
        "cursor": cursor,
        "next_cursor": next_cursor,
        "total": total,
    }


@app.get("/audit/export")
def export_audit_logs(
    request: Request,
    format: str = "jsonl",
    limit: int = 5000,
    event: Optional[str] = None,
    actor: Optional[str] = None,
    user: Dict[str, str] = Depends(require_scope(SCOPE_AUDIT_READ)),
):
    filters = []
    if event:
        filters.append(audit_logs.c.event == event)
    if actor:
        filters.append(audit_logs.c.actor == actor)

    with engine.begin() as conn:
        rows = (
            conn.execute(
                select(audit_logs)
                .where(*filters)
                .order_by(audit_logs.c.occurred_at.desc())
                .limit(limit)
            )
            .mappings()
            .all()
        )

    write_audit(
        event="audit_export",
        actor=user["username"],
        metadata={"format": format, "rows": len(rows)},
        request_id=get_request_id(request),
    )

    if format == "csv":
        buffer = io.StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=["id", "event", "actor", "occurred_at", "metadata"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "id": row["id"],
                    "event": row["event"],
                    "actor": row["actor"],
                    "occurred_at": row["occurred_at"].isoformat(),
                    "metadata": row["metadata"],
                }
            )
        return PlainTextResponse(
            content=buffer.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="audit_logs.csv"'},
        )

    # Default JSONL for offline analysis pipelines.
    lines = []
    for row in rows:
        lines.append(
            json.dumps(
                {
                    "id": row["id"],
                    "event": row["event"],
                    "actor": row["actor"],
                    "occurred_at": row["occurred_at"].isoformat(),
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                }
            )
        )
    return PlainTextResponse(
        content="\n".join(lines) + ("\n" if lines else ""),
        media_type="application/x-ndjson",
        headers={"Content-Disposition": 'attachment; filename="audit_logs.jsonl"'},
    )


@app.get("/metrics")
def metrics(request: Request, user: Dict[str, str] = Depends(require_scope(SCOPE_METRICS_READ))):
    now = datetime.now(timezone.utc)
    window_seconds = int(os.getenv("METRICS_WINDOW_SEC", "60"))
    with engine.begin() as conn:
        flow_count = conn.execute(select(func.count()).select_from(flows)).scalar_one()
        alert_count = conn.execute(select(func.count()).select_from(alerts)).scalar_one()
        open_alerts = conn.execute(select(func.count()).select_from(alerts).where(alerts.c.status == "open")).scalar_one()
        recent_flows = conn.execute(
            select(func.count())
            .select_from(flows)
            .where(flows.c.end_time >= now - timedelta(seconds=window_seconds))
        ).scalar_one()
        recent_bytes = conn.execute(
            select(func.coalesce(func.sum(flows.c.byte_count), 0))
            .select_from(flows)
            .where(flows.c.end_time >= now - timedelta(seconds=window_seconds))
        ).scalar_one()
        recent_packets = conn.execute(
            select(func.coalesce(func.sum(flows.c.packet_count), 0))
            .select_from(flows)
            .where(flows.c.end_time >= now - timedelta(seconds=window_seconds))
        ).scalar_one()
        last_eval = conn.execute(
            select(evaluations).order_by(evaluations.c.created_at.desc()).limit(1)
        ).mappings().first()
    write_audit(
        event="metrics_access",
        actor=user["username"],
        metadata={"role": user["role"]},
        request_id=get_request_id(request),
    )
    # True ingest is traffic volume rate (bytes/s), distinct from flow throughput.
    ingest_rate = float(recent_bytes) / max(window_seconds, 1)
    flows_per_second = recent_flows / max(window_seconds, 1)
    packets_per_second = float(recent_packets) / max(window_seconds, 1)
    uptime_seconds = int(time.time() - START_TIME)
    return {
        "status": "healthy",
        "ingest_rate": ingest_rate,
        "flows_per_second": flows_per_second,
        "packets_per_second": packets_per_second,
        "alerts_count": open_alerts,
        "latency_ms": 0.0,
        "uptime_seconds": uptime_seconds,
        "flows_total": flow_count,
        "alerts_total": alert_count,
        "alerts_open": open_alerts,
        "latest_evaluation": last_eval,
    }


@app.get("/reports")
def reports(request: Request, user: Dict[str, str] = Depends(require_scope(SCOPE_REPORTS_READ))):
    with engine.begin() as conn:
        rows = conn.execute(
            select(detections.c.rules_triggered, func.count()).group_by(detections.c.rules_triggered)
        ).all()
        latest_eval = conn.execute(
            select(evaluations).order_by(evaluations.c.created_at.desc()).limit(1)
        ).mappings().first()
        latest_job = conn.execute(
            select(detection_jobs)
            .where(
                detection_jobs.c.job_type == "analyze",
                detection_jobs.c.status == "completed",
                detection_jobs.c.result_json.isnot(None),
            )
            .order_by(detection_jobs.c.created_at.desc())
            .limit(1)
        ).mappings().first()
    metrics_payload = build_evaluation_metrics(dict(latest_eval) if latest_eval else None)
    if metrics_payload is None and latest_job:
        metrics_payload = build_evaluation_metrics_from_job(dict(latest_job))
    write_audit(
        event="reports_access",
        actor=user["username"],
        metadata={"role": user["role"]},
        request_id=get_request_id(request),
    )
    return {
        "by_rule": [{"rules": r[0], "count": r[1]} for r in rows],
        "latest_evaluation": latest_eval,
        "evaluation_metrics": metrics_payload,
    }


@app.get("/config")
def config(request: Request, user: Dict[str, str] = Depends(require_scope(SCOPE_CONFIG_READ))):
    write_audit(
        event="config_access",
        actor=user["username"],
        metadata={"role": user["role"]},
        request_id=get_request_id(request),
    )
    return {
        "bus": "redis-streams",
        "auth": "jwt",
        "detector_enabled": True,
        "rules_version": os.getenv("RULES_VERSION", "1.0.0"),
        "baseline_window_hours": int(os.getenv("BASELINE_WINDOW_HOURS", "24")),
        "alert_threshold": float(os.getenv("ALERT_THRESHOLD", "0.75")),
        "capture_interface": os.getenv("CAPTURE_INTERFACE", "eth0"),
    }


@app.get("/stream/alerts")
def stream_alerts(request: Request, token: Optional[str] = None, authorization: Optional[str] = None):
    jwt_token = token
    if not jwt_token and authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            jwt_token = parts[1]
    if not jwt_token:
        raise HTTPException(status_code=401, detail="missing_token")

    user = get_current_user(jwt_token)
    if SCOPE_SSE_READ not in ROLE_SCOPES.get(user["role"], set()):
        raise HTTPException(status_code=403, detail="forbidden")
    write_audit(
        event="alerts_stream_open",
        actor=user["username"],
        metadata={"role": user["role"]},
        request_id=get_request_id(request),
    )

    async def event_stream() -> AsyncGenerator[bytes, None]:
        last_sent = None
        while True:
            if await request.is_disconnected():
                break
            with engine.begin() as conn:
                row = conn.execute(
                    select(alerts).order_by(alerts.c.created_at.desc()).limit(1)
                ).mappings().first()
            if row and row.get("id") != last_sent:
                last_sent = row.get("id")
                payload = json.dumps({"event": "alert", "data": jsonable_encoder(dict(row))})
                yield f"data: {payload}\n\n".encode("utf-8")
            else:
                yield b": keep-alive\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def write_audit(event: str, actor: str, metadata: dict, request_id: Optional[str] = None) -> None:
    payload = dict(metadata)
    if request_id:
        payload["request_id"] = request_id
    with engine.begin() as conn:
        conn.execute(
            audit_logs.insert().values(
                id=f"audit-{int(time.time() * 1000)}",
                event=event,
                actor=actor,
                occurred_at=datetime.now(timezone.utc),
                metadata=json.dumps(payload),
            )
        )


def log_json(event: str, fields: dict) -> None:
    payload = {"event": event, "ts": datetime.now(timezone.utc).isoformat()}
    payload.update(fields)
    print(json.dumps(payload), flush=True)


def get_request_id(request: Request) -> Optional[str]:
    return getattr(request.state, "request_id", None)


def parse_time(ts: str) -> datetime:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid_time_format") from exc


def parse_baseline_key(key: str) -> tuple[str, str]:
    if ":" in key:
        prefix, value = key.split(":", 1)
        if prefix == "dst":
            return value, "ip"
        return value, prefix
    return key, "ip"


def build_evaluation_metrics(latest_eval: Optional[Mapping[str, Any]]) -> Optional[dict]:
    """
    Return measured evaluation metrics only.

    Metrics are extracted from `evaluations.notes` when it contains a JSON payload
    with confusion-matrix counts and derived scores. No synthetic values are generated.
    """
    if not latest_eval:
        return None

    notes = latest_eval.get("notes")
    if not notes:
        return None

    try:
        parsed_notes = json.loads(notes) if isinstance(notes, str) else notes
    except Exception:
        return None

    confusion = parsed_notes.get("confusion_matrix")
    metrics = parsed_notes.get("metrics")
    if not isinstance(confusion, dict) or not isinstance(metrics, dict):
        return None

    required_confusion = [
        "true_positives",
        "false_positives",
        "true_negatives",
        "false_negatives",
    ]
    required_metrics = ["precision", "recall", "f1_score", "accuracy"]

    if not all(key in confusion for key in required_confusion):
        return None
    if not all(key in metrics for key in required_metrics):
        return None

    return {
        "true_positives": int(confusion["true_positives"]),
        "false_positives": int(confusion["false_positives"]),
        "true_negatives": int(confusion["true_negatives"]),
        "false_negatives": int(confusion["false_negatives"]),
        "precision": float(metrics["precision"]),
        "recall": float(metrics["recall"]),
        "f1_score": float(metrics["f1_score"]),
        "accuracy": float(metrics["accuracy"]),
    }


def build_evaluation_metrics_from_job(job_row: Mapping[str, Any]) -> Optional[dict]:
    """
    Extract measured evaluation metrics from a persisted detection job result.
    """
    result_json = job_row.get("result_json")
    if not result_json:
        return None
    try:
        parsed = json.loads(result_json) if isinstance(result_json, str) else result_json
    except Exception:
        return None

    evaluation = parsed.get("evaluation") if isinstance(parsed, dict) else None
    if not isinstance(evaluation, dict):
        return None

    confusion = evaluation.get("confusion_matrix")
    metrics = evaluation.get("metrics")
    if not isinstance(confusion, dict) or not isinstance(metrics, dict):
        return None

    required_confusion = [
        "true_positives",
        "false_positives",
        "true_negatives",
        "false_negatives",
    ]
    required_metrics = ["precision", "recall", "f1_score", "accuracy"]
    if not all(k in confusion for k in required_confusion):
        return None
    if not all(k in metrics for k in required_metrics):
        return None

    return {
        "true_positives": int(confusion["true_positives"]),
        "false_positives": int(confusion["false_positives"]),
        "true_negatives": int(confusion["true_negatives"]),
        "false_negatives": int(confusion["false_negatives"]),
        "precision": float(metrics["precision"]),
        "recall": float(metrics["recall"]),
        "f1_score": float(metrics["f1_score"]),
        "accuracy": float(metrics["accuracy"]),
    }


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))


if __name__ == "__main__":
    main()
