from django.urls import path
from . import views

app_name = 'usuarios'

urlpatterns = [
    path('', views.lista_usuarios, name='lista'),
    path('novo/', views.novo_usuario, name='novo'),
    path('<int:pk>/editar/', views.editar_usuario, name='editar'),
    path('alterar-senha/', views.alterar_senha, name='alterar_senha'),
]
