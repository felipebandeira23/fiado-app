from django.contrib import admin
from .models import Consumo, ConsumoItem


class ConsumoItemInline(admin.TabularInline):
    model = ConsumoItem
    readonly_fields = ('subtotal',)
    extra = 0


@admin.register(Consumo)
class ConsumoAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'data', 'hora', 'valor_total', 'faturado', 'usuario')
    list_filter = ('faturado', 'data')
    search_fields = ('cliente__nome', 'cliente__codigo')
    readonly_fields = ('id', 'data', 'hora', 'created_at', 'valor_total')
    inlines = [ConsumoItemInline]

    def has_delete_permission(self, request, obj=None):
        """Nunca permitir exclusão física de consumos."""
        return False
