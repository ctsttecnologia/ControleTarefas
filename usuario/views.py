# usuario/views.py
"""
Views do app Usuário.
Arquitetura:
  - Mixins genéricos em core/mixins.py (AppPermissionMixin, etc.)
  - Mixins específicos em usuario/mixins.py
  - Lógica pesada em services (excel_export, cards)
"""
import logging

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    LoginView, LogoutView, PasswordChangeView,
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView,
)
from django.db.models import ProtectedError, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic import (
    CreateView, DeleteView, DetailView, FormView, ListView, UpdateView,
)
from django.views.generic.detail import SingleObjectMixin

from core.mixins import AppPermissionMixin
from usuario.cards import ALL_CARDS, CARD_SUMMARY, get_card_ids
from usuario.forms import (
    CustomPasswordChangeForm, CustomUserChangeForm,
    CustomUserCreationForm, FilialForm, GrupoForm,
)
from usuario.mixins import (
    FilialScopedUserMixin, HideSuperusersMixin,
    HierarchyProtectionMixin, LastSuperuserProtectionMixin,
    PreventPrivilegeEscalationMixin, PreventSelfActionMixin,
)
from usuario.models import Filial, Group, GroupCardPermissions, Usuario
from usuario.services.excel_export import gerar_excel_usuarios


# Logger de auditoria
audit_logger = logging.getLogger('usuario.audit')

# Duração da sessão (em segundos) — 8 horas
SESSION_EXPIRY_SECONDS = 60 * 60 * 8


# =============================================================================
# AUTENTICAÇÃO (Login / Logout / Seleção de Filial)
# =============================================================================

@method_decorator(sensitive_post_parameters('password'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class CustomLoginView(LoginView):
    """Login com gerenciamento automático de filial ativa na sessão."""
    template_name = 'usuario/login.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.get_user()
        filial_ativa = self._determinar_filial_ativa(user)

        # 🔒 Valida ANTES de autenticar efetivamente
        if not filial_ativa:
            messages.error(
                self.request,
                "Você não está associado a nenhuma filial ativa. "
                "Contate o administrador."
            )
            audit_logger.warning(
                f"Login bloqueado — sem filial: user={user.username}"
            )
            return redirect('usuario:login')

        response = super().form_valid(form)
        self._registrar_filial_na_sessao(filial_ativa)

        audit_logger.info(
            f"Login OK: user={user.username} filial={filial_ativa.nome} "
            f"ip={self.request.META.get('REMOTE_ADDR', '-')}"
        )
        return response

    def _determinar_filial_ativa(self, user):
        if user.filial_ativa_id:
            return user.filial_ativa
        return user.filiais_permitidas.only('id', 'nome').first()

    def _registrar_filial_na_sessao(self, filial):
        self.request.session['active_filial_id'] = filial.id
        self.request.session.set_expiry(SESSION_EXPIRY_SECONDS)
        messages.info(self.request, f"Conectado na filial: {filial.nome}")


class CustomLogoutView(LogoutView):
    """Logout com limpeza da sessão."""
    next_page = reverse_lazy('usuario:login')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            audit_logger.info(f"Logout: user={request.user.username}")
        request.session.pop('active_filial_id', None)
        return super().dispatch(request, *args, **kwargs)


@method_decorator(never_cache, name='dispatch')
class SelecionarFilialView(LoginRequiredMixin, View):
    """Permite ao usuário trocar a filial ativa."""
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        filial_id_str = request.POST.get('filial_id', '').strip()

        # Superusuário limpando filtro ("Todas as Filiais")
        if filial_id_str == '0' and request.user.is_superuser:
            request.session.pop('active_filial_id', None)
            request.user.filial_ativa = None
            request.user.save(update_fields=['filial_ativa'])
            audit_logger.info(
                f"{request.user.username} alternou para 'todas as filiais'"
            )
            messages.success(request, "Exibindo dados de todas as filiais.")
            return redirect(self._safe_next())

        try:
            filial_id = int(filial_id_str)
        except (TypeError, ValueError):
            messages.error(request, "Identificador de filial inválido.")
            return redirect(self._safe_next())

        try:
            # 🔒 SEMPRE via filiais_permitidas (impede forjar filial alheia)
            filial = request.user.filiais_permitidas.get(pk=filial_id)
        except Filial.DoesNotExist:
            audit_logger.warning(
                f"Tentativa de filial não permitida: "
                f"user={request.user.username} filial_id={filial_id}"
            )
            messages.error(request, "Sem permissão para esta filial.")
            return redirect(self._safe_next())

        request.session['active_filial_id'] = filial.id
        request.user.filial_ativa = filial
        request.user.save(update_fields=['filial_ativa'])
        messages.success(request, f"Filial alterada para: {filial.nome}")
        return redirect(self._safe_next())

    def _safe_next(self):
        """🔒 Evita open redirect."""
        next_url = self.request.POST.get('next', '')
        if next_url and url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={self.request.get_host()}
        ):
            return next_url
        return reverse('usuario:profile')


# =============================================================================
# PERFIL E SENHA DO USUÁRIO LOGADO
# =============================================================================

class ProfileView(LoginRequiredMixin, DetailView):
    """Página inicial do usuário com cards de acesso rápido."""
    model = Usuario
    template_name = 'usuario/profile.html'

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['allowed_cards'] = self._build_visible_cards(self.request.user)
        return context

    def _build_visible_cards(self, user):
        """Monta a lista de cards visíveis para o usuário."""
        allowed_ids = self._get_allowed_card_ids(user)
        visible = []

        for card in ALL_CARDS:
            if not self._user_can_see_card(user, card, allowed_ids):
                continue

            filtered_links = [
                link for link in card['links']
                if user.is_superuser
                or user.has_perm(link.get('permission', ''))
                or card['id'] in allowed_ids
            ]

            if filtered_links:
                visible.append({**card, 'links': filtered_links})

        return visible

    def _user_can_see_card(self, user, card, allowed_ids):
        return (
            user.is_superuser
            or user.has_perm(card['permission'])
            or card['id'] in allowed_ids
        )

    def _get_allowed_card_ids(self, user):
        """Retorna IDs de cards permitidos pelos grupos do usuário."""
        if user.is_superuser:
            return get_card_ids()

        ids = set()
        perms = GroupCardPermissions.objects.filter(
            group__in=user.groups.all()
        ).values_list('cards_visiveis', flat=True)

        for cards_list in perms:
            if cards_list:
                ids.update(cards_list)
        return ids


@method_decorator(sensitive_post_parameters(
    'old_password', 'new_password1', 'new_password2'
), name='dispatch')
class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    """Alteração de senha do próprio usuário."""
    form_class = CustomPasswordChangeForm
    template_name = 'usuario/alterar_senha.html'
    success_url = reverse_lazy('usuario:profile')

    def form_valid(self, form):
        audit_logger.info(
            f"Senha alterada (self): user={self.request.user.username}"
        )
        messages.success(self.request, 'Sua senha foi alterada com sucesso!')
        return super().form_valid(form)


# =============================================================================
# CRUD DE USUÁRIOS
# =============================================================================

@method_decorator(never_cache, name='dispatch')
class UserListView(AppPermissionMixin,
                   FilialScopedUserMixin,
                   HideSuperusersMixin,
                   ListView):
    """Lista de usuários com busca e escopo por filial."""
    app_label_required = 'usuario'
    model = Usuario
    template_name = 'usuario/lista_usuarios.html'
    context_object_name = 'usuarios'
    paginate_by = 20

    def get_queryset(self):
        qs = (super().get_queryset()
              .select_related('filial_ativa')
              .order_by('first_name'))

        search = self.request.GET.get('q', '').strip()
        if search:
            qs = qs.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )
        return qs


@method_decorator(never_cache, name='dispatch')
class UserCreateView(AppPermissionMixin,
                     PreventPrivilegeEscalationMixin,
                     CreateView):
    """Criação de novo usuário."""
    permission_required = 'usuario.add_usuario'
    model = Usuario
    form_class = CustomUserCreationForm
    template_name = 'usuario/form_usuario.html'
    success_url = reverse_lazy('usuario:lista_usuarios')

    def dispatch(self, request, *args, **kwargs):
        if not Filial.objects.exists():
            messages.warning(
                request,
                "Cadastre ao menos uma filial antes de criar usuários."
            )
            return redirect('usuario:filial_list')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request_user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.object

        # Define primeira filial permitida como ativa
        primeira = user.filiais_permitidas.first()
        if primeira:
            user.filial_ativa = primeira
            user.save(update_fields=['filial_ativa'])

        audit_logger.info(
            f"Usuário criado: alvo={user.username} "
            f"por={self.request.user.username}"
        )
        messages.success(
            self.request,
            f"Usuário '{user.username}' criado com sucesso."
        )
        return response

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request_user'] = self.request.user
        return kwargs

    def form_invalid(self, form):
        audit_logger.warning(
            f"Falha ao criar usuário por={self.request.user.username} "
            f"erros={dict(form.errors)}"
        )
        return super().form_invalid(form)

@method_decorator(never_cache, name='dispatch')
class UserUpdateView(AppPermissionMixin,
                     FilialScopedUserMixin,
                     HideSuperusersMixin,
                     HierarchyProtectionMixin,
                     PreventPrivilegeEscalationMixin,
                     UpdateView):
    """Edição de usuário existente."""
    permission_required = 'usuario.change_usuario'
    model = Usuario
    form_class = CustomUserChangeForm
    template_name = 'usuario/form_usuario.html'
    success_url = reverse_lazy('usuario:lista_usuarios')

    def get_queryset(self):
        return super().get_queryset().select_related('filial_ativa')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request_user'] = self.request.user
        if self.object:
            kwargs['filiais_permitidas_qs'] = self.object.filiais_permitidas.all()
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)

        # Garante que filial_ativa esteja entre as permitidas
        user = self.object
        if user.filial_ativa and user.filial_ativa not in user.filiais_permitidas.all():
            user.filial_ativa = user.filiais_permitidas.first()
            user.save(update_fields=['filial_ativa'])

        audit_logger.info(
            f"Usuário atualizado: alvo={user.username} "
            f"por={self.request.user.username}"
        )
        messages.success(
            self.request,
            f"Usuário '{user.username}' atualizado com sucesso."
        )
        return response


@method_decorator(never_cache, name='dispatch')
class UserToggleActiveView(AppPermissionMixin,
                           FilialScopedUserMixin,
                           HideSuperusersMixin,
                           PreventSelfActionMixin,
                           HierarchyProtectionMixin,
                           LastSuperuserProtectionMixin,
                           SingleObjectMixin,
                           View):
    """Ativar/desativar um usuário."""
    permission_required = 'usuario.change_usuario'
    model = Usuario
    http_method_names = ['post']
    self_action_message = "Você não pode desativar a si mesmo."

    def post(self, request, *args, **kwargs):
        user_to_toggle = self.get_object()
        user_to_toggle.is_active = not user_to_toggle.is_active
        user_to_toggle.save(update_fields=['is_active'])

        status = "ativado" if user_to_toggle.is_active else "desativado"
        audit_logger.info(
            f"Toggle status: alvo={user_to_toggle.username} "
            f"status={status} por={request.user.username}"
        )
        messages.success(
            request,
            f"Usuário '{user_to_toggle.username}' {status} com sucesso."
        )
        return redirect('usuario:lista_usuarios')


@method_decorator(sensitive_post_parameters(
    'new_password1', 'new_password2'
), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class UserSetPasswordView(AppPermissionMixin,
                          PreventSelfActionMixin,
                          FormView):
    """Permite superusuário definir nova senha para outro usuário."""
    permission_required = 'usuario.change_usuario'
    form_class = SetPasswordForm
    template_name = 'usuario/definir_senha_form.html'
    success_url = reverse_lazy('usuario:lista_usuarios')
    self_action_message = (
        "Use 'Alterar Minha Senha' para redefinir sua própria senha."
    )
    self_action_redirect_url = 'usuario:alterar_senha'

    def has_permission(self):
        # 🔒 Apenas superuser pode redefinir senha de outros
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def get_target_user(self):
        return get_object_or_404(Usuario, pk=self.kwargs['pk'])

    # Para os mixins PreventSelfActionMixin funcionarem
    def get_object(self):
        return self.get_target_user()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.get_target_user()
        return kwargs

    def form_valid(self, form):
        target = form.user
        form.save()
        audit_logger.warning(
            f"SENHA REDEFINIDA: alvo={target.username} "
            f"por={self.request.user.username} "
            f"ip={self.request.META.get('REMOTE_ADDR', '-')}"
        )
        messages.success(
            self.request,
            f"Senha de '{target.username}' redefinida com sucesso."
        )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['usuario_alvo'] = self.get_target_user()
        return context


# =============================================================================
# CRUD DE GRUPOS (Superusuário)
# =============================================================================

class GroupListView(AppPermissionMixin, ListView):
    model = Group
    template_name = 'usuario/grupo_lista.html'
    context_object_name = 'grupos'

    def has_permission(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser


class GroupCreateView(AppPermissionMixin, CreateView):
    model = Group
    form_class = GrupoForm
    template_name = 'usuario/grupo_form.html'
    success_url = reverse_lazy('usuario:grupo_lista')

    def has_permission(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def form_valid(self, form):
        audit_logger.info(
            f"Grupo criado: nome={form.instance.name} "
            f"por={self.request.user.username}"
        )
        messages.success(
            self.request,
            f"Grupo '{form.instance.name}' criado com sucesso."
        )
        return super().form_valid(form)


class GroupUpdateView(AppPermissionMixin, UpdateView):
    model = Group
    form_class = GrupoForm
    template_name = 'usuario/grupo_form.html'
    success_url = reverse_lazy('usuario:grupo_lista')

    def has_permission(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def form_valid(self, form):
        audit_logger.info(
            f"Grupo atualizado: nome={form.instance.name} "
            f"por={self.request.user.username}"
        )
        messages.success(
            self.request,
            f"Grupo '{form.instance.name}' atualizado com sucesso."
        )
        return super().form_valid(form)


class GroupDeleteView(AppPermissionMixin, DeleteView):
    model = Group
    template_name = 'usuario/grupo_confirmar_exclusao.html'
    success_url = reverse_lazy('usuario:grupo_lista')

    def has_permission(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def form_valid(self, form):
        nome = self.object.name
        audit_logger.warning(
            f"Grupo excluído: nome={nome} por={self.request.user.username}"
        )
        messages.success(self.request, f"Grupo '{nome}' excluído com sucesso.")
        return super().form_valid(form)


class GerenciarGruposUsuarioView(AppPermissionMixin, View):
    """Adicionar/remover grupos de um usuário específico."""
    template_name = 'usuario/gerenciar_grupos_usuario.html'
    http_method_names = ['get', 'post']

    def has_permission(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def get(self, request, *args, **kwargs):
        usuario = get_object_or_404(Usuario, pk=self.kwargs.get('pk'))
        grupos_usuario = usuario.groups.all()
        context = {
            'usuario_alvo': usuario,
            'grupos_usuario': grupos_usuario,
            'grupos_disponiveis': Group.objects.exclude(pk__in=grupos_usuario),
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        usuario = get_object_or_404(Usuario, pk=self.kwargs.get('pk'))
        grupo_id = request.POST.get('grupo')
        acao = request.POST.get('acao')

        # 🔒 Whitelist de ações
        if acao not in ('adicionar', 'remover'):
            messages.error(request, "Ação inválida.")
            return redirect('usuario:gerenciar_grupos_usuario', pk=usuario.pk)

        if not grupo_id:
            messages.error(request, "Selecione um grupo.")
            return redirect('usuario:gerenciar_grupos_usuario', pk=usuario.pk)

        grupo = get_object_or_404(Group, pk=grupo_id)

        if acao == 'adicionar':
            usuario.groups.add(grupo)
            audit_logger.info(
                f"Grupo adicionado: grupo={grupo.name} alvo={usuario.username} "
                f"por={request.user.username}"
            )
            messages.success(
                request,
                f"Grupo '{grupo.name}' adicionado a '{usuario.username}'."
            )
        else:
            usuario.groups.remove(grupo)
            audit_logger.info(
                f"Grupo removido: grupo={grupo.name} alvo={usuario.username} "
                f"por={request.user.username}"
            )
            messages.success(
                request,
                f"Grupo '{grupo.name}' removido de '{usuario.username}'."
            )

        return redirect('usuario:gerenciar_grupos_usuario', pk=usuario.pk)


# =============================================================================
# CRUD DE FILIAIS (Superusuário)
# =============================================================================

class _SuperuserOnlyMixin:
    """Mixin interno para views de Filial — apenas superuser."""
    def has_permission(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser


class FilialListView(AppPermissionMixin, _SuperuserOnlyMixin, ListView):
    model = Filial
    template_name = 'usuario/filial_list.html'
    context_object_name = 'filiais'


class FilialCreateView(AppPermissionMixin, _SuperuserOnlyMixin, CreateView):
    model = Filial
    form_class = FilialForm
    template_name = 'usuario/filial_form.html'
    success_url = reverse_lazy('usuario:filial_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Adicionar Nova Filial'
        return context

    def form_valid(self, form):
        audit_logger.info(
            f"Filial criada: nome={form.instance.nome} "
            f"por={self.request.user.username}"
        )
        messages.success(self.request, 'Filial cadastrada com sucesso!')
        return super().form_valid(form)


class FilialUpdateView(AppPermissionMixin, _SuperuserOnlyMixin, UpdateView):
    model = Filial
    form_class = FilialForm
    template_name = 'usuario/filial_form.html'
    success_url = reverse_lazy('usuario:filial_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f'Editar Filial: {self.object.nome}'
        return context

    def form_valid(self, form):
        audit_logger.info(
            f"Filial atualizada: nome={form.instance.nome} "
            f"por={self.request.user.username}"
        )
        messages.success(self.request, 'Filial atualizada com sucesso!')
        return super().form_valid(form)


class FilialDeleteView(AppPermissionMixin, _SuperuserOnlyMixin, DeleteView):
    model = Filial
    template_name = 'usuario/filial_confirm_delete.html'
    success_url = reverse_lazy('usuario:filial_list')

    def post(self, request, *args, **kwargs):
        try:
            nome = self.get_object().nome
            response = super().post(request, *args, **kwargs)
            audit_logger.warning(
                f"Filial excluída: nome={nome} por={request.user.username}"
            )
            messages.success(request, 'Filial excluída com sucesso!')
            return response
        except ProtectedError:
            messages.error(
                request,
                'Esta filial não pode ser excluída pois existem '
                'registros associados a ela.'
            )
            return redirect('usuario:filial_list')


# =============================================================================
# GERENCIAMENTO DE CARDS POR GRUPO
# =============================================================================

class ManageCardPermissionsView(AppPermissionMixin, _SuperuserOnlyMixin, View):
    """Configura quais cards cada grupo pode ver."""
    template_name = 'usuario/gerenciar_cards.html'
    http_method_names = ['get', 'post']

    def get(self, request, *args, **kwargs):
        context = {
            'grupos': Group.objects.all().order_by('name'),
            'todos_os_cards': CARD_SUMMARY,
            'permissoes_por_grupo': {
                p.group_id: p.cards_visiveis
                for p in GroupCardPermissions.objects.all()
            },
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        valid_card_ids = get_card_ids()  # 🔒 whitelist

        for group in Group.objects.all():
            cards_selecionados = [
                cid for cid in valid_card_ids
                if f'group_{group.id}_{cid}' in request.POST
            ]
            GroupCardPermissions.objects.update_or_create(
                group=group,
                defaults={'cards_visiveis': cards_selecionados}
            )

        audit_logger.info(
            f"Permissões de cards atualizadas por={request.user.username}"
        )
        messages.success(request, "Permissões de cards atualizadas com sucesso!")
        return redirect('usuario:gerenciar_cards')


# =============================================================================
# RECUPERAÇÃO DE SENHA
# =============================================================================

@method_decorator(sensitive_post_parameters('email'), name='dispatch')
class CustomPasswordResetView(PasswordResetView):
    template_name = 'usuario/password_reset/form.html'
    email_template_name = 'usuario/password_reset/email.html'
    subject_template_name = 'usuario/password_reset/subject.txt'
    success_url = reverse_lazy('usuario:password_reset_done')


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'usuario/password_reset/done.html'


@method_decorator(sensitive_post_parameters(
    'new_password1', 'new_password2'
), name='dispatch')
class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'usuario/password_reset/confirm.html'
    success_url = reverse_lazy('usuario:password_reset_complete')


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'usuario/password_reset/complete.html'


# =============================================================================
# EXPORTAÇÃO EXCEL
# =============================================================================

@method_decorator(never_cache, name='dispatch')
class ExportarUsuariosExcelView(AppPermissionMixin,
                                FilialScopedUserMixin,
                                HideSuperusersMixin,
                                View):
    """
    Exporta lista de usuários em Excel (.xlsx).
    🔒 Requer permissão de gerenciamento (não apenas staff) por expor PII.
    """
    permission_required = 'usuario.view_usuario'
    model = Usuario

    def has_permission(self):
        # 🔒 Apenas superuser ou quem é gerente/administrador
        user = self.request.user
        if not user.is_authenticated:
            return False
        return (
            user.is_superuser
            or getattr(user, 'is_gerente', False)
            or getattr(user, 'is_administrador', False)
        )

    def get_queryset(self):
        # Base queryset — os mixins de escopo filtrarão
        return Usuario.objects.select_related('filial_ativa').prefetch_related(
            'filiais_permitidas', 'groups'
        ).order_by('first_name', 'last_name')

    def get(self, request, *args, **kwargs):
        qs = self.get_queryset()

        search = request.GET.get('q', '').strip()
        if search:
            qs = qs.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )

        active_filial_id = request.session.get('active_filial_id')

        buffer, filename = gerar_excel_usuarios(
            queryset=qs,
            request_user=request.user,
            active_filial_id=active_filial_id,
            search=search,
        )

        audit_logger.info(
            f"Export Excel usuários: por={request.user.username} "
            f"total={qs.count()} busca='{search}'"
        )

        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
