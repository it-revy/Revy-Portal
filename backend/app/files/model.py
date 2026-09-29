import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime
from app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class FileMetadata(Base):
    __tablename__ = "files"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    file_id = Column(String(100), unique=True, index=True, nullable=False)
    entity_type = Column(String(100), nullable=False, index=True)
    entity_id = Column(String(100), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(100), nullable=False)
    blob_path = Column(Text, nullable=False)
    uploaded_by = Column(String(150), nullable=True)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
