# seguranca_trabalho/admin.py (CORRIGIDO E OTIMIZADO)
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import Equipamento, MatrizEPI, FichaEPI, EntregaEPI, MovimentacaoEstoque, Funcao

# --- Filtros Customizados ---
class TipoEquipamentoFilter(admin.SimpleListFilter):
    title = _('tipo de equipamento')
    parameter_name = 'tipo'

    def lookups(self, request, model_admin):
        return Equipamento.TIPO_CHOICES

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(tipo=self.value())
        return queryset

# CORREÇÃO para E116 em FichaEPIAdmin: Filtro customizado para status
class FichaStatusFilter(admin.SimpleListFilter):
    title = _('status da ficha')
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return (
            ('ativo', _('Ativa')),
            ('inativo', _('Inativa')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'ativo':
            return queryset.filter(data_demissao__isnull=True)
        if self.value() == 'inativo':
            return queryset.filter(data_demissao__isnull=False)
        return queryset

# --- Inlines ---
class MatrizEPIInline(admin.TabularInline):
    model = MatrizEPI
    extra = 1
    autocomplete_fields = ['equipamento']
    verbose_name = "EPI Necessário"
    verbose_name_plural = "EPIs Necessários para este Cargo"

class EntregaEPIInline(admin.TabularInline):
    model = EntregaEPI
    extra = 0
    fields = ('equipamento', 'quantidade', 'data_entrega', 'status', 'validade')
    readonly_fields = ('status', 'validade')
    autocomplete_fields = ['equipamento']
    
    @admin.display(description='Validade do Uso')
    def validade(self, obj):
        return obj.data_vencimento_uso.date() if obj.data_vencimento_uso else '-'

# --- ModelAdmins ---
@admin.register(Funcao)
class FuncaoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'descricao_resumida', 'ativo')
    search_fields = ('nome', 'descricao')
    list_editable = ('ativo',)
    list_filter = ('ativo',)
    inlines = [MatrizEPIInline]
    
    @admin.display(description='Descrição')
    def descricao_resumida(self, obj):
        if obj.descricao and len(obj.descricao) > 100:
            return obj.descricao[:100] + '...'
        return obj.descricao or '-'

@admin.register(Equipamento)
class EquipamentoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'certificado_aprovacao','estoque_minimo', 'precisa_repor_display', 'ativo')
    list_filter = ('ativo', TipoEquipamentoFilter)
    search_fields = ('nome', 'certificado_aprovacao')
    
    list_editable = ('estoque_minimo', 'ativo')
    fieldsets = (
        (None, {'fields': ('nome', 'tipo', 'certificado_aprovacao', 'ativo')}),
        ('Detalhes e Vida Útil', {'fields': ('descricao', 'vida_util_dias')}),
        ('Controle de Estoque', {'fields': ('estoque_minimo', 'estoque_atual')}),
    )

    @admin.display(boolean=True, description='Precisa Repor?', ordering='estoque_atual')
    def precisa_repor_display(self, obj):
        return obj.precisa_repor

@admin.register(FichaEPI)
class FichaEPIAdmin(admin.ModelAdmin):
    # CORREÇÃO para E108: 'ativo' foi substituído por 'status_display'
    list_display = ('colaborador', 'funcao', 'data_admissao', 'total_epis', 'atualizado_em', 'status_display')
    # CORREÇÃO para E116: 'ativo' foi substituído por FichaStatusFilter
    list_filter = ('funcao', 'data_admissao', FichaStatusFilter)
    search_fields = ('colaborador__first_name', 'colaborador__last_name', 'colaborador__username')
    autocomplete_fields = ['colaborador', 'funcao']
    inlines = [EntregaEPIInline]
    date_hierarchy = 'data_admissao'
    
    @admin.display(description='Total de Entregas')
    def total_epis(self, obj):
        return obj.entregas.count()

    @admin.display(description='Status', ordering='data_demissao')
    def status_display(self, obj):
        if obj.data_demissao is None:
            return format_html('<span style="color: green;">● Ativa</span>')
        return format_html('<span style="color: red;">● Inativa</span>')

@admin.register(EntregaEPI)
class EntregaEPIAdmin(admin.ModelAdmin):
    list_display = ('ficha_colaborador', 'equipamento', 'quantidade', 'data_entrega', 'validade', 'status_display')
    list_filter = (
        'equipamento',
        ('data_entrega', admin.DateFieldListFilter),
        ('data_devolucao', admin.DateFieldListFilter),
    )
    search_fields = ('ficha__colaborador__first_name', 'ficha__colaborador__last_name', 'equipamento__nome')
    autocomplete_fields = ['ficha', 'equipamento']
    readonly_fields = ('status_display', 'data_vencimento_uso')
    date_hierarchy = 'data_entrega'
    list_select_related = ('ficha__colaborador', 'equipamento')

    @admin.display(description='Colaborador', ordering='ficha__colaborador__first_name')
    def ficha_colaborador(self, obj):
        return obj.ficha.colaborador.get_full_name()
    
    @admin.display(description='Validade do Uso', ordering='data_entrega')
    def validade(self, obj):
        return obj.data_vencimento_uso.date() if obj.data_vencimento_uso else '-'
    
    @admin.display(description='Status', ordering='data_devolucao')
    def status_display(self, obj):
        status = obj.status
        if status == "Devolvido":
            color = 'gray'
        elif status == "Vencido":
            color = 'red'
        elif status == "Aguardando Assinatura":
            color = 'orange'
        else: # Ativo com Colaborador
            color = 'green'
        return format_html('<span style="color: {};">● {}</span>', color, status)

@admin.register(MovimentacaoEstoque)
class MovimentacaoEstoqueAdmin(admin.ModelAdmin):
    list_display = ('data', 'equipamento', 'tipo_formatado', 'quantidade', 'responsavel', 'justificativa_resumida')
    list_filter = ('tipo', 'data', 'equipamento')
    search_fields = ('equipamento__nome', 'justificativa', 'responsavel__username')
    autocomplete_fields = ['equipamento', 'responsavel']
    date_hierarchy = 'data'
    
    @admin.display(description='Tipo', ordering='tipo')
    def tipo_formatado(self, obj):
        return dict(MovimentacaoEstoque.TIPO_MOVIMENTACAO).get(obj.tipo, obj.tipo)
    
    @admin.display(description='Justificativa')
    def justificativa_resumida(self, obj):
        if obj.justificativa and len(obj.justificativa) > 50:
            return obj.justificativa[:50] + '...'
        return obj.justificativa



