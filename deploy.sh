#!/bin/bash
set -e

cd /opt/CheekSplittersAnalytics

echo "=== Pulling latest code ==="
git pull --ff-only

echo "=== Building ==="
/usr/bin/python3 build.py

echo "=== Restarting SharpStack ==="
sudo systemctl restart sharpstack

echo "=== Verifying service ==="
sudo systemctl --no-pager --lines=5 status sharpstack

echo "=== Deployment complete ==="
