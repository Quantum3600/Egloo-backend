import asyncio

from app.database import AsyncSessionLocal
from app.services.auth_service import register_user, get_user_by_email


async def seed():
    async with AsyncSessionLocal() as db:
        existing = await get_user_by_email(db, "demo@egloo.app")
        if existing:
            print("[SKIP] Demo user already exists -- skipping seed")
            return

        access_token, refresh_token, user = await register_user(
            db,
            email="demo@egloo.app",
            password="password123",
            full_name="PenGo Demo",
        )
        print(f"[OK] Demo user created: {user.email}")
        print(f"     Access token: {access_token[:40]}...")


if __name__ == "__main__":
    asyncio.run(seed())
