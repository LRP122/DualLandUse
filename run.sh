#!/usr/bin/env bash
# Run the AgriPV Flask app — open http://localhost:8080 in your browser
cd "$(dirname "$0")/app"
MPLBACKEND=Agg ../.venv/bin/python app.py
