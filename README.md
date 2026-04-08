# App de Fiado — Sistema de Controle de Crédito para Restaurante

Stack: **Django 4.2 + PostgreSQL (Supabase) + Railway**

---

## Instalação local

### 1. Clonar e criar ambiente virtual

```bash
git clone <url-do-repositorio>
cd fiado_app
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
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

Edite o arquivo `.env` com suas credenciais:

```env
SECRET_KEY=gere-uma-chave-longa-aleatoria
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Cole aqui a string de conexão do Supabase
DATABASE_URL=postgresql://postgres:[SENHA]@db.[PROJETO].supabase.co:5432/postgres
```

#### Como obter a DATABASE_URL do Supabase:
1. Acesse seu projeto em supabase.com
2. Vá em **Project Settings → Database**
3. Copie a **Connection String** no formato URI
4. Substitua `[YOUR-PASSWORD]` pela sua senha do banco

### 4. Criar as tabelas e superusuário

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

### 1. Criar conta no Railway
Acesse [railway.app](https://railway.app) e crie uma conta gratuita (pode entrar com GitHub).

### 2. Criar novo projeto
- Clique em **New Project → Deploy from GitHub repo**
- Selecione o repositório do projeto

### 3. Configurar variáveis de ambiente no Railway
No painel do Railway, vá em **Variables** e adicione:

```
SECRET_KEY      = <chave-secreta-forte>
DEBUG           = False
ALLOWED_HOSTS   = <domínio-gerado-pelo-railway>
DATABASE_URL    = <connection-string-do-supabase>
```

### 4. Deploy automático
O Railway detecta o `Procfile` e faz o deploy automaticamente.
As migrações rodam automaticamente via `release` no Procfile.

---

## Estrutura do projeto

```
fiado_app/
├── apps/
│   ├── usuarios/     # Autenticação e perfis
│   ├── clientes/     # Clientes + QR Code
│   └── produtos/     # Catálogo de produtos
├── templates/        # Templates HTML
├── static/css/       # CSS customizado
├── fiado_project/    # Configurações Django
├── requirements.txt
├── Procfile          # Deploy Railway
├── railway.toml      # Configuração Railway
└── .env.example      # Variáveis de ambiente
```

## Fases de desenvolvimento

- ✅ **Fase 1** (atual): Clientes, Produtos, Usuários, QR Code
- 🔜 **Fase 2**: Venda Rápida + leitura de QR Code
- 🔜 **Fase 3**: Faturas mensais + Pagamentos
- 🔜 **Fase 4**: Relatórios + Auditoria
