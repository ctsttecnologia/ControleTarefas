
# ata_reuniao/admin.py

from django.contrib import admin
from .models import AtaReuniao
from core.mixins import FilialScopedQuerysetMixin # Assumindo que o mixin está em core/mixins.py

@admin.register(AtaReuniao)
class AtaReuniaoAdmin(FilialScopedQuerysetMixin, admin.ModelAdmin):
    # Campos a serem exibidos na lista
    list_display = (
        'id', 
        'contrato', 
        'filial', 
        'coordenador', 
        'responsavel', 
        'natureza', 
        'entrada', 
        'prazo', 
        'status'
    )
    # Adicionando 'status' ao list_editable para mudanças rápidas
    list_editable = ('status',)
    list_display_links = ('id', 'contrato')

    # Filtros na barra lateral
    list_filter = ('status', 'filial', 'natureza', 'entrada', 'prazo')
    
    # Campos para a barra de busca
    search_fields = (
        'id', 
        'acao',
        'contrato__nome',
        'coordenador__username', # Use __username ou __first_name, dependendo do seu modelo User
        'responsavel__username'
    )
    
    # Navegação por hierarquia de datas
    date_hierarchy = 'entrada'
    ordering = ('-entrada',)
    
    # Habilita busca otimizada para campos ForeignKey
    autocomplete_fields = ['contrato', 'coordenador', 'responsavel']
    
    fieldsets = (
        ('Informações Gerais', {
            'fields': ('filial', 'contrato', 'status')
        }),
        ('Responsabilidade', {
            'fields': ('coordenador', 'responsavel')
        }),
        ('Detalhes e Ação', {
            'fields': ('natureza', 'acao')
        }),
        ('Datas', {
            'fields': ('entrada', 'prazo')
        }),
    )

    actions = ['marcar_como_concluido']

    def marcar_como_concluido(self, request, queryset):
        # Acessa o valor do Choice através do enum/TextChoices
        updated = queryset.update(status=AtaReuniao.Status.CONCLUIDO)
        self.message_user(request, f"{updated} ata(s) foi(ram) marcada(s) como Concluída(s).")
    
    # Define o nome que aparecerá no dropdown de ações
    marcar_como_concluido.short_description = "Marcar selecionadas como Concluído"
    
    # Garante que o campo 'filial' seja preenchido automaticamente, se não for editável
    def save_model(self, request, obj, form, change):
        if not obj.filial_id and request.session.get('active_filial_id'):
            obj.filial_id = request.session.get('active_filial_id')
        super().save_model(request, obj, form, change)
    