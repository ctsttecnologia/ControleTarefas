
# gerenciandoTarefas/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.views.generic import RedirectView
from django.views.static import serve
from django.urls import re_path

# Importar as views de erro
from core.views import (
    error_400_view,
    error_403_view,
    error_404_view,
    error_500_view,
    error_503_view
)

# Adicione esta view simples para redirecionar
def home_redirect(request):
    if request.user.is_authenticated:
        return redirect('usuario:profile')
    else:
        return redirect('usuario:login')


# Adicione esta importação para a sua ProfileView
from usuario.views import ProfileView


urlpatterns = [
    path('admin/', admin.site.urls),
    
    # A Rota raiz ('/') agora aponta para a sua ProfileView
    # Esta será a sua página inicial/dashboard após o login
    path('', ProfileView.as_view(), name='home'),

    path('', include('core.urls')), 

    # Rotas das apps com seus prefixos
    path('favicon.ico', RedirectView.as_view(url='/static/img/favicon.ico', permanent=True)),
    path('contas/', include('usuario.urls', namespace='usuario')), # Onde está o seu CustomLoginView
    path('logradouro/', include('logradouro.urls')),
    path('cliente/', include('cliente.urls')),
    path('tarefas/', include('tarefas.urls', namespace='tarefas')),
    path('seguranca/', include('seguranca_trabalho.urls', namespace='seguranca_trabalho')),
    path('suprimentos/', include('suprimentos.urls', namespace='suprimentos')),
    path('departamento_pessoal/', include('departamento_pessoal.urls', namespace='departamento_pessoal')),
    path('gestao_riscos/', include('gestao_riscos.urls', namespace='gestao_riscos')),  
    path('treinamentos/', include('treinamentos.urls')),
    path('tributacao/', include('tributacao.urls')),
    path('automovel/', include('automovel.urls')),
    path('atas/', include('ata_reuniao.urls')),
    path('ferramentas/', include('ferramentas.urls', namespace='ferramentas')),
    path('controle_de_telefone/', include('controle_de_telefone.urls')),
    path('select2/', include('django_select2.urls')),
    path('chat/', include('chat.urls')),
    path('documentos/', include('documentos.urls', namespace='documentos')),
    path('pgr_gestao/', include('pgr_gestao.urls', namespace='pgr_gestao')),
    # Isso permite usar o namespace "dashboard..."
    path('dashboard/', include('dashboard.urls')),
    # API URLs
    path('api/', include('api.urls')),
    path('api/auth/', include('dj_rest_auth.urls')),
    path('notifications/', include('notifications.urls', namespace='notifications')),  # Para manter compatibilidade com URLs antigas
    path("ltcat/", include("ltcat.urls")),


   
]


# Configurar handlers de erro
handler400 = 'core.views.error_400_view'
handler403 = 'core.views.error_403_view'
handler404 = 'core.views.error_404_view'
handler500 = 'core.views.error_500_view'
handler503 = 'core.views.error_503_view'

# Configuração global
admin.site.site_header = "Sistema de Gestão Integrada"
admin.site.site_title = "Dashboard"
admin.site.index_title = "Painel de Controle"

# Configuração para servir arquivos de mídia e estáticos
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # ✅ Serve arquivos privados em desenvolvimento
    urlpatterns += static(settings.SENDFILE_URL, document_root=settings.PRIVATE_MEDIA_ROOT)

#if settings.STORAGE_PROVIDER != 'GCS':
#    urlpatterns += [
#        re_path(r'^midia/(?P<path>.*)$', serve, {
#            'document_root': settings.MEDIA_ROOT,
#        }),
#    ]