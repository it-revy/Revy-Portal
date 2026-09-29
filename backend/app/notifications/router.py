from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user, CurrentUser
from app.notifications.service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("")
@router.get("/")
def get_my_notifications(
    unread_only: bool = Query(False),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = NotificationService(db)
    notifs = service.get_user_notifications(current_user.id, unread_only=unread_only)
    return {
        "success": True,
        "count": len(notifs),
        "notifications": [
            {
                "notificationId": n.notification_id,
                "title": n.title,
                "message": n.message,
                "module": n.module,
                "entityId": n.entity_id,
                "notificationType": n.notification_type,
                "isRead": n.is_read,
                "createdAt": n.created_at.isoformat() if n.created_at else None
            }
            for n in notifs
        ]
    }

@router.put("/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = NotificationService(db)
    notif = service.mark_as_read(notification_id, current_user.id)
    return {
        "success": True,
        "message": "Notification marked as read",
        "notification": {
            "notificationId": notif.notification_id if notif else notification_id,
            "isRead": True
        } if notif else None
    }
