import uuid
from django.conf import settings
from django.db import models


class Notificacao(models.Model):
    TIPO_CONSUMO = 'consumo'
    TIPO_FATURA = 'fatura'
    TIPO_PAGAMENTO = 'pagamento'
    TIPO_SISTEMA = 'sistema'
    TIPO_CHOICES = [
        (TIPO_CONSUMO, 'Consumo registrado'),
        (TIPO_FATURA, 'Fatura'),
        (TIPO_PAGAMENTO, 'Pagamento'),
        (TIPO_SISTEMA, 'Sistema'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notificacoes',
        verbose_name='Usuário',
    )
    tipo = models.CharField('Tipo', max_length=20, choices=TIPO_CHOICES, default=TIPO_SISTEMA)
    titulo = models.CharField('Título', max_length=200)
    mensagem = models.TextField('Mensagem')
    lida = models.BooleanField('Lida', default=False)
    # Link opcional para o objeto relacionado (ex: detalhe do consumo)
    url = models.CharField('URL', max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Notificação'
        verbose_name_plural = 'Notificações'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.titulo} — {self.usuario}'
