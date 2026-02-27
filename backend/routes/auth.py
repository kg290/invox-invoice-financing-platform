"""
Authentication routes — JWT + OTP 2FA.

Flow:
  1. Register → creates User + sends OTP via chosen channel (whatsapp/sms/email)
  2. Verify OTP → returns JWT access + refresh tokens
  3. Login → validates credentials + sends OTP
  4. Verify OTP → returns JWT
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
import bcrypt
import random
import json

from database import get_db
from models import User, Vendor, Lender, Notification, ActivityLog
from services.email_service import email_service

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ── Config ──
SECRET_KEY = "invox-secret-key-change-in-production-2026"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
OTP_EXPIRE_MINUTES = 5


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ═══════════════════════════════════════════════
#  SCHEMAS
# ═══════════════════════════════════════════════

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    email: str = Field(..., min_length=5, max_length=200)
    phone: str = Field(..., min_length=10, max_length=15)
    password: str = Field(..., min_length=6, max_length=100)
    role: str = Field(..., pattern="^(vendor|lender)$")
    otp_channel: str = Field(default="email", pattern="^(whatsapp|sms|email)$")
    # Lender extra fields
    organization: Optional[str] = None
    lender_type: Optional[str] = Field(default="individual")


class LoginRequest(BaseModel):
    email: str
    password: str
    otp_channel: str = Field(default="email", pattern="^(whatsapp|sms|email)$")


class VerifyOTPRequest(BaseModel):
    email: str
    otp: str = Field(..., min_length=6, max_length=6)


class RefreshRequest(BaseModel):
    refresh_token: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    role: str
    vendor_id: Optional[int] = None
    lender_id: Optional[int] = None
    is_verified: bool
    created_at: Optional[str] = None


# ═══════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════

def generate_otp() -> str:
    """Generate a 6-digit OTP."""
    return str(random.randint(100000, 999999))


def send_otp(phone: str, email: str, otp: str, channel: str, user_name: str = "User"):
    """
    Send OTP via the chosen channel.
    - Email: sends a branded HTML email via Gmail API
    - WhatsApp/SMS: console log (future integration)
    Always logs to console as backup.
    """
    channel_icons = {"whatsapp": "📱 WhatsApp", "sms": "💬 SMS", "email": "📧 Email"}
    target = phone if channel in ("whatsapp", "sms") else email

    # Console log (always, as backup/debug)
    print(f"\n{'='*50}")
    print(f"  🔐 OTP SENT via {channel_icons.get(channel, channel)}")
    print(f"  To: {target}")
    print(f"  OTP: {otp}")
    print(f"  Expires in {OTP_EXPIRE_MINUTES} minutes")
    print(f"{'='*50}\n")

    # Real email delivery via Gmail API
    if channel == "email" and email:
        try:
            sent = email_service.send_otp_email(to=email, otp=otp, user_name=user_name)
            if sent:
                print(f"  ✅ OTP email delivered to {email}")
            else:
                print(f"  ⚠️  Gmail send returned False — OTP logged above")
        except Exception as exc:
            print(f"  ❌ Gmail error: {exc} — OTP logged above")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> User:
    """Dependency to extract current user from JWT Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token expired or invalid")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


def user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
        "vendor_id": user.vendor_id,
        "lender_id": user.lender_id,
        "is_verified": user.is_verified,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def log_activity(db: Session, entity_type: str, entity_id: int, action: str, description: str, user_id: int = None, metadata: dict = None):
    entry = ActivityLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        description=description,
        user_id=user_id,
        metadata_json=json.dumps(metadata) if metadata else None,
    )
    db.add(entry)


# ═══════════════════════════════════════════════
#  REGISTER
# ═══════════════════════════════════════════════

@router.post("/register", status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user account. Sends OTP for verification."""
    # Check duplicate email
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash password
    password_hash = _hash_password(data.password)

    # Create user
    user = User(
        name=data.name,
        email=data.email,
        phone=data.phone,
        password_hash=password_hash,
        role=data.role,
        otp_channel=data.otp_channel,
        is_verified=False,
    )

    # For lenders, create linked Lender record
    if data.role == "lender":
        lender = Lender(
            name=data.name,
            email=data.email,
            phone=data.phone,
            organization=data.organization,
            lender_type=data.lender_type or "individual",
        )
        db.add(lender)
        db.flush()  # Get lender.id
        user.lender_id = lender.id

    db.add(user)
    db.flush()

    # Generate & send OTP
    otp = generate_otp()
    user.otp_code = otp
    user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)
    send_otp(data.phone, data.email, otp, data.otp_channel, user_name=data.name)

    # Log activity
    log_activity(db, "user", user.id, "register", f"New {data.role} account registered: {data.name}", user.id)

    # Create welcome notification
    notif = Notification(
        user_id=user.id,
        title="Welcome to InvoX!",
        message=f"Your {data.role} account has been created. Complete OTP verification to get started.",
        notification_type="system",
        link=f"/verify-otp",
    )
    db.add(notif)
    db.commit()
    db.refresh(user)

    return {
        "message": f"OTP sent via {data.otp_channel}",
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
        "otp_channel": data.otp_channel,
        "debug_otp": otp,  # ⚠️ Remove in production — shown for demo only
    }


# ═══════════════════════════════════════════════
#  LOGIN (step 1 — credentials + send OTP)
# ═══════════════════════════════════════════════

@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """Step 1: Validate email + password, then send OTP for 2FA."""
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not _verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    # Generate OTP for 2FA
    otp = generate_otp()
    user.otp_code = otp
    user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)
    user.otp_channel = data.otp_channel

    send_otp(user.phone or "", user.email, otp, data.otp_channel, user_name=user.name)

    log_activity(db, "user", user.id, "login_attempt", f"Login attempt — OTP sent via {data.otp_channel}", user.id)

    db.commit()

    # ── Demo accounts: auto-verify and return tokens directly ──
    if user.email.endswith("@invox.demo"):
        # Auto-link vendor/lender if needed
        if user.role == "vendor" and user.vendor_id is None:
            vendor = db.query(Vendor).filter(Vendor.email == user.email).first()
            if vendor:
                user.vendor_id = vendor.id
        elif user.role == "lender" and user.lender_id is None:
            lender = db.query(Lender).filter(Lender.email == user.email).first()
            if lender:
                user.lender_id = lender.id

        user.otp_code = None
        user.otp_expires_at = None
        user.is_verified = True
        token_data = {"sub": str(user.id), "role": user.role, "email": user.email}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        log_activity(db, "user", user.id, "demo_login", f"Demo auto-login as {user.role}", user.id)
        db.commit()
        return {
            "message": "Demo login — OTP skipped",
            "email": user.email,
            "otp_channel": data.otp_channel,
            "debug_otp": otp,
            "auto_verified": True,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": user_to_dict(user),
        }

    return {
        "message": f"OTP sent via {data.otp_channel}",
        "email": user.email,
        "otp_channel": data.otp_channel,
        "debug_otp": otp,  # ⚠️ Remove in production
    }


# ═══════════════════════════════════════════════
#  VERIFY OTP (step 2 — returns JWT)
# ═══════════════════════════════════════════════

@router.post("/verify-otp", response_model=AuthResponse)
def verify_otp(data: VerifyOTPRequest, db: Session = Depends(get_db)):
    """Step 2: Verify OTP and return JWT tokens."""
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.otp_code:
        raise HTTPException(status_code=400, detail="No OTP pending. Please login again.")

    if user.otp_expires_at and datetime.now(timezone.utc) > user.otp_expires_at.replace(tzinfo=timezone.utc if user.otp_expires_at.tzinfo is None else user.otp_expires_at.tzinfo):
        user.otp_code = None
        db.commit()
        raise HTTPException(status_code=400, detail="OTP expired. Please login again.")

    if user.otp_code != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # OTP verified — clear it
    user.otp_code = None
    user.otp_expires_at = None
    user.is_verified = True

    # Auto-link vendor/lender if not already linked (handles users created before auto-link was added)
    if user.role == "vendor" and user.vendor_id is None:
        vendor = db.query(Vendor).filter(Vendor.email == user.email).first()
        if vendor:
            user.vendor_id = vendor.id
    elif user.role == "lender" and user.lender_id is None:
        lender = db.query(Lender).filter(Lender.email == user.email).first()
        if lender:
            user.lender_id = lender.id

    # Create tokens
    token_data = {"sub": str(user.id), "role": user.role, "email": user.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    log_activity(db, "user", user.id, "login_success", f"OTP verified — logged in as {user.role}", user.id)

    db.commit()

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_to_dict(user),
    )


# ═══════════════════════════════════════════════
#  REFRESH TOKEN
# ═══════════════════════════════════════════════

@router.post("/refresh", response_model=AuthResponse)
def refresh_token(data: RefreshRequest, db: Session = Depends(get_db)):
    """Get new access token using refresh token."""
    try:
        payload = jwt.decode(data.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    token_data = {"sub": str(user.id), "role": user.role, "email": user.email}
    new_access = create_access_token(token_data)
    new_refresh = create_refresh_token(token_data)

    return AuthResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        user=user_to_dict(user),
    )


# ═══════════════════════════════════════════════
#  GET CURRENT USER
# ═══════════════════════════════════════════════

@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    """Get the currently authenticated user's profile."""
    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        role=user.role,
        vendor_id=user.vendor_id,
        lender_id=user.lender_id,
        is_verified=user.is_verified,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


# ═══════════════════════════════════════════════
#  RESEND OTP
# ═══════════════════════════════════════════════

@router.post("/resend-otp")
def resend_otp(data: LoginRequest, db: Session = Depends(get_db)):
    """Resend OTP to user (requires valid credentials)."""
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not _verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    otp = generate_otp()
    user.otp_code = otp
    user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)
    user.otp_channel = data.otp_channel

    send_otp(user.phone or "", user.email, otp, data.otp_channel, user_name=user.name)
    db.commit()

    return {
        "message": f"OTP resent via {data.otp_channel}",
        "debug_otp": otp,
    }


# ═══════════════════════════════════════════════
#  LINK VENDOR TO USER
# ═══════════════════════════════════════════════

@router.post("/link-vendor/{vendor_id}")
def link_vendor(vendor_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Link a vendor profile to the authenticated user account."""
    if user.role != "vendor":
        raise HTTPException(status_code=403, detail="Only vendor accounts can link vendor profiles")

    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # Check if another user is already linked
    existing = db.query(User).filter(User.vendor_id == vendor_id, User.id != user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="This vendor profile is already linked to another account")

    user.vendor_id = vendor_id
    log_activity(db, "user", user.id, "link_vendor", f"Linked vendor #{vendor_id} to user account", user.id)
    db.commit()

    return {"message": "Vendor profile linked", "vendor_id": vendor_id}
