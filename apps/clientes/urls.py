from django.urls import path
from . import views

app_name = 'clientes'

urlpatterns = [
    # Dashboard (página inicial)
    path('', views.dashboard, name='dashboard'),

    # CRUD
    path('clientes/', views.lista_clientes, name='lista'),
    path('clientes/novo/', views.novo_cliente, name='novo'),
    path('clientes/<uuid:pk>/', views.detalhe_cliente, name='detalhe'),
    path('clientes/<uuid:pk>/editar/', views.editar_cliente, name='editar'),
    path('clientes/<uuid:pk>/qrcode/', views.qrcode_cliente, name='qrcode'),
    path('clientes/<uuid:pk>/qrcode/download/', views.download_qrcode, name='download_qrcode'),

    # API JSON
    path('api/cliente/qr/<uuid:token>/', views.api_cliente_por_qr, name='api_qr'),
    path('api/clientes/busca/', views.api_busca_clientes, name='api_busca'),
]
