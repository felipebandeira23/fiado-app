web: gunicorn fiado_project.wsgi --workers 2 --timeout 120 --log-file -
release: python manage.py collectstatic --no-input && python manage.py migrate
