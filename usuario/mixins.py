
# usuario/mixins.py
"""
Mixins específicos do app Usuário.

Contém regras de negócio e proteções que dependem diretamente do model
`Usuario` e do domínio de gestão de contas/privilégios.

⚠️ Mixins GENÉRICOS (Staff, Superuser, AppPermission, etc.) estão em
   `core/mixins.py`. Aqui ficam apenas as regras específicas de usuário.
"""

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.db.models import Q, QuerySet

from usuario.models import Usuario


# =============================================================================
# == MIXINS DE ESCOPO DE QUERYSET (Nível de Listagem/Edição)
# =============================================================================

class FilialScopedUserMixin:
    """
    Filtra queryset de `Usuario` pela filial do solicitante.

    Regras:
      - Superusuário: vê todos os usuários.
      - Demais: vê apenas usuários que compartilham AO MENOS UMA
        filial permitida com o solicitante.

    IMPORTANTE:
      - Deve ser herdado APÓS o mixin de permissão (ex: AppPermissionMixin)
        e ANTES da View base (ListView, UpdateView, etc.).

    Ex:
        class UserListView(AppPermissionMixin, FilialScopedUserMixin, ListView):
            app_label_required = 'usuario'
            model = Usuario
    """

    def get_queryset(self) -> QuerySet:
        qs = super().get_queryset()
        user = self.request.user

        if user.is_superuser:
            return qs

        filiais_ids = user.filiais_permitidas.values_list('pk', flat=True)
        return qs.filter(filiais_permitidas__in=filiais_ids).distinct()


class HideSuperusersMixin:
    """
    Oculta superusuários da listagem para quem NÃO é superuser.

    Deve ser combinado com `FilialScopedUserMixin` em telas de gestão
    de usuários, para evitar que gerentes/administradores enxerguem
    (e tentem editar) superusuários.

    Ex:
        class UserListView(AppPermissionMixin,
                           FilialScopedUserMixin,
                           HideSuperusersMixin,
                           ListView):
            ...
    """

    def get_queryset(self) -> QuerySet:
        qs = super().get_queryset()
        if not self.request.user.is_superuser:
            qs = qs.exclude(is_superuser=True)
        return qs


# =============================================================================
# == MIXINS DE PROTEÇÃO HIERÁRQUICA (Nível de Objeto)
# =============================================================================

class HierarchyProtectionMixin:
    """
    Impede que usuários NÃO superusuários editem/desativem/excluam
    um superusuário.

    Deve ser usado em DetailView, UpdateView, DeleteView ou qualquer
    view que implemente `get_object()`.

    Ex:
        class UserUpdateView(AppPermissionMixin,
                             FilialScopedUserMixin,
                             HierarchyProtectionMixin,
                             UpdateView):
            ...
    """
    hierarchy_redirect_url = 'usuario:lista_usuarios'
    hierarchy_error_message = "Você não tem privilégios para alterar este usuário."

    def dispatch(self, request, *args, **kwargs):
        target = self._get_target_user()

        if target and target.is_superuser and not request.user.is_superuser:
            messages.error(request, self.hierarchy_error_message)
            return redirect(self.hierarchy_redirect_url)

        return super().dispatch(request, *args, **kwargs)

    def _get_target_user(self):
        """Obtém o usuário-alvo sem quebrar se get_object() falhar."""
        if not hasattr(self, 'get_object'):
            return None
        try:
            return self.get_object()
        except Exception:
            return None


class PreventSelfActionMixin:
    """
    Impede que o usuário logado execute ação destrutiva em si mesmo
    (desativar, excluir, redefinir senha, remover grupos, etc.).

    Ex:
        class UserToggleActiveView(AppPermissionMixin,
                                   PreventSelfActionMixin,
                                   View):
            self_action_message = "Você não pode desativar a si mesmo."
    """
    self_action_redirect_url = 'usuario:lista_usuarios'
    self_action_message = "Você não pode executar esta ação em si mesmo."

    def dispatch(self, request, *args, **kwargs):
        target = self._get_target_user()

        if target and target.pk == request.user.pk:
            messages.error(request, self.self_action_message)
            return redirect(self.self_action_redirect_url)

        return super().dispatch(request, *args, **kwargs)

    def _get_target_user(self):
        """Tenta obter o alvo via get_object() ou via kwargs['pk']."""
        if hasattr(self, 'get_object'):
            try:
                return self.get_object()
            except Exception:
                pass

        pk = self.kwargs.get('pk')
        if pk:
            try:
                return Usuario.objects.only('pk').get(pk=pk)
            except Usuario.DoesNotExist:
                return None
        return None


class LastSuperuserProtectionMixin:
    """
    Impede desativação ou exclusão do ÚLTIMO superusuário ativo do sistema.

    Proteção crítica contra lockout total (cenário em que ninguém
    mais consegue administrar a aplicação).

    Aplica-se apenas quando o alvo É superuser E está ativo.

    Ex:
        class UserToggleActiveView(AppPermissionMixin,
                                   LastSuperuserProtectionMixin,
                                   View):
            ...
    """
    last_superuser_redirect_url = 'usuario:lista_usuarios'
    last_superuser_message = (
        "Operação bloqueada: este é o último superusuário ativo do sistema. "
        "Promova outro usuário a superusuário antes de executar esta ação."
    )

    def dispatch(self, request, *args, **kwargs):
        target = self._get_target_user()

        if target and target.is_superuser and target.is_active:
            ativos = Usuario.objects.filter(
                is_superuser=True, is_active=True
            ).count()
            if ativos <= 1:
                messages.error(request, self.last_superuser_message)
                return redirect(self.last_superuser_redirect_url)

        return super().dispatch(request, *args, **kwargs)

    def _get_target_user(self):
        if hasattr(self, 'get_object'):
            try:
                return self.get_object()
            except Exception:
                pass

        pk = self.kwargs.get('pk')
        if pk:
            try:
                return Usuario.objects.only(
                    'pk', 'is_superuser', 'is_active'
                ).get(pk=pk)
            except Usuario.DoesNotExist:
                return None
        return None


# =============================================================================
# == MIXINS DE SEGURANÇA DE FORMULÁRIOS (Anti-escalação de privilégios)
# =============================================================================

class PreventPrivilegeEscalationMixin:
    """
    Impede que usuários NÃO superusuários concedam (a si ou a terceiros)
    as flags `is_superuser` e `is_staff` através do formulário.

    Mesmo que o atacante manipule o HTML ou envie POST direto, esta trava
    força os valores originais do objeto antes de salvar.

    Deve ser usado em UpdateView/CreateView do model `Usuario`.

    Ex:
        class UserUpdateView(AppPermissionMixin,
                             PreventPrivilegeEscalationMixin,
                             UpdateView):
            ...
    """
    protected_flags = ('is_superuser', 'is_staff')

    def form_valid(self, form):
        if not self.request.user.is_superuser:
            # BUSCA DO BANCO (não usa self.object, pois pode já estar adulterado
            # pelo form.full_clean() que atribui cleaned_data em form.instance)
            pk = form.instance.pk
            if pk:
                # UpdateView: recarrega valores originais direto do DB
                original = type(form.instance)._default_manager.get(pk=pk)
                for flag in self.protected_flags:
                    setattr(form.instance, flag, getattr(original, flag))
            else:
                # CreateView: força False (usuário não-super não cria privilegiado)
                for flag in self.protected_flags:
                    setattr(form.instance, flag, False)

        return super().form_valid(form)


# =============================================================================
# == MIXINS DE SESSÃO / FILIAL ATIVA
# =============================================================================

class RequireActiveFilialMixin:
    """
    Garante que há uma filial ativa na sessão antes de executar a view.

    Se não houver, redireciona o usuário para o perfil com mensagem
    solicitando a seleção de filial.

    Útil em views de criação de objetos que DEPENDEM da filial ativa
    para determinar escopo (ex: criação de tarefa, cliente, etc.).

    Ex:
        class CriarTarefaView(AppPermissionMixin,
                              RequireActiveFilialMixin,
                              CreateView):
            ...
    """
    active_filial_redirect_url = 'usuario:profile'
    active_filial_message = (
        "Selecione uma filial ativa no menu superior antes de continuar."
    )

    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('active_filial_id'):
            # Superusers podem operar em "Todas as Filiais"
            if not request.user.is_superuser:
                messages.warning(request, self.active_filial_message)
                return redirect(self.active_filial_redirect_url)

        return super().dispatch(request, *args, **kwargs)

