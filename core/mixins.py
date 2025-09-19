# Em core/mixins.py

from django.db.models import Q
from django.contrib import admin, messages
from django.shortcuts import render
from django.core.exceptions import PermissionDenied
from .forms import ChangeFilialForm 
from django.contrib.auth.mixins import AccessMixin, PermissionRequiredMixin
from django.shortcuts import redirect



class SSTPermissionMixin(PermissionRequiredMixin):
    """
    Mixin que herda do PermissionRequiredMixin do Django, mas customiza
    o comportamento em caso de falha de permissão.
    """

    def handle_no_permission(self):
        """
        Sobrescreve o método padrão para redirecionar o usuário com uma
        mensagem de erro, em vez de mostrar a página 403 Forbidden.
        """
        # Adiciona a mensagem de erro que será exibida na próxima página.
        messages.error(self.request, "Você não tem permissão para acessar esta página.")
        
        # Redireciona o usuário para a página inicial do seu sistema.
        # MUDE AQUI para a URL da sua página inicial/dashboard, se for diferente.
        return redirect('usuario:profile') 


class BaseFilialScopedQueryset:
    """
    Classe base que contém a lógica de filtragem por filial.
    """
    def _get_filtered_queryset(self, request, base_qs):
        """
        Lógica de filtragem centralizada.
        Recebe o request e a queryset base, e retorna a queryset filtrada.
        """
        active_filial_id = request.session.get('active_filial_id')

        # Condição 1: Superuser sem filial na sessão vê tudo
        if request.user.is_superuser and not active_filial_id:
            return base_qs

        # Condição 2: Qualquer usuário com uma filial ativa na sessão
        if active_filial_id:
            return base_qs.filter(filial_id=active_filial_id)

        # Condição 3: Usuário comum sem filial na sessão: usa as filiais permitidas no perfil
        if hasattr(request.user, 'filiais_permitidas'):
            # CORRIGIDO: Agora usa o relacionamento ManyToManyField
            return base_qs.filter(filial__in=request.user.filiais_permitidas.all())
        
        # Condição 4: Se não tem filiais permitidas, não vê nada
        return base_qs.none()


class AdminFilialScopedMixin(BaseFilialScopedQueryset):
    """
    Mixin para ser usado EXCLUSIVAMENTE no admin.py (ModelAdmin).
    """
    def get_queryset(self, request):
        # A assinatura correta para o ModelAdmin
        qs = super().get_queryset(request)
        return self._get_filtered_queryset(request, qs)


class ViewFilialScopedMixin(BaseFilialScopedQueryset):
    """
    Mixin para ser usado EXCLUSIVAMENTE em Class-Based Views (views.py).
    """
    def get_queryset(self):
        # A assinatura correta para CBVs
        qs = super().get_queryset()
        # Acessa o request via self.request
        return self._get_filtered_queryset(self.request, qs)


class TarefaPermissionMixin(AccessMixin):
    """
    Garanta que o usuário logado seja o criador ou o responsável pela tarefa.
    Deve ser usado em conjunto com FilialScopedQuerysetMixin.
    """
    # Este mixin já está escrito da forma correta e vai encadear perfeitamente
    # com o FilialScopedQuerysetMixin corrigido. Nenhuma alteração necessária aqui.
    def get_queryset(self):
        qs = super().get_queryset()
        # Aplica o filtro de permissão SOBRE a queryset já filtrada pela filial
        return qs.filter(Q(usuario=self.request.user) | Q(responsavel=self.request.user)).distinct()
    

class FilialCreateMixin:
    """
    Mixin para views de criação. Atribui automaticamente a filial da sessão
    ao novo objeto antes de salvá-lo.
    """
    def form_valid(self, form):
        # Lembre-se que seu mixin usa a chave 'active_filial_id'
        filial_id = self.request.session.get('active_filial_id')
        if not filial_id:
            messages.error(self.request, "Nenhuma filial selecionada. Por favor, escolha uma filial no menu superior.")
            raise PermissionDenied("Nenhuma filial selecionada para criação de objeto.")
        
        form.instance.filial_id = filial_id
        messages.success(self.request, f"{self.model._meta.verbose_name.capitalize()} criado(a) com sucesso.")
        return super().form_valid(form)

    
# Trocar filal, só administradores

class ChangeFilialAdminMixin:
 
    actions = ['change_filial_action']
    def change_filial_action(self, request, queryset):
        """
        Ação de admin que gerencia a mudança de filial, com tratamento de erros aprimorado.
        """
        if not request.user.is_superuser:
            self.message_user(request, "Erro: IDs de seleção inválidos.", level=messages.ERROR)
        # Inicializa o form como None para garantir que a variável sempre exista
        form = None
        # Se o formulário intermediário foi enviado (identificado pelo campo 'post')
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

                # Abordagem explícita: iterar e salvar cada objeto individualmente
                queryset_para_atualizar = self.model.objects.filter(pk__in=ids_selecionados)
                contador = 0
                for obj in queryset_para_atualizar:
                    obj.filial = nova_filial
                    obj.save()
                    contador += 1

                nome_filial = nova_filial.nome if nova_filial else "Global (Todas as Filiais)"
                self.message_user(request, f"{contador} item(ns) foram movidos com sucesso para a filial: {nome_filial}.", messages.SUCCESS)
                
                # Finaliza a ação com sucesso
                return None

        # Se o form não foi criado (é a primeira exibição) ou se ele é inválido
        if not form:
            ids_selecionados = ','.join(str(pk) for pk in queryset.values_list('pk', flat=True))
            form = ChangeFilialForm(initial={'selected_ids': ids_selecionados})

        # Renderiza a página intermediária com o contexto necessário
        contexto = {
            'opts': self.model._meta,
            'queryset': queryset,
            'form': form, # Passa o formulário (novo ou com erros) para o template
            'title': "Alterar Filial"
        }
        return render(request, 'admin/actions/change_filial_intermediate.html', contexto)

    change_filial_action.short_description = "Alterar filial dos itens selecionados"


