import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(150), default="", nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(50), default="", nullable=False)
    password_hash = Column(String(255), nullable=False)
    status = Column(String(20), default="active", nullable=False)
    manager_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    force_password_change = Column(Boolean, default=False, nullable=False)
    is_hard_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    manager = relationship("User", remote_side=[id], backref="direct_reports")
    roles = relationship("Role", secondary=user_roles, back_populates="users", lazy="joined")
    employee = relationship("Employee", back_populates="user", uselist=False, lazy="joined")
    module_memberships = relationship("UserModuleMembership", back_populates="user", cascade="all, delete-orphan", lazy="joined")

    @property
    def is_active(self) -> bool:
        return self.status == "active" and not self.is_hard_deleted
