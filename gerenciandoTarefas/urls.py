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
    path('suprimentos/', include('suprimentos.urls', namespace='suprimentos')),
    path('departamento_pessoal/', include('departamento_pessoal.urls', namespace='departamento_pessoal')),
    path('gestao_riscos/', include('gestao_riscos.urls', namespace='gestao_riscos')),
    path('cliente/', include('cliente.urls')),
    path('logradouro/', include('logradouro.urls')), 
    path('treinamentos/', include('treinamentos.urls')),
    path('automovel/', include('automovel.urls')),
    path('atas/', include('ata_reuniao.urls')),
    path('ferramentas/', include('ferramentas.urls', namespace='ferramentas')),
    path('core/', include('core.urls')),
    path('controle_de_telefone/', include('controle_de_telefone.urls')), 
]

# Configuração para servir arquivos de mídia e estáticos
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Definição da variável que o Django usará para qualquer erro 404 na aplicação.
# Fica no mesmo nível do urlpatterns, não dentro dele.
handler404 = 'core.views.error_404_view'

# Da mesma forma, você pode definir para outros erros comuns:
# handler500 = 'core.views.error_500_view' # Para erros internos do servidor
# handler403 = 'core.views.error_403_view' # Para erros de permissão negada