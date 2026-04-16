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

    def test_atualiza_admin_sem_duplicar_quando_ja_existe(self):
        user_model = get_user_model()
        user_model.objects.create_user(
            username="admin",
            email="admin@fiado.app",
            password="senha-existente",
        )

        call_command("create_superuser_auto")

        admin = user_model.objects.get(username="admin")
        self.assertEqual(user_model.objects.filter(username="admin").count(), 1)
        self.assertTrue(admin.check_password("admin"))
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

        if hasattr(user_model, "PERFIL_ADMIN"):
            self.assertEqual(admin.perfil, user_model.PERFIL_ADMIN)

    def test_nao_altera_outros_usuarios(self):
        user_model = get_user_model()
        atendente = user_model.objects.create_user(
            username="atendente",
            email="atendente@fiado.app",
            password="senha-atendente",
        )

        call_command("create_superuser_auto")

        atendente.refresh_from_db()
        self.assertTrue(atendente.check_password("senha-atendente"))
        self.assertFalse(atendente.is_superuser)
