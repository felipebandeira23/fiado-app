from django.urls import path
from . import views

app_name = 'produtos'

urlpatterns = [
    path('', views.lista_produtos, name='lista'),
    path('novo/', views.novo_produto, name='novo'),
    path('<uuid:pk>/editar/', views.editar_produto, name='editar'),
    path('<uuid:pk>/toggle/', views.toggle_ativo, name='toggle'),
    path('api/ativos/', views.api_produtos_ativos, name='api_ativos'),
]
