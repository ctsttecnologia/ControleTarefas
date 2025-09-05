
# automovel/admin.py

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import Carro, Agendamento, Checklist, Foto
from core.mixins import AdminFilialScopedMixin, ChangeFilialAdminMixin

# MELHORIA DE USABILIDADE: Definindo Inlines para Agendamento
class ChecklistInline(admin.TabularInline):
    """Permite visualizar e adicionar checklists diretamente na página do agendamento."""
    model = Checklist
    extra = 0  # Não mostra formulários extras para adicionar por padrão
    fields = ('tipo', 'data_hora', 'km_inicial', 'km_final', 'usuario')
    readonly_fields = ('data_hora', 'filial',) # Impede a edição da filial após a criação.)
    show_change_link = True # Adiciona um link para a página de detalhes do checklist

class FotoInline(admin.TabularInline):
    """Permite visualizar e adicionar fotos diretamente na página do agendamento."""
    model = Foto
    extra = 0
    fields = ('imagem', 'observacao', 'image_preview')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.imagem:
            return format_html('<img src="{0}" width="100" />', obj.imagem.url)
        return "Sem imagem"
    image_preview.short_description = 'Preview'


@admin.register(Carro)
class CarroAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('placa', 'modelo', 'marca', 'filial', 'disponivel', 'ativo')
    list_filter = ('filial', 'marca', 'disponivel', 'ativo')
    search_fields = ('placa', 'modelo', 'marca')
    list_editable = ('disponivel', 'ativo')
    list_per_page = 20
    readonly_fields = ('filial',)

    # ORGANIZAÇÃO: Agrupando campos na tela de edição
    fieldsets = (
        ('Informações Principais', {
            'fields': ('placa', 'modelo', 'marca', 'cor', 'ano', 'renavan', 'filial')
        }),
        ('Status e Manutenção', {
            'fields': ('disponivel', 'ativo', 'data_ultima_manutencao', 'data_proxima_manutencao')
        }),
        ('Outras Informações', {
            'fields': ('observacoes',)
        }),
    )

@admin.register(Agendamento)
class AgendamentoAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'link_para_carro', 'funcionario', 'data_hora_agenda', 'status', 'filial')
    list_filter = ('filial', 'status', 'carro__marca', 'data_hora_agenda')
    search_fields = ('funcionario', 'carro__placa', 'usuario__username', 'id')
    autocomplete_fields = ('carro', 'usuario')
    date_hierarchy = 'data_hora_agenda'
    list_per_page = 20
    readonly_fields = ('filial', 'usuario') # Usuário que criou não deve ser alterado
    
    # OTIMIZAÇÃO: Reduz queries na listagem
    list_select_related = ('carro', 'usuario', 'filial')

    # ORGANIZAÇÃO: Agrupando campos na tela de edição
    fieldsets = (
        (None, {
            'fields': ('status', 'cancelar_agenda', 'motivo_cancelamento')
        }),
        ('Detalhes do Agendamento', {
            'fields': ('carro', 'funcionario', 'cm', 'data_hora_agenda', 'data_hora_devolucao', 'descricao')
        }),
        ('Informações da Viagem', {
            'fields': ('pedagio', 'abastecimento', 'km_inicial', 'km_final', 'ocorrencia')
        }),
        ('Responsáveis', {
            'fields': ('responsavel', 'usuario', 'filial', 'assinatura')
        }),
    )
    
    # USABILIDADE: Adicionando os inlines criados acima
    inlines = [ChecklistInline, FotoInline]

    def link_para_carro(self, obj):
        """Cria um link para a página de edição do carro."""
        link = reverse("admin:automovel_carro_change", args=[obj.carro.id])
        return format_html('<a href="{}">{}</a>', link, obj.carro)
    link_para_carro.short_description = 'Carro'
    link_para_carro.admin_order_field = 'carro'


@admin.register(Checklist)
class ChecklistAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'link_para_agendamento', 'tipo', 'data_hora', 'filial')
    list_filter = ('filial', 'tipo', 'data_hora')
    search_fields = ('agendamento__carro__placa', 'agendamento__funcionario', 'agendamento__id')
    autocomplete_fields = ('agendamento', 'usuario')
    date_hierarchy = 'data_hora'
    list_per_page = 20
    readonly_fields = ('filial',)

    # OTIMIZAÇÃO: Reduz queries na listagem
    list_select_related = ('agendamento__carro', 'usuario', 'filial')

    def link_para_agendamento(self, obj):
        """Cria um link para a página de edição do agendamento."""
        link = reverse("admin:automovel_agendamento_change", args=[obj.agendamento.id])
        return format_html('<a href="{}">Agendamento #{}</a>', link, obj.agendamento.id)
    link_para_agendamento.short_description = 'Agendamento'
    link_para_agendamento.admin_order_field = 'agendamento'


@admin.register(Foto)
class FotoAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'agendamento', 'data_criacao', 'image_preview', 'filial')
    list_filter = ('filial', 'data_criacao',)
    search_fields = ('agendamento__id',)
    autocomplete_fields = ('agendamento',)
    readonly_fields = ('filial',)

    # OTIMIZAÇÃO: Reduz queries na listagem
    list_select_related = ('agendamento', 'filial')

    def image_preview(self, obj):
        if obj.imagem:
            return format_html('<a href="{0}" target="_blank"><img src="{0}" width="80" /></a>', obj.imagem.url)
        return "Sem imagem"
    image_preview.short_description = 'Preview da Imagem'


