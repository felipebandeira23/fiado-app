import uuid
from django.db import models
from django.conf import settings
from django.db.models import Sum


class FaturaMensal(models.Model):
    STATUS_ABERTA = 'aberta'
    STATUS_FECHADA = 'fechada'
    STATUS_PAGA = 'paga'
    STATUS_VENCIDA = 'vencida'
    STATUS_CHOICES = [
        (STATUS_ABERTA, 'Aberta'),
        (STATUS_FECHADA, 'Fechada'),
        (STATUS_PAGA, 'Paga'),
        (STATUS_VENCIDA, 'Vencida'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cliente = models.ForeignKey(
        'clientes.Cliente',
        on_delete=models.PROTECT,
        related_name='faturas',
        verbose_name='Cliente',
    )
    mes = models.PositiveSmallIntegerField('Mês')
    ano = models.PositiveSmallIntegerField('Ano')
    valor_total = models.DecimalField(
        'Valor total (R$)', max_digits=10, decimal_places=2, default=0
    )
    valor_pago = models.DecimalField(
        'Valor pago (R$)', max_digits=10, decimal_places=2, default=0
    )
    status = models.CharField(
        'Status', max_length=20, choices=STATUS_CHOICES, default=STATUS_ABERTA
    )
    data_fechamento = models.DateField('Data de fechamento', null=True, blank=True)
    data_vencimento = models.DateField('Data de vencimento', null=True, blank=True)
    observacao = models.TextField('Observação', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Fatura Mensal'
        verbose_name_plural = 'Faturas Mensais'
        ordering = ['-ano', '-mes', 'cliente__nome']
        unique_together = [('cliente', 'mes', 'ano')]

    def __str__(self):
        return f'Fatura {self.cliente.nome} – {self.mes:02d}/{self.ano}'

    @property
    def valor_restante(self):
        return self.valor_total - self.valor_pago

    @property
    def esta_quitada(self):
        return self.valor_pago >= self.valor_total

    def recalcular_total(self):
        """Soma os consumos vinculados e atualiza valor_total."""
        from apps.consumos.models import Consumo
        total = Consumo.objects.filter(fatura=self).aggregate(
            soma=Sum('valor_total')
        )['soma'] or 0
        self.valor_total = total
        self.save(update_fields=['valor_total'])
        return total

    def recalcular_pago(self):
        """Soma os pagamentos e atualiza valor_pago + status."""
        total_pago = self.pagamentos.aggregate(soma=Sum('valor'))['soma'] or 0
        self.valor_pago = total_pago
        if self.valor_pago >= self.valor_total and self.valor_total > 0:
            self.status = self.STATUS_PAGA
        self.save(update_fields=['valor_pago', 'status'])
        return total_pago


class Pagamento(models.Model):
    FORMA_DINHEIRO = 'dinheiro'
    FORMA_PIX = 'pix'
    FORMA_CARTAO_DEBITO = 'cartao_debito'
    FORMA_CARTAO_CREDITO = 'cartao_credito'
    FORMA_CHOICES = [
        (FORMA_DINHEIRO, 'Dinheiro'),
        (FORMA_PIX, 'PIX'),
        (FORMA_CARTAO_DEBITO, 'Cartão de Débito'),
        (FORMA_CARTAO_CREDITO, 'Cartão de Crédito'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fatura = models.ForeignKey(
        FaturaMensal,
        on_delete=models.PROTECT,
        related_name='pagamentos',
        verbose_name='Fatura',
    )
    valor = models.DecimalField('Valor (R$)', max_digits=10, decimal_places=2)
    forma_pagamento = models.CharField(
        'Forma de pagamento', max_length=20, choices=FORMA_CHOICES, default=FORMA_DINHEIRO
    )
    data = models.DateField('Data do pagamento', auto_now_add=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='pagamentos_registrados',
        verbose_name='Registrado por',
    )
    observacao = models.TextField('Observação', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Pagamento'
        verbose_name_plural = 'Pagamentos'
        ordering = ['-created_at']

    def __str__(self):
        return f'Pagamento R$ {self.valor} – {self.fatura}'


class AuditLog(models.Model):
    """Registro de auditoria de ações críticas do sistema."""
    id = models.BigAutoField(primary_key=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name='Usuário',
    )
    acao = models.CharField('Ação', max_length=100)
    descricao = models.TextField('Descrição')
    data = models.DateTimeField('Data/Hora', auto_now_add=True)

    class Meta:
        verbose_name = 'Log de Auditoria'
        verbose_name_plural = 'Logs de Auditoria'
        ordering = ['-data']

    def __str__(self):
        return f'{self.acao} — {self.usuario} — {self.data:%d/%m/%Y %H:%M}'
