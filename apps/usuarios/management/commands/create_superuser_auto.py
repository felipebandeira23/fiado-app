from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Cria ou atualiza o superusuário admin/admin automaticamente."

    def handle(self, *args, **options):
        User = get_user_model()
        username = "admin"
        password = "admin"
        email = "admin@fiado.app"

        user = User.objects.filter(username=username).first()

        if user:
            user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.email = email
            if hasattr(User, "PERFIL_ADMIN"):
                user.perfil = User.PERFIL_ADMIN
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f'Superusuário "{username}" atualizado com senha redefinida!')
            )
        else:
            defaults = {
                "email": email,
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            }
            if hasattr(User, "PERFIL_ADMIN"):
                defaults["perfil"] = User.PERFIL_ADMIN
            user = User.objects.create_superuser(
                username=username, email=email, password=password, **{
                    k: v for k, v in defaults.items() if k not in ("email",)
                }
            )
            self.stdout.write(
                self.style.SUCCESS(f'Superusuário "{username}" criado com sucesso!')
            )
