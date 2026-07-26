#!/bin/bash
set -e

echo "Starting ApnaERP FastAPI server in reload mode..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
