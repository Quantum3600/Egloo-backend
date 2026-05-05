from pydantic import BaseModel, Field
from uuid import UUID
from datetime import date, datetime
from typing import Optional, List, Any, Dict

class ActionItem(BaseModel):
    task: str
    source_type: Optional[str] = ""
    sender: Optional[str] = ""
    urgency: Optional[str] = "medium"
    due_hint: Optional[str] = "no deadline"

class TopicCluster(BaseModel):
    name: str
    summary: str
    source_types: Optional[List[str]] = Field(default_factory=list)
    item_count: Optional[int] = 0

class DigestResponse(BaseModel):
    id: UUID
    date: date
    summary_text: Optional[str]
    action_items: Optional[List[Any]] = Field(default_factory=list)
    topics: Optional[List[Any]] = Field(default_factory=list)
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}

class DigestListResponse(BaseModel):
    digests: List[DigestResponse]
    total: int

class GenerateDigestRequest(BaseModel):
    force_regenerate: bool = False
    fcm_token: Optional[str] = None
    target_date: Optional[date] = None

class MessageResponse(BaseModel):
    message: str
