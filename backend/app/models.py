# Import all models here so that SQLAlchemy Base.metadata has all tables registered
from app.core.database import Base
from app.roles.model import Role, Permission, role_permissions
from app.users.model import User, user_roles
from app.employees.model import Department, Employee
from app.audit.model import AuditLog
from app.notifications.model import Notification
from app.files.model import FileMetadata
from app.breakfast.model import (
    PublicHoliday,
    BreakfastSetting,
    BreakfastReason,
    BreakfastRecord,
    BreakfastNonParticipationPeriod,
    BreakfastDailyEntry,
    BreakfastAdditionalOrder,
    BreakfastOrder,
    BreakfastOrderItem,
    BreakfastMoneyTransaction,
    BreakfastFundRequest
)

__all__ = [
    "Base",
    "Role",
    "Permission",
    "role_permissions",
    "User",
    "user_roles",
    "Department",
    "Employee",
    "AuditLog",
    "Notification",
    "FileMetadata",
    "PublicHoliday",
    "BreakfastSetting",
    "BreakfastReason",
    "BreakfastRecord",
    "BreakfastNonParticipationPeriod",
    "BreakfastDailyEntry",
    "BreakfastAdditionalOrder",
    "BreakfastOrder",
    "BreakfastOrderItem",
    "BreakfastMoneyTransaction",
    "BreakfastFundRequest"
]
