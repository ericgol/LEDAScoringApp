# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

LEDA Drone Scoring is a Flask web application for automated scoring of LEDA (NIST Standard Test Methods for sUAS) drone proficiency check-rides. Pilots fly a NIST course, capture sequential images of colored rings inside buckets on stands, and submit images for automated scoring via Azure Computer Vision.

The app runs in two modes:
- **Local dev mode**: No Azure credentials needed; images stored in `data/uploads/`, CV analysis returns placeholders.
- **Azure mode**: Uses Azure Blob Storage, Computer Vision (Image Analysis), and Key Vault with managed identity (DefaultAzureCredential).

## Build and Run Commands

```bash
# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Run dev server (http://localhost:5000)
python run.py

# Production (used by App Service)
gunicorn --bind=0.0.0.0 --timeout 600 run:app
```

### Infrastructure Deployment (Azure Bicep)

```bash
az group create --name rg-dronescoring-dev --location eastus

# Dry-run
az deployment group what-if \
  --resource-group rg-dronescoring-dev \
  --template-file infra/main.bicep \
  --parameters infra/main.parameters.json

# Deploy
az deployment group create \
  --resource-group rg-dronescoring-dev \
  --template-file infra/main.bicep \
  --parameters infra/main.parameters.json

# Deploy app code
az webapp up \
  --name app-dronescoring-dev \
  --resource-group rg-dronescoring-dev \
  --runtime "PYTHON:3.11"
```

## Architecture

### Application Layer (`app/`)

Flask app factory pattern in `app/__init__.py` (`create_app()`). Configuration loaded from environment variables via `app/config.py` with `python-dotenv`.

Three Flask blueprints handle routes:
- `app/routes/courses.py` — `/api/courses` endpoints: list courses and get course detail. Read-only, returns course definitions from in-memory registry.
- `app/routes/upload.py` — `/api/upload` endpoint: accepts multipart image uploads, validates file extensions, stores via storage service. Allowed extensions: jpg, jpeg, png, tiff, tif, bmp, dng, raw.
- `app/routes/scoring.py` — `/api/sessions` and `/api/analyze` endpoints: creates scoring sessions, orchestrates the upload→analyze→score pipeline, renders results HTML.

### Domain Model (`app/models/course.py`)

All domain objects are Python dataclasses: `ManeuverStep`, `Maneuver`, `Course`, `ScoringSession`.

Course definitions (Level 1 and Level 2) are built in-memory by `_build_level1()` and `_build_level2()` and cached in a module-level `_COURSES` dict. There is no database — session persistence uses a flat JSON file (`data/sessions.json`) via `_load_sessions()` / `_save_sessions()`. Level 2 reuses Level 1's Position and Traverse maneuvers with new IDs, then adds Orbit, Inspect, and Recon.

Each `ManeuverStep` defines an expected bucket ID (e.g. "2A", "3B") and whether it captures an image. The scoring pipeline matches uploaded images to expected buckets in sequential order.

### Service Layer (`app/services/`)

- `storage.py` — Wraps Azure Blob Storage with local filesystem fallback. Uses `DefaultAzureCredential`. Falls back to `data/uploads/<session_id>/` when `AZURE_STORAGE_ACCOUNT_NAME` is empty.
- `vision.py` — Wraps Azure AI Vision Image Analysis SDK. Requests tags, objects, caption, dense captions, and OCR. Falls back to key-based auth if `AZURE_COMPUTER_VISION_KEY` is set; otherwise uses `DefaultAzureCredential`. Returns placeholder dict when endpoint is not configured.
- `scoring.py` — Placeholder scoring engine. Currently returns `"needs_review"` for all images with basic heuristics (ring keyword matching, OCR bucket-label matching). Designed to be replaced by a custom ring detection model. Scoring rule: UNBROKEN ring → PASS, BROKEN ring → FAIL.

### Infrastructure (`infra/`)

Bicep IaC with a main orchestrator (`main.bicep`) and four modules:
- `appservice.bicep` — Linux App Service Plan (B1) + Web App with system-assigned managed identity.
- `cognitiveservices.bicep` — Computer Vision (S1) with Cognitive Services User RBAC role for the web app identity.
- `storage.bicep` — StorageV2 account (shared key disabled, RBAC-only) with `drone-images` and `session-data` containers. Blob Data Contributor role for the web app identity.
- `keyvault.bicep` — Key Vault with RBAC authorization, soft delete, purge protection. Secrets User role for the web app identity.

All modules use a `{resourcePrefix}-{baseName}-{environment}` naming convention parameterized through `main.parameters.json`.

### Frontend (`app/static/`, `app/templates/`)

Vanilla JS single-page flow in `app/static/js/app.js` — no build step. Three-phase UI: session setup → image upload (supports File System Access API for SD card folder picker, webkitdirectory fallback, file picker, drag-and-drop) → results display. Templates use Jinja2 (`base.html`, `index.html`, `results.html`).

## Key Design Decisions

- **No database**: Sessions persist as JSON on disk (`data/sessions.json`). This is intentional for the current scope.
- **Sequential image matching**: Uploaded images are matched to expected maneuver steps by index order (not by content). The files are sorted by filename before upload.
- **Graceful Azure fallback**: Every service gracefully degrades when Azure credentials/endpoints are absent, allowing full local development.
- **Scoring is placeholder**: The scoring engine (`app/services/scoring.py`) awaits a custom vision model. All images currently score as `"needs_review"`. The integration point is `score_image()`.
- **Auth strategy**: Azure resources use managed identity (RBAC) in production. Local dev can use `az` CLI auth or optionally `AZURE_COMPUTER_VISION_KEY` for key-based Computer Vision access.
