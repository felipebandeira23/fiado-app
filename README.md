# Fiado App

Sistema web para controle de clientes, vendas fiado, faturas, pagamentos e relatórios.

## Tecnologias

- Python 3.11+
- Django 4.2+
- PostgreSQL
- Gunicorn
- Nginx
- WhiteNoise
- Bootstrap 5

---

## Requisitos no Ubuntu Server

Instale os pacotes básicos:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip postgresql postgresql-contrib nginx
```

---

## Configuração do PostgreSQL local

Crie o banco e o usuário:

```bash
sudo -u postgres psql
```

No console do PostgreSQL:

```sql
CREATE DATABASE fiado_db;
CREATE USER fiado_user WITH PASSWORD 'sua_senha_forte';
ALTER ROLE fiado_user SET client_encoding TO 'utf8';
ALTER ROLE fiado_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE fiado_user SET timezone TO 'America/Sao_Paulo';
GRANT ALL PRIVILEGES ON DATABASE fiado_db TO fiado_user;
\q
```

---

## Instalação do projeto

Clone o repositório:

```bash
git clone https://github.com/felipebandeira23/fiado-app.git
cd fiado-app
```

Crie e ative o ambiente virtual:

```bash
python3 -m venv venv
source venv/bin/activate
```

Instale as dependências:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Arquivo `.env`

Copie o arquivo de exemplo:

```bash
cp .env.example .env
```

Exemplo de configuração:

```dotenv
SECRET_KEY=coloque-uma-chave-longa-e-secreta
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,seu-dominio.com
CSRF_TRUSTED_ORIGINS=https://seu-dominio.com

DB_NAME=fiado_db
DB_USER=fiado_user
DB_PASSWORD=sua_senha_forte
DB_HOST=localhost
DB_PORT=5432

EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=App de Fiado <noreply@fiadoapp.com>
```

---

## Migrações, arquivos estáticos e usuário admin

Execute:

```bash
python manage.py migrate --no-input
python manage.py collectstatic --no-input
python manage.py create_superuser_auto
```

Esse último comando garante automaticamente a criação do usuário padrão:

- login: `admin`
- senha: `admin`

O comando é idempotente e pode ser executado várias vezes sem criar duplicados.

---

## Rodando localmente

Para testes de desenvolvimento:

```bash
python manage.py runserver 0.0.0.0:8000
```

Acesse:

```text
http://localhost:8000
```

---

## Deploy no Ubuntu Server

### 1. Estrutura recomendada

Exemplo:

```text
/var/www/fiado-app/
```

Dentro dela:

- código-fonte
- `.env`
- `venv/`
- `staticfiles/`
- `media/`

---

### 2. Script de bootstrap

Você pode usar um script como `deploy.sh` para automatizar:

```bash
#!/usr/bin/env bash
set -e

python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

python manage.py migrate --no-input
python manage.py collectstatic --no-input
python manage.py create_superuser_auto
```

---

### 3. Gunicorn

Instale e execute com Gunicorn:

```bash
pip install gunicorn
gunicorn fiado_project.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

---

### 4. Serviço systemd

Crie um serviço para manter o app ativo:

```ini
[Unit]
Description=Fiado App Django Service
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/fiado-app
EnvironmentFile=/var/www/fiado-app/.env
ExecStart=/var/www/fiado-app/venv/bin/gunicorn fiado_project.wsgi:application --bind 127.0.0.1:8000 --workers 3
Restart=always

[Install]
WantedBy=multi-user.target
```

Ative com:

```bash
sudo systemctl daemon-reload
sudo systemctl enable fiado-app
sudo systemctl start fiado-app
sudo systemctl status fiado-app
```

---

### 5. Configuração do Nginx

Exemplo de reverse proxy:

```nginx
server {
    listen 80;
    server_name seu-dominio.com;

    location /static/ {
        alias /var/www/fiado-app/staticfiles/;
    }

    location /media/ {
        alias /var/www/fiado-app/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Depois:

```bash
sudo ln -s /etc/nginx/sites-available/fiado-app /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## Comandos úteis

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --no-input
python manage.py createsuperuser
python manage.py create_superuser_auto
python manage.py test
```

---

## Usuário padrão

Após o primeiro deploy local ou no Ubuntu Server, o sistema cria automaticamente:

- usuário: `admin`
- senha: `admin`

Se o usuário já existir, o comando não cria duplicata.

---

## Observações

- Para produção, use `DEBUG=False`
- Configure `ALLOWED_HOSTS` corretamente
- Use uma `SECRET_KEY` forte
- Recomenda-se HTTPS com certificado válido
- Se desejar, use `certbot` para habilitar SSL no Nginx

---

## Estrutura principal do projeto

```text
fiado_app/
├── apps/
├── templates/
├── static/
├── media/
├── fiado_project/
├── manage.py
├── requirements.txt
├── deploy.sh
└── .env.example
```
