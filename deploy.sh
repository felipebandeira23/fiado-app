#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${VENV_DIR:-$APP_DIR/.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "$APP_DIR"

if [ ! -d "$VENV_DIR" ]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f "$APP_DIR/.env" ]; then
  echo "Arquivo .env não encontrado. Copie .env.example para .env e ajuste os valores antes do deploy."
  exit 1
fi

if ! grep -q '^SECRET_KEY=' "$APP_DIR/.env"; then
  echo "SECRET_KEY não configurada no .env."
  exit 1
fi

python manage.py migrate --no-input
python manage.py collectstatic --no-input
python manage.py create_superuser_auto
