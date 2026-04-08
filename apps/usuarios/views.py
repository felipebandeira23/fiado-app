from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from .models import Usuario
from .forms import UsuarioCreateForm, UsuarioEditForm


def admin_required(view_func):
    """Decorator: só administradores podem acessar."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_admin_sistema:
            return HttpResponseForbidden('Acesso restrito a administradores.')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
@admin_required
def lista_usuarios(request):
    usuarios = Usuario.objects.all().order_by('nome_completo')
    return render(request, 'usuarios/lista.html', {'usuarios': usuarios})


@login_required
@admin_required
def novo_usuario(request):
    if request.method == 'POST':
        form = UsuarioCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuário criado com sucesso!')
            return redirect('usuarios:lista')
    else:
        form = UsuarioCreateForm()
    return render(request, 'usuarios/form.html', {'form': form, 'titulo': 'Novo Usuário'})


@login_required
@admin_required
def editar_usuario(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    if request.method == 'POST':
        form = UsuarioEditForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuário atualizado!')
            return redirect('usuarios:lista')
    else:
        form = UsuarioEditForm(instance=usuario)
    return render(request, 'usuarios/form.html', {'form': form, 'titulo': 'Editar Usuário', 'usuario': usuario})


@login_required
def alterar_senha(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Senha alterada com sucesso!')
            return redirect('/')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'usuarios/alterar_senha.html', {'form': form})
