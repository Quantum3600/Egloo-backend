import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.ingest import IngestResponse, IngestResultResponse
from app.schemas.job import JobStatusResponse, JobListResponse
from app.services.source_service import get_source_by_id, get_all_sources
from app.services.ingestion_service import ingest_source
from app.utils.job_tracker import create_job, get_job, get_user_jobs

router = APIRouter(prefix="/ingest", tags=["ingest"])

@router.post("/trigger/{source_id}", response_model=IngestResponse)
async def trigger_ingest(
    source_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger ingestion via Celery — returns immediately.
    Poll /ingest/job/{job_id} to track progress."""
    from app.workers.tasks import sync_source

    source = await get_source_by_id(db, source_id, current_user.id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    if source.sync_status == "syncing":
        raise HTTPException(status_code=400, detail="Sync already in progress")

    job_id = str(uuid.uuid4())

    # Create job record in Redis before queuing
    await create_job(
        job_id=job_id,
        user_id=str(current_user.id),
        source_id=str(source_id),
        source_type=source.source_type,
    )

    # Queue Celery task — runs in worker container
    sync_source.delay(
        source_id=str(source_id),
        user_id=str(current_user.id),
        job_id=job_id,
    )

    return IngestResponse(
        job_id=job_id,
        source_id=source_id,
        source_type=source.source_type,
        message=f"Job queued! Poll /ingest/job/{job_id} for progress.",
    )

@router.post("/trigger-all", response_model=list[IngestResponse])
async def trigger_all_ingest(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger ingestion for all connected sources at once."""
    from app.workers.tasks import sync_source

    sources = await get_all_sources(db, current_user.id)
    if not sources:
        raise HTTPException(
            status_code=404,
            detail="No sources connected. Connect Gmail, Slack, or Drive first.",
        )

    responses = []
    for source in sources:
        if source.sync_status == "syncing":
            continue

        job_id = str(uuid.uuid4())

        await create_job(
            job_id=job_id,
            user_id=str(current_user.id),
            source_id=str(source.id),
            source_type=source.source_type,
        )

        sync_source.delay(
            source_id=str(source.id),
            user_id=str(current_user.id),
            job_id=job_id,
        )

        responses.append(IngestResponse(
            job_id=job_id,
            source_id=source.id,
            source_type=source.source_type,
            message=f"Job queued for {source.source_type}!",
        ))

    return responses

@router.post("/trigger-direct/{source_id}", response_model=IngestResultResponse)
async def trigger_ingest_direct(
    source_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Synchronous ingestion — waits for full result.
    Uses request-scoped session safely because it
    completes before the response is sent.
    Use for testing only."""
    source = await get_source_by_id(db, source_id, current_user.id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    if source.sync_status == "syncing":
        raise HTTPException(status_code=400, detail="Sync already in progress")

    try:
        result = await ingest_source(db, source, str(current_user.id))
        return IngestResultResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ingestion failed: {str(e)}",
        )

@router.get("/job/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    """Poll this endpoint to track ingestion progress.
    Frontend polls every 2-3 seconds while status is queued or started.
    Status values: queued -> started -> success | failed
    Progress: 0 -> 10 -> 20 -> 100"""
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Security: users can only see their own jobs
    if job.get("user_id") != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    return JobStatusResponse(**job)

@router.get("/jobs", response_model=JobListResponse)
async def list_user_jobs(
    current_user: User = Depends(get_current_user),
):
    """List all recent ingestion jobs for the current user."""
    jobs = await get_user_jobs(str(current_user.id))
    return JobListResponse(
        jobs=[JobStatusResponse(**j) for j in jobs],
        total=len(jobs),
    )
