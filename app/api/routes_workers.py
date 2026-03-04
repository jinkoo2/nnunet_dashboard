import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from app.core.auth import verify_api_key
from app.core.database import get_db
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

OFFLINE_THRESHOLD_SECONDS = 120


class WorkerRegisterRequest(BaseModel):
    name: str
    hostname: Optional[str] = None
    cpu_cores: Optional[int] = None
    gpu_memory_gb: Optional[float] = None
    gpu_name: Optional[str] = None
    system_memory_gb: Optional[float] = None
    description: Optional[str] = None


class HeartbeatRequest(BaseModel):
    status: Optional[str] = "online"


def _worker_row_to_dict(row, now: datetime) -> dict:
    d = dict(row)
    if d.get("last_heartbeat"):
        try:
            hb = datetime.fromisoformat(d["last_heartbeat"])
            if hb.tzinfo is None:
                hb = hb.replace(tzinfo=timezone.utc)
            if (now - hb).total_seconds() > OFFLINE_THRESHOLD_SECONDS:
                d["status"] = "offline"
        except Exception:
            d["status"] = "offline"
    else:
        d["status"] = "offline"
    return d


@router.post("/register")
def register_worker(req: WorkerRegisterRequest, _: str = Depends(verify_api_key)):
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    try:
        existing = conn.execute("SELECT id FROM workers WHERE name = ?", (req.name,)).fetchone()
        if existing:
            worker_id = existing["id"]
            conn.execute(
                """UPDATE workers SET hostname=?, cpu_cores=?, gpu_memory_gb=?, gpu_name=?,
                   system_memory_gb=?, description=?, last_heartbeat=?, status='online' WHERE id=?""",
                (req.hostname, req.cpu_cores, req.gpu_memory_gb, req.gpu_name,
                 req.system_memory_gb, req.description, now, worker_id)
            )
        else:
            worker_id = str(uuid.uuid4())
            conn.execute(
                """INSERT INTO workers (id, name, hostname, cpu_cores, gpu_memory_gb, gpu_name,
                   system_memory_gb, description, registered_at, last_heartbeat, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'online')""",
                (worker_id, req.name, req.hostname, req.cpu_cores, req.gpu_memory_gb,
                 req.gpu_name, req.system_memory_gb, req.description, now, now)
            )
        conn.commit()
        row = conn.execute("SELECT * FROM workers WHERE id = ?", (worker_id,)).fetchone()
        return dict(row)
    finally:
        conn.close()


@router.post("/{worker_id}/heartbeat")
def heartbeat(worker_id: str, req: HeartbeatRequest, _: str = Depends(verify_api_key)):
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    try:
        row = conn.execute("SELECT id FROM workers WHERE id = ?", (worker_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Worker not found")
        conn.execute(
            "UPDATE workers SET last_heartbeat=?, status=? WHERE id=?",
            (now, req.status or "online", worker_id)
        )
        conn.commit()
        return {"ok": True, "last_heartbeat": now}
    finally:
        conn.close()


@router.get("/")
def list_workers(_: str = Depends(verify_api_key)):
    now = datetime.now(timezone.utc)
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM workers ORDER BY registered_at DESC").fetchall()
        return [_worker_row_to_dict(r, now) for r in rows]
    finally:
        conn.close()


@router.get("/{worker_id}")
def get_worker(worker_id: str, _: str = Depends(verify_api_key)):
    now = datetime.now(timezone.utc)
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM workers WHERE id = ?", (worker_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Worker not found")
        return _worker_row_to_dict(row, now)
    finally:
        conn.close()
