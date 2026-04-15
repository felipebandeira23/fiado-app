"""
Configurações para execução de testes automatizados.

Substitui o banco PostgreSQL por SQLite em memória, permitindo
rodar os testes sem conexão com banco externo.

Uso:
    python manage.py test --settings=fiado_project.settings_test apps.faturas.tests
"""
from .settings import *  # noqa: F401, F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Desabilita checagem de senhas para facilitar fixtures nos testes
AUTH_PASSWORD_VALIDATORS = []

# Desabilita e-mail real nos testes
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Desabilita WhatsApp nos testes (mockado individualmente em cada test case)
WHATSAPP_PROVIDER = ''

# Usa armazenamento estático simples (sem manifest hash) para testes
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
