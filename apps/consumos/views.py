import json
from decimal import Decimal, InvalidOperation
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.db import transaction

from django.urls import reverse

from apps.clientes.models import Cliente
from apps.notificacoes.models import Notificacao
from apps.produtos.models import Produto
from .models import Consumo, ConsumoItem

SISTEMA_ITEM_AVULSO_NOME = '[SISTEMA] Item avulso'
SISTEMA_ITEM_AVULSO_VALOR_PADRAO = Decimal('0.01')


def _obter_produto_item_avulso():
    produto, _ = Produto.objects.get_or_create(
        nome=SISTEMA_ITEM_AVULSO_NOME,
        defaults={
            'descricao': 'Produto reservado para lançamentos por valor livre na Venda Rápida.',
            'categoria': 'Sistema',
            'valor_unitario': SISTEMA_ITEM_AVULSO_VALOR_PADRAO,
            'ativo': False,
        },
    )
    return produto


def _cliente_do_usuario(user):
    try:
        return user.cliente_vinculado
    except ObjectDoesNotExist:
        return None


# ─── Venda Rápida ─────────────────────────────────────────────────────────────

@login_required
def venda_rapida(request):
    """Tela principal de atendimento no balcão."""
    if _cliente_do_usuario(request.user):
        messages.error(request, 'Acesso não permitido para perfil de cliente.')
        return redirect('clientes:meu_perfil')
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
    if _cliente_do_usuario(request.user):
        return JsonResponse({'erro': 'Acesso não permitido para perfil de cliente.'}, status=403)

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
        qtd_raw = item.get('quantidade', 1)
        try:
            qtd = int(qtd_raw)
        except (TypeError, ValueError):
            return JsonResponse({'erro': 'Quantidade inválida.'}, status=400)

        if qtd <= 0:
            return JsonResponse({'erro': 'Quantidade deve ser maior que zero.'}, status=400)

        produto_id = item.get('produto_id')
        item_avulso = item.get('avulso') is True

        if item_avulso:
            valor_unit_raw = item.get('valor_unitario')
            if valor_unit_raw in (None, ''):
                return JsonResponse({'erro': 'Valor avulso é obrigatório.'}, status=400)

            try:
                valor_unit = Decimal(str(valor_unit_raw))
            except (InvalidOperation, TypeError, ValueError):
                return JsonResponse({'erro': 'Valor avulso inválido.'}, status=400)

            if valor_unit <= 0:
                return JsonResponse({'erro': 'Valor avulso deve ser maior que zero.'}, status=400)

            produto = _obter_produto_item_avulso()
        else:
            if not produto_id:
                return JsonResponse({'erro': 'Produto não informado.'}, status=400)

            try:
                produto = Produto.objects.get(pk=produto_id, ativo=True)
            except Produto.DoesNotExist:
                return JsonResponse({'erro': 'Produto inválido ou inativo.'}, status=400)

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

        # ── Notificação interna para o cliente ──
        if cliente.usuario_id:
            linhas = []
            for item in itens_validos:
                nome = item['produto'].nome
                if nome == '[SISTEMA] Item avulso':
                    nome = 'Item avulso'
                linhas.append(f'{nome} x{item["quantidade"]} — R$ {item["subtotal"]:.2f}')
            detalhe = '\n'.join(linhas)
            Notificacao.objects.create(
                usuario_id=cliente.usuario_id,
                tipo=Notificacao.TIPO_CONSUMO,
                titulo=f'Consumo registrado: R$ {total:.2f}',
                mensagem=(
                    f'Um consumo foi registrado em sua conta.\n\n'
                    f'{detalhe}\n\n'
                    f'Total: R$ {total:.2f}\n\n'
                    f'Confira se os itens e valores estão corretos.'
                ),
                url=reverse('consumos:detalhe', kwargs={'pk': consumo.pk}),
            )

    response_data = {
        'sucesso': True,
        'consumo_id': str(consumo.id),
        'cliente_nome': cliente.nome,
        'valor_total': float(total),
        'num_itens': len(itens_validos),
        'notificacao_enviada': cliente.usuario_id is not None,
    }
    if aviso_limite:
        response_data['aviso'] = aviso_limite

    return JsonResponse(response_data)


# ─── Histórico de Consumos ─────────────────────────────────────────────────────

@login_required
def lista_consumos(request):
    """Histórico geral de consumos com filtros por cliente e período."""
    cliente_logado = _cliente_do_usuario(request.user)
    cliente_id = request.GET.get('cliente_id', '')
    data_de = request.GET.get('data_de', '')
    data_ate = request.GET.get('data_ate', '')

    consumos = Consumo.objects.select_related('cliente', 'usuario').prefetch_related('itens')

    cliente = cliente_logado
    if cliente_logado:
        consumos = consumos.filter(cliente=cliente_logado)
    elif cliente_id:
        try:
            cliente = Cliente.objects.get(pk=cliente_id)
            consumos = consumos.filter(cliente=cliente)
        except (Cliente.DoesNotExist, Exception):
            pass

    if data_de:
        consumos = consumos.filter(data__gte=data_de)
    if data_ate:
        consumos = consumos.filter(data__lte=data_ate)

    paginator = Paginator(consumos, 30)
    page_obj = paginator.get_page(request.GET.get('page'))

    query_params = request.GET.copy()
    query_params.pop('page', None)

    return render(request, 'consumos/lista.html', {
        'consumos': page_obj,
        'page_obj': page_obj,
        'current_query_string': query_params.urlencode(),
        'cliente': cliente,
        'data_de': data_de,
        'data_ate': data_ate,
        'is_customer': cliente_logado is not None,
    })


@login_required
def detalhe_consumo(request, pk):
    consumo = get_object_or_404(
        Consumo.objects.select_related('cliente', 'usuario').prefetch_related('itens__produto'),
        pk=pk
    )
    cliente_logado = _cliente_do_usuario(request.user)
    is_customer = cliente_logado is not None
    if is_customer and consumo.cliente_id != cliente_logado.id:
        return redirect('clientes:meu_perfil')
    return render(request, 'consumos/detalhe.html', {
        'consumo': consumo,
        'is_customer': is_customer,
    })
