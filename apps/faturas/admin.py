from django.contrib import admin
from .models import FaturaMensal, Pagamento


class PagamentoInline(admin.TabularInline):
    model = Pagamento
    extra = 0
    readonly_fields = ['created_at']


@admin.register(FaturaMensal)
class FaturaMensalAdmin(admin.ModelAdmin):
    list_display = ['cliente', 'mes', 'ano', 'valor_total', 'valor_pago', 'status']
    list_filter = ['status', 'ano', 'mes']
    search_fields = ['cliente__nome', 'cliente__codigo']
    inlines = [PagamentoInline]
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Pagamento)
class PagamentoAdmin(admin.ModelAdmin):
    list_display = ['fatura', 'valor', 'forma_pagamento', 'data', 'registrado_por']
    list_filter = ['forma_pagamento', 'data']
    readonly_fields = ['created_at']
