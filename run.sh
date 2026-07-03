#!/bin/bash

cd "$(dirname "$0")"

PY="/opt/homebrew/bin/python3"

echo ""
echo "=========================================="
echo "        SharpStack Analytics"
echo "=========================================="
echo ""

echo "Using Python:"
$PY --version

echo ""
echo "Pulling latest code..."
git pull

echo ""
echo "Building KBO..."
$PY cheek_splitters_engine.py || true

echo ""
echo "Building MLB..."
$PY tools_build_mlb_card.py

echo ""
echo "Building Bomb Lab..."
$PY tools_build_bomb_lab.py

echo ""
echo "Tracking recommendations..."
$PY tools_track_recommendations.py

echo ""
echo "Building Discord report..."
$PY tools_build_discord_report.py

echo ""
echo "Launching Dashboard..."
$PY -m streamlit run dashboard/app.py