# nnUNet Dashboard

Centralized nnUNet training and model management server. Training requesters submit datasets via API; administrators create and assign training jobs to workers via a web dashboard; remote worker nodes poll the API for work, run nnUNet preprocessing + training, report detailed progress, and upload trained model ZIPs. Admins then approve models for use.

## Stack

- **FastAPI** — REST API + web dashboard
- **SQLite** (raw sqlite3) — persistent storage
- **Poetry** — dependency management
- **Docker** — containerized deployment

No Redis/RQ — workers poll REST API directly.

## Quick Start

```bash
# Development
cp .env.example .env
poetry install
poetry run dev      # starts on http://localhost:9100
```

Open http://localhost:9100/dashboard (default: admin/admin)

## Docker

```bash
cp .env.example .env
# Edit .env — set a strong API_KEY and DASHBOARD_PASSWORD
docker-compose up --build
```

## API Authentication

- **Dashboard** (`/dashboard`): HTTP Basic Auth — `DASHBOARD_USER` / `DASHBOARD_PASSWORD`
- **API** (`/api/*`): `X-Api-Key` header — `API_KEY`

## Worker Polling Flow

1. Worker registers: `POST /api/workers/register`
2. Worker polls: `GET /api/jobs?worker_id={id}&status=pending`
3. Worker acknowledges: `PUT /api/jobs/{id}/status` → `{status: "assigned"}`
4. Worker reports progress:
   - `POST /api/jobs/{id}/preprocessing_progress`
   - `PUT /api/jobs/{id}/status` → `preprocessing` / `training` / etc.
   - `POST /api/jobs/{id}/training_progress` (per epoch)
   - `POST /api/jobs/{id}/log/{fold}` (log text body)
   - `POST /api/jobs/{id}/validation_result`
5. Worker uploads model: `POST /api/jobs/{id}/model` (multipart zip)
6. Admin approves: `POST /api/models/{id}/approve`

## Training Progress Log Format

Workers parse nnUNet log lines such as:
```
2026-03-01 22:05:50.045034: Epoch 605
2026-03-01 22:05:50.045146: Current learning rate: 0.00433
2026-03-01 22:08:05.183549: train_loss -0.6752
2026-03-01 22:08:05.183808: val_loss -0.4224
2026-03-01 22:08:05.183965: Pseudo dice [0.8876, 0.8706, ...]
2026-03-01 22:05:48.650428: Epoch time: 125.29 s
```

## Data Layout

```
data/
├── datasets/{dataset_id}/data.zip
├── logs/{job_id}/fold{n}/training_log.txt
└── models/{model_id}/model.zip
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `API_KEY` | `changeme` | Shared key for all `/api/*` endpoints |
| `DASHBOARD_USER` | `admin` | Basic auth username for dashboard |
| `DASHBOARD_PASSWORD` | `admin` | Basic auth password for dashboard |
| `DATA_DIR` | `/app/data` | Root directory for stored files |
| `DB_PATH` | `/app/data/dashboard.db` | SQLite database path |
| `LOG_LEVEL` | `DEBUG` | Logging level |

## nnUNet Model Export/Import

```bash
# Export trained model to zip (run on worker)
nnUNetv2_export_model_to_zip ...

# Install model from zip (run on inference server)
nnUNetv2_install_pretrained_model_from_zip model.zip
```
