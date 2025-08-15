# Em core/mixins.py

from pyexpat.errors import messages
from django.db.models import Q
from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied


class FilialScopedQuerysetMixin:
    """
    Mixin universal para filtrar querysets pela filial ativa na sessão do usuário.
    Compatível com ModelAdmin e Class-Based Views.
    """
    def get_queryset(self): # MUDANÇA 1: A assinatura agora é o padrão do Django.
        # super().get_queryset() agora funciona de forma confiável com qualquer view do Django.
        qs = super().get_queryset() 
        
        # MUDANÇA 2: Acessamos o request de forma segura através de self.request.
        request = self.request
        
        # O NOME DA SUA CHAVE DE SESSÃO: 'active_filial_id'
        active_filial_id = request.session.get('active_filial_id')

        # =====================================================================
        # TODA A SUA LÓGICA DE NEGÓCIO ABAIXO PERMANECE IDÊNTICA.
        # Nenhuma outra aplicação será afetada no seu comportamento.
        # =====================================================================

        if request.user.is_superuser and not active_filial_id:
            # Superuser sem filial selecionada vê tudo.
            return qs

        if active_filial_id:
            # Qualquer usuário com filial selecionada vê apenas os dados daquela filial.
            # Esta é a condição principal e tem prioridade.
            return qs.filter(filial_id=active_filial_id)
        
        if not request.user.is_superuser:
            # Fallback para usuário comum SEM filial selecionada na sessão.
            # Usa as filiais permitidas no perfil dele.
            if hasattr(request.user, 'filiais_permitidas'):
                return qs.filter(filial__in=request.user.filiais_permitidas.all())
            
            # Se não tiver nem filial na sessão, nem filiais permitidas, não vê nada.
            return qs.none()

        # Fallback final para o superuser (se as outras condições não se aplicarem).
        return qs

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
    
class FilialAdminScopedMixin:
    """
    Mixin completo para o Django Admin que:
    1. Filtra a listagem de objetos pela filial ativa na sessão (`get_queryset`).
    2. Atribui automaticamente a filial ativa ao criar um novo objeto (`save_model`).
    3. Filtra os campos de ForeignKey (dropdowns) para mostrar apenas opções da filial ativa (`formfield_for_foreignkey`).
    """

    def get_queryset(self, request):
        # A assinatura do ModelAdmin.get_queryset recebe 'request' como argumento.
        qs = super().get_queryset(request)
        
        # Usamos 'active_filial_id' que é a chave da sua sessão.
        filial_id = request.session.get('active_filial_id')

        # Se o usuário for superuser e não houver filial na sessão, ele vê tudo.
        if request.user.is_superuser and not filial_id:
            return qs
        
        if filial_id:
            return qs.filter(filial_id=filial_id)
        
        # Se não for superuser e não tiver filial na sessão, não vê nada por segurança.
        return qs.none()

    def save_model(self, request, obj, form, change):
        """
        Chamado ao salvar um objeto.
        'change' é True se for uma edição, False se for uma criação.
        """
        # Se for um novo objeto (change=False), atribui a filial da sessão.
        if not change:
            filial_id = request.session.get('active_filial_id')
            if filial_id:
                obj.filial_id = filial_id
            else:
                # Impede a criação se nenhuma filial estiver ativa (exceto para superuser).
                if not request.user.is_superuser:
                    raise PermissionDenied("Nenhuma filial selecionada para criar o objeto.")
        
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Filtra os dropdowns de chaves estrangeiras.
        """
        filial_id = request.session.get('active_filial_id')

        if filial_id:
            # Se o campo for uma FK para um modelo que tem um campo 'filial'...
            # (Ex: os campos 'cargo' e 'departamento' no formulário de Funcionario)
            if hasattr(db_field.related_model, 'filial'):
                kwargs['queryset'] = db_field.related_model.objects.filter(
                    filial_id=filial_id
                )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    