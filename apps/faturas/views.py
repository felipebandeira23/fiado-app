import calendar
from datetime import date, timedelta
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum, F, ExpressionWrapper, DecimalField
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from apps.clientes.models import Cliente
from apps.consumos.models import Consumo
from .models import FaturaMensal, Pagamento
from .forms import PagamentoForm, FecharMesForm


# ─── Lista de Faturas ─────────────────────────────────────────────────────────

@login_required
def lista_faturas(request):
    qs = FaturaMensal.objects.select_related('cliente').all()

    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    mes = request.GET.get('mes', '')
    ano = request.GET.get('ano', '')

    if q:
        qs = qs.filter(Q(cliente__nome__icontains=q) | Q(cliente__codigo__icontains=q))
    if status:
        qs = qs.filter(status=status)
    if mes:
        qs = qs.filter(mes=mes)
    if ano:
        qs = qs.filter(ano=ano)

    restante_expr = ExpressionWrapper(
        F('valor_total') - F('valor_pago'), output_field=DecimalField()
    )
    abertas_qs = qs.exclude(status=FaturaMensal.STATUS_PAGA).annotate(restante=restante_expr)
    total_a_receber = abertas_qs.aggregate(soma=Sum('restante'))['soma'] or 0

    resumo = {
        'total_faturas': qs.count(),
        'abertas': qs.filter(status=FaturaMensal.STATUS_ABERTA).count(),
        'fechadas': qs.filter(status=FaturaMensal.STATUS_FECHADA).count(),
        'vencidas': qs.filter(status=FaturaMensal.STATUS_VENCIDA).count(),
        'pagas': qs.filter(status=FaturaMensal.STATUS_PAGA).count(),
    }

    hoje = date.today()
    form_fechar = FecharMesForm(initial={'mes': hoje.month, 'ano': hoje.year})

    return render(request, 'faturas/lista.html', {
        'faturas': qs,
        'q': q,
        'status_filtro': status,
        'mes_filtro': mes,
        'ano_filtro': ano,
        'status_choices': FaturaMensal.STATUS_CHOICES,
        'resumo': resumo,
        'form_fechar': form_fechar,
    })


# ─── Detalhe da Fatura ────────────────────────────────────────────────────────

@login_required
def detalhe_fatura(request, pk):
    fatura = get_object_or_404(FaturaMensal.objects.select_related('cliente'), pk=pk)
    consumos = Consumo.objects.filter(fatura=fatura).prefetch_related('itens__produto')
    pagamentos = fatura.pagamentos.select_related('registrado_por').all()
    form = PagamentoForm()

    return render(request, 'faturas/detalhe.html', {
        'fatura': fatura,
        'consumos': consumos,
        'pagamentos': pagamentos,
        'form': form,
    })


# ─── Registrar Pagamento ──────────────────────────────────────────────────────

@login_required
@require_POST
def registrar_pagamento(request, pk):
    fatura = get_object_or_404(FaturaMensal, pk=pk)

    if fatura.status == FaturaMensal.STATUS_PAGA:
        messages.warning(request, 'Esta fatura já está totalmente paga.')
        return redirect('faturas:detalhe', pk=pk)

    form = PagamentoForm(request.POST)
    if form.is_valid():
        valor = form.cleaned_data['valor']
        restante = fatura.valor_restante

        if valor > restante:
            messages.error(request, f'Valor excede o restante da fatura (R$ {restante:.2f}).')
            return redirect('faturas:detalhe', pk=pk)

        with transaction.atomic():
            pagamento = form.save(commit=False)
            pagamento.fatura = fatura
            pagamento.registrado_por = request.user
            pagamento.save()
            # recalcular_pago() é chamado automaticamente pelo signal post_save de Pagamento

        messages.success(request, f'Pagamento de R$ {valor:.2f} registrado com sucesso!')
    else:
        messages.error(request, 'Erro ao registrar pagamento. Verifique os dados.')

    return redirect('faturas:detalhe', pk=pk)


# ─── Fechar Mês (gerar faturas) ───────────────────────────────────────────────

@login_required
def fechar_mes(request):
    if request.method == 'POST':
        form = FecharMesForm(request.POST)
        if form.is_valid():
            mes = form.cleaned_data['mes']
            ano = form.cleaned_data['ano']

            # Consumos não faturados do mês/ano
            consumos_sem_fatura = Consumo.objects.filter(
                faturado=False,
                data__month=mes,
                data__year=ano,
            ).select_related('cliente')

            if not consumos_sem_fatura.exists():
                messages.warning(
                    request,
                    f'Nenhum consumo sem fatura encontrado para {mes:02d}/{ano}.'
                )
                return redirect('faturas:lista')

            # Agrupar por cliente
            clientes_ids = consumos_sem_fatura.values_list('cliente_id', flat=True).distinct()

            # Calcular data de vencimento (último dia do mês)
            ultimo_dia = calendar.monthrange(ano, mes)[1]
            data_vencimento = date(ano, mes, ultimo_dia)

            faturas_criadas = 0
            faturas_atualizadas = 0

            with transaction.atomic():
                for cliente_id in clientes_ids:
                    consumos_cliente = consumos_sem_fatura.filter(cliente_id=cliente_id)
                    total = consumos_cliente.aggregate(soma=Sum('valor_total'))['soma'] or 0

                    fatura, criada = FaturaMensal.objects.get_or_create(
                        cliente_id=cliente_id,
                        mes=mes,
                        ano=ano,
                        defaults={
                            'valor_total': total,
                            'status': FaturaMensal.STATUS_FECHADA,
                            'data_fechamento': date.today(),
                            'data_vencimento': data_vencimento,
                        }
                    )

                    if not criada:
                        # Fatura já existia — atualiza
                        fatura.data_fechamento = date.today()
                        fatura.status = FaturaMensal.STATUS_FECHADA
                        fatura.save(update_fields=['data_fechamento', 'status'])
                        faturas_atualizadas += 1
                    else:
                        faturas_criadas += 1

                    # Vincular consumos à fatura e marcar como faturados
                    consumos_cliente.update(fatura=fatura, faturado=True)
                    fatura.recalcular_total()

            msg_parts = []
            if faturas_criadas:
                msg_parts.append(f'{faturas_criadas} fatura(s) criada(s)')
            if faturas_atualizadas:
                msg_parts.append(f'{faturas_atualizadas} fatura(s) atualizada(s)')
            messages.success(request, f'Mês {mes:02d}/{ano} fechado: {", ".join(msg_parts)}.')
            return redirect('faturas:lista')
    else:
        hoje = date.today()
        form = FecharMesForm(initial={'mes': hoje.month, 'ano': hoje.year})

    return render(request, 'faturas/fechar_mes.html', {'form': form})


# ─── Relatórios ──────────────────────────────────────────────────────────────

@login_required
def relatorios(request):
    from django.db.models import Count, F, ExpressionWrapper, DecimalField
    from apps.consumos.models import Consumo

    restante_expr = ExpressionWrapper(
        F('valor_total') - F('valor_pago'), output_field=DecimalField()
    )

    # Resumo geral
    total_faturado = FaturaMensal.objects.aggregate(soma=Sum('valor_total'))['soma'] or 0
    total_recebido = FaturaMensal.objects.aggregate(soma=Sum('valor_pago'))['soma'] or 0
    total_em_aberto = FaturaMensal.objects.exclude(
        status=FaturaMensal.STATUS_PAGA
    ).annotate(restante=restante_expr).aggregate(soma=Sum('restante'))['soma'] or 0

    # Receita por mês (últimos 12 meses)
    receita_por_mes = (
        FaturaMensal.objects
        .values('ano', 'mes')
        .annotate(faturado=Sum('valor_total'), recebido=Sum('valor_pago'))
        .order_by('-ano', '-mes')[:12]
    )

    # Clientes inadimplentes com saldo
    inadimplentes = (
        Cliente.objects
        .filter(status__in=[Cliente.STATUS_INADIMPLENTE, Cliente.STATUS_BLOQUEADO])
        .prefetch_related('faturas')
        .order_by('nome')
    )
    inadimplentes_com_saldo = []
    for c in inadimplentes:
        saldo = c.saldo_devedor_total
        if saldo > 0:
            inadimplentes_com_saldo.append({'cliente': c, 'saldo': saldo})
    inadimplentes_com_saldo.sort(key=lambda x: x['saldo'], reverse=True)

    # Ranking de clientes por consumo total (top 10)
    ranking_clientes = (
        Consumo.objects
        .values('cliente__id', 'cliente__nome', 'cliente__codigo')
        .annotate(total_consumido=Sum('valor_total'), num_consumos=Count('id'))
        .order_by('-total_consumido')[:10]
    )

    # Faturas vencidas em aberto
    faturas_vencidas = FaturaMensal.objects.filter(
        status=FaturaMensal.STATUS_VENCIDA
    ).select_related('cliente').annotate(restante=restante_expr).order_by('-restante')

    return render(request, 'relatorios/relatorios.html', {
        'total_faturado': total_faturado,
        'total_recebido': total_recebido,
        'total_em_aberto': total_em_aberto,
        'receita_por_mes': receita_por_mes,
        'inadimplentes_com_saldo': inadimplentes_com_saldo,
        'ranking_clientes': ranking_clientes,
        'faturas_vencidas': faturas_vencidas,
    })


# ─── Bloquear / Desbloquear Cliente ──────────────────────────────────────────

@login_required
def alternar_bloqueio_cliente(request, cliente_id):
    """Alterna o status do cliente entre ATIVO e BLOQUEADO."""
    from apps.usuarios.models import Usuario
    if not request.user.is_admin_sistema:
        messages.error(request, 'Apenas administradores podem bloquear clientes.')
        return redirect('clientes:detalhe', pk=cliente_id)

    cliente = get_object_or_404(Cliente, pk=cliente_id)
    if cliente.status == Cliente.STATUS_BLOQUEADO:
        cliente.status = Cliente.STATUS_ATIVO
        cliente.save(update_fields=['status'])
        messages.success(request, f'{cliente.nome} foi desbloqueado.')
    else:
        cliente.status = Cliente.STATUS_BLOQUEADO
        cliente.save(update_fields=['status'])
        messages.warning(request, f'{cliente.nome} foi bloqueado.')

    return redirect('clientes:detalhe', pk=cliente_id)


# ─── API: Débito do cliente ───────────────────────────────────────────────────

@login_required
def api_debito_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, pk=cliente_id)
    faturas = FaturaMensal.objects.filter(
        cliente=cliente
    ).exclude(status=FaturaMensal.STATUS_PAGA)

    total_devido = sum(f.valor_restante for f in faturas)
    faturas_data = [
        {
            'id': str(f.id),
            'periodo': f'{f.mes:02d}/{f.ano}',
            'valor_total': float(f.valor_total),
            'valor_pago': float(f.valor_pago),
            'valor_restante': float(f.valor_restante),
            'status': f.status,
        }
        for f in faturas
    ]

    return JsonResponse({
        'cliente_id': str(cliente.id),
        'cliente_nome': cliente.nome,
        'total_devido': float(total_devido),
        'faturas': faturas_data,
    })
