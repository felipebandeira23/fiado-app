import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Cria o superusuário admin/admin automaticamente caso não exista."

    def handle(self, *args, **options):
        username = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
        password = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin")
        email = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@fiado.app")
        user_model = get_user_model()
        defaults = {
            "email": email,
            "is_staff": True,
            "is_superuser": True,
        }

        if hasattr(user_model, "PERFIL_ADMIN"):
            defaults["perfil"] = user_model.PERFIL_ADMIN

        user, created = user_model.objects.get_or_create(username=username, defaults=defaults)

        if created:
            user.set_password(password)
            user.save(update_fields=["password"])
            self.stdout.write(
                self.style.SUCCESS(f"Superusuário {username} criado com sucesso!")
            )
            return

        updated_fields = []
        if not user.is_staff:
            user.is_staff = True
            updated_fields.append("is_staff")
        if not user.is_superuser:
            user.is_superuser = True
            updated_fields.append("is_superuser")
        if hasattr(user_model, "PERFIL_ADMIN") and getattr(user, "perfil", None) != user_model.PERFIL_ADMIN:
            user.perfil = user_model.PERFIL_ADMIN
            updated_fields.append("perfil")
        if not user.check_password(password):
            user.set_password(password)
            updated_fields.append("password")

        if updated_fields:
            user.save(update_fields=updated_fields)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Superusuário {username} atualizado para garantir acesso padrão."
                )
            )
            return

        self.stdout.write(f"Superusuário {username} já está configurado.")
