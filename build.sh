#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input
python manage.py create_superuser_auto

# Fallback: criar superusuário admin/admin caso não exista
python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fiado_project.settings')
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser(username='admin', email='admin@fiado.app', password='admin')
    print('Superusuário admin criado com sucesso!')
else:
    print('Superusuário admin já existe.')
"
