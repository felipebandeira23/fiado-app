import calendar
import json
from datetime import date, timedelta, datetime
from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum, F, Count, ExpressionWrapper, DecimalField
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from apps.clientes.models import Cliente
from apps.consumos.models import Consumo
from .models import FaturaMensal, Pagamento, AuditLog
from .forms import PagamentoForm, FecharMesForm
from .whatsapp import enviar_notificacao_fatura_fechada


def _registrar_auditoria(usuario, acao, descricao):
    """Registra uma entrada no log de auditoria."""
    AuditLog.objects.create(usuario=usuario, acao=acao, descricao=descricao)


# ─── Lista de Faturas ─────────────────────────────────────────────────────────

@login_required
def lista_faturas(request):
    qs = FaturaMensal.objects.select_related('cliente').all()

    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    mes = request.GET.get('mes', '')
    ano_atual = datetime.now().year
    ano_param = request.GET.get('ano')
    ano = str(ano_atual) if ano_param is None else (ano_param or '').strip()

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

    paginator = Paginator(qs, 30)
    page_obj = paginator.get_page(request.GET.get('page'))

    query_params = request.GET.copy()
    query_params.pop('page', None)

    return render(request, 'faturas/lista.html', {
        'faturas': page_obj,
        'page_obj': page_obj,
        'current_query_string': query_params.urlencode(),
        'q': q,
        'status_filtro': status,
        'mes_filtro': mes,
        'ano_filtro': ano,
        'status_choices': FaturaMensal.STATUS_CHOICES,
        'resumo': resumo,
        'form_fechar': form_fechar,
        'ano_atual': ano_atual,
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

        _registrar_auditoria(
            request.user,
            'pagamento',
            f'Pagamento de R$ {valor:.2f} ({form.cleaned_data["forma_pagamento"]}) '
            f'registrado na fatura {fatura.mes:02d}/{fatura.ano} de {fatura.cliente.nome}.',
        )
        messages.success(request, f'Pagamento de R$ {valor:.2f} registrado com sucesso!')
    else:
        erro = next(iter(form.errors.values()))[0] if form.errors else 'Erro ao registrar pagamento. Verifique os dados.'
        messages.error(request, erro)

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
                            # Fatura recém-gerada fica em aberto aguardando pagamento.
                            'status': FaturaMensal.STATUS_ABERTA,
                            'data_fechamento': date.today(),
                            'data_vencimento': data_vencimento,
                        }
                    )

                    if not criada:
                        # Fatura já existia — atualiza
                        fatura.data_fechamento = date.today()
                        fatura.status = FaturaMensal.STATUS_ABERTA
                        fatura.save(update_fields=['data_fechamento', 'status'])
                        faturas_atualizadas += 1
                    else:
                        faturas_criadas += 1

                    # Vincular consumos à fatura e marcar como faturados
                    consumos_cliente.update(fatura=fatura, faturado=True)
                    fatura.recalcular_total()

                    # Notificar cliente via WhatsApp
                    enviar_notificacao_fatura_fechada(fatura)

            msg_parts = []
            if faturas_criadas:
                msg_parts.append(f'{faturas_criadas} fatura(s) criada(s)')
            if faturas_atualizadas:
                msg_parts.append(f'{faturas_atualizadas} fatura(s) atualizada(s)')
            resumo_msg = ', '.join(msg_parts)
            _registrar_auditoria(
                request.user,
                'fechar_mes',
                f'Mês {mes:02d}/{ano} fechado: {resumo_msg}.',
            )
            messages.success(request, f'Mês {mes:02d}/{ano} fechado: {resumo_msg}.')
            return redirect('faturas:lista')
    else:
        hoje = date.today()
        form = FecharMesForm(initial={'mes': hoje.month, 'ano': hoje.year})

    return render(request, 'faturas/fechar_mes.html', {'form': form})


# ─── Relatórios ──────────────────────────────────────────────────────────────

@login_required
def relatorios(request):
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

    # Receita por mês (últimos 12 meses) — inclui pendente calculado
    receita_por_mes_qs = (
        FaturaMensal.objects
        .values('ano', 'mes')
        .annotate(faturado=Sum('valor_total'), recebido=Sum('valor_pago'))
        .order_by('-ano', '-mes')[:12]
    )
    receita_por_mes = [
        {**row, 'pendente': (row['faturado'] or 0) - (row['recebido'] or 0)}
        for row in receita_por_mes_qs
    ]

    # Dados para gráfico de receita (ordem cronológica — mês mais antigo primeiro)
    receita_cronologica = list(reversed(receita_por_mes))
    chart_labels = json.dumps([f'{r["mes"]:02d}/{r["ano"]}' for r in receita_cronologica])
    chart_faturado = json.dumps([float(r['faturado'] or 0) for r in receita_cronologica])
    chart_recebido = json.dumps([float(r['recebido'] or 0) for r in receita_cronologica])

    # Dados para gráfico de formas de pagamento
    pagamentos_por_forma = (
        Pagamento.objects
        .values('forma_pagamento')
        .annotate(total=Sum('valor'), quantidade=Count('id'))
        .order_by('-total')
    )
    forma_labels = json.dumps([
        dict(Pagamento.FORMA_CHOICES).get(p['forma_pagamento'], p['forma_pagamento'])
        for p in pagamentos_por_forma
    ])
    forma_valores = json.dumps([float(p['total'] or 0) for p in pagamentos_por_forma])

    # Clientes inadimplentes com saldo
    inadimplentes = Cliente.objects.prefetch_related('faturas').order_by('nome')
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
        'chart_labels': chart_labels,
        'chart_faturado': chart_faturado,
        'chart_recebido': chart_recebido,
        'forma_labels': forma_labels,
        'forma_valores': forma_valores,
    })


# ─── PDF da Fatura ────────────────────────────────────────────────────────────

@login_required
def fatura_pdf(request, pk):
    """Gera um PDF da fatura para impressão/envio ao cliente."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable

    fatura = get_object_or_404(FaturaMensal.objects.select_related('cliente'), pk=pk)
    consumos = Consumo.objects.filter(fatura=fatura).prefetch_related('itens__produto')
    pagamentos = fatura.pagamentos.select_related('registrado_por').all()

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    cor_azul = colors.HexColor('#1F4E79')
    cor_cinza = colors.HexColor('#6c757d')
    cor_verde = colors.HexColor('#198754')
    cor_vermelho = colors.HexColor('#dc3545')

    style_titulo = ParagraphStyle('titulo', parent=styles['Title'], textColor=cor_azul, fontSize=18)
    style_subtitulo = ParagraphStyle('subtitulo', parent=styles['Normal'], textColor=cor_cinza, fontSize=10)
    style_secao = ParagraphStyle('secao', parent=styles['Heading2'], textColor=cor_azul, fontSize=12, spaceBefore=12)
    style_normal = styles['Normal']
    style_normal.fontSize = 9

    elementos = []

    # Cabeçalho
    elementos.append(Paragraph('App de Fiado', style_titulo))
    elementos.append(Paragraph('Sistema de Controle de Crédito', style_subtitulo))
    elementos.append(Spacer(1, 0.3 * cm))
    elementos.append(HRFlowable(width='100%', thickness=2, color=cor_azul))
    elementos.append(Spacer(1, 0.4 * cm))

    # Info da fatura
    status_map = {'aberta': 'Aberta', 'fechada': 'Fechada', 'paga': 'Paga', 'vencida': 'Vencida'}
    info_data = [
        ['FATURA', f'{fatura.mes:02d}/{fatura.ano}'],
        ['Cliente', fatura.cliente.nome],
        ['Código', fatura.cliente.codigo],
        ['Telefone', fatura.cliente.telefone or '—'],
        ['Status', status_map.get(fatura.status, fatura.status)],
        ['Vencimento', fatura.data_vencimento.strftime('%d/%m/%Y') if fatura.data_vencimento else '—'],
    ]
    info_table = Table(info_data, colWidths=[4 * cm, 12 * cm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), cor_cinza),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('FONTSIZE', (1, 0), (1, 0), 14),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
        ('TEXTCOLOR', (1, 0), (1, 0), cor_azul),
    ]))
    elementos.append(info_table)
    elementos.append(Spacer(1, 0.5 * cm))
    elementos.append(HRFlowable(width='100%', thickness=0.5, color=cor_cinza))

    # Consumos
    elementos.append(Paragraph('Consumos', style_secao))
    consumo_rows = [['Data', 'Produto', 'Qtd', 'Valor Unit.', 'Subtotal']]
    for consumo in consumos:
        for item in consumo.itens.all():
            consumo_rows.append([
                consumo.data.strftime('%d/%m/%Y'),
                item.produto.nome,
                str(item.quantidade),
                f'R$ {item.valor_unitario:.2f}',
                f'R$ {item.subtotal:.2f}',
            ])
    if len(consumo_rows) == 1:
        consumo_rows.append(['—', 'Nenhum consumo vinculado', '', '', ''])

    consumo_rows.append(['', 'TOTAL DA FATURA', '', '', f'R$ {fatura.valor_total:.2f}'])

    consumo_table = Table(consumo_rows, colWidths=[2.5 * cm, 7 * cm, 1.5 * cm, 2.5 * cm, 2.5 * cm])
    consumo_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), cor_azul),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -2), 0.5, colors.HexColor('#dee2e6')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f8f9fa')]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f4fd')),
        ('TEXTCOLOR', (0, -1), (-1, -1), cor_azul),
    ]))
    elementos.append(consumo_table)

    # Pagamentos
    elementos.append(Paragraph('Pagamentos Recebidos', style_secao))
    pag_rows = [['Data', 'Forma', 'Observação', 'Valor']]
    for pag in pagamentos:
        pag_rows.append([
            pag.data.strftime('%d/%m/%Y'),
            dict(Pagamento.FORMA_CHOICES).get(pag.forma_pagamento, pag.forma_pagamento),
            pag.observacao or '—',
            f'R$ {pag.valor:.2f}',
        ])
    if len(pag_rows) == 1:
        pag_rows.append(['—', 'Nenhum pagamento registrado', '', ''])

    pag_table = Table(pag_rows, colWidths=[2.5 * cm, 3.5 * cm, 7.5 * cm, 2.5 * cm])
    pag_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), cor_verde),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fff4')]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elementos.append(pag_table)

    # Resumo financeiro
    elementos.append(Spacer(1, 0.5 * cm))
    cor_restante = cor_verde if fatura.valor_restante == 0 else cor_vermelho
    resumo_data = [
        ['Total da fatura:', f'R$ {fatura.valor_total:.2f}'],
        ['Total pago:', f'R$ {fatura.valor_pago:.2f}'],
        ['Restante a pagar:', f'R$ {fatura.valor_restante:.2f}'],
    ]
    resumo_table = Table(resumo_data, colWidths=[10 * cm, 6 * cm])
    resumo_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TEXTCOLOR', (0, -1), (-1, -1), cor_restante),
        ('LINEABOVE', (0, -1), (-1, -1), 1, cor_cinza),
    ]))
    elementos.append(resumo_table)

    doc.build(elementos)
    buffer.seek(0)

    filename = f'fatura_{fatura.cliente.codigo}_{fatura.mes:02d}{fatura.ano}.pdf'
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ─── PDF do Relatório Financeiro ─────────────────────────────────────────────

@login_required
def relatorio_pdf(request):
    """Gera um PDF com o resumo financeiro do sistema."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable

    restante_expr = ExpressionWrapper(
        F('valor_total') - F('valor_pago'), output_field=DecimalField()
    )
    total_faturado = FaturaMensal.objects.aggregate(soma=Sum('valor_total'))['soma'] or 0
    total_recebido = FaturaMensal.objects.aggregate(soma=Sum('valor_pago'))['soma'] or 0
    total_em_aberto = FaturaMensal.objects.exclude(
        status=FaturaMensal.STATUS_PAGA
    ).annotate(restante=restante_expr).aggregate(soma=Sum('restante'))['soma'] or 0

    receita_por_mes = (
        FaturaMensal.objects
        .values('ano', 'mes')
        .annotate(faturado=Sum('valor_total'), recebido=Sum('valor_pago'))
        .order_by('-ano', '-mes')[:12]
    )

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
            inadimplentes_com_saldo.append((c.nome, c.codigo, c.get_status_display(), f'R$ {saldo:.2f}'))

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        leftMargin=2 * cm, rightMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    cor_azul = colors.HexColor('#1F4E79')
    cor_cinza = colors.HexColor('#6c757d')
    style_titulo = ParagraphStyle('titulo', parent=styles['Title'], textColor=cor_azul, fontSize=18)
    style_subtitulo = ParagraphStyle('subtitulo', parent=styles['Normal'], textColor=cor_cinza, fontSize=10)
    style_secao = ParagraphStyle('secao', parent=styles['Heading2'], textColor=cor_azul, fontSize=12, spaceBefore=12)

    elementos = []

    elementos.append(Paragraph('App de Fiado — Relatório Financeiro', style_titulo))
    elementos.append(Paragraph(f'Gerado em {date.today().strftime("%d/%m/%Y")}', style_subtitulo))
    elementos.append(Spacer(1, 0.3 * cm))
    elementos.append(HRFlowable(width='100%', thickness=2, color=cor_azul))
    elementos.append(Spacer(1, 0.5 * cm))

    # Resumo geral
    resumo_data = [
        ['Total faturado (histórico)', f'R$ {total_faturado:.2f}'],
        ['Total recebido', f'R$ {total_recebido:.2f}'],
        ['Em aberto (a receber)', f'R$ {total_em_aberto:.2f}'],
    ]
    resumo_table = Table(resumo_data, colWidths=[10 * cm, 6 * cm])
    resumo_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.HexColor('#e8f4fd'), colors.HexColor('#e8f8ee'), colors.HexColor('#fdecea')]),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
    ]))
    elementos.append(resumo_table)

    # Receita por mês
    elementos.append(Paragraph('Receita por Mês (últimos 12)', style_secao))
    mes_rows = [['Período', 'Faturado', 'Recebido', 'Pendente']]
    for row in receita_por_mes:
        pendente = row['faturado'] - row['recebido']
        mes_rows.append([
            f'{row["mes"]:02d}/{row["ano"]}',
            f'R$ {row["faturado"]:.2f}',
            f'R$ {row["recebido"]:.2f}',
            f'R$ {pendente:.2f}',
        ])
    if len(mes_rows) == 1:
        mes_rows.append(['—', '—', '—', '—'])

    mes_table = Table(mes_rows, colWidths=[4 * cm, 4 * cm, 4 * cm, 4 * cm])
    mes_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), cor_azul),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elementos.append(mes_table)

    # Inadimplentes
    if inadimplentes_com_saldo:
        elementos.append(Paragraph('Clientes com Débito', style_secao))
        inad_rows = [['Cliente', 'Código', 'Status', 'Saldo Devedor']] + list(inadimplentes_com_saldo)
        inad_table = Table(inad_rows, colWidths=[6 * cm, 2.5 * cm, 3 * cm, 4.5 * cm])
        inad_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc3545')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fdecea')]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elementos.append(inad_table)

    doc.build(elementos)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="relatorio_{date.today().strftime("%Y%m%d")}.pdf"'
    return response


# ─── Bloquear / Desbloquear Cliente ──────────────────────────────────────────

@login_required
def alternar_bloqueio_cliente(request, cliente_id):
    """Alterna o status do cliente entre ATIVO e BLOQUEADO."""
    if not request.user.is_admin_sistema:
        messages.error(request, 'Apenas administradores podem bloquear clientes.')
        return redirect('clientes:detalhe', pk=cliente_id)

    cliente = get_object_or_404(Cliente, pk=cliente_id)
    if cliente.status == Cliente.STATUS_BLOQUEADO:
        cliente.status = Cliente.STATUS_ATIVO
        cliente.save(update_fields=['status'])
        _registrar_auditoria(request.user, 'desbloquear_cliente', f'Cliente {cliente.nome} ({cliente.codigo}) desbloqueado.')
        messages.success(request, f'{cliente.nome} foi desbloqueado.')
    else:
        cliente.status = Cliente.STATUS_BLOQUEADO
        cliente.save(update_fields=['status'])
        _registrar_auditoria(request.user, 'bloquear_cliente', f'Cliente {cliente.nome} ({cliente.codigo}) bloqueado.')
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
