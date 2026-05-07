from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, List


class AvailableSource(BaseModel):
    id: str
    name: str
    displayName: str
    icon: str
    description: str
    requiresAuth: bool
    scopes: List[str]


class ConnectedSource(BaseModel):
    id: str  # This can be "type_userId" or just the UUID string
    type: str
    sourceId: str  # Maps to AvailableSource.id
    accountName: Optional[str] = None
    isConnected: bool
    oauthProviderAccount: Optional[str] = None
    itemCount: int
    lastSyncedAt: Optional[datetime] = None
    nextSyncAt: Optional[datetime] = None
    syncStatus: str


class SourceResponse(BaseModel):
    id: UUID
    source_type: str
    sync_status: str
    last_synced_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SourceListResponse(BaseModel):
    sources: List[SourceResponse]
    total: int


class SyncStatusResponse(BaseModel):
    source_id: UUID
    source_type: str
    sync_status: str
    last_synced_at: Optional[datetime] = None
    message: str


class MessageResponse(BaseModel):
    message: str
