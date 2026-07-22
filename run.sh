#!/bin/bash

set -e

PROJECT_DIR="$HOME/Development/CheekSplittersAnalytics"
PYTHON="/opt/homebrew/bin/python3"

cd "$PROJECT_DIR"

echo ""
echo "============================================================"
echo "SharpStack Mac Runner"
echo "============================================================"

echo ""
echo "Pulling latest code..."
git pull

echo ""
echo "Python:"
"$PYTHON" --version

echo ""
echo "Building System"
"$PYTHON" build.py

echo ""
echo "Launching SharpStack..."
"$PYTHON" -m streamlit run dashboard/app.py
