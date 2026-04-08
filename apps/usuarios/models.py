from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    PERFIL_ADMIN = 'admin'
    PERFIL_ATENDENTE = 'atendente'
    PERFIL_CHOICES = [
        (PERFIL_ADMIN, 'Administrador'),
        (PERFIL_ATENDENTE, 'Atendente'),
    ]

    nome_completo = models.CharField('Nome completo', max_length=200, blank=True)
    perfil = models.CharField(
        'Perfil de acesso',
        max_length=20,
        choices=PERFIL_CHOICES,
        default=PERFIL_ATENDENTE,
    )

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        ordering = ['nome_completo']

    def __str__(self):
        return self.nome_completo or self.username

    @property
    def is_admin_sistema(self):
        return self.perfil == self.PERFIL_ADMIN or self.is_superuser

    def get_perfil_display_badge(self):
        if self.is_admin_sistema:
            return '<span class="badge bg-danger">Administrador</span>'
        return '<span class="badge bg-secondary">Atendente</span>'
