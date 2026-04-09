# App de Fiado — Sistema de Controle de Crédito para Restaurante

Sistema completo para gerenciar clientes fiados em restaurantes e bares: cadastro de clientes com QR Code, registro de consumos, faturamento mensal, controle de pagamentos e relatórios financeiros.

**Stack:** Django 4.2 · PostgreSQL (Supabase) · Bootstrap 5 · Deploy no Railway

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

# Supabase PostgreSQL
DATABASE_URL=postgresql://postgres:[SENHA]@db.[PROJETO].supabase.co:5432/postgres

# Supabase Storage — deixe em branco para usar disco local em desenvolvimento
SUPABASE_S3_KEY_ID=
SUPABASE_S3_SECRET=
SUPABASE_S3_BUCKET=media
SUPABASE_S3_ENDPOINT=https://[PROJECT_REF].supabase.co/storage/v1/s3
SUPABASE_S3_PUBLIC_DOMAIN=[PROJECT_REF].supabase.co/storage/v1/object/public/media
```

> **Como obter a DATABASE_URL do Supabase:**
> Supabase Dashboard → Project Settings → Database → Connection String (URI)

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

## Deploy no Railway

### 1. Criar o projeto no Railway

- Acesse [railway.app](https://railway.app) e faça login com GitHub
- **New Project → Deploy from GitHub repo** → selecione este repositório

### 2. Configurar variáveis de ambiente

No painel do Railway → **Variables**, adicione:

```
SECRET_KEY               = <chave-secreta-forte>
DEBUG                    = False
DATABASE_URL             = <connection-string-do-supabase>
SUPABASE_S3_KEY_ID       = <access-key-id-do-supabase-storage>
SUPABASE_S3_SECRET       = <secret-key-do-supabase-storage>
SUPABASE_S3_BUCKET       = media
SUPABASE_S3_ENDPOINT     = https://<project-ref>.supabase.co/storage/v1/s3
SUPABASE_S3_PUBLIC_DOMAIN = <project-ref>.supabase.co/storage/v1/object/public/media
```

> **Como configurar o Supabase Storage:**
> 1. Supabase Dashboard → Storage → **New Bucket** → nome `media`, marcar como **Public**
> 2. Storage → **S3 Access Keys** → New access key → copie o ID e Secret

### 3. Deploy automático

O Railway detecta o `Procfile` e faz o deploy automaticamente. As migrações rodam via `release` no Procfile.

### 4. Cron job (verificar vencimentos diariamente)

No Railway → seu projeto → **+ New → Cron Job**:
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
├── Procfile                # Deploy Railway
├── railway.toml
└── .env.example
```

---

## Fases de desenvolvimento

- ✅ **Fase 1** — Autenticação, Clientes, Produtos, QR Code
- ✅ **Fase 2** — Venda Rápida, leitura de QR Code por webcam e scanner USB
- ✅ **Fase 3** — Faturas mensais, registro de pagamentos (parcial/total)
- ✅ **Fase 4** — Relatórios financeiros, inadimplência automática, storage em produção

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
```
