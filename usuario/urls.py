
# usuario/urls.py

from django.urls import path
from .views import (
    # ... todos os seus imports ...
    CustomLoginView, CustomLogoutView, ProfileView, CustomPasswordChangeView, SelecionarFilialView,
    UserListView, UserCreateView, UserUpdateView, UserSetPasswordView, UserToggleActiveView,
    GerenciarGruposUsuarioView, GroupListView, GroupCreateView, GroupUpdateView, GroupDeleteView,
    CustomPasswordResetView, CustomPasswordResetDoneView, CustomPasswordResetConfirmView, 
    CustomPasswordResetCompleteView,
    FilialListView, FilialCreateView, FilialUpdateView, FilialDeleteView, ManageCardPermissionsView
)

app_name = 'usuario'

urlpatterns = [
    # --- Autenticação ---
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),

    # --- Perfil do Usuário Logado ---
    path('perfil/', ProfileView.as_view(), name='profile'),
    path('perfil/alterar-senha/', CustomPasswordChangeView.as_view(), name='alterar_senha_propria'),

    # --- Gerenciamento de Usuários (CRUD) ---
    path('usuarios/', UserListView.as_view(), name='lista_usuarios'),
    # --- O nome correto para a criação é 'cadastrar_usuario'
    path('usuarios/novo/', UserCreateView.as_view(), name='usuario_criar'),
    # ---- O nome correto para a edição é 'usuario_editar'
    path('usuarios/editar/<int:pk>/', UserUpdateView.as_view(), name='usuario_editar'),
    path('usuarios/toggle-active/<int:pk>/', UserToggleActiveView.as_view(), name='toggle_active_usuario'),
    path('usuarios/definir-senha/<int:pk>/', UserSetPasswordView.as_view(), name='alterar_senha'),
    path('usuarios/gerenciar-grupos/<int:pk>/', GerenciarGruposUsuarioView.as_view(), name='gerenciar_grupos_usuario'),

    # --- Gerenciamento de Grupos (CRUD) ---
    path('grupos/', GroupListView.as_view(), name='grupo_lista'),
    path('grupos/novo/', GroupCreateView.as_view(), name='grupo_criar'),
    path('grupos/editar/<int:pk>/', GroupUpdateView.as_view(), name='grupo_form'),
    path('grupos/excluir/<int:pk>/', GroupDeleteView.as_view(), name='grupo_excluir'),
    path('gerenciar-cards/', ManageCardPermissionsView.as_view(), name='gerenciar_cards'),
    
    # --- Redefinição de Senha (Esqueci a Senha) ---
    path('password_reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # --- URLs para Gestão de Filiais ---
    path('filiais/', FilialListView.as_view(), name='filial_list'),
    path('selecionar-filial/', SelecionarFilialView.as_view(), name='selecionar_filial'),
    path('filiais/adicionar/', FilialCreateView.as_view(), name='filial_create'),
    path('filiais/<int:pk>/editar/', FilialUpdateView.as_view(), name='filial_update'),
    path('filiais/<int:pk>/excluir/', FilialDeleteView.as_view(), name='filial_delete'),
    
]