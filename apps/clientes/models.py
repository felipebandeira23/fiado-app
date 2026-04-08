import uuid
import qrcode
from io import BytesIO
from django.core.files import File
from django.db import models
from django.urls import reverse


class Cliente(models.Model):
    STATUS_ATIVO = 'ativo'
    STATUS_BLOQUEADO = 'bloqueado'
    STATUS_INADIMPLENTE = 'inadimplente'
    STATUS_CHOICES = [
        (STATUS_ATIVO, 'Ativo'),
        (STATUS_BLOQUEADO, 'Bloqueado'),
        (STATUS_INADIMPLENTE, 'Inadimplente'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.CharField('Código', max_length=20, unique=True, blank=True)
    nome = models.CharField('Nome', max_length=200)
    telefone = models.CharField('Telefone / WhatsApp', max_length=20)
    cpf = models.CharField('CPF', max_length=14, blank=True, null=True, unique=True)
    endereco = models.TextField('Endereço', blank=True)
    foto = models.ImageField('Foto', upload_to='clientes/fotos/', blank=True, null=True)
    limite_credito = models.DecimalField(
        'Limite de crédito (R$)', max_digits=10, decimal_places=2, default=0,
        help_text='0 = sem limite definido'
    )
    status = models.CharField(
        'Status', max_length=20, choices=STATUS_CHOICES, default=STATUS_ATIVO
    )
    token_qr = models.UUIDField(
        'Token QR Code', default=uuid.uuid4, unique=True, editable=False
    )
    observacoes = models.TextField('Observações', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['nome']

    def __str__(self):
        return f'{self.codigo} – {self.nome}'

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self._gerar_codigo()
        super().save(*args, **kwargs)

    def _gerar_codigo(self):
        ultimo = Cliente.objects.order_by('-created_at').first()
        if ultimo and ultimo.codigo and ultimo.codigo.startswith('CLI-'):
            try:
                num = int(ultimo.codigo.split('-')[1]) + 1
            except (IndexError, ValueError):
                num = 1
        else:
            num = 1
        return f'CLI-{num:04d}'

    def get_absolute_url(self):
        return reverse('clientes:detalhe', kwargs={'pk': self.pk})

    @property
    def esta_bloqueado(self):
        return self.status == self.STATUS_BLOQUEADO

    @property
    def saldo_devedor_total(self):
        """Soma de todas as faturas em aberto do cliente."""
        from django.db.models import Sum
        # Será implementado na Fase 3 com o app faturas
        # Por ora retorna 0
        return 0

    @property
    def status_badge(self):
        badges = {
            'ativo': 'success',
            'bloqueado': 'danger',
            'inadimplente': 'warning',
        }
        color = badges.get(self.status, 'secondary')
        return f'<span class="badge bg-{color}">{self.get_status_display()}</span>'

    def gerar_qrcode_url(self):
        """Retorna a URL que o QR Code deve codificar."""
        return f'/api/cliente/qr/{self.token_qr}/'


class ClienteQRCode(models.Model):
    """Armazena a imagem do QR Code gerada para cada cliente."""
    cliente = models.OneToOneField(
        Cliente, on_delete=models.CASCADE, related_name='qrcode_obj'
    )
    imagem = models.ImageField(upload_to='clientes/qrcodes/')
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'QR Code – {self.cliente.nome}'
