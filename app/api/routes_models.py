import os
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.core.auth import verify_api_key
from app.core.database import get_db
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


class UpdateModelRequest(BaseModel):
    description: Optional[str] = None


class ApproveRequest(BaseModel):
    approved_by: Optional[str] = "admin"


class RejectRequest(BaseModel):
    reason: Optional[str] = None


@router.get("/")
def list_models(status: Optional[str] = None, _: str = Depends(verify_api_key)):
    conn = get_db()
    try:
        query = "SELECT * FROM models WHERE 1=1"
        params = []
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/{model_id}")
def get_model(model_id: str, _: str = Depends(verify_api_key)):
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM models WHERE id = ?", (model_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Model not found")
        model = dict(row)
        vr_rows = conn.execute(
            "SELECT * FROM validation_results WHERE job_id = ? ORDER BY fold",
            (model["job_id"],)
        ).fetchall()
        model["validation_results"] = [dict(r) for r in vr_rows]
        return model
    finally:
        conn.close()


@router.put("/{model_id}")
def update_model(model_id: str, req: UpdateModelRequest, _: str = Depends(verify_api_key)):
    conn = get_db()
    try:
        row = conn.execute("SELECT id FROM models WHERE id = ?", (model_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Model not found")
        if req.description is not None:
            conn.execute("UPDATE models SET description = ? WHERE id = ?", (req.description, model_id))
            conn.commit()
        row = conn.execute("SELECT * FROM models WHERE id = ?", (model_id,)).fetchone()
        return dict(row)
    finally:
        conn.close()


@router.post("/{model_id}/approve")
def approve_model(model_id: str, req: ApproveRequest, _: str = Depends(verify_api_key)):
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    try:
        row = conn.execute("SELECT id, status FROM models WHERE id = ?", (model_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Model not found")
        if row["status"] != "pending_approval":
            raise HTTPException(status_code=400, detail=f"Model is not pending approval (status: {row['status']})")
        conn.execute(
            "UPDATE models SET status='approved', approved_by=?, approved_at=? WHERE id=?",
            (req.approved_by, now, model_id)
        )
        conn.commit()
        row = conn.execute("SELECT * FROM models WHERE id = ?", (model_id,)).fetchone()
        return dict(row)
    finally:
        conn.close()


@router.post("/{model_id}/reject")
def reject_model(model_id: str, req: RejectRequest, _: str = Depends(verify_api_key)):
    conn = get_db()
    try:
        row = conn.execute("SELECT id, status FROM models WHERE id = ?", (model_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Model not found")
        if row["status"] != "pending_approval":
            raise HTTPException(status_code=400, detail=f"Model is not pending approval (status: {row['status']})")
        conn.execute("UPDATE models SET status='rejected' WHERE id=?", (model_id,))
        conn.commit()
        row = conn.execute("SELECT * FROM models WHERE id = ?", (model_id,)).fetchone()
        return dict(row)
    finally:
        conn.close()


@router.get("/{model_id}/download")
def download_model(model_id: str, _: str = Depends(verify_api_key)):
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM models WHERE id = ?", (model_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Model not found")
        zip_path = os.path.join(settings.DATA_DIR, row["zip_path"])
        if not os.path.exists(zip_path):
            raise HTTPException(status_code=404, detail="Model file not found")
        return FileResponse(zip_path, media_type="application/zip", filename=f"model_{model_id}.zip")
    finally:
        conn.close()
