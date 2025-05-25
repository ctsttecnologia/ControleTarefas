from django.contrib import admin
from .models import AtaReuniao

@admin.register(AtaReuniao)
class AtaReuniaoAdmin(admin.ModelAdmin):
    list_display = ('id', 'contrato', 'coordenador', 'responsavel', 'natureza', 'entrada', 'prazo', 'status')
    list_filter = ('id', 'contrato', 'coordenador', 'responsavel', 'natureza', 'entrada', 'prazo', 'status')
    search_fields = ('id', 'contrato', 'coordenador', 'responsavel', 'natureza', 'entrada', 'prazo', 'status')
    date_hierarchy = 'entrada'
    ordering = ('-entrada',)
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

    # Adicionando um campo de ação personalizado
    actions = ['marcar_como_concluido']

    def marcar_como_concluido(self, request, queryset):
        updated = queryset.update(status='Concluído')
        self.message_user(request, f"{updated} atas marcadas como concluídas.")
    marcar_como_concluido.short_description = "Marcar selecionadas como Concluído"

    