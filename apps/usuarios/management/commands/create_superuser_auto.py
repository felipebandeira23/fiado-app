from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Cria o superusuário admin/admin automaticamente caso não exista."

    def handle(self, *args, **options):
        user_model = get_user_model()
        defaults = {
            "email": "admin@fiado.app",
            "is_staff": True,
            "is_superuser": True,
        }

        if hasattr(user_model, "PERFIL_ADMIN"):
            defaults["perfil"] = user_model.PERFIL_ADMIN

        user, created = user_model.objects.get_or_create(username="admin", defaults=defaults)

        if created:
            user.set_password("admin")
            user.save()
            self.stdout.write(self.style.SUCCESS("Superusuário admin criado com sucesso!"))
            return

        self.stdout.write("Superusuário admin já existe.")
