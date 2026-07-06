#!/bin/bash

cd "$(dirname "$0")"

PY="/opt/homebrew/bin/python3"

echo ""
echo "=========================================="
echo "        SharpStack Analytics"
echo "=========================================="
echo ""

$PY build.py --launch
