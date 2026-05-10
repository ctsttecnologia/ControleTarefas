
# usuario/urls.py

from django.urls import path
from usuario.views import (
    # Autenticação e Perfil
    CustomLoginView, CustomLogoutView, ProfileView,
    CustomPasswordChangeView, SelecionarFilialView,

    # Usuários
    UserListView, UserCreateView, UserUpdateView,
    UserSetPasswordView, UserToggleActiveView,
    GerenciarGruposUsuarioView, ExportarUsuariosExcelView,

    # Grupos e Permissões
    GroupListView, GroupCreateView, GroupUpdateView, GroupDeleteView,
    ManageCardPermissionsView,

    # Redefinição de Senha
    CustomPasswordResetView, CustomPasswordResetDoneView,
    CustomPasswordResetConfirmView, CustomPasswordResetCompleteView,

    # Filiais
    FilialListView, FilialCreateView, FilialUpdateView, FilialDeleteView,
)

app_name = 'usuario'

urlpatterns = [
    # ===========================================================
    # 🔐 AUTENTICAÇÃO
    # ===========================================================
    path('login/',  CustomLoginView.as_view(),  name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),

    # ===========================================================
    # 👤 PERFIL DO USUÁRIO LOGADO
    # ===========================================================
    path('perfil/',                ProfileView.as_view(),                name='profile'),
    path('perfil/alterar-senha/',  CustomPasswordChangeView.as_view(),   name='alterar_senha_propria'),

    # ===========================================================
    # 🔑 REDEFINIÇÃO DE SENHA (Esqueci minha senha)
    # ===========================================================
    path('senha/reset/',
         CustomPasswordResetView.as_view(),
         name='password_reset'),

    path('senha/reset/enviado/',
         CustomPasswordResetDoneView.as_view(),
         name='password_reset_done'),

    path('senha/reset/<uidb64>/<token>/',
         CustomPasswordResetConfirmView.as_view(),
         name='password_reset_confirm'),

    path('senha/reset/concluido/',
         CustomPasswordResetCompleteView.as_view(),
         name='password_reset_complete'),

    # ===========================================================
    # 👥 GERENCIAMENTO DE USUÁRIOS (CRUD)
    # ===========================================================
    path('usuarios/', UserListView.as_view(), name='usuario_lista'),
    path('usuarios/novo/', UserCreateView.as_view(), name='usuario_criar'),
    path('usuarios/<int:pk>/editar/', UserUpdateView.as_view(), name='usuario_editar'),
    path('usuarios/<int:pk>/toggle-active/', UserToggleActiveView.as_view(), name='usuario_toggle_active'),
    path('usuarios/<int:pk>/definir-senha/', UserSetPasswordView.as_view(), name='usuario_definir_senha'),
    path('usuarios/<int:pk>/gerenciar-grupos/', GerenciarGruposUsuarioView.as_view(), name='usuario_gerenciar_grupos'),
    path('usuarios/exportar-excel/', ExportarUsuariosExcelView.as_view(), name='usuario_exportar_excel'),

    # ===========================================================
    # 🛡️ GERENCIAMENTO DE GRUPOS (CRUD)
    # ===========================================================
    path('grupos/', GroupListView.as_view(), name='grupo_lista'),
    path('grupos/novo/', GroupCreateView.as_view(), name='grupo_criar'),
    path('grupos/<int:pk>/editar/', GroupUpdateView.as_view(), name='grupo_editar'),
    path('grupos/<int:pk>/excluir/', GroupDeleteView.as_view(), name='grupo_excluir'),
    path('gerenciar-cards/', ManageCardPermissionsView.as_view(), name='gerenciar_cards'),

    # ===========================================================
    # 🏢 GESTÃO DE FILIAIS
    # ===========================================================
    path('filiais/', FilialListView.as_view(), name='filial_lista'),
    path('filiais/nova/', FilialCreateView.as_view(), name='filial_criar'),
    path('filiais/<int:pk>/editar/', FilialUpdateView.as_view(), name='filial_editar'),
    path('filiais/<int:pk>/excluir/', FilialDeleteView.as_view(), name='filial_excluir'),
    path('selecionar-filial/', SelecionarFilialView.as_view(), name='selecionar_filial'),
]
