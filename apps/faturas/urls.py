from django.urls import path
from . import views

app_name = 'faturas'

urlpatterns = [
    path('faturas/', views.lista_faturas, name='lista'),
    path('faturas/fechar-mes/', views.fechar_mes, name='fechar_mes'),
    path('faturas/<uuid:pk>/', views.detalhe_fatura, name='detalhe'),
    path('faturas/<uuid:pk>/pagamento/', views.registrar_pagamento, name='pagamento'),
    path('faturas/<uuid:pk>/pdf/', views.fatura_pdf, name='fatura_pdf'),
    path('relatorios/', views.relatorios, name='relatorios'),
    path('relatorios/pdf/', views.relatorio_pdf, name='relatorio_pdf'),
    path('clientes/<uuid:cliente_id>/bloquear/', views.alternar_bloqueio_cliente, name='bloquear_cliente'),
    path('api/cliente/<uuid:cliente_id>/debito/', views.api_debito_cliente, name='api_debito'),
]
