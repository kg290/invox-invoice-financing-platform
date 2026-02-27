"""
Chat routes — direct messaging between vendors and lenders.

Features:
- Start a conversation (linked to a marketplace listing or general)
- Send messages
- List conversations for current user
- Get messages in a conversation
- Mark messages as read
- Unread count
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone

from database import get_db
from models import ChatConversation, ChatMessage, User, Vendor, Lender, MarketplaceListing
from routes.auth import get_current_user

router = APIRouter(prefix="/api/chat", tags=["Chat"])


# ═══════════════════════════════════════════════
#  SCHEMAS
# ═══════════════════════════════════════════════

class StartConversationRequest(BaseModel):
    other_user_id: int = Field(..., description="The user ID of the person to chat with")
    listing_id: Optional[int] = None
    invoice_id: Optional[int] = None
    subject: Optional[str] = None
    initial_message: Optional[str] = None


class SendMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    message_type: str = Field(default="text")


class ConversationResponse(BaseModel):
    id: int
    other_user_id: int
    other_user_name: str
    other_user_role: str
    subject: Optional[str]
    last_message: Optional[str]
    last_message_at: Optional[str]
    unread_count: int
    listing_id: Optional[int]
    invoice_id: Optional[int]
    created_at: str


class MessageResponse(BaseModel):
    id: int
    sender_user_id: int
    sender_name: str
    message: str
    message_type: str
    is_read: bool
    created_at: str


# ═══════════════════════════════════════════════
#  START / GET CONVERSATION
# ═══════════════════════════════════════════════

@router.post("/conversations", status_code=201)
def start_conversation(
    data: StartConversationRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start a new conversation or return existing one between two users."""
    other_user = db.query(User).filter(User.id == data.other_user_id).first()
    if not other_user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == data.other_user_id:
        raise HTTPException(status_code=400, detail="Cannot chat with yourself")

    # Determine vendor/lender roles
    if user.role == "vendor":
        vendor_uid = user.id
        lender_uid = data.other_user_id
    else:
        vendor_uid = data.other_user_id
        lender_uid = user.id

    # Check for existing conversation between same users (and same listing if specified)
    existing_q = db.query(ChatConversation).filter(
        ChatConversation.vendor_user_id == vendor_uid,
        ChatConversation.lender_user_id == lender_uid,
    )
    if data.listing_id:
        existing_q = existing_q.filter(ChatConversation.listing_id == data.listing_id)

    existing = existing_q.first()
    if existing:
        return _conversation_to_dict(existing, user, db)

    # Create new conversation
    conv = ChatConversation(
        vendor_user_id=vendor_uid,
        lender_user_id=lender_uid,
        listing_id=data.listing_id,
        invoice_id=data.invoice_id,
        subject=data.subject or f"Chat between {user.name} and {other_user.name}",
    )
    db.add(conv)
    db.flush()

    # Send initial message if provided
    if data.initial_message:
        msg = ChatMessage(
            conversation_id=conv.id,
            sender_user_id=user.id,
            message=data.initial_message,
            message_type="text",
        )
        db.add(msg)
        conv.last_message_text = data.initial_message
        conv.last_message_at = datetime.now(timezone.utc)
        if user.role == "vendor":
            conv.lender_unread = (conv.lender_unread or 0) + 1
        else:
            conv.vendor_unread = (conv.vendor_unread or 0) + 1

    db.commit()
    db.refresh(conv)
    return _conversation_to_dict(conv, user, db)


@router.get("/conversations")
def list_conversations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all conversations for the current user."""
    convs = db.query(ChatConversation).filter(
        or_(
            ChatConversation.vendor_user_id == user.id,
            ChatConversation.lender_user_id == user.id,
        )
    ).order_by(desc(ChatConversation.last_message_at)).all()

    return [_conversation_to_dict(c, user, db) for c in convs]


@router.get("/conversations/{conversation_id}")
def get_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific conversation with its messages."""
    conv = db.query(ChatConversation).filter(ChatConversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if user.id not in (conv.vendor_user_id, conv.lender_user_id):
        raise HTTPException(status_code=403, detail="Not a participant in this conversation")

    return _conversation_to_dict(conv, user, db)


# ═══════════════════════════════════════════════
#  MESSAGES
# ═══════════════════════════════════════════════

@router.get("/conversations/{conversation_id}/messages")
def get_messages(
    conversation_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get messages in a conversation, newest first."""
    conv = db.query(ChatConversation).filter(ChatConversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if user.id not in (conv.vendor_user_id, conv.lender_user_id):
        raise HTTPException(status_code=403, detail="Not a participant")

    # Mark messages as read for the current user
    unread_msgs = db.query(ChatMessage).filter(
        ChatMessage.conversation_id == conversation_id,
        ChatMessage.sender_user_id != user.id,
        ChatMessage.is_read == False,
    ).all()

    for msg in unread_msgs:
        msg.is_read = True

    # Reset unread count
    if user.id == conv.vendor_user_id:
        conv.vendor_unread = 0
    else:
        conv.lender_unread = 0

    db.commit()

    # Fetch messages
    messages = db.query(ChatMessage).filter(
        ChatMessage.conversation_id == conversation_id
    ).order_by(ChatMessage.created_at.asc()).offset(offset).limit(limit).all()

    result = []
    for msg in messages:
        sender = db.query(User).filter(User.id == msg.sender_user_id).first()
        result.append({
            "id": msg.id,
            "sender_user_id": msg.sender_user_id,
            "sender_name": sender.name if sender else "Unknown",
            "message": msg.message,
            "message_type": msg.message_type,
            "is_read": msg.is_read,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
        })

    return {"messages": result, "total": len(result), "conversation_id": conversation_id}


@router.post("/conversations/{conversation_id}/messages", status_code=201)
def send_message(
    conversation_id: int,
    data: SendMessageRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send a message in a conversation."""
    conv = db.query(ChatConversation).filter(ChatConversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if user.id not in (conv.vendor_user_id, conv.lender_user_id):
        raise HTTPException(status_code=403, detail="Not a participant")

    msg = ChatMessage(
        conversation_id=conversation_id,
        sender_user_id=user.id,
        message=data.message,
        message_type=data.message_type,
    )
    db.add(msg)

    # Update conversation metadata
    conv.last_message_text = data.message[:200]
    conv.last_message_at = datetime.now(timezone.utc)

    # Increment unread for the other user
    if user.id == conv.vendor_user_id:
        conv.lender_unread = (conv.lender_unread or 0) + 1
    else:
        conv.vendor_unread = (conv.vendor_unread or 0) + 1

    db.commit()
    db.refresh(msg)

    return {
        "id": msg.id,
        "sender_user_id": msg.sender_user_id,
        "sender_name": user.name,
        "message": msg.message,
        "message_type": msg.message_type,
        "is_read": False,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }


# ═══════════════════════════════════════════════
#  UNREAD COUNT
# ═══════════════════════════════════════════════

@router.get("/unread-count")
def get_unread_count(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get total unread message count across all conversations."""
    convs = db.query(ChatConversation).filter(
        or_(
            ChatConversation.vendor_user_id == user.id,
            ChatConversation.lender_user_id == user.id,
        )
    ).all()

    total_unread = 0
    for c in convs:
        if user.id == c.vendor_user_id:
            total_unread += c.vendor_unread or 0
        else:
            total_unread += c.lender_unread or 0

    return {"unread_count": total_unread}


# ═══════════════════════════════════════════════
#  FIND USERS TO CHAT WITH
# ═══════════════════════════════════════════════

@router.get("/available-users")
def get_available_chat_users(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get list of users the current user can chat with.
    Vendors see lenders, lenders see vendors."""
    if user.role == "vendor":
        users = db.query(User).filter(User.role == "lender", User.is_active == True).all()
    else:
        users = db.query(User).filter(User.role == "vendor", User.is_active == True).all()

    return [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
        }
        for u in users
    ]


# ═══════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════

def _conversation_to_dict(conv: ChatConversation, current_user: User, db: Session) -> dict:
    """Convert a conversation to a response dict with the other user's info."""
    if current_user.id == conv.vendor_user_id:
        other_uid = conv.lender_user_id
        unread = conv.vendor_unread or 0
    else:
        other_uid = conv.vendor_user_id
        unread = conv.lender_unread or 0

    other_user = db.query(User).filter(User.id == other_uid).first()

    return {
        "id": conv.id,
        "other_user_id": other_uid,
        "other_user_name": other_user.name if other_user else "Unknown",
        "other_user_role": other_user.role if other_user else "unknown",
        "subject": conv.subject,
        "last_message": conv.last_message_text,
        "last_message_at": conv.last_message_at.isoformat() if conv.last_message_at else None,
        "unread_count": unread,
        "listing_id": conv.listing_id,
        "invoice_id": conv.invoice_id,
        "created_at": conv.created_at.isoformat() if conv.created_at else None,
    }
