import uuid
import os
import zipfile
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse
from app.core.auth import verify_api_key
from app.core.database import get_db
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


def _check_has_plan(zip_path: str) -> bool:
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for name in zf.namelist():
                if os.path.basename(name) == "nnUNetPlans.json":
                    return True
    except Exception:
        pass
    return False


@router.post("/")
async def submit_dataset(
    zip_file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(""),
    submitted_by: str = Form(""),
    _: str = Depends(verify_api_key),
):
    dataset_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    dataset_dir = os.path.join(settings.DATA_DIR, "datasets", dataset_id)
    os.makedirs(dataset_dir, exist_ok=True)
    zip_path = os.path.join(dataset_dir, "data.zip")

    content = await zip_file.read()

    # Validate zip
    import io
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            has_plan = any(os.path.basename(n) == "nnUNetPlans.json" for n in zf.namelist())
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid ZIP archive")

    with open(zip_path, "wb") as f:
        f.write(content)

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
