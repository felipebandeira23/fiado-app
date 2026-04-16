# App de Fiado — Sistema de Controle de Crédito para Restaurante

Sistema completo para gerenciar clientes fiados em restaurantes e bares: cadastro de clientes com QR Code, registro de consumos, faturamento mensal, controle de pagamentos e relatórios financeiros.

**Stack:** Django 4.2 · PostgreSQL (Supabase/Neon) · Bootstrap 5 · Deploy no Render

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

# Banco de dados (variáveis individuais)
DATABASE_URL=postgresql://user:password@host:5432/dbname?sslmode=require
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=SUA_SENHA
DB_HOST=db.SEU_PROJETO.supabase.co
DB_PORT=5432

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
```

> **Como obter as credenciais do Supabase:**
> Supabase Dashboard → Project Settings → Database → Connection Parameters

### 4. Criar tabelas e superusuário

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 5. Rodar o servidor

```bash
python manage.py runserver
```

Acesse: http://localhost:8000

---

## Deploy no Render

### 1. Criar o projeto no Render

- Acesse [render.com](https://render.com) e faça login com GitHub
- Clique em **New + → Blueprint** e selecione este repositório
- O Render usará o `render.yaml` para criar o Web Service e o banco PostgreSQL

### 2. Configurar variáveis de ambiente

No painel do Render → **Environment**, confirme/ajuste:

```
SECRET_KEY               = <chave-secreta-forte>
DEBUG                    = False
ALLOWED_HOSTS            = .onrender.com
DATABASE_URL             = <connectionString do Postgres>
SUPABASE_S3_KEY_ID       = <access-key-id-do-supabase-storage>
SUPABASE_S3_SECRET       = <secret-key-do-supabase-storage>
SUPABASE_S3_BUCKET       = media
SUPABASE_S3_ENDPOINT     = https://<project-ref>.supabase.co/storage/v1/s3
SUPABASE_S3_PUBLIC_DOMAIN = <project-ref>.supabase.co/storage/v1/object/public/media
# (opcional) Para envio de e-mail de recuperação de senha:
EMAIL_BACKEND            = django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST               = smtp.gmail.com
EMAIL_PORT               = 587
EMAIL_USE_TLS            = True
EMAIL_HOST_USER          = seu@email.com
EMAIL_HOST_PASSWORD      = <senha-de-app-gmail>
DEFAULT_FROM_EMAIL       = App de Fiado <noreply@fiadoapp.com>
```

> **Banco gratuito sem expiração (recomendado):**
> Você pode usar o web service no Render e conectar um PostgreSQL do [Neon](https://neon.tech) com `DATABASE_URL`.
> O PostgreSQL free do Render expira em 30 dias.
>
> **Como configurar o Supabase Storage:**
> 1. Supabase Dashboard → Storage → **New Bucket** → nome `media`, marcar como **Public**
> 2. Storage → **S3 Access Keys** → New access key → copie o ID e Secret

### 3. Deploy automático

O Render executa o build/start definidos no `render.yaml`. As migrações rodam no `build.sh`.
Durante o build também é executado `python manage.py create_superuser_auto`, que garante um usuário padrão `admin`/`admin` quando ele ainda não existe (idempotente em redeploys).

### 4. Cron job (verificar vencimentos diariamente)

No Render → **New + → Cron Job**:
- **Command:** `python manage.py verificar_vencimentos`
- **Schedule:** `0 6 * * *` (todo dia às 6h)

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
├── requirements.txt
├── Procfile                # Comando web alternativo
├── render.yaml             # Blueprint de deploy no Render
├── build.sh                # Build/migrate no Render
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
