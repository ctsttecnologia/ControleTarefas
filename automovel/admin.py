
# automovel/admin.py

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import Carro, Carro_agendamento, Carro_checklist, Carro_foto
from core.mixins import AdminFilialScopedMixin # Supondo que você tenha este mixin

# MUDANÇA CRÍTICA: Removido 'km_inicial' e 'km_final' do inline.
class ChecklistInline(admin.TabularInline):
    model = Carro_checklist
    extra = 0
    fields = ('tipo', 'data_hora', 'usuario', 'link_para_checklist') # Campos que existem no modelo
    readonly_fields = ('data_hora', 'link_para_checklist')
    
    def link_para_checklist(self, obj):
        if obj.pk:
            link = reverse("admin:automovel_checklist_change", args=[obj.pk])
            return format_html('<a href="{}">Ver/Editar Detalhes</a>', link)
        return "N/A"
    link_para_checklist.short_description = 'Ações'

class FotoInline(admin.TabularInline):
    model = Carro_foto
    extra = 0
    fields = ('imagem', 'observacao', 'image_preview')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.imagem:
            return format_html('<img src="{0}" width="100" />', obj.imagem.url)
        return "Sem imagem"
    image_preview.short_description = 'Preview'

@admin.register(Carro)
class CarroAdmin(AdminFilialScopedMixin, admin.ModelAdmin):
    list_display = ('placa', 'modelo', 'marca', 'filial', 'disponivel', 'ativo')
    list_filter = ('filial', 'marca', 'disponivel', 'ativo')
    search_fields = ('placa', 'modelo', 'marca')
    list_editable = ('disponivel',)

    # MUDANÇA: Boas práticas para definir valores automáticos no admin
    def save_model(self, request, obj, form, change):
        if not obj.pk: # Se for um novo objeto
            obj.filial = request.user.filial_ativa
        super().save_model(request, obj, form, change)
    
    def get_readonly_fields(self, request, obj=None):
        if obj: # Se estiver editando um objeto existente
            return ('filial',)
        return ()

@admin.register(Carro_agendamento)
class AgendamentoAdmin(AdminFilialScopedMixin, admin.ModelAdmin):
    list_display = ('id', 'link_para_carro', 'funcionario', 'data_hora_agenda', 'status', 'filial')
    # ... (o resto da sua configuração do AgendamentoAdmin estava ótima)
    list_filter = ('filial', 'status', 'carro__marca', 'data_hora_agenda')
    search_fields = ('funcionario', 'carro__placa', 'usuario__username', 'id')
    autocomplete_fields = ('carro', 'usuario')
    list_select_related = ('carro', 'usuario', 'filial')
    inlines = [ChecklistInline, FotoInline]

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.filial = request.user.filial_ativa
            obj.usuario = request.user
        super().save_model(request, obj, form, change)
    
    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ('filial', 'usuario')
        return ()

    def link_para_carro(self, obj):
        link = reverse("admin:automovel_carro_change", args=[obj.carro.id])
        return format_html('<a href="{}">{}</a>', link, obj.carro)
    link_para_carro.short_description = 'Carro'



@admin.register(Carro_checklist)
class ChecklistAdmin(AdminFilialScopedMixin, admin.ModelAdmin):
    list_display = ('id', 'link_para_agendamento', 'tipo', 'data_hora', 'filial')
    list_filter = ('filial', 'tipo', 'data_hora')
    search_fields = ('agendamento__carro__placa', 'agendamento__funcionario', 'agendamento__id')
    autocomplete_fields = ('agendamento', 'usuario')
    date_hierarchy = 'data_hora'
    list_per_page = 30
    readonly_fields = ('filial',)

    # OTIMIZAÇÃO: Reduz queries na listagem
    list_select_related = ('agendamento__carro', 'usuario', 'filial')

    def link_para_agendamento(self, obj):
        """Cria um link para a página de edição do agendamento."""
        link = reverse("admin:automovel_agendamento_change", args=[obj.agendamento.id])
        return format_html('<a href="{}">Agendamento #{}</a>', link, obj.agendamento.id)
    link_para_agendamento.short_description = 'Agendamento'
    link_para_agendamento.admin_order_field = 'agendamento'

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.filial = request.user.filial_ativa
            obj.usuario = request.user
        super().save_model(request, obj, form, change)


@admin.register(Carro_foto)
class FotoAdmin(AdminFilialScopedMixin, admin.ModelAdmin):
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


