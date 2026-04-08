from django.contrib import admin
from .models import Produto


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'categoria', 'valor_unitario', 'ativo', 'created_at')
    list_filter = ('ativo', 'categoria')
    search_fields = ('nome', 'categoria')
    list_editable = ('ativo',)
