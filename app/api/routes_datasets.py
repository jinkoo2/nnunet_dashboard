import uuid
import os
import json
import shutil
import zipfile
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.core.auth import verify_api_key
from app.core.database import get_db
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

CHUNK_DIR_NAME = "uploads"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_zip_and_check_plan(zip_path: str) -> bool:
    """Return True if zip is valid and contains nnUNetPlans.json."""
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            return any(os.path.basename(n) == "nnUNetPlans.json" for n in zf.namelist())
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="File is not a valid ZIP archive")


def _chunk_path(upload_id: str, index: int) -> str:
    return os.path.join(settings.DATA_DIR, CHUNK_DIR_NAME, upload_id, f"{index:06d}.chunk")


def _upload_dir(upload_id: str) -> str:
    return os.path.join(settings.DATA_DIR, CHUNK_DIR_NAME, upload_id)


# ---------------------------------------------------------------------------
# Single-file upload (small datasets, kept for convenience)
# ---------------------------------------------------------------------------

@router.post("/")
async def submit_dataset(
    zip_file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(""),
    submitted_by: str = Form(""),
    _: str = Depends(verify_api_key),
):
    """Direct upload — streams to disk. Use chunked upload for large datasets."""
    dataset_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    dataset_dir = os.path.join(settings.DATA_DIR, "datasets", dataset_id)
    os.makedirs(dataset_dir, exist_ok=True)
    zip_path = os.path.join(dataset_dir, "data.zip")

    # Stream to disk — do not buffer entire file in memory
    with open(zip_path, "wb") as f:
        while chunk := await zip_file.read(1024 * 1024):  # 1 MB chunks
            f.write(chunk)

    has_plan = _validate_zip_and_check_plan(zip_path)
    relative_zip_path = os.path.join("datasets", dataset_id, "data.zip")

    conn = get_db()
    try:
        conn.execute(
            """INSERT INTO datasets (id, name, description, submitted_by, submitted_at, zip_path, has_plan)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (dataset_id, name, description, submitted_by, now, relative_zip_path, 1 if has_plan else 0)
        )
        conn.commit()
        row = conn.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
        return dict(row)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Chunked upload (large datasets, resumable)
# ---------------------------------------------------------------------------

class InitUploadRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    submitted_by: Optional[str] = ""
    total_chunks: int
    total_size: Optional[int] = None  # bytes, informational


@router.post("/upload/init")
def init_upload(req: InitUploadRequest, _: str = Depends(verify_api_key)):
    """
    Start a resumable chunked upload session.
    Returns upload_id to be used for subsequent chunk uploads.
    """
    if req.total_chunks < 1:
        raise HTTPException(status_code=400, detail="total_chunks must be >= 1")

    upload_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    os.makedirs(_upload_dir(upload_id), exist_ok=True)

    conn = get_db()
    try:
        conn.execute(
            """INSERT INTO uploads (id, name, description, submitted_by, total_chunks, total_size, received_chunks, created_at, status)
               VALUES (?, ?, ?, ?, ?, ?, '[]', ?, 'in_progress')""",
            (upload_id, req.name, req.description, req.submitted_by,
             req.total_chunks, req.total_size, now)
        )
        conn.commit()
        return {
            "upload_id": upload_id,
            "total_chunks": req.total_chunks,
            "status": "in_progress",
        }
    finally:
        conn.close()


@router.get("/upload/{upload_id}/status")
def get_upload_status(upload_id: str, _: str = Depends(verify_api_key)):
    """
    Query which chunks have been received. Use this to resume a failed upload:
    compare received_chunks against range(total_chunks) and re-send missing ones.
    """
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM uploads WHERE id = ?", (upload_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Upload session not found")
        row = dict(row)
        received = json.loads(row["received_chunks"])
        missing = [i for i in range(row["total_chunks"]) if i not in received]
        return {
            "upload_id": upload_id,
            "name": row["name"],
            "status": row["status"],
            "total_chunks": row["total_chunks"],
            "total_size": row["total_size"],
            "received_chunks": sorted(received),
            "missing_chunks": missing,
            "progress_pct": round(len(received) / row["total_chunks"] * 100, 1),
        }
    finally:
        conn.close()


@router.post("/upload/{upload_id}/chunk/{chunk_index}")
async def upload_chunk(
    upload_id: str,
    chunk_index: int,
    request: Request,
    _: str = Depends(verify_api_key),
):
    """
    Upload a single chunk (raw bytes body).
    Chunks may be uploaded in any order and re-uploaded safely (idempotent).
    Recommended chunk size: 10–100 MB.
    """
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM uploads WHERE id = ?", (upload_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Upload session not found")
        row = dict(row)
        if row["status"] != "in_progress":
            raise HTTPException(status_code=400, detail=f"Upload is not in progress (status: {row['status']})")
        if chunk_index < 0 or chunk_index >= row["total_chunks"]:
            raise HTTPException(status_code=400, detail=f"chunk_index out of range [0, {row['total_chunks'] - 1}]")

        # Write chunk to disk
        chunk_file = _chunk_path(upload_id, chunk_index)
        body = await request.body()
        if not body:
            raise HTTPException(status_code=400, detail="Empty chunk body")
        with open(chunk_file, "wb") as f:
            f.write(body)

        # Update received_chunks list
        received = json.loads(row["received_chunks"])
        if chunk_index not in received:
            received.append(chunk_index)
            conn.execute(
                "UPDATE uploads SET received_chunks = ? WHERE id = ?",
                (json.dumps(received), upload_id)
            )
            conn.commit()

        return {
            "ok": True,
            "chunk_index": chunk_index,
            "received": len(received),
            "total_chunks": row["total_chunks"],
        }
    finally:
        conn.close()


@router.post("/upload/{upload_id}/complete")
def complete_upload(upload_id: str, _: str = Depends(verify_api_key)):
    """
    Assemble all chunks into the final ZIP, validate it, and create the dataset record.
    All chunks must be present before calling this.
    """
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM uploads WHERE id = ?", (upload_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Upload session not found")
        row = dict(row)
        if row["status"] != "in_progress":
            raise HTTPException(status_code=400, detail=f"Upload is not in progress (status: {row['status']})")

        received = json.loads(row["received_chunks"])
        missing = [i for i in range(row["total_chunks"]) if i not in received]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Missing {len(missing)} chunk(s): {missing[:10]}{'...' if len(missing) > 10 else ''}"
            )

        # Mark as assembling
        conn.execute("UPDATE uploads SET status = 'assembling' WHERE id = ?", (upload_id,))
        conn.commit()

        # Assemble chunks → dataset zip
        dataset_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        dataset_dir = os.path.join(settings.DATA_DIR, "datasets", dataset_id)
        os.makedirs(dataset_dir, exist_ok=True)
        zip_path = os.path.join(dataset_dir, "data.zip")

        logger.info(f"Assembling {row['total_chunks']} chunks for upload {upload_id} → {zip_path}")
        with open(zip_path, "wb") as out:
            for i in range(row["total_chunks"]):
                chunk_file = _chunk_path(upload_id, i)
                with open(chunk_file, "rb") as cf:
                    shutil.copyfileobj(cf, out)

        # Validate and check for nnUNetPlans.json
        has_plan = _validate_zip_and_check_plan(zip_path)
        relative_zip_path = os.path.join("datasets", dataset_id, "data.zip")

        # Create dataset record
        conn.execute(
            """INSERT INTO datasets (id, name, description, submitted_by, submitted_at, zip_path, has_plan)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (dataset_id, row["name"], row["description"], row["submitted_by"],
             now, relative_zip_path, 1 if has_plan else 0)
        )
        conn.execute("UPDATE uploads SET status = 'complete' WHERE id = ?", (upload_id,))
        conn.commit()

        # Clean up chunks
        shutil.rmtree(_upload_dir(upload_id), ignore_errors=True)
        logger.info(f"Upload {upload_id} complete → dataset {dataset_id}")

        dataset_row = conn.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
        return dict(dataset_row)

    except HTTPException:
        conn.execute("UPDATE uploads SET status = 'in_progress' WHERE id = ?", (upload_id,))
        conn.commit()
        raise
    except Exception as e:
        conn.execute("UPDATE uploads SET status = 'failed' WHERE id = ?", (upload_id,))
        conn.commit()
        logger.error(f"Failed to assemble upload {upload_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Assembly failed: {e}")
    finally:
        conn.close()


@router.delete("/upload/{upload_id}")
def cancel_upload(upload_id: str, _: str = Depends(verify_api_key)):
    """Cancel an in-progress upload and delete all stored chunks."""
    conn = get_db()
    try:
        row = conn.execute("SELECT id FROM uploads WHERE id = ?", (upload_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Upload session not found")
        conn.execute("DELETE FROM uploads WHERE id = ?", (upload_id,))
        conn.commit()
        shutil.rmtree(_upload_dir(upload_id), ignore_errors=True)
        return {"ok": True}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Dataset list / detail / download  (unchanged)
# ---------------------------------------------------------------------------

@router.get("/")
def list_datasets(_: str = Depends(verify_api_key)):
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM datasets ORDER BY submitted_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/{dataset_id}")
def get_dataset(dataset_id: str, _: str = Depends(verify_api_key)):
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Dataset not found")
        return dict(row)
    finally:
        conn.close()


@router.get("/{dataset_id}/download")
def download_dataset(dataset_id: str, _: str = Depends(verify_api_key)):
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Dataset not found")
        zip_path = os.path.join(settings.DATA_DIR, row["zip_path"])
        if not os.path.exists(zip_path):
            raise HTTPException(status_code=404, detail="Dataset file not found")
        return FileResponse(zip_path, media_type="application/zip", filename=f"dataset_{dataset_id}.zip")
    finally:
        conn.close()
