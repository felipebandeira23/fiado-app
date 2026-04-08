from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import Usuario


class UsuarioCreateForm(UserCreationForm):
    class Meta:
        model = Usuario
        fields = ('username', 'nome_completo', 'email', 'perfil', 'password1', 'password2')
        labels = {
            'username': 'Login',
            'nome_completo': 'Nome completo',
            'email': 'E-mail',
            'perfil': 'Perfil de acesso',
        }


class UsuarioEditForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ('username', 'nome_completo', 'email', 'perfil', 'is_active')
        labels = {
            'username': 'Login',
            'nome_completo': 'Nome completo',
            'email': 'E-mail',
            'perfil': 'Perfil de acesso',
            'is_active': 'Usuário ativo',
        }
