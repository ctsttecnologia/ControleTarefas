from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from tarefas import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # URLs de autenticação, Apps principais 
    path('login/', LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', LogoutView.as_view(template_name='logout.html'), name='logout'),
    path('', include('home.urls')),  # Inclui as URLs do app home
    path('accounts/', include('usuario.urls')),
    path('usuario/', include(('usuario.urls', 'usuario'), namespace='usuariouse')),
    
    # Outros apps
    path('profile/', views.profile_view, name='profile'),
    path('epi/', include('epi.urls')),
    path('cliente/', include('cliente.urls')),
    path('seguranca/', include('seguranca_trabalho.urls')),
    path('departamento_pessoal/', include('departamento_pessoal.urls')),
    path('tarefas/', include('tarefas.urls')),
    path('logradouro/', include('logradouro.urls')),
    path('treinamentos/', include('treinamentos.urls')),
    path('automovel/', include('automovel.urls')),
    path('atas/', include('ata_reuniao.urls')),
    
    # URLs estáticas e de mídia (para desenvolvimento)
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)