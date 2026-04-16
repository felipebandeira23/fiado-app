from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from apps.usuarios.models import Usuario


class CreateSuperuserAutoCommandTests(TestCase):
    def test_cria_superusuario_quando_variaveis_estao_definidas(self):
        output = StringIO()
        with patch.dict('os.environ', {
            'DJANGO_SUPERUSER_USERNAME': 'admin_auto',
            'DJANGO_SUPERUSER_PASSWORD': 'senha-forte-123',
            'DJANGO_SUPERUSER_EMAIL': 'admin@example.com',
        }, clear=False):
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
        with patch.dict('os.environ', {
            'DJANGO_SUPERUSER_USERNAME': 'admin_existente',
            'DJANGO_SUPERUSER_PASSWORD': 'senha-forte-123',
            'DJANGO_SUPERUSER_EMAIL': 'existente@example.com',
        }, clear=False):
            call_command('create_superuser_auto', stdout=output)

        self.assertEqual(Usuario.objects.filter(username='admin_existente').count(), 1)
        self.assertIn('já existe', output.getvalue())

    def test_pula_criacao_sem_username_ou_password(self):
        output = StringIO()
        with patch.dict('os.environ', {
            'DJANGO_SUPERUSER_USERNAME': '',
            'DJANGO_SUPERUSER_PASSWORD': '',
        }, clear=False):
            call_command('create_superuser_auto', stdout=output)

        self.assertEqual(Usuario.objects.count(), 0)
        self.assertIn('Pulando criação do superusuário', output.getvalue())
