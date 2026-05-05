from uuid import UUID
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, date, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_

from app.models.digest import Digest
from app.models.document_chunk import DocumentChunk
from app.config import settings
from app.ai.digest_ai import (
    cluster_into_topics,
    extract_action_items,
    generate_summary,
)


# ─── Fetch recent chunks from PostgreSQL ─────────────────────────────────────

async def fetch_recent_chunks(
    db: AsyncSession,
    user_id: UUID,
    hours_back: int = None,
) -> List[Dict[str, Any]]:
    """
    Fetch all chunks ingested in the last N hours for this user.
    Returns list of dicts (not ORM objects) for safety.
    """
    if hours_back is None:
        hours_back = settings.DIGEST_LOOKBACK_HOURS

    since = datetime.now(timezone.utc) - timedelta(hours=hours_back)

    result = await db.execute(
        select(DocumentChunk)
        .where(
            and_(
                DocumentChunk.user_id == user_id,
                DocumentChunk.created_at >= since,
            )
        )
        .order_by(desc(DocumentChunk.created_at))
        .limit(settings.DIGEST_MAX_CHUNKS)
    )
    chunks = result.scalars().all()

    # Convert to plain dicts immediately
    # so we never touch the ORM object outside this session
    return [
        {
            "id": str(c.id),
            "content": c.content,
            "chunk_metadata": c.chunk_metadata or {},
            "source_id": str(c.source_id),
            "created_at": c.created_at.isoformat() if c.created_at else "",
        }
        for c in chunks
    ]


# ─── Check if digest already exists for today ────────────────────────────────

async def get_existing_digest(
    db: AsyncSession,
    user_id: UUID,
    target_date: date,
) -> Optional[Digest]:
    result = await db.execute(
        select(Digest).where(
            and_(
                Digest.user_id == user_id,
                Digest.date == target_date,
            )
        )
    )
    return result.scalar_one_or_none()


# ─── Save digest to PostgreSQL ────────────────────────────────────────────────

async def save_digest(
    db: AsyncSession,
    user_id: UUID,
    target_date: date,
    summary_text: str,
    action_items: List[Dict],
    topics: List[Dict],
) -> Digest:
    """
    Save or update a digest for a given date.
    If one already exists for this date, overwrites it.
    """
    existing = await get_existing_digest(db, user_id, target_date)

    if existing:
        existing.summary_text = summary_text
        existing.action_items = action_items
        existing.topics = topics
        await db.commit()
        await db.refresh(existing)
        return existing

    digest = Digest(
        user_id=user_id,
        date=target_date,
        summary_text=summary_text,
        action_items=action_items,
        topics=topics,
    )
    db.add(digest)
    await db.commit()
    await db.refresh(digest)
    return digest


# ─── Main digest generation pipeline ─────────────────────────────────────────

async def generate_digest(
    db: AsyncSession,
    user_id: str,
    target_date: Optional[date] = None,
    force_regenerate: bool = False,
    fcm_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Full digest generation pipeline for one user.

    Steps:
    1. Check if digest already exists for today
    2. Fetch recent chunks from PostgreSQL
    3. Check minimum chunk threshold
    4. Cluster chunks into topics (LLM)
    5. Extract action items (LLM)
    6. Generate summary paragraph (LLM)
    7. Save to PostgreSQL
    8. Send FCM push notification (optional)

    Returns dict with full digest data.
    """
    user_uuid = UUID(user_id)

    if target_date is None:
        target_date = datetime.now(timezone.utc).date()

    print(f"[INFO] PenGo generating digest for user {user_id} date {target_date}")

    # ── Step 1: Check existing ────────────────────────────────────────────────
    if not force_regenerate:
        existing = await get_existing_digest(db, user_uuid, target_date)
        if existing:
            print(f"[CACHE] Digest already exists for {target_date} — returning cached")
            return _digest_to_dict(existing)

    # ── Step 2: Fetch recent chunks ───────────────────────────────────────────
    chunks = await fetch_recent_chunks(db, user_uuid)

    print(f"[INFO] Found {len(chunks)} chunks for digest")

    # ── Step 3: Check minimum threshold ──────────────────────────────────────
    if len(chunks) < settings.DIGEST_MIN_CHUNKS:
        print(
            f"[WARNING] Only {len(chunks)} chunks found "
            f"(minimum {settings.DIGEST_MIN_CHUNKS}) — creating minimal digest"
        )
        summary_text = (
            f"Not enough activity found in the last "
            f"{settings.DIGEST_LOOKBACK_HOURS} hours to generate a "
            f"meaningful digest. Connect more sources or wait for more data."
        )
        digest = await save_digest(
            db=db,
            user_id=user_uuid,
            target_date=target_date,
            summary_text=summary_text,
            action_items=[],
            topics=[],
        )
        return _digest_to_dict(digest)

    # ── Step 4: Cluster into topics ───────────────────────────────────────────
    topics = await cluster_into_topics(chunks)

    # ── Step 5: Extract action items ──────────────────────────────────────────
    action_items = await extract_action_items(chunks)

    # ── Step 6: Generate summary ──────────────────────────────────────────────
    source_types = list({
        c["chunk_metadata"].get("source_type", "unknown")
        for c in chunks
    })
    summary_text = await generate_summary(
        topics=topics,
        action_items=action_items,
        chunk_count=len(chunks),
        source_types=source_types,
    )

    # ── Step 7: Save to PostgreSQL ────────────────────────────────────────────
    digest = await save_digest(
        db=db,
        user_id=user_uuid,
        target_date=target_date,
        summary_text=summary_text,
        action_items=action_items,
        topics=topics,
    )

    print(
        f"[OK] Digest saved: {len(topics)} topics, "
        f"{len(action_items)} action items"
    )

    # ── Step 8: FCM push notification (optional) ──────────────────────────────
    if fcm_token:
        from app.services.notification_service import send_digest_notification
        await send_digest_notification(
            fcm_token=fcm_token,
            digest_date=str(target_date),
            action_item_count=len(action_items),
            topic_count=len(topics),
        )

    return _digest_to_dict(digest)


# ─── Helper: convert Digest ORM to dict ──────────────────────────────────────

def _digest_to_dict(digest: Digest) -> Dict[str, Any]:
    return {
        "id": str(digest.id),
        "user_id": str(digest.user_id),
        "date": str(digest.date),
        "summary_text": digest.summary_text,
        "action_items": digest.action_items or [],
        "topics": digest.topics or [],
        "created_at": (
            digest.created_at.isoformat()
            if digest.created_at else ""
        ),
    }


# ─── Get digest history ───────────────────────────────────────────────────────

async def get_digest_history(
    db: AsyncSession,
    user_id: UUID,
    limit: int = 30,
) -> List[Digest]:
    result = await db.execute(
        select(Digest)
        .where(Digest.user_id == user_id)
        .order_by(desc(Digest.date))
        .limit(limit)
    )
    return result.scalars().all()


async def get_digest_by_id(
    db: AsyncSession,
    digest_id: UUID,
    user_id: UUID,
) -> Optional[Digest]:
    result = await db.execute(
        select(Digest).where(
            and_(
                Digest.id == digest_id,
                Digest.user_id == user_id,
            )
        )
    )
    return result.scalar_one_or_none()
