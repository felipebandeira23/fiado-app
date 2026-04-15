from django.contrib import admin
from .models import FaturaMensal, Pagamento, AuditLog


class PagamentoInline(admin.TabularInline):
    model = Pagamento
    extra = 0
    readonly_fields = ['created_at']


@admin.register(FaturaMensal)
class FaturaMensalAdmin(admin.ModelAdmin):
    list_display = ['cliente', 'mes', 'ano', 'valor_total', 'valor_pago', 'status', 'data_vencimento']
    list_filter = ['status', 'ano', 'mes']
    search_fields = ['cliente__nome', 'cliente__codigo']
    inlines = [PagamentoInline]
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Pagamento)
class PagamentoAdmin(admin.ModelAdmin):
    list_display = ['fatura', 'valor', 'forma_pagamento', 'data', 'registrado_por']
    list_filter = ['forma_pagamento', 'data']
    readonly_fields = ['created_at']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['data', 'usuario', 'acao', 'descricao']
    list_filter = ['acao', 'data']
    search_fields = ['usuario__username', 'usuario__nome_completo', 'acao', 'descricao']
    readonly_fields = ['data', 'usuario', 'acao', 'descricao']
    date_hierarchy = 'data'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
