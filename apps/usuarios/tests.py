from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase


class CreateSuperuserAutoCommandTest(TestCase):
    def test_cria_superusuario_admin_quando_nao_existe(self):
        call_command("create_superuser_auto")

        user_model = get_user_model()
        admin = user_model.objects.get(username="admin")

        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.check_password("admin"))

        if hasattr(user_model, "PERFIL_ADMIN"):
            self.assertEqual(admin.perfil, user_model.PERFIL_ADMIN)

    def test_nao_cria_duplicado_quando_admin_ja_existe(self):
        user_model = get_user_model()
        user_model.objects.create_superuser(
            username="admin",
            email="admin@fiado.app",
            password="senha-existente",
        )

        call_command("create_superuser_auto")

        self.assertEqual(user_model.objects.filter(username="admin").count(), 1)
