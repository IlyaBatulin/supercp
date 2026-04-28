#!/usr/bin/env bash
set -euo pipefail

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Applying Django migrations..."
python manage.py migrate

echo "Starting Django server for Replit..."
echo "Configurable variables:"
echo "  LAB_LOGIN, LAB_PASSWORD, SUPERCOMPUTER_ACCESS_KEY"
echo "  NODE_PASSWORD_ALPHA, NODE_PASSWORD_BETA, NODE_PASSWORD_GAMMA"
echo "  DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS, PORT"

PORT="${PORT:-8000}"
python manage.py runserver "0.0.0.0:${PORT}"
