# Ficheiro 1: O seu urls.py PRINCIPAL (gerenciandoTarefas/urls.py)
#
# Este ficheiro está CORRETO. Ele define o prefixo 'logradouro/'
# e inclui as URLs da sua aplicação.

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from usuario.views import CustomLoginView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Rota raiz ('/') aponta para a página de Login.
    path('', CustomLoginView.as_view(), name='home'),

    # Rotas das apps com seus prefixos
    path('contas/', include('usuario.urls', namespace='usuario')),
    path('tarefas/', include('tarefas.urls', namespace='tarefas')),
    path('seguranca/', include('seguranca_trabalho.urls', namespace='seguranca_trabalho')),
    path('departamento_pessoal/', include('departamento_pessoal.urls', namespace='departamento_pessoal')),
    path('gestao_riscos/', include('gestao_riscos.urls', namespace='gestao_riscos')),
    path('cliente/', include('cliente.urls')),
    path('logradouro/', include('logradouro.urls')), # <-- Esta linha está correta
    path('treinamentos/', include('treinamentos.urls')),
    path('automovel/', include('automovel.urls')),
    path('atas/', include('ata_reuniao.urls')),
]

# Configuração para servir arquivos de mídia e estáticos
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
