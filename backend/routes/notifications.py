"""
Notification routes — in-app notification system.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from database import get_db
from models import Notification, User
from routes.auth import get_current_user

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    notification_type: str
    is_read: bool
    link: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/{user_id}", response_model=List[NotificationResponse])
def get_notifications(user_id: int, limit: int = 50, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get all notifications for a user."""
    notifs = db.query(Notification).filter(
        Notification.user_id == user_id
    ).order_by(Notification.created_at.desc()).limit(limit).all()

    return [NotificationResponse(
        id=n.id,
        user_id=n.user_id,
        title=n.title,
        message=n.message,
        notification_type=n.notification_type,
        is_read=n.is_read,
        link=n.link,
        created_at=n.created_at.isoformat() if n.created_at else None,
    ) for n in notifs]


@router.get("/{user_id}/unread-count")
def unread_count(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get unread notification count."""
    count = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False,
    ).count()
    return {"unread": count}


@router.patch("/{notification_id}/read")
def mark_read(notification_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Mark a single notification as read."""
    notif = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    db.commit()
    return {"message": "Marked as read"}


@router.patch("/read-all/{user_id}")
def mark_all_read(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Mark all notifications as read for a user."""
    db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False,
    ).update({"is_read": True})
    db.commit()
    return {"message": "All notifications marked as read"}
