import os
from contextlib import contextmanager
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.usuarios.models import Usuario


class CreateSuperuserAutoCommandTests(TestCase):
    @contextmanager
    def _superuser_env(self, **values):
        keys = (
            'DJANGO_SUPERUSER_USERNAME',
            'DJANGO_SUPERUSER_PASSWORD',
            'DJANGO_SUPERUSER_EMAIL',
        )
        original = {key: os.environ.get(key) for key in keys}
        for key in keys:
            os.environ.pop(key, None)
        for key, value in values.items():
            if value is not None:
                os.environ[key] = value
        try:
            yield
        finally:
            for key in keys:
                os.environ.pop(key, None)
            for key, value in original.items():
                if value is not None:
                    os.environ[key] = value

    def test_cria_superusuario_quando_variaveis_estao_definidas(self):
        output = StringIO()
        with self._superuser_env(
            DJANGO_SUPERUSER_USERNAME='admin_auto',
            DJANGO_SUPERUSER_PASSWORD='senha-forte-123',
            DJANGO_SUPERUSER_EMAIL='admin@example.com',
        ):
            call_command('create_superuser_auto', stdout=output)

        usuario = Usuario.objects.get(username='admin_auto')
        self.assertTrue(usuario.is_superuser)
        self.assertTrue(usuario.is_staff)
        self.assertIn('criado com sucesso', output.getvalue())

    def test_nao_cria_usuario_se_ja_existir(self):
        Usuario.objects.create_superuser(
            username='admin_existente',
            email='existente@example.com',
            password='senha-forte-123',
        )
        output = StringIO()
        with self._superuser_env(
            DJANGO_SUPERUSER_USERNAME='admin_existente',
            DJANGO_SUPERUSER_PASSWORD='senha-forte-123',
            DJANGO_SUPERUSER_EMAIL='existente@example.com',
        ):
            call_command('create_superuser_auto', stdout=output)

        self.assertEqual(Usuario.objects.filter(username='admin_existente').count(), 1)
        self.assertIn('já existe', output.getvalue())

    def test_pula_criacao_quando_faltam_credenciais(self):
        output = StringIO()
        with self._superuser_env():
            call_command('create_superuser_auto', stdout=output)

        self.assertEqual(Usuario.objects.count(), 0)
        self.assertIn('Pulando criação do superusuário', output.getvalue())
