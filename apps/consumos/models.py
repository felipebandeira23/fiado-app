import uuid
from django.db import models
from django.conf import settings


class Consumo(models.Model):
    """Registro de consumo fiado de um cliente."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cliente = models.ForeignKey(
        'clientes.Cliente',
        on_delete=models.PROTECT,
        related_name='consumos',
        verbose_name='Cliente',
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='consumos_registrados',
        verbose_name='Registrado por',
    )
    data = models.DateField('Data', auto_now_add=True)
    hora = models.TimeField('Hora', auto_now_add=True)
    valor_total = models.DecimalField(
        'Valor total (R$)', max_digits=10, decimal_places=2, default=0
    )
    observacao = models.TextField('Observação', blank=True)
    faturado = models.BooleanField('Faturado', default=False)
    # fatura será preenchido na Fase 3
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Consumo'
        verbose_name_plural = 'Consumos'
        ordering = ['-created_at']

    def __str__(self):
        return f'Consumo {self.cliente.nome} – {self.data} – R$ {self.valor_total}'

    def calcular_total(self):
        """Recalcula e salva o valor_total a partir dos itens."""
        from django.db.models import Sum
        total = self.itens.aggregate(soma=Sum('subtotal'))['soma'] or 0
        self.valor_total = total
        self.save(update_fields=['valor_total'])
        return total


class ConsumoItem(models.Model):
    """Item individual dentro de um consumo."""
    consumo = models.ForeignKey(
        Consumo,
        on_delete=models.CASCADE,
        related_name='itens',
        verbose_name='Consumo',
    )
    produto = models.ForeignKey(
        'produtos.Produto',
        on_delete=models.PROTECT,
        related_name='consumo_itens',
        verbose_name='Produto',
    )
    quantidade = models.PositiveIntegerField('Quantidade', default=1)
    valor_unitario = models.DecimalField(
        'Valor unitário (R$)', max_digits=10, decimal_places=2,
        help_text='Preço no momento do consumo (histórico)',
    )
    subtotal = models.DecimalField('Subtotal (R$)', max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'Item de consumo'
        verbose_name_plural = 'Itens de consumo'

    def save(self, *args, **kwargs):
        self.subtotal = self.quantidade * self.valor_unitario
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.produto.nome} x{self.quantidade} = R$ {self.subtotal}'
