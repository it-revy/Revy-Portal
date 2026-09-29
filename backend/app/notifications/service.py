from typing import List, Optional
from sqlalchemy.orm import Session
from app.notifications.repository import NotificationRepository
from app.notifications.model import Notification

class NotificationService:
    def __init__(self, db: Session):
        self.repo = NotificationRepository(db)

    def send(
        self,
        title: str,
        message: str,
        user_id: Optional[str] = None,
        module: str = "BREAKFAST",
        entity_id: Optional[str] = None,
        notification_type: str = "IN_APP"
    ) -> Notification:
        return self.repo.create(
            title=title,
            message=message,
            user_id=user_id,
            module=module,
            entity_id=entity_id,
            notification_type=notification_type
        )

    def get_user_notifications(self, user_id: str, unread_only: bool = False) -> List[Notification]:
        return self.repo.get_by_user(user_id, unread_only)

    def mark_as_read(self, notification_id: str, user_id: str) -> Optional[Notification]:
        return self.repo.mark_read(notification_id, user_id)
