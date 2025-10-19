# Em core/mixins.py
from django.db.models import Q, QuerySet
from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.core.exceptions import PermissionDenied
from .forms import ChangeFilialForm 
from django.contrib.auth.mixins import AccessMixin, PermissionRequiredMixin
from ferramentas.models import Atividade
from django.http import HttpResponse

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
        """
        Sobrescreve o método padrão para redirecionar o usuário com uma
        mensagem de erro, em vez de mostrar a página 403 Forbidden.
        """
        # Adiciona a mensagem de erro que será exibida na próxima página.
        messages.error(self.request, "Você não tem permissão para acessar esta página.")
        
        # Redireciona o usuário para a página inicial do seu sistema.
        return redirect('usuario:profile') 


# CLASSE REMOVIDA: 'BaseFilialScopedQueryset' foi removida.
# A lógica agora vive em 'core/managers.py'


class AdminFilialScopedMixin:
    """
    NÍVEL 2 (Horizontal/Filial) - Para o Admin:
    Mixin para ser usado EXCLUSIVAMENTE no admin.py (ModelAdmin).
    Filtra o queryset chamando o método 'for_request(request)' 
    do manager do modelo.
    
    IMPORTANTE: O modelo deste ModelAdmin DEVE usar o 'FilialManager'.
    """
    def get_queryset(self, request):
        # A assinatura correta para o ModelAdmin
        qs = super().get_queryset(request)
        # Delega a lógica de filtragem para o manager do modelo
        return qs.for_request(request)


class ViewFilialScopedMixin:
    """
    NÍVEL 2 (Horizontal/Filial) - Para Views:
    Mixin para ser usado EXCLUSIVAMENTE em Class-Based Views (views.py).
    Filtra o queryset chamando o método 'for_request(request)' 
    do manager do modelo.

    IMPORTANTE: O modelo desta View DEVE usar o 'FilialManager'.
    """
    def get_queryset(self):
        # A assinatura correta para CBVs
        qs = super().get_queryset()
        # Delega a lógica de filtragem para o manager do modelo
        return qs.for_request(self.request)


class TecnicoScopeMixin:
    """
    NÍVEL 3 (Vertical/Dados):
    Mixin global para filtrar querysets para usuários do grupo 'TÉCNICO'.
    Deve ser herdado ANTES do ViewFilialScopedMixin.
    
    Ex: class MinhaView(SSTPermissionMixin, TecnicoScopeMixin, ViewFilialScopedMixin, ListView):
    """
    
    tecnico_scope_lookup = None  # Padrão é None. DEVE ser sobrescrito na View.

    def _is_tecnico(self) -> bool:
        """Helper interno para checar o grupo e cachear o resultado no request."""
        user = self.request.user
        if not hasattr(user, '_is_tecnico'):
            # Cacheia o resultado no objeto 'user' para esta requisição
            user._is_tecnico = user.groups.filter(name='TÉCNICO').exists()
        return user._is_tecnico

    def get_queryset(self) -> QuerySet:
        """
        Sobrescreve o get_queryset padrão para aplicar o escopo.
        """
        # 1. Obtém o queryset de mixins anteriores (ex: ViewFilialScopedMixin)
        queryset = super().get_queryset()
        
        # 2. Aplica o filtro usando o método auxiliar
        return self.scope_tecnico_queryset(queryset)

    def scope_tecnico_queryset(self, queryset: QuerySet) -> QuerySet:
        """
        Método auxiliar para aplicar o filtro de escopo em qualquer queryset.
        """
        # 1. Se não for técnico, retorna o queryset original (ex: admin, gerente)
        if not self._is_tecnico():
            return queryset

        # 2. Se FOR técnico, verificar se o lookup foi configurado na View
        if self.tecnico_scope_lookup:
            filter_kwargs = {self.tecnico_scope_lookup: self.request.user}
            return queryset.filter(**filter_kwargs).distinct()

        # 3. Se FOR técnico e o lookup for None: "negar por padrão"
        return queryset.none()


class TarefaPermissionMixin(AccessMixin):
    """
    Mixin de permissão a nível de objeto (Exemplo).
    Garante que o usuário logado seja o criador ou o responsável pela tarefa.
    Deve ser usado em conjunto com um mixin de escopo de filial (ex: `ViewFilialScopedMixin`).
    """
    def get_queryset(self):
        qs = super().get_queryset()
        # Aplica o filtro de permissão SOBRE a queryset já filtrada pela filial/técnico
        return qs.filter(Q(usuario=self.request.user) | Q(responsavel=self.request.user)).distinct()


# =============================================================================
# == MIXINS UTILITÁRIOS (Seu código original, preservado)
# =============================================================================

class FilialCreateMixin:
    """
    Mixin para views de criação. Atribui automaticamente a filial da sessão
    ao novo objeto antes de salvá-lo.
    """
    def form_valid(self, form):
        filial_id = self.request.session.get('active_filial_id')
        if not filial_id:
            messages.error(self.request, "Nenhuma filial selecionada. Por favor, escolha uma filial no menu superior.")
            raise PermissionDenied("Nenhuma filial selecionada para criação de objeto.")
        
        form.instance.filial_id = filial_id
        messages.success(self.request, f"{self.model._meta.verbose_name.capitalize()} criado(a) com sucesso.")
        return super().form_valid(form)

    
class ChangeFilialAdminMixin:
    """
    Ação de Admin para trocar a filial de objetos em lote.
    """
    actions = ['change_filial_action']

    def change_filial_action(self, request, queryset):
        """
        Ação de admin que gerencia a mudança de filial, com tratamento de erros aprimorado.
        """
        if not request.user.is_superuser:
            self.message_user(request, "Apenas superusuários podem mover itens entre filiais.", level=messages.ERROR)
            return None # Adicionado para segurança

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
                self.message_user(request, f"{contador} item(ns) foram movidos com sucesso para a filial: {nome_filial}.", messages.SUCCESS)
                
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
        """
        Cria um log de atividade. Requer um tipo, uma descrição, e
        exclusivamente um objeto 'ferramenta' OU 'mala'.
        """
        if not ferramenta and not mala:
            raise ValueError("A função _log_atividade requer um objeto 'ferramenta' ou 'mala'.")

        item = ferramenta or mala
        
        # Garante que o usuário esteja disponível (comum em CBVs)
        if not hasattr(self, 'request') or not hasattr(self.request, 'user'):
             raise TypeError(f"O {self.__class__.__name__} deve ter acesso ao 'request.user' para logar atividades.")

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
        """
        Se a requisição for HTMX, usa o template parcial, senão, o completo.
        """
        if self.request.htmx:
            # Assumindo que seu template parcial segue um padrão de nome
            # ex: 'tarefas/partials/tarefa_form_partial.html'
            original_template = super().get_template_names()[0]
            base, ext = original_template.rsplit('.', 1)
            return [f"{base}_partial.{ext}"]
        return super().get_template_names()

    def form_valid(self, form):
        """
        Após salvar o formulário com sucesso, envia uma resposta para o HTMX
        fechar o modal e redirecionar a página principal.
        """
        # Primeiro, executa a lógica padrão (salvar o objeto, etc.)
        response = super().form_valid(form)

        # Se a requisição for HTMX, intercepta a resposta de redirecionamento
        # e a transforma em uma resposta HX-Redirect.
        if self.request.htmx:
            # Cria uma resposta vazia
            htmx_response = HttpResponse(status=204) # 204 No Content
            # Adiciona o header que o HTMX usará para redirecionar a página de fundo
            # Pega a URL de sucesso do 'super().form_valid()'
            htmx_response['HX-Redirect'] = response.url 
            return htmx_response
        
        # Se não for HTMX, retorna a resposta padrão (redirecionamento)
        return response

