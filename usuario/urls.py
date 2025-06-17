
# usuario/urls.py
from django.urls import path
from . import views
from .views import ( 
        UsuarioCreateView, 
        UsuarioUpdateView, 
        GrupoCreateView, 
        GrupoUpdateView,
        GrupoListView,
        GrupoDeleteView,
        gerenciar_grupos_usuario,
        alterar_senha,
        perfil_view,
        cadastrar_usuario, 
        lista_usuarios, 
        alterar_senha,
        CustomPasswordResetView,
        CustomPasswordResetDoneView,
        CustomPasswordResetConfirmView,
        CustomPasswordResetCompleteView
    )  # Garanta que todas as views de classe estão importadas

app_name = 'usuario' # Namespace do app

urlpatterns = [
    # Autenticação
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('profile/', views.perfil_view, name='profile'),
 
    # Usuários (Views específicas para o modelo Usuario)
    path('', views.lista_usuarios, name='lista_usuarios'), # Nome mais específico para a lista
    
    # URL para a view de cadastro de usuário (cadastrar_usuario função ou UsuarioCreateView)
    # Se você quiser usar a função cadastrar_usuario:
    path('cadastrar/', views.cadastrar_usuario, name='cadastrar_usuario'),     
    path('usuario_editar/<int:pk>/', UsuarioUpdateView.as_view(), name='usuario_editar'),
    path('gerenciar_grupos_usuario/<int:pk>/', views.gerenciar_grupos_usuario, name='gerenciar_grupos_usuario'),

    # Tratamento de senhas e acesso
    path('alterar-senha/<int:pk>/', views.alterar_senha, name='alterar_senha'),
    path('desativar-usuario/<int:pk>/', views.desativar_usuario, name='desativar_usuario'),
    path('ativar-usuario/<int:pk>/', views.ativar_usuario, name='ativar_usuario'),

    # Grupos (Views específicas para o modelo Group)
    path('grupos/', views.GrupoListView.as_view(), name='grupo_lista'),
    path('grupos/novo/', views.GrupoCreateView.as_view(), name='grupo_criar'),
    path('grupos/editar/<int:pk>/', GrupoUpdateView.as_view(), name='grupo_editar'),
    path('grupos/excluir/<int:pk>/', GrupoDeleteView.as_view(), name='grupo_excluir'),

    # Recuperação de senha
    #path('login/', auth_views.LoginView.as_view(template_name='usuario/login.html'), name='login'),
    #path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    #path('cadastrar/', cadastrar_usuario, name='cadastrar_usuario'),
    #path('lista/', lista_usuarios, name='lista_usuarios'),
    path('alterar-senha/<int:pk>/', alterar_senha, name='alterar_senha'),
    
    # URLs para redefinição de senha
    path('password-reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
]