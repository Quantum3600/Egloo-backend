from pydantic import BaseModel
from typing import Optional, Dict, Any

class JobStatusResponse(BaseModel):
    job_id: str
    source_id: str
    source_type: str
    status: str
    progress: int
    message: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str

class JobListResponse(BaseModel):
    jobs: list[JobStatusResponse]
    total: int
