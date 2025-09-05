
# ata_reuniao/admin.py

from django.contrib import admin, messages
from .models import AtaReuniao
from core.mixins import ChangeFilialAdminMixin, AdminFilialScopedMixin
from django.shortcuts import render
from .forms import TransferenciaFilialForm 


@admin.register(AtaReuniao)
class AtaReuniaoAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    
    actions = ['marcar_como_concluido', 'transferir_filial']
    # --- Configuração da Lista ---
    list_display = (
        'id', 'contrato', 'filial', 'coordenador', 'responsavel', 
        'natureza', 'entrada', 'prazo', 'status'
    )
    list_display_links = ('id', 'contrato')
    list_editable = ('status',)
    list_filter = ('status', 'filial', 'natureza', 'entrada', 'prazo')
    
    # Pré-busca os objetos relacionados em uma única consulta
    # Essencial para campos em list_display, search_fields e list_filter que são ForeignKeys.
    list_select_related = ('contrato', 'filial', 'coordenador', 'responsavel')

    # --- Configuração de Busca e Ordenação ---
    search_fields = (
        'id', 
        'acao',
        'contrato__nome',
        # REVISÃO: Certifique-se que o modelo Funcionario tem estes campos para busca
        'coordenador__nome_completo', 
        'responsavel__nome_completo'
    )
    ordering = ('-entrada',)
    date_hierarchy = 'entrada'

    # --- Configuração do Formulário de Edição ---
    # 'readonly_fields' declarado apenas uma vez.
    readonly_fields = ('criado_em', 'atualizado_em')

    # PRÉ-REQUISITO: Garanta que os admins de Cliente e Funcionario tenham 'search_fields' definidos.
    autocomplete_fields = ['contrato', 'coordenador', 'responsavel']
    
    fieldsets = (
        ('Informações Gerais', {
            'fields': ('contrato', 'status', 'filial')
        }),
        ('Responsabilidade', {
            'fields': ('coordenador', 'responsavel')
        }),
        ('Detalhes da Ação', {
            'fields': ('natureza', 'acao')
        }),
        ('Datas e Prazos', {
            'fields': ('entrada', 'prazo')
        }),
        ('Informações do Sistema', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',) # REVISÃO: Oculta por padrão para um form mais limpo
        }),
    )

    # --- Ações Customizadas ---
    actions = ['marcar_como_concluido', 'marcar_como_pendente']

    def marcar_como_concluido(self, request, queryset):
        updated = queryset.update(status=AtaReuniao.Status.CONCLUIDO)
        self.message_user(request, f"{updated} ata(s) foi(ram) marcada(s) como Concluída(s).", messages.SUCCESS)
    marcar_como_concluido.short_description = "Marcar selecionadas como Concluído"

    # Adicionada nova ação para consistência
    def marcar_como_pendente(self, request, queryset):
        updated = queryset.update(status=AtaReuniao.Status.PENDENTE)
        self.message_user(request, f"{updated} ata(s) foi(ram) marcada(s) como Pendente(s).", messages.INFO)
    marcar_como_pendente.short_description = "Marcar selecionadas como Pendente"
    
    # O método save_model foi removido.
    # A lógica de atribuir a filial deve ser responsabilidade do AdminFilialScopedMixin.
    # Se o mixin não faz isso, ele deve ser corrigido lá para manter o código DRY.
    def get_readonly_fields(self, request, obj=None):
        """
        Define campos como somente leitura.
        - Após a criação, usuários normais não podem mudar a filial.
        - Superusuários PODEM mudar a filial para fazer transferências.
        """
        # Campos que são sempre somente leitura
        base_readonly = ('criado_em', 'atualizado_em')

        if obj: # Se estiver na página de edição
            # Se o usuário não for superuser, bloqueia a edição da filial
            if not request.user.is_superuser:
                return base_readonly + ('filial',)
        
        return base_readonly



@admin.action(description='Marcar selecionadas como Concluído')
def marcar_como_concluido(self, request, queryset):
    updated = queryset.update(status=AtaReuniao.Status.CONCLUIDO)
    self.message_user(request, f"{updated} ata(s) foi(ram) marcada(s) como Concluída(s).", messages.SUCCESS)

@admin.action(description='Transferir selecionadas para outra Filial')
def transferir_filial(self, request, queryset):
        # Se o formulário intermediário foi enviado
        if 'apply' in request.POST:
            form = TransferenciaFilialForm(request.POST)
            if form.is_valid():
                filial_destino = form.cleaned_data['filial_destino']
                updated = queryset.update(filial=filial_destino)
                self.message_user(request, f"{updated} ata(s) foi(ram) transferida(s) para a filial {filial_destino}.", messages.SUCCESS)
                return

        # Se não, mostra a página intermediária
        form = TransferenciaFilialForm()
        context = {
            'queryset': queryset,
            'form': form,
            'title': 'Transferir Atas',
            'opts': self.model._meta, # Necessário para o template admin
        }
        return render(request, 'admin/transfer_intermediate.html', context)

    