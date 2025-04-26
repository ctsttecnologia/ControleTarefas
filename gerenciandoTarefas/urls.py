
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

from tarefas import views
 

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('home.urls')),
    path('accounts/', include('usuario.urls')),
    path('usuario/', include(('usuario.urls', 'usuario'), namespace='usuario')),  
    path('login/', LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', LogoutView.as_view(template_name='logout.html'), name='logout'),
    path('profile/', views.profile_view, name='profile'),  # URL para a página de perfil
   
    path('epi/', include('epi.urls')),
    path('cliente/', include('cliente.urls')),
    path('seguranca/', include('seguranca_trabalho.urls')),
    path('departamento_pessoal', include('departamento_pessoal.urls')),
    path('tarefas/', include('tarefas.urls')),
    path('logradouro/', include('logradouro.urls')),
    path('treinamentos/', include('treinamentos.urls')),
    path('automovel/', include('automovel.urls')),
  

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)