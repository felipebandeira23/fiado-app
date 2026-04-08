from django.urls import path
from . import views

app_name = 'consumos'

urlpatterns = [
    path('venda-rapida/', views.venda_rapida, name='venda_rapida'),
    path('consumos/', views.lista_consumos, name='lista'),
    path('consumos/<uuid:pk>/', views.detalhe_consumo, name='detalhe'),

    # API
    path('api/consumos/salvar/', views.api_salvar_consumo, name='api_salvar'),
]
