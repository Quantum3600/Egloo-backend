import asyncio
import httpx
import uuid
import sys

BASE_URL = "http://localhost:8000/api/v1"

async def test_e2e():
    print("\n" + "=" * 55)
    print("🐧 EGLOO — End-to-End Test Suite")
    print("=" * 55)

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # 1. Auth Flow
        print("\n[1/7] Testing Authentication...")
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        password = "password123"
        
        reg_res = await client.post("/auth/register", json={
            "email": email, 
            "password": password, 
            "full_name": "Test User"
        })
        if reg_res.status_code not in (200, 201):
            print(f"❌ Registration failed: {reg_res.text}")
            return

        login_res = await client.post("/auth/login", data={
            "username": email, 
            "password": password
        })
        if login_res.status_code != 200:
            print(f"❌ Login failed: {login_res.text}")
            return
            
        token = login_res.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Auth successful")

        # 2. Ingest a "Thought"
        print("\n[2/7] Testing Manual Ingestion...")
        thought_content = "I need to remember to buy milk and eggs, and also review the project architecture."
        ingest_res = await client.post("/ingest/manual", json={
            "content": thought_content,
            "metadata": {"type": "note"}
        }, headers=headers)
        if ingest_res.status_code != 200:
            print(f"❌ Ingestion failed: {ingest_res.text}")
        else:
            print("✅ Thought ingested")

        # 3. Semantic Query
        print("\n[3/7] Testing Semantic Query...")
        query_res = await client.post("/query/ask", json={
            "query": "What do I need to remember?",
            "stream": False
        }, headers=headers)
        if query_res.status_code != 200:
            print(f"❌ Query failed: {query_res.text}")
        else:
            print(f"✅ Query successful. Response: {query_res.json().get('answer')[:50]}...")

        # 4. Digest Generation
        print("\n[4/7] Testing Digest Generation...")
        digest_res = await client.post("/digest/generate", json={
            "force_regenerate": True
        }, headers=headers)
        if digest_res.status_code != 200:
            print(f"❌ Digest failed: {digest_res.text}")
        else:
            print("✅ Digest generated")

        # 5. Fetch Topics
        print("\n[5/7] Testing Topic Clustering...")
        topics_res = await client.get("/topics/", headers=headers)
        if topics_res.status_code != 200:
            print(f"❌ Topics fetch failed: {topics_res.text}")
        else:
            topics = topics_res.json()
            print(f"✅ Topics retrieved: {len(topics)} found")

        # 6. Save an Item
        print("\n[6/7] Testing Saved Items...")
        save_res = await client.post("/saved/quick-save", json={
            "content_type": "query_result",
            "content": {"query": "test", "answer": "test answer"},
            "title": "Test Save"
        }, headers=headers)
        if save_res.status_code != 200:
            print(f"❌ Save failed: {save_res.text}")
        else:
            save_id = save_res.json().get("id")
            print(f"✅ Item saved (ID: {save_id})")

        # 7. List Saved Items
        print("\n[7/7] Verifying Saved Items...")
        list_res = await client.get("/saved/", headers=headers)
        if list_res.status_code != 200:
            print(f"❌ List saved failed: {list_res.text}")
        else:
            print(f"✅ Saved items list: {len(list_res.json())} items")

    print("\n" + "=" * 55)
    print("✅ E2E TEST COMPLETE — Pingo is healthy! 🐧")
    print("=" * 55 + "\n")

if __name__ == "__main__":
    try:
        asyncio.run(test_e2e())
    except Exception as e:
        print(f"❌ Test script crashed: {e}")
        sys.exit(1)
