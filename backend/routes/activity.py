"""
Activity log routes — audit trail for all entity actions.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import json

from database import get_db
from models import ActivityLog, User
from routes.auth import get_current_user

router = APIRouter(prefix="/api/activity", tags=["activity"])


class ActivityResponse(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    action: str
    description: str
    user_id: Optional[int] = None
    metadata: Optional[dict] = None
    created_at: Optional[str] = None


@router.get("/{entity_type}/{entity_id}", response_model=List[ActivityResponse])
def get_entity_activity(entity_type: str, entity_id: int, limit: int = 50, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get activity log for a specific entity (vendor, invoice, listing, lender)."""
    entries = db.query(ActivityLog).filter(
        ActivityLog.entity_type == entity_type,
        ActivityLog.entity_id == entity_id,
    ).order_by(ActivityLog.created_at.desc()).limit(limit).all()

    return [ActivityResponse(
        id=e.id,
        entity_type=e.entity_type,
        entity_id=e.entity_id,
        action=e.action,
        description=e.description,
        user_id=e.user_id,
        metadata=json.loads(e.metadata_json) if e.metadata_json else None,
        created_at=e.created_at.isoformat() if e.created_at else None,
    ) for e in entries]


@router.get("/user/{user_id}", response_model=List[ActivityResponse])
def get_user_activity(user_id: int, limit: int = 50, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get all activity by a specific user."""
    entries = db.query(ActivityLog).filter(
        ActivityLog.user_id == user_id
    ).order_by(ActivityLog.created_at.desc()).limit(limit).all()

    return [ActivityResponse(
        id=e.id,
        entity_type=e.entity_type,
        entity_id=e.entity_id,
        action=e.action,
        description=e.description,
        user_id=e.user_id,
        metadata=json.loads(e.metadata_json) if e.metadata_json else None,
        created_at=e.created_at.isoformat() if e.created_at else None,
    ) for e in entries]


@router.get("/recent")
def get_recent_activity(limit: int = 20, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get the most recent activity across the entire system."""
    entries = db.query(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(limit).all()
    return [ActivityResponse(
        id=e.id,
        entity_type=e.entity_type,
        entity_id=e.entity_id,
        action=e.action,
        description=e.description,
        user_id=e.user_id,
        metadata=json.loads(e.metadata_json) if e.metadata_json else None,
        created_at=e.created_at.isoformat() if e.created_at else None,
    ) for e in entries]
