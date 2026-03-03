# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Centralized nnUNet training and model management server. Training requesters submit datasets (ZIP) via API; administrators create and assign training jobs to remote workers via a web dashboard; workers poll the REST API for work, run nnUNet preprocessing + training, report detailed progress, and upload trained model ZIPs. Admins approve models for use.

Companion to `nnunet_server` (inference + data browser). No Redis/RQ — workers poll REST API directly.

## Commands

```bash
# Development (conda env: nnunet_dashboard, Python 3.12)
conda activate nnunet_dashboard
poetry install
poetry run dev              # starts on http://localhost:9333

# Or run directly with uvicorn
/home/jk/miniconda3/envs/nnunet_dashboard/bin/uvicorn app.main:app --reload --port 9333

# Production
poetry run prod
docker-compose up --build   # single api service, port 9333

# Install deps without poetry (into conda env)
/home/jk/miniconda3/envs/nnunet_dashboard/bin/pip install -e .
```

## Architecture

**Stack:** Python 3.12, FastAPI, SQLite (raw sqlite3, WAL mode), Poetry, Docker

**Key files:**
- `app/main.py` — FastAPI app factory, route registration, startup (`init_db`)
- `app/scripts.py` — CLI entry points (`run_dev`, `run_prod`), both on port 9333
- `app/core/config.py` — Pydantic `BaseSettings` loaded from `.env`
- `app/core/auth.py` — HTTP Basic Auth (dashboard) + API key header (API routes)
- `app/core/database.py` — `init_db()` creates all tables; `get_db()` returns connection
- `app/api/routes_dashboard.py` — Single-page web UI (inline HTML/CSS/JS), Basic Auth gated
- `app/api/routes_datasets.py` — Dataset submit (direct + chunked), list, detail, download, file viewer
- `app/api/routes_jobs.py` — Training job CRUD, status updates, progress reporting, log upload, model upload
- `app/api/routes_models.py` — Model list, approve/reject, description edit, download
- `app/api/routes_workers.py` — Worker register (upsert by name), heartbeat, list, detail

## Database Schema (8 tables)

- `workers` — registered remote worker nodes (id, name, hostname, gpu_name, gpu_memory_gb, cpu_cores, status, last_heartbeat)
- `datasets` — submitted dataset ZIPs (id, name, description, submitted_by, zip_path, has_plan)
- `training_jobs` — jobs created by admin (id, dataset_id, worker_id, configuration, status, timestamps, error_message)
- `preprocessing_progress` — per-job preprocessing updates (total_images, done_images, mean_time_per_image_s)
- `training_progress` — per-epoch metrics per fold (epoch, learning_rate, train_loss, val_loss, pseudo_dice JSON, epoch_time_s)
- `validation_results` — fold validation summary JSON blobs
- `models` — uploaded trained model ZIPs (id, job_id, dataset_id, zip_path, status, approved_by)
- `uploads` — chunked upload sessions (id, total_chunks, received_chunks JSON array, status)

## Authentication

Two schemes in `app/core/auth.py`:
- **HTTP Basic Auth** — `DASHBOARD_USER` / `DASHBOARD_PASSWORD` — gates `/dashboard`
- **API Key** — `X-Api-Key: <API_KEY>` header — required on all `/api/*` routes (workers and requesters)

## API Route Prefixes

| prefix | file | description |
|---|---|---|
| `/api/workers` | routes_workers.py | register, heartbeat, list, detail |
| `/api/datasets` | routes_datasets.py | submit, chunked upload, list, detail, download, file viewer |
| `/api/jobs` | routes_jobs.py | CRUD, progress reporting, log/model upload |
| `/api/models` | routes_models.py | list, approve/reject, download |
| `/dashboard` | routes_dashboard.py | single-page admin UI (Basic Auth) |

## Dataset Chunked Upload Flow

Large dataset ZIPs (e.g. hundreds of CT scans) use a resumable chunked upload:
1. `POST /api/datasets/upload/init` — returns `upload_id`
2. `POST /api/datasets/upload/{id}/chunk/{n}` — raw bytes body, idempotent, any order
3. `GET /api/datasets/upload/{id}/status` — check received/missing chunks
4. `POST /api/datasets/upload/{id}/complete` — assemble chunks → validate ZIP → create dataset record
5. `DELETE /api/datasets/upload/{id}` — cancel and clean up

Chunks stored at `data/uploads/{upload_id}/{n:06d}.chunk`.

## Worker Polling Flow

1. `POST /api/workers/register` — upsert by name, returns worker_id
2. `POST /api/workers/{id}/heartbeat` — keep status alive (worker considered offline if >120s since last heartbeat)
3. `GET /api/jobs?worker_id={id}&status=pending` — poll for assigned work
4. `PUT /api/jobs/{id}/status` — advance status: `pending → assigned → preprocessing → training → validating → uploading → done / failed`
5. `POST /api/jobs/{id}/preprocessing_progress` — report image counts
6. `POST /api/jobs/{id}/training_progress` — report per-fold/epoch metrics
7. `POST /api/jobs/{id}/log/{fold}` — upload latest log text (overwrites each time)
8. `POST /api/jobs/{id}/validation_result` — upload fold summary.json content
9. `POST /api/jobs/{id}/model` — multipart ZIP upload → creates `models` row with `status=pending_approval`

## Web Dashboard UI

Single self-contained HTML/CSS/JS page in `routes_dashboard.py` (`DASHBOARD_HTML` string). API key injected at serve time by replacing `__DASHBOARD_API_KEY__` placeholder with `settings.API_KEY`. Polls every 10 seconds. Four tabs:

- **Datasets** — table with Files button (JSONEditor tree viewer modal for dataset.json / dataset_fingerprint.json / nnUNetPlans.json) and Create Job button
- **Training Jobs** — expandable rows with preprocessing progress bar, per-fold epoch metrics table, log viewer
- **Models** — approve/reject buttons, description edit, download link for approved models
- **Workers** — status dots, last heartbeat, GPU info; offline if heartbeat >120s

JSONEditor loaded lazily from CDN (`cdnjs.cloudflare.com/ajax/libs/jsoneditor/10.1.0`). Dark mode applied via scoped CSS overrides on `.file-viewer .jsoneditor`.

## Data Layout

```
data/
├── datasets/{dataset_id}/data.zip
├── logs/{job_id}/fold{n}/training_log.txt
├── models/{model_id}/model.zip
└── uploads/{upload_id}/{n:06d}.chunk   ← cleaned up after complete/cancel
```

## Configuration (`.env`)

| Variable | Default | Description |
|---|---|---|
| `API_KEY` | `changeme` | Shared key for all `/api/*` endpoints |
| `DASHBOARD_USER` | `admin` | Basic auth username |
| `DASHBOARD_PASSWORD` | `admin` | Basic auth password |
| `DATA_DIR` | `/app/data` | Root for stored files |
| `DB_PATH` | `/app/data/dashboard.db` | SQLite database path |
| `LOG_LEVEL` | `DEBUG` | Logging level |

## Docker

Single `api` service in `docker-compose.yml`. Port `9333:9333`. Volume `./data:/app/data`. Reads `.env` via `env_file`.

## Integration with nnunet_server

`nnunet_server` can push preprocessed datasets directly to this dashboard:
- Context menu **"Upload to Training Dashboard"** on `preprocessed/Dataset###_Name` folders in the data browser
- Zips `raw/Dataset###_Name/` + 3 plan files from preprocessed, then uploads via chunked upload API
- Configured via `TRAINING_DASHBOARD_URL` and `TRAINING_DASHBOARD_API_KEY` in nnunet_server's `.env` and `docker-compose.yml`

## Conventions

- Route files named `routes_*.py`
- All primary keys are `uuid.uuid4()` strings
- Timestamps are UTC ISO strings (`datetime.now(timezone.utc).isoformat()`)
- `get_db()` returns a sqlite3 connection with `row_factory = sqlite3.Row`; always close in `finally`
- Web UI is a single self-contained HTML string in the route file (same pattern as nnunet_server's data browser)
