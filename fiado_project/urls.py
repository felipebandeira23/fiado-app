from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Autenticação
    path('login/', auth_views.LoginView.as_view(template_name='usuarios/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Apps
    path('', include('apps.clientes.urls')),
    path('produtos/', include('apps.produtos.urls')),
    path('usuarios/', include('apps.usuarios.urls')),
    path('', include('apps.consumos.urls')),
    path('', include('apps.faturas.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
