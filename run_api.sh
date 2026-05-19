#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
export FLASK_ENV=development
python api/app.py
