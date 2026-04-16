import environ
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

# Render injeta automaticamente a variável RENDER_EXTERNAL_HOSTNAME
RENDER_HOST = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_HOST:
    ALLOWED_HOSTS.append(RENDER_HOST)

_trusted = []
if RENDER_HOST:
    _trusted.append(f'https://{RENDER_HOST}')
# Permitir domínios customizados via variável de ambiente
_extra_origins = env('CSRF_TRUSTED_ORIGINS', default='')
if _extra_origins:
    _trusted.extend([o.strip() for o in _extra_origins.split(',') if o.strip()])
CSRF_TRUSTED_ORIGINS = _trusted

# ── Segurança em produção ─────────────────────────────────────────────────────
if not DEBUG:
    # Render termina SSL no proxy — confiar no header X-Forwarded-Proto
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000       # 1 ano
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Terceiros
    'crispy_forms',
    'crispy_bootstrap5',
    'django_filters',
    'storages',
    # Apps do projeto
    'apps.usuarios',
    'apps.clientes',
    'apps.produtos',
    'apps.consumos',
    'apps.faturas',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'fiado_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'fiado_project.wsgi.application'

# Banco de dados — DATABASE_URL (Render/Neon) ou variáveis individuais (local)
DATABASE_URL = env('DATABASE_URL', default='')
if DATABASE_URL:
    DATABASES = {
        'default': env.db()
    }
    # Garantir SSL para conexões externas
    DATABASES['default'].setdefault('OPTIONS', {})
    DATABASES['default']['OPTIONS']['sslmode'] = 'require'
    DATABASES['default']['CONN_MAX_AGE'] = 60
else:
    _db_host = env('DB_HOST', default='localhost')
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env('DB_NAME', default='postgres'),
            'USER': env('DB_USER', default='postgres'),
            'PASSWORD': env('DB_PASSWORD', default=''),
            'HOST': _db_host,
            'PORT': env('DB_PORT', default='5432'),
            'OPTIONS': {
                'sslmode': 'require',
            } if _db_host and _db_host not in ('localhost', '127.0.0.1') else {},
            'CONN_MAX_AGE': 60,
        }
    }

# Autenticação — usa nosso model customizado
AUTH_USER_MODEL = 'usuarios.Usuario'
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# Arquivos estáticos
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ── Arquivos de mídia ────────────────────────────────────────────────────────
#
# Em desenvolvimento (sem SUPABASE_S3_KEY_ID): salva em disco local.
# Em produção (com SUPABASE_S3_KEY_ID definida): usa Supabase Storage via S3.
#
# Para configurar no Supabase:
#   1. Supabase Dashboard → Storage → Create bucket "media" (Public)
#   2. Storage → S3 Access Keys → Create new key
#   3. Copie Access Key ID e Secret para as variáveis de ambiente abaixo
#
_SUPABASE_S3_KEY_ID = env('SUPABASE_S3_KEY_ID', default='')

if _SUPABASE_S3_KEY_ID:
    # ── Produção: Supabase Storage ──
    AWS_ACCESS_KEY_ID = _SUPABASE_S3_KEY_ID
    AWS_SECRET_ACCESS_KEY = env('SUPABASE_S3_SECRET')
    AWS_STORAGE_BUCKET_NAME = env('SUPABASE_S3_BUCKET', default='media')
    AWS_S3_ENDPOINT_URL = env('SUPABASE_S3_ENDPOINT')
    AWS_S3_REGION_NAME = 'us-east-1'  # Supabase exige us-east-1 independente da região real
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None            # ACL gerenciada pelas RLS policies do Supabase
    AWS_QUERYSTRING_AUTH = False      # URLs públicas sem assinatura

    # Domínio público do bucket: <project-ref>.supabase.co/storage/v1/object/public/<bucket>
    AWS_S3_CUSTOM_DOMAIN = env('SUPABASE_S3_PUBLIC_DOMAIN')

    DEFAULT_FILE_STORAGE = 'fiado_project.storage_backends.SupabaseMediaStorage'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/'
    MEDIA_ROOT = ''  # Não usado em produção
else:
    # ── Desenvolvimento: disco local ──
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# Sessão: expira em 8 horas (uso no turno do restaurante)
SESSION_COOKIE_AGE = 28800

# ── E-mail ────────────────────────────────────────────────────────────────────
# Em desenvolvimento: EMAIL_BACKEND=console (imprime no terminal).
# Em produção: configure EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
# e as variáveis SMTP abaixo via variáveis de ambiente.
EMAIL_BACKEND = env(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.console.EmailBackend',
)
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='App de Fiado <noreply@fiadoapp.com>')

# ── WhatsApp ──────────────────────────────────────────────────────────────────
# Provedor: "zapi" | "twilio" | "" (vazio = desabilitado)
WHATSAPP_PROVIDER = env('WHATSAPP_PROVIDER', default='')
# Z-API
ZAPI_INSTANCE_ID = env('ZAPI_INSTANCE_ID', default='')
ZAPI_TOKEN = env('ZAPI_TOKEN', default='')
ZAPI_CLIENT_TOKEN = env('ZAPI_CLIENT_TOKEN', default='')
# Twilio
TWILIO_ACCOUNT_SID = env('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN = env('TWILIO_AUTH_TOKEN', default='')
TWILIO_FROM_NUMBER = env('TWILIO_FROM_NUMBER', default='')
