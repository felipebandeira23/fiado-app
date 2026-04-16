from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from apps.clientes.views import healthcheck

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', healthcheck, name='healthcheck'),

    # Autenticação
    path('login/', auth_views.LoginView.as_view(template_name='usuarios/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Redefinição de senha (recuperação para usuários que esqueceram)
    path('senha/redefinir/',
         auth_views.PasswordResetView.as_view(
             template_name='usuarios/password_reset.html',
             email_template_name='usuarios/password_reset_email.txt',
             subject_template_name='usuarios/password_reset_subject.txt',
         ),
         name='password_reset'),
    path('senha/redefinir/enviado/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='usuarios/password_reset_done.html',
         ),
         name='password_reset_done'),
    path('senha/redefinir/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='usuarios/password_reset_confirm.html',
         ),
         name='password_reset_confirm'),
    path('senha/redefinir/concluido/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='usuarios/password_reset_complete.html',
         ),
         name='password_reset_complete'),

    # Apps
    path('', include('apps.clientes.urls')),
    path('produtos/', include('apps.produtos.urls')),
    path('usuarios/', include('apps.usuarios.urls')),
    path('', include('apps.consumos.urls')),
    path('', include('apps.faturas.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
