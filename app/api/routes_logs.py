from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from app.core.auth import verify_api_key
from app.core.database import get_db
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

LOG_RETENTION_DAYS = 7


class LogEntry(BaseModel):
    worker_id: Optional[str] = None
    worker_name: Optional[str] = None
    level: str = "INFO"
    message: str


@router.post("/")
def post_log(entry: LogEntry, _: str = Depends(verify_api_key)):
    now = datetime.now(timezone.utc).isoformat()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=LOG_RETENTION_DAYS)).isoformat()
    conn = get_db()
    try:
        conn.execute("DELETE FROM worker_logs WHERE created_at < ?", (cutoff,))
        conn.execute(
            "INSERT INTO worker_logs (worker_id, worker_name, level, message, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (entry.worker_id, entry.worker_name, entry.level, entry.message, now),
        )
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@router.get("/")
def get_logs(
    page: int = 1,
    per_page: int = 20,
    worker_id: Optional[str] = None,
    _: str = Depends(verify_api_key),
):
    conn = get_db()
    try:
        if worker_id:
            total = conn.execute(
                "SELECT COUNT(*) FROM worker_logs WHERE worker_id = ?", (worker_id,)
            ).fetchone()[0]
            offset = (page - 1) * per_page
            rows = conn.execute(
                "SELECT * FROM worker_logs WHERE worker_id = ? ORDER BY id DESC LIMIT ? OFFSET ?",
                (worker_id, per_page, offset),
            ).fetchall()
        else:
            total = conn.execute("SELECT COUNT(*) FROM worker_logs").fetchone()[0]
            offset = (page - 1) * per_page
            rows = conn.execute(
                "SELECT * FROM worker_logs ORDER BY id DESC LIMIT ? OFFSET ?",
                (per_page, offset),
            ).fetchall()
        return {
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": max(1, -(-total // per_page)),
            "items": [dict(r) for r in rows],
        }
    finally:
        conn.close()


@router.delete("/")
def clear_logs(worker_id: Optional[str] = None, _: str = Depends(verify_api_key)):
    conn = get_db()
    try:
        if worker_id:
            conn.execute("DELETE FROM worker_logs WHERE worker_id = ?", (worker_id,))
        else:
            conn.execute("DELETE FROM worker_logs")
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()
