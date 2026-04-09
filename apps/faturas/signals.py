from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import FaturaMensal, Pagamento


@receiver(post_save, sender=FaturaMensal)
def atualizar_status_cliente_fatura(sender, instance, **kwargs):
    """
    Quando uma fatura é marcada como VENCIDA → cliente vira INADIMPLENTE.
    Quando TODAS as faturas em aberto do cliente são PAGAS → cliente volta a ATIVO.
    """
    cliente = instance.cliente

    if instance.status == FaturaMensal.STATUS_VENCIDA:
        if cliente.status == cliente.STATUS_ATIVO:
            cliente.status = cliente.STATUS_INADIMPLENTE
            cliente.save(update_fields=['status'])

    elif instance.status == FaturaMensal.STATUS_PAGA:
        tem_divida = FaturaMensal.objects.filter(
            cliente=cliente
        ).exclude(status=FaturaMensal.STATUS_PAGA).exists()

        if not tem_divida and cliente.status == cliente.STATUS_INADIMPLENTE:
            cliente.status = cliente.STATUS_ATIVO
            cliente.save(update_fields=['status'])


@receiver(post_save, sender=Pagamento)
def recalcular_fatura_apos_pagamento(sender, instance, created, **kwargs):
    """Ao salvar um pagamento, recalcula totais da fatura."""
    if created:
        instance.fatura.recalcular_pago()
