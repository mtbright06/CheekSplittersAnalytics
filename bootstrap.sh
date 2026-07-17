#!/bin/bash

set -e

echo ""
echo "======================================"
echo " SharpStack Bootstrap"
echo "======================================"
echo ""

python -m venv .venv

source .venv/bin/activate

python -m pip install --upgrade pip

pip install -r requirements.txt

pip install -r requirements-dev.txt

python verify_environment.py

echo ""
echo "======================================"
echo " SharpStack Ready"
echo "======================================"