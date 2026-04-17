"""
Management command: verificar_vencimentos

Executa a verificação diária de faturas vencidas.
Marca como VENCIDA qualquer FaturaMensal com data_vencimento < hoje e status ABERTA/FECHADA.
O signal post_save cuidará de atualizar o status do cliente para INADIMPLENTE.
Envia notificação WhatsApp aos clientes cujas faturas acabaram de vencer (se configurado).

Uso:
    python manage.py verificar_vencimentos
"""
from datetime import date
from django.core.management.base import BaseCommand
from apps.faturas.models import FaturaMensal
from apps.faturas.whatsapp import enviar_notificacao_fatura_vencida


class Command(BaseCommand):
    help = 'Marca faturas vencidas e atualiza status dos clientes inadimplentes.'

    def handle(self, *args, **options):
        hoje = date.today()

        vencidas = FaturaMensal.objects.filter(
            status__in=[FaturaMensal.STATUS_ABERTA, FaturaMensal.STATUS_FECHADA],
            data_vencimento__lt=hoje,
        ).select_related('cliente')

        total = vencidas.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS('Nenhuma nova fatura vencida encontrada.'))
            return

        enviados = 0

        for fatura in vencidas:
            fatura.status = FaturaMensal.STATUS_VENCIDA
            fatura.save(update_fields=['status'])
            # O signal atualiza o cliente automaticamente

            if enviar_notificacao_fatura_vencida(fatura):
                enviados += 1

        self.stdout.write(
            self.style.SUCCESS(f'{total} fatura(s) marcada(s) como vencida(s).')
        )
        if enviados:
            self.stdout.write(
                self.style.SUCCESS(f'{enviados} notificação(ões) WhatsApp enviada(s).')
            )
