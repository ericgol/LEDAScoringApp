# LEDA Drone Scoring

Automated scoring application for LEDA (NIST Standard Test Methods for sUAS) drone proficiency check-rides. Pilots fly a NIST course with a proctor, capture sequential images of colored rings inside buckets on stands, and submit images via SD card or drag-and-drop for automated scoring.

## Features

- **Course Definitions**: Level 1 (Position + Traverse) and Level 2 (all 5 maneuvers) built-in
- **Image Upload**: SD card folder picker (File System Access API), drag-and-drop, or file dialog
- **Azure Computer Vision**: Automated image analysis (tags, objects, captions, OCR)
- **Scoring Engine**: Placeholder scoring with hooks for custom ring detection model
- **Session Management**: Track pilot info, conditions, and per-image results

## Quick Start (Local Development)

```bash
# 1. Create virtual environment
cd ~/DroneScoring
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your Azure credentials (optional for local dev)

# 4. Run the application
python run.py
# Open http://localhost:5000
```

The app runs in local mode without Azure — images are stored in `data/uploads/` and CV analysis returns placeholder results.

## Azure Deployment

### Prerequisites

- Azure CLI (`az`) installed and logged in
- A subscription with permissions to create resources

### Deploy Infrastructure

```bash
# Create resource group
az group create --name rg-dronescoring-dev --location eastus

# Validate first
az deployment group what-if \
  --resource-group rg-dronescoring-dev \
  --template-file infra/main.bicep \
  --parameters infra/main.parameters.json

# Deploy
az deployment group create \
  --resource-group rg-dronescoring-dev \
  --template-file infra/main.bicep \
  --parameters infra/main.parameters.json
```

### Deploy Application

```bash
az webapp up \
  --name app-dronescoring-dev \
  --resource-group rg-dronescoring-dev \
  --runtime "PYTHON:3.11"
```

## Project Structure

```
DroneScoring/
├── infra/                    # Bicep IaC
│   ├── main.bicep            # Orchestrator
│   ├── main.parameters.json  # Parameters
│   └── modules/              # Resource modules
├── app/                      # Flask application
│   ├── __init__.py           # App factory
│   ├── config.py             # Configuration
│   ├── routes/               # API endpoints
│   ├── services/             # Azure service wrappers
│   ├── models/               # Course & session models
│   ├── static/               # CSS, JS
│   └── templates/            # HTML templates
├── data/                     # Local data storage
├── requirements.txt
├── run.py                    # Dev entry point
└── .env.example
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Main upload page |
| GET | `/api/courses` | List available courses |
| GET | `/api/courses/<id>` | Course detail |
| POST | `/api/sessions` | Create scoring session |
| GET | `/api/sessions/<id>` | Get session details |
| POST | `/api/upload` | Upload images |
| POST | `/api/analyze` | Upload + analyze + score images |
| GET | `/api/results/<id>` | View results page |

## LEDA Courses

### Level 1 — 2 Maneuvers, 7 min/maneuver
- **MAN 1 (Position)**: 18 scoring images
- **MAN 2 (Traverse)**: 18 scoring images

### Level 2 — 5 Maneuvers, timed per maneuver
- **MAN 1–2**: Same as Level 1
- **MAN 3 (Orbit)**: 20 scoring images
- **MAN 4 (Inspect)**: 20 scoring images
- **MAN 5 (Recon)**: 20 scoring images (5 laps)

## Scoring

Each image is scored based on whether the colored ring in the bucket is:
- **UNBROKEN** → PASS (circled on scoresheet)
- **BROKEN** → FAIL (X'd on scoresheet)

Currently uses Azure Computer Vision general analysis. Custom ring detection model will be integrated once training data is provided.
