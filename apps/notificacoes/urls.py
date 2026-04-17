from django.urls import path
from . import views

app_name = 'notificacoes'

urlpatterns = [
    path('api/notificacoes/', views.api_notificacoes, name='api_lista'),
    path('api/notificacoes/<uuid:pk>/lida/', views.api_marcar_lida, name='api_marcar_lida'),
    path('api/notificacoes/marcar-todas-lidas/', views.api_marcar_todas_lidas, name='api_marcar_todas_lidas'),
]
