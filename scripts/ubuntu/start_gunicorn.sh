#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/fiado-app}"
VENV_DIR="${VENV_DIR:-$APP_DIR/.venv}"
GUNICORN_BIND="${GUNICORN_BIND:-127.0.0.1:8000}"
GUNICORN_WORKERS="${GUNICORN_WORKERS:-2}"
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-120}"

cd "$APP_DIR"
source "$VENV_DIR/bin/activate"

python manage.py migrate --no-input
python manage.py collectstatic --no-input
python manage.py create_superuser_auto

exec gunicorn fiado_project.wsgi:application \
  --bind "$GUNICORN_BIND" \
  --workers "$GUNICORN_WORKERS" \
  --timeout "$GUNICORN_TIMEOUT" \
  --log-file -
