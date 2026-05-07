from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from app.database import Base


class UploadedDocument(Base):
    """
    Relational metadata for files uploaded manually by the user (e.g. PDFs).
    Each record represents one file.
    """
    __tablename__ = "uploaded_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_type = Column(String, default="pdf_upload")
    filename = Column(String, nullable=False)
    page_count = Column(Integer, default=0)
    
    # "queued" | "processing" | "success" | "failed"
    sync_status = Column(String, default="queued")
    
    file_metadata = Column(JSONB, nullable=True)
    # {size, page_count, upload_time, etc.}

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
