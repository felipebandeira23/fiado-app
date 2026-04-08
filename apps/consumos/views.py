import json
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.db import transaction

from apps.clientes.models import Cliente
from apps.produtos.models import Produto
from .models import Consumo, ConsumoItem


# ─── Venda Rápida ─────────────────────────────────────────────────────────────

@login_required
def venda_rapida(request):
    """Tela principal de atendimento no balcão."""
    return render(request, 'consumos/venda_rapida.html')


@login_required
@require_POST
def api_salvar_consumo(request):
    """
    Recebe JSON com cliente_id, observacao e lista de itens.
    Valida, cria Consumo + ConsumoItens e retorna resultado.

    Body esperado:
    {
        "cliente_id": "uuid",
        "observacao": "...",
        "itens": [
            {"produto_id": "uuid", "quantidade": 2, "valor_unitario": 15.50},
            ...
        ]
    }
    """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'erro': 'JSON inválido.'}, status=400)

    cliente_id = body.get('cliente_id')
    itens_data = body.get('itens', [])
    observacao = body.get('observacao', '').strip()

    # ── Validações ──
    if not cliente_id:
        return JsonResponse({'erro': 'Cliente não informado.'}, status=400)

    if not itens_data:
        return JsonResponse({'erro': 'Nenhum item no carrinho.'}, status=400)

    try:
        cliente = Cliente.objects.get(pk=cliente_id)
    except Cliente.DoesNotExist:
        return JsonResponse({'erro': 'Cliente não encontrado.'}, status=404)

    if cliente.esta_bloqueado:
        return JsonResponse({
            'erro': f'Cliente {cliente.nome} está BLOQUEADO. Não é possível registrar consumo.'
        }, status=403)

    # ── Calcular total ──
    total = Decimal('0')
    itens_validos = []
    for item in itens_data:
        try:
            produto = Produto.objects.get(pk=item['produto_id'], ativo=True)
        except Produto.DoesNotExist:
            return JsonResponse({'erro': f'Produto inválido ou inativo.'}, status=400)

        qtd = int(item.get('quantidade', 1))
        if qtd <= 0:
            return JsonResponse({'erro': 'Quantidade deve ser maior que zero.'}, status=400)

        # Usar o valor atual do produto como histórico
        valor_unit = produto.valor_unitario
        subtotal = valor_unit * qtd
        total += subtotal
        itens_validos.append({
            'produto': produto,
            'quantidade': qtd,
            'valor_unitario': valor_unit,
            'subtotal': subtotal,
        })

    # ── Verificar limite de crédito ──
    aviso_limite = None
    if cliente.limite_credito > 0:
        saldo_atual = cliente.saldo_devedor_total
        if saldo_atual + total > cliente.limite_credito:
            aviso_limite = (
                f'⚠️ Atenção: este consumo (R$ {total:.2f}) ultrapassaria o limite '
                f'de crédito do cliente (limite: R$ {cliente.limite_credito:.2f}, '
                f'saldo atual: R$ {saldo_atual:.2f}).'
            )
            # Por padrão: apenas aviso, não bloqueia.
            # Para bloquear, descomentar a linha abaixo:
            # return JsonResponse({'erro': aviso_limite}, status=403)

    # ── Salvar ──
    with transaction.atomic():
        consumo = Consumo.objects.create(
            cliente=cliente,
            usuario=request.user,
            observacao=observacao,
            valor_total=total,
        )
        for item in itens_validos:
            ConsumoItem.objects.create(
                consumo=consumo,
                produto=item['produto'],
                quantidade=item['quantidade'],
                valor_unitario=item['valor_unitario'],
                subtotal=item['subtotal'],
            )

    response_data = {
        'sucesso': True,
        'consumo_id': str(consumo.id),
        'cliente_nome': cliente.nome,
        'valor_total': float(total),
        'num_itens': len(itens_validos),
    }
    if aviso_limite:
        response_data['aviso'] = aviso_limite

    return JsonResponse(response_data)


# ─── Histórico de Consumos ─────────────────────────────────────────────────────

@login_required
def lista_consumos(request):
    """Histórico geral de consumos com filtro por cliente."""
    cliente_id = request.GET.get('cliente_id', '')
    consumos = Consumo.objects.select_related('cliente', 'usuario').prefetch_related('itens')

    cliente = None
    if cliente_id:
        try:
            cliente = Cliente.objects.get(pk=cliente_id)
            consumos = consumos.filter(cliente=cliente)
        except (Cliente.DoesNotExist, Exception):
            pass

    consumos = consumos[:100]  # Limitar para performance
    return render(request, 'consumos/lista.html', {
        'consumos': consumos,
        'cliente': cliente,
    })


@login_required
def detalhe_consumo(request, pk):
    consumo = get_object_or_404(
        Consumo.objects.select_related('cliente', 'usuario').prefetch_related('itens__produto'),
        pk=pk
    )
    return render(request, 'consumos/detalhe.html', {'consumo': consumo})
