#!/bin/bash

cd "$(dirname "$0")"

PY="/opt/homebrew/bin/python3"
STREAMLIT="$PY -m streamlit"

echo ""
echo "=========================================="
echo " SharpStack Analytics"
echo "=========================================="
echo ""

echo "Using Python:"
$PY --version

echo ""
echo "Building KBO..."
$PY cheek_splitters_engine.py || true

echo ""
echo "Building MLB..."
$PY tools_build_mlb_card.py

echo ""
echo "Launching Dashboard..."
$STREAMLIT run dashboard/app.py