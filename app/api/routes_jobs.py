import uuid
import os
import json
import shutil
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Request
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel
from app.core.auth import verify_api_key
from app.core.database import get_db
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

VALID_STATUSES = {
    "pending", "assigned", "preprocessing", "training",
    "validating", "uploading", "done", "failed", "cancelled"
}


class CreateJobRequest(BaseModel):
    dataset_id: str
    worker_id: str
    configuration: str


class UpdateStatusRequest(BaseModel):
    status: str
    error_message: Optional[str] = None


class PreprocessingProgressRequest(BaseModel):
    total_images: Optional[int] = None
    done_images: Optional[int] = None
    mean_time_per_image_s: Optional[float] = None


class TrainingProgressRequest(BaseModel):
    fold: int
    epoch: int
    learning_rate: Optional[float] = None
    train_loss: Optional[float] = None
    val_loss: Optional[float] = None
    pseudo_dice: Optional[str] = None  # JSON array as string
    epoch_time_s: Optional[float] = None


class ValidationResultRequest(BaseModel):
    fold: int
    summary_json: str


@router.post("/")
def create_job(req: CreateJobRequest, _: str = Depends(verify_api_key)):
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    try:
        dataset = conn.execute("SELECT id FROM datasets WHERE id = ?", (req.dataset_id,)).fetchone()
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        worker = conn.execute("SELECT id FROM workers WHERE id = ?", (req.worker_id,)).fetchone()
        if not worker:
            raise HTTPException(status_code=404, detail="Worker not found")

        job_id = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO training_jobs (id, dataset_id, worker_id, configuration, status, created_at)
               VALUES (?, ?, ?, ?, 'pending', ?)""",
            (job_id, req.dataset_id, req.worker_id, req.configuration, now)
        )
        conn.commit()
        row = conn.execute("SELECT * FROM training_jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row)
    finally:
        conn.close()


@router.get("/")
def list_jobs(
    worker_id: Optional[str] = None,
    status: Optional[str] = None,
    _: str = Depends(verify_api_key),
):
    conn = get_db()
    try:
        query = "SELECT * FROM training_jobs WHERE 1=1"
        params = []
        if worker_id:
            query += " AND worker_id = ?"
            params.append(worker_id)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC"
        rows = conn.execute(query, params).fetchall()
        jobs = []
        for row in rows:
            j = dict(row)
            tp = conn.execute(
                "SELECT fold, epoch FROM training_progress WHERE job_id=? ORDER BY id DESC LIMIT 1",
                (j["id"],)
            ).fetchone()
            if tp:
                j["latest_fold"] = tp["fold"]
                j["latest_epoch"] = tp["epoch"]
            jobs.append(j)
        return jobs
    finally:
        conn.close()


@router.get("/{job_id}")
def get_job(job_id: str, _: str = Depends(verify_api_key)):
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM training_jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")

        job = dict(row)

        # Latest preprocessing progress
        pp = conn.execute(
            "SELECT * FROM preprocessing_progress WHERE job_id = ? ORDER BY id DESC LIMIT 1",
            (job_id,)
        ).fetchone()
        job["preprocessing_progress"] = dict(pp) if pp else None

        # Training progress (all rows)
        tp_rows = conn.execute(
            "SELECT * FROM training_progress WHERE job_id = ? ORDER BY fold, epoch",
            (job_id,)
        ).fetchall()
        job["training_progress"] = [dict(r) for r in tp_rows]

        # Validation results
        vr_rows = conn.execute(
            "SELECT * FROM validation_results WHERE job_id = ? ORDER BY fold",
            (job_id,)
        ).fetchall()
        job["validation_results"] = [dict(r) for r in vr_rows]

        return job
    finally:
        conn.close()


@router.delete("/{job_id}")
def delete_job(job_id: str, _: str = Depends(verify_api_key)):
    """Hard-delete a job and all its related records."""
    conn = get_db()
    try:
        row = conn.execute("SELECT id FROM training_jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        conn.execute("DELETE FROM training_progress WHERE job_id = ?", (job_id,))
        conn.execute("DELETE FROM preprocessing_progress WHERE job_id = ?", (job_id,))
        conn.execute("DELETE FROM validation_results WHERE job_id = ?", (job_id,))
        conn.execute("DELETE FROM models WHERE job_id = ?", (job_id,))
        conn.execute("DELETE FROM training_jobs WHERE id = ?", (job_id,))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@router.put("/{job_id}/status")
def update_job_status(job_id: str, req: UpdateStatusRequest, _: str = Depends(verify_api_key)):
    if req.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {req.status}")
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    try:
        row = conn.execute("SELECT id FROM training_jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")

        updates = ["status = ?"]
        params = [req.status]

        if req.status in ("assigned", "preprocessing") and req.status == "assigned":
            updates.append("started_at = ?")
            params.append(now)
        if req.status in ("done", "failed", "cancelled"):
            updates.append("completed_at = ?")
            params.append(now)
        if req.error_message is not None:
            updates.append("error_message = ?")
            params.append(req.error_message)

        params.append(job_id)
        conn.execute(f"UPDATE training_jobs SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
        row = conn.execute("SELECT * FROM training_jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row)
    finally:
        conn.close()


@router.post("/{job_id}/preprocessing_progress")
def report_preprocessing_progress(
    job_id: str, req: PreprocessingProgressRequest, _: str = Depends(verify_api_key)
):
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    try:
        row = conn.execute("SELECT id FROM training_jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        conn.execute(
            """INSERT INTO preprocessing_progress (job_id, total_images, done_images, mean_time_per_image_s, reported_at)
               VALUES (?, ?, ?, ?, ?)""",
            (job_id, req.total_images, req.done_images, req.mean_time_per_image_s, now)
        )
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@router.post("/{job_id}/training_progress")
def report_training_progress(
    job_id: str, req: TrainingProgressRequest, _: str = Depends(verify_api_key)
):
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    try:
        row = conn.execute("SELECT id FROM training_jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        conn.execute(
            """INSERT INTO training_progress
               (job_id, fold, epoch, learning_rate, train_loss, val_loss, pseudo_dice, epoch_time_s, reported_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (job_id, req.fold, req.epoch, req.learning_rate, req.train_loss,
             req.val_loss, req.pseudo_dice, req.epoch_time_s, now)
        )
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@router.post("/{job_id}/validation_result")
def report_validation_result(
    job_id: str, req: ValidationResultRequest, _: str = Depends(verify_api_key)
):
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    try:
        row = conn.execute("SELECT id FROM training_jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        conn.execute(
            "INSERT INTO validation_results (job_id, fold, summary_json, reported_at) VALUES (?, ?, ?, ?)",
            (job_id, req.fold, req.summary_json, now)
        )
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@router.post("/{job_id}/log/{fold}")
async def upload_log(job_id: str, fold: int, request: Request, _: str = Depends(verify_api_key)):
    conn = get_db()
    try:
        row = conn.execute("SELECT id FROM training_jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
    finally:
        conn.close()

    log_dir = os.path.join(settings.DATA_DIR, "logs", job_id, f"fold{fold}")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "training_log.txt")

    body = await request.body()
    with open(log_path, "wb") as f:
        f.write(body)

    return {"ok": True}


@router.get("/{job_id}/log/{fold}")
def get_log(job_id: str, fold: int, _: str = Depends(verify_api_key)):
    log_path = os.path.join(settings.DATA_DIR, "logs", job_id, f"fold{fold}", "training_log.txt")
    if not os.path.exists(log_path):
        raise HTTPException(status_code=404, detail="Log not found")
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    return PlainTextResponse(content)


@router.post("/{job_id}/model")
async def upload_model(
    job_id: str,
    zip_file: UploadFile = File(...),
    _: str = Depends(verify_api_key),
):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, dataset_id FROM training_jobs WHERE id = ?", (job_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        dataset_id = row["dataset_id"]

        model_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        model_dir = os.path.join(settings.DATA_DIR, "models", model_id)
        os.makedirs(model_dir, exist_ok=True)
        zip_path = os.path.join(model_dir, "model.zip")

        content = await zip_file.read()
        with open(zip_path, "wb") as f:
            f.write(content)

        relative_path = os.path.join("models", model_id, "model.zip")
        conn.execute(
            """INSERT INTO models (id, job_id, dataset_id, zip_path, status, created_at)
               VALUES (?, ?, ?, ?, 'pending_approval', ?)""",
            (model_id, job_id, dataset_id, relative_path, now)
        )
        conn.commit()
        model_row = conn.execute("SELECT * FROM models WHERE id = ?", (model_id,)).fetchone()
        return dict(model_row)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Chunked model upload (for large model ZIPs that exceed ingress size limits)
# ---------------------------------------------------------------------------

def _model_upload_dir(upload_id: str) -> str:
    return os.path.join(settings.DATA_DIR, "model_uploads", upload_id)

def _model_upload_meta_path(upload_id: str) -> str:
    return os.path.join(_model_upload_dir(upload_id), "meta.json")

def _model_chunk_path(upload_id: str, index: int) -> str:
    return os.path.join(_model_upload_dir(upload_id), f"{index:06d}.chunk")

def _load_model_upload_meta(upload_id: str) -> dict:
    path = _model_upload_meta_path(upload_id)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Model upload session not found")
    with open(path) as f:
        return json.load(f)

def _save_model_upload_meta(upload_id: str, meta: dict):
    with open(_model_upload_meta_path(upload_id), "w") as f:
        json.dump(meta, f)


class InitModelUploadRequest(BaseModel):
    total_chunks: int
    total_size: Optional[int] = None  # bytes, informational


@router.post("/{job_id}/model/upload/init")
def init_model_upload(job_id: str, req: InitModelUploadRequest, _: str = Depends(verify_api_key)):
    """Start a chunked model upload session. Returns upload_id."""
    conn = get_db()
    try:
        row = conn.execute("SELECT id FROM training_jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
    finally:
        conn.close()

    if req.total_chunks < 1:
        raise HTTPException(status_code=400, detail="total_chunks must be >= 1")

    upload_id = str(uuid.uuid4())
    os.makedirs(_model_upload_dir(upload_id), exist_ok=True)
    _save_model_upload_meta(upload_id, {
        "job_id": job_id,
        "total_chunks": req.total_chunks,
        "total_size": req.total_size,
        "received_chunks": [],
    })
    return {"upload_id": upload_id, "total_chunks": req.total_chunks}


@router.post("/{job_id}/model/upload/{upload_id}/chunk/{chunk_index}")
async def upload_model_chunk(
    job_id: str,
    upload_id: str,
    chunk_index: int,
    request: Request,
    _: str = Depends(verify_api_key),
):
    """Upload one chunk (raw bytes body). Idempotent."""
    meta = _load_model_upload_meta(upload_id)
    if meta["job_id"] != job_id:
        raise HTTPException(status_code=400, detail="upload_id does not belong to this job")
    if chunk_index < 0 or chunk_index >= meta["total_chunks"]:
        raise HTTPException(status_code=400, detail=f"chunk_index out of range [0, {meta['total_chunks'] - 1}]")

    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Empty chunk body")

    with open(_model_chunk_path(upload_id, chunk_index), "wb") as f:
        f.write(body)

    if chunk_index not in meta["received_chunks"]:
        meta["received_chunks"].append(chunk_index)
        _save_model_upload_meta(upload_id, meta)

    return {
        "ok": True,
        "chunk_index": chunk_index,
        "received": len(meta["received_chunks"]),
        "total_chunks": meta["total_chunks"],
    }


@router.post("/{job_id}/model/upload/{upload_id}/complete")
def complete_model_upload(job_id: str, upload_id: str, _: str = Depends(verify_api_key)):
    """Assemble all chunks and create the model record."""
    meta = _load_model_upload_meta(upload_id)
    if meta["job_id"] != job_id:
        raise HTTPException(status_code=400, detail="upload_id does not belong to this job")

    missing = [i for i in range(meta["total_chunks"]) if i not in meta["received_chunks"]]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing {len(missing)} chunk(s): {missing[:10]}{'...' if len(missing) > 10 else ''}"
        )

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, dataset_id FROM training_jobs WHERE id = ?", (job_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        dataset_id = row["dataset_id"]

        model_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        model_dir = os.path.join(settings.DATA_DIR, "models", model_id)
        os.makedirs(model_dir, exist_ok=True)
        zip_path = os.path.join(model_dir, "model.zip")

        logger.info(f"Assembling {meta['total_chunks']} model chunks for upload {upload_id} → {zip_path}")
        with open(zip_path, "wb") as out:
            for i in range(meta["total_chunks"]):
                with open(_model_chunk_path(upload_id, i), "rb") as cf:
                    shutil.copyfileobj(cf, out)

        relative_path = os.path.join("models", model_id, "model.zip")
        conn.execute(
            """INSERT INTO models (id, job_id, dataset_id, zip_path, status, created_at)
               VALUES (?, ?, ?, ?, 'pending_approval', ?)""",
            (model_id, job_id, dataset_id, relative_path, now)
        )
        conn.commit()

        shutil.rmtree(_model_upload_dir(upload_id), ignore_errors=True)
        logger.info(f"Model upload {upload_id} complete → model {model_id}")

        model_row = conn.execute("SELECT * FROM models WHERE id = ?", (model_id,)).fetchone()
        return dict(model_row)
    finally:
        conn.close()
