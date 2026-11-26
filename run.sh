#!/bin/sh
set -e
cd "$(dirname "$0")"
exec ../.venv/bin/python3 manage.py runserver 0.0.0.0:8000
