# core/mixins.py
from django.db.models import Q, QuerySet
from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.core.exceptions import PermissionDenied
from .forms import ChangeFilialForm
from django.contrib.auth.mixins import AccessMixin, PermissionRequiredMixin
from ferramentas.models import Atividade
from django.http import HttpResponse


# AppPermissionMixin, # 1º — Verifica acesso ao módulo
# SSTPermissionMixin, # 2º — Verifica permissão específica
# ViewFilialScopedMixin, # 3º — Filtra queryset por filial
# AtividadeLogMixin, # 4º — Funcionalidade auxiliar
# ListView, # Último — View genérica do Django

# =============================================================================
# == MIXINS DE PERMISSÃO E ESCOPO (A SUA ARQUITETURA DE 3 NÍVEIS)
# =============================================================================

class SSTPermissionMixin(PermissionRequiredMixin):
    """
    NÍVEL 1 (Página):
    Mixin que herda do PermissionRequiredMixin do Django, mas customiza
    o comportamento em caso de falha de permissão (UX amigável).
    """

    def handle_no_permission(self):
        messages.error(self.request, "Você não tem permissão para acessar esta página.")
        return redirect('usuario:profile')


class AdminFilialScopedMixin:
    """
    NÍVEL 2 (Horizontal/Filial) - Para o Admin:
    Mixin para ser usado EXCLUSIVAMENTE no admin.py (ModelAdmin e Inlines).
    Filtra o queryset chamando o método 'for_request(request)' 
    do manager do modelo, SE disponível.

    Seguro para uso em inlines cujo modelo NÃO possui FilialManager.
    """

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        # ✅ Só chama for_request() se o queryset/manager suportar
        if hasattr(qs, 'for_request'):
            return qs.for_request(request)

        return qs


class ViewFilialScopedMixin:
    """
    NÍVEL 2 (Horizontal/Filial) - Para Views:
    Mixin para ser usado EXCLUSIVAMENTE em Class-Based Views (views.py).
    Filtra o queryset chamando o método 'for_request(request)' 
    do manager do modelo.

    IMPORTANTE: O modelo desta View DEVE usar o 'FilialManager'.
    """

    def get_queryset(self):
        qs = super().get_queryset()

        if hasattr(qs, 'for_request'):
            return qs.for_request(self.request)

        return qs


class TecnicoScopeMixin:
    """
    NÍVEL 3 (Vertical/Dados):
    Mixin global para filtrar querysets para usuários do grupo 'TÉCNICO'.
    Deve ser herdado ANTES do ViewFilialScopedMixin.

    Ex: class MinhaView(SSTPermissionMixin, TecnicoScopeMixin, ViewFilialScopedMixin, ListView):
    """

    tecnico_scope_lookup = None

    def _is_tecnico(self) -> bool:
        user = self.request.user
        if not hasattr(user, '_is_tecnico'):
            user._is_tecnico = user.groups.filter(name='TÉCNICO').exists()
        return user._is_tecnico

    def get_queryset(self) -> QuerySet:
        queryset = super().get_queryset()
        return self.scope_tecnico_queryset(queryset)

    def scope_tecnico_queryset(self, queryset: QuerySet) -> QuerySet:
        if not self._is_tecnico():
            return queryset

        if self.tecnico_scope_lookup:
            filter_kwargs = {self.tecnico_scope_lookup: self.request.user}
            return queryset.filter(**filter_kwargs).distinct()

        return queryset.none()


class TarefaPermissionMixin(AccessMixin):
    """
    Mixin de permissão a nível de objeto.
    Garante que o usuário logado seja o criador ou o responsável pela tarefa.
    """

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(
            Q(usuario=self.request.user) | Q(responsavel=self.request.user)
        ).distinct()


# =============================================================================
# == MIXINS UTILITÁRIOS
# =============================================================================

class FilialCreateMixin:
    """
    Mixin para views de criação. Atribui automaticamente a filial da sessão
    ao novo objeto antes de salvá-lo.
    """

    def form_valid(self, form):
        filial_id = self.request.session.get('active_filial_id')
        if not filial_id:
            messages.error(
                self.request,
                "Nenhuma filial selecionada. Por favor, escolha uma filial no menu superior."
            )
            raise PermissionDenied("Nenhuma filial selecionada para criação de objeto.")

        form.instance.filial_id = filial_id
        messages.success(
            self.request,
            f"{self.model._meta.verbose_name.capitalize()} criado(a) com sucesso."
        )
        return super().form_valid(form)


class ChangeFilialAdminMixin:
    """
    Ação de Admin para trocar a filial de objetos em lote.
    """
    actions = ['change_filial_action']

    def change_filial_action(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(
                request,
                "Apenas superusuários podem mover itens entre filiais.",
                level=messages.ERROR
            )
            return None

        form = None
        if 'post' in request.POST:
            form = ChangeFilialForm(request.POST)

            if form.is_valid():
                nova_filial = form.cleaned_data['filial']
                ids_selecionados_str = form.cleaned_data['selected_ids']

                try:
                    ids_selecionados = [int(pk) for pk in ids_selecionados_str.split(',')]
                except (ValueError, TypeError):
                    self.message_user(request, "Erro: IDs de seleção inválidos.", messages.ERROR)
                    return None

                queryset_para_atualizar = self.model.objects.filter(pk__in=ids_selecionados)
                contador = 0
                for obj in queryset_para_atualizar:
                    obj.filial = nova_filial
                    obj.save()
                    contador += 1

                nome_filial = nova_filial.nome if nova_filial else "Global (Sem Filial)"
                self.message_user(
                    request,
                    f"{contador} item(ns) foram movidos com sucesso para a filial: {nome_filial}.",
                    messages.SUCCESS
                )
                return None

        if not form:
            ids_selecionados = ','.join(str(pk) for pk in queryset.values_list('pk', flat=True))
            form = ChangeFilialForm(initial={'selected_ids': ids_selecionados})

        contexto = {
            'opts': self.model._meta,
            'queryset': queryset,
            'form': form,
            'title': "Alterar Filial"
        }
        return render(request, 'admin/actions/change_filial_intermediate.html', contexto)

    change_filial_action.short_description = "Alterar filial dos itens selecionados"


class AtividadeLogMixin:
    """
    Mixin refatorado para criar logs de atividade para Ferramentas ou Malas.
    """

    def _log_atividade(self, tipo, descricao, ferramenta=None, mala=None):
        if not ferramenta and not mala:
            raise ValueError("A função _log_atividade requer um objeto 'ferramenta' ou 'mala'.")

        item = ferramenta or mala

        if not hasattr(self, 'request') or not hasattr(self.request, 'user'):
            raise TypeError(
                f"O {self.__class__.__name__} deve ter acesso ao 'request.user' para logar atividades."
            )

        Atividade.objects.create(
            ferramenta=ferramenta,
            mala=mala,
            filial=item.filial,
            tipo_atividade=tipo,
            descricao=descricao,
            usuario=self.request.user
        )


class HTMXModalFormMixin:
    """
    Mixin para adaptar CreateView e UpdateView para funcionar com modais HTMX.
    """

    def get_template_names(self):
        if self.request.htmx:
            original_template = super().get_template_names()[0]
            base, ext = original_template.rsplit('.', 1)
            return [f"{base}_partial.{ext}"]
        return super().get_template_names()

    def form_valid(self, form):
        response = super().form_valid(form)

        if self.request.htmx:
            htmx_response = HttpResponse(status=204)
            htmx_response['HX-Redirect'] = response.url
            return htmx_response

        return response


# =============================================================================
# == MIXIN DE ACESSO A TAREFAS
# =============================================================================

class TarefaAccessMixin:
    """
    Mixin que garante acesso à tarefa.
    Acesso: criador, responsável, participantes, staff, superuser.
    """

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not self.user_can_access(self.request.user, obj):
            raise PermissionDenied('Você não tem permissão para acessar esta tarefa.')
        return obj

    @staticmethod
    def user_can_access(user, tarefa):
        if user.is_superuser or user.is_staff:
            return True
        if tarefa.usuario_id == user.pk:
            return True
        if tarefa.responsavel_id == user.pk:
            return True
        if tarefa.participantes.filter(pk=user.pk).exists():
            return True
        return False

    @staticmethod
    def user_can_edit(user, tarefa):
        if user.is_superuser or user.is_staff:
            return True
        if tarefa.usuario_id == user.pk:
            return True
        if tarefa.responsavel_id == user.pk:
            return True
        return False


# =============================================================================
# == MIXIN DE PERMISSÃO POR APP (Controle de acesso por módulo)
# =============================================================================

class AppPermissionMixin(PermissionRequiredMixin):
    """
    Mixin que verifica se o usuário tem pelo menos UMA permissão
    do app especificado. Superusers passam direto.

    Uso nas views:
        class MinhaView(LoginRequiredMixin, AppPermissionMixin, ListView):
            app_label_required = 'ata_reuniao'

    Também aceita o padrão do Django:
        class MinhaView(LoginRequiredMixin, AppPermissionMixin, ListView):
            permission_required = 'ata_reuniao.view_atareuniao'
    """
    app_label_required = None
    permission_required = None
    raise_exception = True

    def get_permission_required(self):
        if self.permission_required:
            if isinstance(self.permission_required, str):
                return (self.permission_required,)
            return self.permission_required
        return ()

    def has_permission(self):
        user = self.request.user

        if user.is_superuser:
            return True

        if self.permission_required:
            return super().has_permission()

        if self.app_label_required:
            all_perms = user.get_all_permissions()
            return any(
                perm.startswith(f'{self.app_label_required}.')
                for perm in all_perms
            )

        return False

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return render(self.request, 'errors/acesso_negado.html', {
                'titulo': 'Acesso Negado',
                'mensagem': (
                    'Você não possui permissão para acessar este módulo. '
                    'Solicite acesso ao administrador do sistema.'
                ),
            }, status=403)
        return super().handle_no_permission()

