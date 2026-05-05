from uuid import UUID
from datetime import date as DateType
from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.digest import (
    DigestResponse, DigestListResponse,
    GenerateDigestRequest, MessageResponse,
)
from app.services.digest_service import (
    generate_digest, get_digest_history,
    get_digest_by_id, get_existing_digest,
    _digest_to_dict,
)

router = APIRouter(prefix="/digest", tags=["Digest"])


@router.get("/today", response_model=DigestResponse)
async def get_today_digest(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get today's digest.
    If it doesn't exist yet, generates it on demand.
    If it already exists, returns the cached version instantly.
    """
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).date()

    existing = await get_existing_digest(db, current_user.id, today)
    if existing:
        return existing

    # Generate on demand if not yet created
    try:
        result = await generate_digest(
            db=db,
            user_id=str(current_user.id),
            target_date=today,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Digest generation failed: {str(e)}",
        )

    # Re-fetch from DB to return as ORM object for response_model
    existing = await get_existing_digest(db, current_user.id, today)
    if existing:
        return existing

    raise HTTPException(status_code=500, detail="Digest generation failed")


@router.post("/generate", response_model=dict)
async def generate_digest_endpoint(
    body: GenerateDigestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually trigger digest generation.
    Set force_regenerate=true to overwrite existing digest.
    Optionally pass fcm_token for push notification.
    Optionally pass target_date to generate for a past date.
    """
    try:
        result = await generate_digest(
            db=db,
            user_id=str(current_user.id),
            target_date=body.target_date,
            force_regenerate=body.force_regenerate,
            fcm_token=body.fcm_token,
        )
        return {
            "message": "PenGo generated your digest successfully!",
            "digest": result,
        }
    except RuntimeError as e:
        raise HTTPException(
            status_code=503,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Digest generation failed: {str(e)}",
        )


@router.post("/generate/async", response_model=dict)
async def generate_digest_async(
    body: GenerateDigestRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Queue digest generation as a Celery background task.
    Returns immediately. Check /digest/today after ~30 seconds.
    """
    from app.workers.tasks import generate_digest_for_user

    generate_digest_for_user.delay(
        user_id=str(current_user.id),
        fcm_token=body.fcm_token,
    )

    return {
        "message": (
            "PenGo is generating your digest in the background. "
            "Check /digest/today in about 30 seconds."
        ),
        "queued": True,
    }


@router.get("/history", response_model=DigestListResponse)
async def list_digest_history(
    limit: int = QueryParam(default=30, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List past digests for the current user.
    Returns up to 90 days of history.
    """
    digests = await get_digest_history(db, current_user.id, limit=limit)
    return DigestListResponse(
        digests=digests,
        total=len(digests),
    )


@router.get("/{digest_id}", response_model=DigestResponse)
async def get_digest(
    digest_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific digest by ID."""
    digest = await get_digest_by_id(db, digest_id, current_user.id)
    if not digest:
        raise HTTPException(status_code=404, detail="Digest not found")
    return digest


@router.delete("/{digest_id}", response_model=MessageResponse)
async def delete_digest(
    digest_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a specific digest."""
    digest = await get_digest_by_id(db, digest_id, current_user.id)
    if not digest:
        raise HTTPException(status_code=404, detail="Digest not found")
    await db.delete(digest)
    await db.commit()
    return MessageResponse(
        message="Digest deleted. PenGo will generate a fresh one tomorrow."
    )
