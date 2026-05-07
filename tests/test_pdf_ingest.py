import pytest
import os
import uuid
from httpx import AsyncClient
from app.main import app
from app.database import AsyncSessionLocal
from app.models.uploaded_document import UploadedDocument
from sqlalchemy import select

@pytest.mark.asyncio
async def test_pdf_upload_flow(auth_headers):
    # 1. Create a test PDF
    test_pdf_path = "tests/data/test_upload.pdf"
    os.makedirs("tests/data", exist_ok=True)
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Project Alpha is a secret initiative to build a sustainable habitat on Mars.")
    doc.save(test_pdf_path)
    doc.close()

    async with AsyncClient(app=app, base_url="http://test") as ac:
        # 2. Upload the PDF
        with open(test_pdf_path, "rb") as f:
            response = await ac.post(
                "/api/v1/ingest/pdf",
                files={"file": ("test_upload.pdf", f, "application/pdf")},
                headers=auth_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "document_id" in data
        assert "job_id" in data
        doc_id = data["document_id"]
        job_id = data["job_id"]

        # 3. Verify record in DB
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(UploadedDocument).where(UploadedDocument.id == uuid.UUID(doc_id)))
            doc_record = result.scalar_one_or_none()
            assert doc_record is not None
            assert doc_record.filename == "test_upload.pdf"
            assert doc_record.sync_status == "queued"

        # 4. Check Job Status
        response = await ac.get(f"/api/v1/ingest/job/{job_id}", headers=auth_headers)
        assert response.status_code == 200
        job_data = response.json()
        assert job_data["status"] in ["queued", "started", "success"]

    # Cleanup
    if os.path.exists(test_pdf_path):
        os.remove(test_pdf_path)
