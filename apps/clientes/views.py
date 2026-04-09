import qrcode
import json
from io import BytesIO
from django.core.files import File
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_GET
from .models import Cliente, ClienteQRCode
from .forms import ClienteForm


# ─── Dashboard ────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    from django.db.models import Sum, F, ExpressionWrapper, DecimalField
    from apps.faturas.models import FaturaMensal

    total_clientes = Cliente.objects.count()
    ativos = Cliente.objects.filter(status='ativo').count()
    bloqueados = Cliente.objects.filter(status='bloqueado').count()
    inadimplentes = Cliente.objects.filter(status='inadimplente').count()
    ultimos = Cliente.objects.order_by('-created_at')[:5]

    restante_expr = ExpressionWrapper(F('valor_total') - F('valor_pago'), output_field=DecimalField())
    total_a_receber = FaturaMensal.objects.exclude(
        status=FaturaMensal.STATUS_PAGA
    ).annotate(restante=restante_expr).aggregate(soma=Sum('restante'))['soma'] or 0
    faturas_vencidas = FaturaMensal.objects.filter(status=FaturaMensal.STATUS_VENCIDA).count()
    ultimas_faturas = FaturaMensal.objects.select_related('cliente').order_by('-created_at')[:5]

    return render(request, 'dashboard.html', {
        'total_clientes': total_clientes,
        'ativos': ativos,
        'bloqueados': bloqueados,
        'inadimplentes': inadimplentes,
        'ultimos': ultimos,
        'total_a_receber': total_a_receber,
        'faturas_vencidas': faturas_vencidas,
        'ultimas_faturas': ultimas_faturas,
    })


# ─── CRUD de Clientes ─────────────────────────────────────────────────────────

@login_required
def lista_clientes(request):
    qs = Cliente.objects.all()
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')

    if q:
        qs = qs.filter(
            Q(nome__icontains=q) |
            Q(telefone__icontains=q) |
            Q(codigo__icontains=q) |
            Q(cpf__icontains=q)
        )
    if status:
        qs = qs.filter(status=status)

    return render(request, 'clientes/lista.html', {
        'clientes': qs,
        'q': q,
        'status_filtro': status,
        'status_choices': Cliente.STATUS_CHOICES,
    })


@login_required
def novo_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST, request.FILES)
        if form.is_valid():
            cliente = form.save()
            _gerar_qrcode(cliente)
            messages.success(request, f'Cliente {cliente.nome} cadastrado com sucesso!')
            return redirect('clientes:detalhe', pk=cliente.pk)
    else:
        form = ClienteForm()
    return render(request, 'clientes/form.html', {'form': form, 'titulo': 'Novo Cliente'})


@login_required
def detalhe_cliente(request, pk):
    from apps.faturas.models import FaturaMensal
    cliente = get_object_or_404(Cliente, pk=pk)
    faturas = FaturaMensal.objects.filter(cliente=cliente).order_by('-ano', '-mes')[:12]
    return render(request, 'clientes/detalhe.html', {'cliente': cliente, 'faturas': faturas})


@login_required
def editar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        form = ClienteForm(request.POST, request.FILES, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cliente atualizado com sucesso!')
            return redirect('clientes:detalhe', pk=cliente.pk)
    else:
        form = ClienteForm(instance=cliente)
    return render(request, 'clientes/form.html', {
        'form': form,
        'titulo': 'Editar Cliente',
        'cliente': cliente,
    })


@login_required
def qrcode_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    # Garante que o QR Code existe
    if not hasattr(cliente, 'qrcode_obj'):
        _gerar_qrcode(cliente)
    cliente.refresh_from_db()
    return render(request, 'clientes/qrcode.html', {'cliente': cliente})


@login_required
def download_qrcode(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if not hasattr(cliente, 'qrcode_obj'):
        _gerar_qrcode(cliente)
        cliente.refresh_from_db()
    qr_img = cliente.qrcode_obj.imagem
    response = HttpResponse(qr_img.read(), content_type='image/png')
    response['Content-Disposition'] = f'attachment; filename="qrcode_{cliente.codigo}.png"'
    return response


# ─── API JSON ─────────────────────────────────────────────────────────────────

@login_required
@require_GET
def api_cliente_por_qr(request, token):
    """Retorna dados do cliente pelo token do QR Code (chamado via AJAX)."""
    try:
        cliente = Cliente.objects.get(token_qr=token)
    except Cliente.DoesNotExist:
        return JsonResponse({'erro': 'Cliente não encontrado.'}, status=404)

    foto_url = cliente.foto.url if cliente.foto else None
    return JsonResponse({
        'id': str(cliente.id),
        'codigo': cliente.codigo,
        'nome': cliente.nome,
        'telefone': cliente.telefone,
        'status': cliente.status,
        'status_display': cliente.get_status_display(),
        'bloqueado': cliente.esta_bloqueado,
        'limite_credito': float(cliente.limite_credito),
        'saldo_devedor': float(cliente.saldo_devedor_total),
        'foto_url': foto_url,
    })


@login_required
@require_GET
def api_busca_clientes(request):
    """Autocomplete: busca clientes por nome, telefone ou código."""
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse([], safe=False)

    clientes = Cliente.objects.filter(
        Q(nome__icontains=q) |
        Q(telefone__icontains=q) |
        Q(codigo__icontains=q)
    ).filter(status=Cliente.STATUS_ATIVO)[:10]

    data = [
        {
            'id': str(c.id),
            'codigo': c.codigo,
            'nome': c.nome,
            'telefone': c.telefone,
            'status': c.status,
        }
        for c in clientes
    ]
    return JsonResponse(data, safe=False)


# ─── Utilitários ──────────────────────────────────────────────────────────────

def _gerar_qrcode(cliente):
    """Gera a imagem PNG do QR Code e salva no model ClienteQRCode."""
    token_url = cliente.gerar_qrcode_url()

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(token_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color='#1F4E79', back_color='white')

    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    qr_obj, _ = ClienteQRCode.objects.get_or_create(cliente=cliente)
    qr_obj.imagem.save(
        f'qrcode_{cliente.codigo}.png',
        File(buffer),
        save=True
    )
