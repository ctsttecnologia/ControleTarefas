# =============================================================================
# gestao_riscos/admin.py
# =============================================================================
from django import forms
from django.contrib import admin, messages

from core.mixins import AdminFilialScopedMixin, ChangeFilialAdminMixin
from .models import CartaoTag, Incidente, Inspecao, TipoRisco

PERM_SAUDE = 'gestao_riscos.view_dados_saude_incidente'
SECAO_SAUDE = 'Envolvido e dados de saúde (LGPD)'


class FilialAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    """Base: escopo por filial + filial somente leitura."""
    readonly_fields = ('filial',)
    list_per_page = 25


@admin.register(Incidente)
class IncidenteAdmin(FilialAdmin):
    list_display = ('descricao', 'tipo_ocorrencia', 'classificacao', 'gravidade',
                    'setor', 'data_ocorrencia', 'registrado_por', 'filial')
    list_filter = ('classificacao', 'tipo_ocorrencia', 'gravidade', 'setor', 'data_ocorrencia', 'filial')
    search_fields = ('descricao', 'local_especifico', 'setor')
    date_hierarchy = 'data_ocorrencia'
    list_select_related = ('registrado_por', 'filial')
    autocomplete_fields = ['funcionario_envolvido']
    readonly_fields = ('classificacao', 'registrado_por', 'data_registro', 'filial')
    fieldsets = (
        ('Ocorrência', {'fields': ('tipo_ocorrencia', 'classificacao', 'gravidade', 'descricao',
                                   'detalhes', 'setor', 'local_especifico', 'data_ocorrencia',
                                   'acao_imediata')}),
        (SECAO_SAUDE, {'fields': ('funcionario_envolvido', 'parte_corpo_atingida',
                                  'dias_afastamento', 'cat_emitida', 'numero_cat')}),
        ('Registro', {'fields': ('registrado_por', 'data_registro', 'filial')}),
    )

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if request.user.has_perm(PERM_SAUDE):
            return fieldsets
        return [fs for fs in fieldsets if fs[0] != SECAO_SAUDE]  # LGPD art. 11

    def save_model(self, request, obj, form, change):
        if not change and not obj.registrado_por_id:
            obj.registrado_por = request.user
        super().save_model(request, obj, form, change)


class InspecaoAdminForm(forms.ModelForm):
    class Meta:
        model = Inspecao
        fields = '__all__'

    def clean(self):
        cd = super().clean()
        if not cd.get('equipamento') and not cd.get('entrega_epi'):
            raise forms.ValidationError('Informe um Equipamento ou um Item de EPI.')
        return cd


@admin.register(Inspecao)
class InspecaoAdmin(FilialAdmin):
    form = InspecaoAdminForm
    list_display = ('__str__', 'data_agendada', 'data_realizacao', 'status', 'responsavel', 'filial')
    list_filter = ('status', 'data_agendada', 'filial')
    search_fields = ('equipamento__nome', 'responsavel__username', 'entrega_epi__numero_serie')
    date_hierarchy = 'data_agendada'
    list_select_related = ('equipamento', 'responsavel', 'filial')
    autocomplete_fields = ['equipamento', 'responsavel']
    raw_id_fields = ('entrega_epi',)
    actions = ['cancelar_selecionadas', 'reabrir_selecionadas']

    @admin.action(description='Cancelar inspeções selecionadas', permissions=['change'])
    def cancelar_selecionadas(self, request, queryset):
        n = queryset.filter(status__in=['PENDENTE_APROVACAO', 'PENDENTE']).update(status='CANCELADA')
        self.message_user(request, f'{n} inspeção(ões) cancelada(s).', messages.SUCCESS)

    @admin.action(description='Reabrir (volta para aprovação)', permissions=['change'])
    def reabrir_selecionadas(self, request, queryset):
        n = queryset.filter(status='CANCELADA').update(status='PENDENTE_APROVACAO')
        self.message_user(request, f'{n} inspeção(ões) reaberta(s).', messages.SUCCESS)


@admin.register(CartaoTag)
class CartaoTagAdmin(FilialAdmin):
    """Cartões de Bloqueio (Tags)."""
    list_display = ('funcionario', 'cargo', 'fone', 'data_criacao', 'data_validade', 'ativo', 'filial')
    list_filter = ('ativo', 'data_validade', 'filial')
    search_fields = ('funcionario__nome_completo',)
    list_select_related = ('funcionario', 'cargo', 'filial')
    autocomplete_fields = ['funcionario']


@admin.register(TipoRisco)
class TipoRiscoAdmin(FilialAdmin):
    list_display = ('categoria', 'nome', 'codigo_cor', 'nr_referencia', 'ativo', 'filial')
    list_editable = ('ativo',)
    list_filter = ('categoria', 'ativo', 'filial')
    search_fields = ('nome', 'nr_referencia')
    ordering = ('categoria', 'nome')
    list_select_related = ('filial',)
