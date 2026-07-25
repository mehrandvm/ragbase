# backend/app/api/routes/ingest.py
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File

from app.core.ingestion import ingest
from app.core.registry import get_kb
from app.config import settings

router = APIRouter(prefix="/kb", tags=["ingestion"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


@router.post("/{kb_id}/ingest")
async def ingest_file(kb_id: str, file: UploadFile = File(...)):
    if not get_kb(kb_id):
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type '{ext}'. Allowed: {ALLOWED_EXTENSIONS}",
        )

    # save upload to temp path
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    temp_path  = upload_dir / file.filename

    with open(temp_path, "wb") as f:
        f.write(await file.read())

    try:
        chunks_stored = ingest(
            file_path=str(temp_path),
            kb_id=kb_id,
            file_name=file.filename,
        )
    except Exception as e:
        # clean up if ingestion fails
        if temp_path.exists():
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "kb_id":         kb_id,
        "file_name":     file.filename,
        "chunks_stored": chunks_stored,
    }


# Accepts a multipart file upload, validates extension, saves to a temp folder,
# hands the path to the ingestion pipeline, then returns the chunk count.
# ingestion.py deletes the temp file itself after embedding — no cleanup needed here
# on the happy path. The try/except handles the edge case where ingestion crashes
# before reaching its own cleanup.