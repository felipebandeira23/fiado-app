import uuid
from django.db import models


class Produto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField('Nome', max_length=200)
    descricao = models.TextField('Descrição', blank=True)
    categoria = models.CharField('Categoria', max_length=100, blank=True)
    valor_unitario = models.DecimalField('Valor unitário (R$)', max_digits=10, decimal_places=2)
    ativo = models.BooleanField('Ativo', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'
        ordering = ['categoria', 'nome']

    def __str__(self):
        return f'{self.nome} – R$ {self.valor_unitario:.2f}'
