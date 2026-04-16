# App de Fiado — Sistema de Controle de Crédito para Restaurante

Sistema completo para gerenciar clientes fiados em restaurantes e bares: cadastro de clientes com QR Code, registro de consumos, faturamento mensal, controle de pagamentos e relatórios financeiros.

**Stack:** Django 4.2 · PostgreSQL · Bootstrap 5 · Deploy em Ubuntu Server

---

## Funcionalidades

| Módulo | Descrição |
|--------|-----------|
| **Clientes** | Cadastro com foto, CPF, limite de crédito e QR Code individual |
| **Venda Rápida** | Tela de atendimento no balcão — busca de cliente por QR Code ou nome |
| **Consumos** | Registro de itens por produto com histórico completo |
| **Faturas** | Fechamento mensal automático agrupando consumos por cliente |
| **Pagamentos** | Registro parcial ou total com PIX, dinheiro ou cartão |
| **Relatórios** | Receita por mês, ranking de clientes, inadimplência e faturas vencidas |
| **Usuários** | Dois perfis: Administrador (acesso total) e Atendente (operação) |

---

## Instalação local

### 1. Clonar e criar ambiente virtual

```bash
git clone <url-do-repositorio>
cd fiado_app

# Windows
python -m venv venv
venv\Scripts\activate

# Linux / Mac
python3 -m venv venv
source venv/bin/activate
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Configurar variáveis de ambiente

```bash
cp .env.example .env
```

Edite o `.env` com suas credenciais:

```env
SECRET_KEY=gere-uma-chave-longa-aleatoria
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Banco de dados (localhost no Ubuntu Server)
# Se DATABASE_URL for preenchida, ela tem prioridade
DATABASE_URL=
DB_NAME=fiado_app
DB_USER=fiado_app
DB_PASSWORD=SUA_SENHA_FORTE
DB_HOST=localhost
DB_PORT=5432

# Host externo opcional (domínio/IP público)
EXTERNAL_HOSTNAME=

# Supabase Storage — deixe em branco para usar disco local em desenvolvimento
SUPABASE_S3_KEY_ID=
SUPABASE_S3_SECRET=
SUPABASE_S3_BUCKET=media
SUPABASE_S3_ENDPOINT=https://[PROJECT_REF].supabase.co/storage/v1/s3
SUPABASE_S3_PUBLIC_DOMAIN=[PROJECT_REF].supabase.co/storage/v1/object/public/media

# E-mail (opcional — para recuperação de senha)
# Em desenvolvimento, EMAIL_BACKEND=console imprime o e-mail no terminal.
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=seu@email.com
EMAIL_HOST_PASSWORD=sua-senha-de-app
DEFAULT_FROM_EMAIL=App de Fiado <noreply@fiadoapp.com>

# Admin padrão criado automaticamente no bootstrap/start
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=admin
DEFAULT_ADMIN_EMAIL=admin@fiado.app
```

### 4. Criar tabelas e garantir admin padrão

```bash
python manage.py migrate
python manage.py create_superuser_auto
```

### 5. Rodar o servidor

```bash
python manage.py runserver
```

Acesse: http://localhost:8000

---

## Deploy em Ubuntu Server (PostgreSQL local)

### 1. Preparar variáveis de ambiente

```bash
cd /opt/fiado-app
cp .env.example .env
```

No `.env`, configure principalmente:

```env
DEBUG=False
ALLOWED_HOSTS=seu-dominio.com,IP_DO_SERVIDOR
CSRF_TRUSTED_ORIGINS=https://seu-dominio.com
DB_NAME=fiado_app
DB_USER=fiado_app
DB_PASSWORD=SUA_SENHA_FORTE
DB_HOST=localhost
DB_PORT=5432
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=admin
DEFAULT_ADMIN_EMAIL=admin@fiado.app
```

### 2. Bootstrap (instala dependências + PostgreSQL + migrations + estáticos + seed admin)

```bash
cd /opt/fiado-app
chmod +x scripts/ubuntu/bootstrap.sh scripts/ubuntu/start_gunicorn.sh
./scripts/ubuntu/bootstrap.sh
```

O bootstrap é idempotente:
- cria usuário/banco PostgreSQL local somente se não existirem;
- aplica migrations;
- roda `collectstatic`;
- garante o usuário padrão `admin/admin` com o comando `create_superuser_auto`.

### 3. Configurar systemd (Gunicorn)

```bash
sudo cp deploy/systemd/fiado-app.service /etc/systemd/system/fiado-app.service
sudo systemctl daemon-reload
sudo systemctl enable --now fiado-app
sudo systemctl status fiado-app
```

### 4. Configurar Nginx (proxy reverso)

```bash
sudo cp deploy/nginx/fiado-app.conf /etc/nginx/sites-available/fiado-app
sudo ln -sf /etc/nginx/sites-available/fiado-app /etc/nginx/sites-enabled/fiado-app
sudo nginx -t
sudo systemctl reload nginx
```

### 5. Fluxo de deploy/restart

Sempre que atualizar o código:

```bash
cd /opt/fiado-app
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart fiado-app
```

O serviço executa automaticamente, nesta ordem: migrations → collectstatic → seed do admin → Gunicorn.

## Deploy no Render (opcional/legado)

Ainda existe suporte ao `render.yaml`, mas o fluxo principal documentado do projeto passa a ser Ubuntu Server com PostgreSQL local.

---

## Estrutura do projeto

```
fiado_app/
├── apps/
│   ├── usuarios/           # Autenticação e perfis de acesso
│   ├── clientes/           # Cadastro de clientes + QR Code
│   ├── produtos/           # Catálogo de produtos
│   ├── consumos/           # Registro de consumos (venda rápida)
│   └── faturas/            # Faturas mensais, pagamentos e relatórios
│       └── management/
│           └── commands/
│               └── verificar_vencimentos.py
├── templates/              # Templates HTML (Bootstrap 5)
├── static/css/             # CSS customizado
├── fiado_project/
│   ├── settings.py         # Configurações Django
│   └── storage_backends.py # Supabase Storage (S3)
├── scripts/ubuntu/         # Bootstrap e start para Ubuntu Server
├── deploy/systemd/         # Exemplo de service do systemd
├── deploy/nginx/           # Exemplo de configuração Nginx
├── requirements.txt
├── Procfile                # Comando web alternativo
├── render.yaml             # Blueprint Render (opcional/legado)
├── build.sh                # Build de dependências/estáticos
└── .env.example
```

---

## Fases de desenvolvimento

- ✅ **Fase 1** — Autenticação, Clientes, Produtos, QR Code
- ✅ **Fase 2** — Venda Rápida, leitura de QR Code por webcam e scanner USB
- ✅ **Fase 3** — Faturas mensais, registro de pagamentos (parcial/total)
- ✅ **Fase 4** — Relatórios financeiros, inadimplência automática, storage em produção
- ✅ **Fase 5** — PDF de faturas e relatórios, paginação, auditoria, recuperação de senha, gráficos Chart.js

---

## Comandos úteis

```bash
# Verificar faturas vencidas e atualizar status dos clientes
python manage.py verificar_vencimentos

# Gerar migrations após alterar models
python manage.py makemigrations

# Aplicar migrations no banco
python manage.py migrate

# Coletar arquivos estáticos (para deploy)
python manage.py collectstatic

# Rodar testes automatizados (usa SQLite in-memory, sem precisar de PostgreSQL)
python manage.py test --settings=fiado_project.settings_test apps.faturas.tests --verbosity=2
```
