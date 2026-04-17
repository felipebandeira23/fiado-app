from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import Notificacao


@login_required
def api_notificacoes(request):
    """Retorna as notificações não lidas do usuário logado."""
    notificacoes = Notificacao.objects.filter(
        usuario=request.user, lida=False
    ).values('id', 'tipo', 'titulo', 'mensagem', 'url', 'created_at')
    return JsonResponse({'notificacoes': list(notificacoes)})


@login_required
@require_POST
def api_marcar_lida(request, pk):
    """Marca uma notificação como lida."""
    try:
        notif = Notificacao.objects.get(pk=pk, usuario=request.user)
        notif.lida = True
        notif.save(update_fields=['lida'])
        return JsonResponse({'ok': True})
    except Notificacao.DoesNotExist:
        return JsonResponse({'erro': 'Notificação não encontrada.'}, status=404)


@login_required
@require_POST
def api_marcar_todas_lidas(request):
    """Marca todas as notificações do usuário como lidas."""
    Notificacao.objects.filter(usuario=request.user, lida=False).update(lida=True)
    return JsonResponse({'ok': True})
