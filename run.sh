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
echo "Building Bomb Lab..."
"$PYTHON" tools_build_bomb_lab.py

echo ""
echo "Building MLB..."
"$PYTHON" tools_build_mlb_card.py

echo ""
echo "Building First 5..."
"$PYTHON" tools_build_first5_card.py

echo ""
echo "Building KBO..."
if [ -f "cheek_splitters_engine.py" ]; then
    "$PYTHON" cheek_splitters_engine.py || echo "KBO build skipped or returned no games."
else
    echo "KBO engine file not found; skipping."
fi

echo ""
echo "Launching SharpStack..."
"$PYTHON" -m streamlit run dashboard/app.py