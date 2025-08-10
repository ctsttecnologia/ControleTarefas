from django.contrib import admin

from core.admin import FilialAdminMixin
from seguranca_trabalho.models import Equipamento
from .models import Incidente, Inspecao, User


# -----------------------------------------------------------------------------
# ADMIN MIXIN PARA SEGURANÇA DE FILIAL
# -----------------------------------------------------------------------------
class FilialScopedQuerysetMixin(admin.ModelAdmin):
    """
    Um ModelAdmin base que garante que superusuários vejam tudo, mas outros
    usuários do admin vejam e editem apenas os dados de sua própria filial.
    """
    # Adiciona 'filial' às colunas e filtros para fácil visualização
    list_display = ('filial',)
    list_filter = ('filial',)
    
    def get_queryset(self, request):
        """Filtra os objetos na lista principal do admin."""
        qs = super().get_queryset(request)
        # Superusuários podem ver tudo
        if request.user.is_superuser:
            return qs
        # Outros usuários veem apenas dados de sua filial
        if hasattr(request.user, 'filial'):
            return qs.filter(filial=request.user.filial)
        return qs.none()

    def save_model(self, request, obj, form, change):
        """Ao criar um novo objeto, atribui a filial do usuário."""
        if not obj.pk and hasattr(request.user, 'filial'): # 'obj.pk' é nulo se for um novo objeto
            obj.filial = request.user.filial
        super().save_model(request, obj, form, change)
        
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filtra os dropdowns de chaves estrangeiras dentro do formulário do admin."""
        if not request.user.is_superuser and hasattr(request.user, 'filial'):
            # Exemplo: Se o campo for 'equipamento', filtra por filial
            if db_field.name == "equipamento":
                kwargs["queryset"] = Equipamento.objects.filter(filial=request.user.filial)
            # Exemplo: Se o campo for 'inspetor', filtra por filial
            if db_field.name == "inspetor":
                kwargs["queryset"] = User.objects.filter(filial=request.user.filial)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

# -----------------------------------------------------------------------------
# ADMINS REATORADOS
# -----------------------------------------------------------------------------

@admin.register(Incidente)
class IncidenteAdmin(FilialAdminMixin, FilialScopedQuerysetMixin):
    """Admin para Incidentes, protegido pelo escopo de filial."""
    # Adiciona os campos específicos do modelo ao list_display herdado
    list_display = ('descricao', 'setor', 'tipo_incidente', 'data_ocorrencia', 'registrado_por') + FilialScopedQuerysetMixin.list_display
    list_filter = ('setor', 'tipo_incidente', 'data_ocorrencia') + FilialScopedQuerysetMixin.list_filter
    search_fields = ('descricao', 'detalhes', 'setor')
    date_hierarchy = 'data_ocorrencia'

@admin.register(Inspecao)
class InspecaoAdmin(FilialScopedQuerysetMixin):
    """Admin para Inspeções, protegido pelo escopo de filial."""
    list_display = ('__str__', 'data_agendada', 'status', 'inspetor') + FilialScopedQuerysetMixin.list_display
    list_filter = ('status', 'data_agendada') + FilialScopedQuerysetMixin.list_filter
    search_fields = ('equipamento__nome', 'inspetor__username') # Corrigido para o lookup correto
    autocomplete_fields = ['equipamento', 'inspetor']