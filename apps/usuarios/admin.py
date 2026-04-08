from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'nome_completo', 'email', 'perfil', 'is_active')
    list_filter = ('perfil', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Dados do Sistema', {'fields': ('nome_completo', 'perfil')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Dados do Sistema', {'fields': ('nome_completo', 'perfil')}),
    )
