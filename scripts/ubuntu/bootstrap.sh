#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
VENV_DIR="${VENV_DIR:-$APP_DIR/.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
APP_USER="${APP_USER:-$USER}"

# Banco PostgreSQL local (localhost)
DB_NAME="${DB_NAME:-fiado_app}"
DB_USER="${DB_USER:-fiado_app}"
DB_PASSWORD="${DB_PASSWORD:-fiado_app}"

echo "==> Instalando dependências de sistema (Ubuntu)"
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip postgresql postgresql-contrib nginx

echo "==> Garantindo usuário e banco PostgreSQL locais"
sudo -u postgres psql \
  --set=db_user="$DB_USER" \
  --set=db_password="$DB_PASSWORD" \
  --set=db_name="$DB_NAME" <<'SQL'
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'db_user') THEN
        EXECUTE format('CREATE ROLE %I LOGIN PASSWORD %L', :'db_user', :'db_password');
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'db_name') THEN
        EXECUTE format('CREATE DATABASE %I OWNER %I', :'db_name', :'db_user');
    END IF;
END
$$;
SQL

echo "==> Preparando virtualenv em $VENV_DIR"
cd "$APP_DIR"
$PYTHON_BIN -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f "$APP_DIR/.env" ]; then
  cp "$APP_DIR/.env.example" "$APP_DIR/.env"
fi

echo "==> Rodando bootstrap da aplicação"
export DB_NAME DB_USER DB_PASSWORD
export DB_HOST="${DB_HOST:-localhost}"
export DB_PORT="${DB_PORT:-5432}"
export DEBUG="${DEBUG:-False}"
export ALLOWED_HOSTS="${ALLOWED_HOSTS:-127.0.0.1,localhost}"
export SECRET_KEY="${SECRET_KEY:-change-me-in-production}"
python manage.py migrate --no-input
python manage.py collectstatic --no-input
python manage.py create_superuser_auto

echo "==> Bootstrap concluído. Para rodar em produção:"
echo "   sudo cp deploy/systemd/fiado-app.service /etc/systemd/system/"
echo "   sudo systemctl daemon-reload && sudo systemctl enable --now fiado-app"
echo "   sudo cp deploy/nginx/fiado-app.conf /etc/nginx/sites-available/fiado-app"
echo "   sudo ln -s /etc/nginx/sites-available/fiado-app /etc/nginx/sites-enabled/fiado-app"
echo "   sudo nginx -t && sudo systemctl reload nginx"
