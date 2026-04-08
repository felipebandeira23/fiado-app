from django.contrib import admin
from .models import Cliente, ClienteQRCode


class ClienteQRCodeInline(admin.TabularInline):
    model = ClienteQRCode
    readonly_fields = ('imagem', 'criado_em')
    extra = 0


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nome', 'telefone', 'status', 'limite_credito', 'created_at')
    list_filter = ('status',)
    search_fields = ('nome', 'telefone', 'codigo', 'cpf')
    readonly_fields = ('id', 'codigo', 'token_qr', 'created_at', 'updated_at')
    inlines = [ClienteQRCodeInline]
