import uuid
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.notifications.model import Notification

class NotificationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        title: str,
        message: str,
        user_id: Optional[str] = None,
        module: str = "BREAKFAST",
        entity_id: Optional[str] = None,
        notification_type: str = "IN_APP"
    ) -> Notification:
        notif_id = f"NOTIF-{int(datetime.now(timezone.utc).timestamp()*1000)}-{str(uuid.uuid4())[:4]}"
        notif = Notification(
            notification_id=notif_id,
            user_id=user_id,
            title=title,
            message=message,
            module=module,
            entity_id=entity_id,
            notification_type=notification_type,
            is_read=False,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(notif)
        self.db.commit()
        self.db.refresh(notif)
        return notif

    def get_by_user(self, user_id: str, unread_only: bool = False, limit: int = 50) -> List[Notification]:
        q = self.db.query(Notification).filter(Notification.user_id == user_id)
        if unread_only:
            q = q.filter(Notification.is_read == False)
        return q.order_by(Notification.created_at.desc()).limit(limit).all()

    def mark_read(self, notification_id: str, user_id: str) -> Optional[Notification]:
        notif = self.db.query(Notification).filter(
            Notification.notification_id == notification_id,
            Notification.user_id == user_id
        ).first()
        if notif:
            notif.is_read = True
            self.db.commit()
            self.db.refresh(notif)
        return notif
