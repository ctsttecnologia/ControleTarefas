
# ata_reuniao/admin.py

from django.contrib import admin
from .models import AtaReuniao

# --------------------------------------------------------------------------
# PASSO 1: REGISTRAR O ADMIN PARA OS MODELOS RELACIONADOS
# --------------------------------------------------------------------------

@admin.register(AtaReuniao)
class AtaReuniaoAdmin(admin.ModelAdmin):
    list_display = ('id', 'contrato', 'coordenador', 'responsavel', 'natureza', 'entrada', 'prazo', 'status')
    list_filter = ('status', 'natureza', 'entrada', 'prazo')
    
    # Refinado para buscas mais eficientes e direcionadas
    search_fields = (
        'id', 
        'acao',
        'contrato__nome',      # Busca no nome do cliente relacionado
        'coordenador__nome',   # Busca no nome do coordenador relacionado
        'responsavel__nome'    # Busca no nome do responsável relacionado
    )
    
    date_hierarchy = 'entrada'
    ordering = ('-entrada',)
    
    # Agora que ClienteAdmin e FuncionarioAdmin existem e têm 'search_fields',
    # esta linha funcionará perfeitamente.
    autocomplete_fields = ['contrato', 'coordenador', 'responsavel']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('contrato', 'status')
        }),
        ('Responsáveis', {
            'fields': ('coordenador', 'responsavel')
        }),
        ('Detalhes da Reunião', {
            'fields': ('natureza', 'acao')
        }),
        ('Prazos', {
            'fields': ('entrada', 'prazo')
        }),
    )

    actions = ['marcar_como_concluido']

    def marcar_como_concluido(self, request, queryset):
        # Usando o TextChoices para mais segurança
        updated = queryset.update(status=AtaReuniao.Status.CONCLUIDO)
        self.message_user(request, f"{updated} ata(s) marcada(s) como Concluída(s).")
    marcar_como_concluido.short_description = "Marcar selecionadas como Concluído"
    