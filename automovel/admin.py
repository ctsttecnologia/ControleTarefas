
# automovel/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.contrib.auth.admin import UserAdmin
from django import forms

from .models import Carro, Agendamento, FotoAgendamento, Checklist_Carro

from .forms import ChecklistCarroForm

class FotoAgendamentoInline(admin.TabularInline):
    model = FotoAgendamento
    extra = 1
    fields = ('imagem', 'observacao', 'data_criacao', 'imagem_preview')
    readonly_fields = ('data_criacao', 'imagem_preview')
    
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        if obj:
            form = formset.form
            # Verifica se o campo existe antes de tentar acessá-lo
            if 'agendamento' in form.base_fields:
                form.base_fields['agendamento'].initial = obj
                form.base_fields['agendamento'].widget = forms.HiddenInput()
        return formset

    def imagem_preview(self, obj):
        if obj.imagem and hasattr(obj.imagem, 'url'):
            return format_html('<img src="{}" width="150" />', obj.imagem.url)
        return "-"
    imagem_preview.short_description = 'Pré-visualização'


class ChecklistCarroInline(admin.TabularInline):
    model = Checklist_Carro
    extra = 0
    max_num = 2
    fields = ('tipo', 'data_criacao', 'confirmacao', 'link_para_checklist')
    readonly_fields = ('data_criacao', 'link_para_checklist')
    
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        if obj:
            form = formset.form
            # Verificação segura para o campo agendamento
            if 'agendamento' in form.base_fields:
                form.base_fields['agendamento'].initial = obj
                form.base_fields['agendamento'].widget = forms.HiddenInput()
            
            # Verificação segura para o campo usuario
            if 'usuario' in form.base_fields:
                form.base_fields['usuario'].initial = request.user
                form.base_fields['usuario'].widget = forms.HiddenInput()
        return formset

    def link_para_checklist(self, obj):
        if obj.id:
            url = reverse("admin:automovel_checklist_carro_change", args=[obj.id])
            return format_html('<a href="{}">Ver Checklist</a>', url)
        return "-"
    link_para_checklist.short_description = 'Ações'


@admin.register(Carro)
class CarroAdmin(admin.ModelAdmin):
    list_display = ('marca', 'modelo', 'placa', 'ano', 'cor', 'ativo')
    list_filter = ('marca', 'modelo', 'ativo', 'cor')
    search_fields = ('placa', 'modelo', 'marca', 'renavan')
    ordering = ('marca', 'modelo')
    list_per_page = 20
    date_hierarchy = 'data_ultima_manutencao'
    
    # Removido status_display dos readonly_fields
    readonly_fields = ('idade',)
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('marca', 'modelo', 'ano', 'cor', 'placa', 'renavan')
        }),
        ('Status e Manutenção', {
            'fields': ('ativo', 'data_ultima_manutencao', 'data_proxima_manutencao')
        }),
        ('Outras Informações', {
            'fields': ('observacoes', 'idade'),
            'classes': ('collapse',)
        }),
    )
    
     # Removido actions relacionadas ao status
    actions = ['desativar_carros', 'ativar_carros']
    
    def desativar_carros(self, request, queryset):
        queryset.update(ativo=False)
    desativar_carros.short_description = "Desativar carros selecionados"
    
    def ativar_carros(self, request, queryset):
        queryset.update(ativo=True)
    ativar_carros.short_description = "Ativar carros selecionados"
    
    def marcar_como_disponivel(self, request, queryset):
        queryset.update(status='disponivel')
    marcar_como_disponivel.short_description = "Marcar como Disponível"
    
    def marcar_como_manutencao(self, request, queryset):
        queryset.update(status='manutencao')
    marcar_como_manutencao.short_description = "Marcar como em Manutenção"


@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display = ('id', 'carro_link', 'funcionario', 'data_hora_agenda', 'status_display')
    list_filter = ('status', 'carro__marca', 'data_hora_agenda')
    search_fields = ('carro__placa', 'funcionario', 'id')
    date_hierarchy = 'data_hora_agenda'
    ordering = ('-data_hora_agenda',)
    inlines = [FotoAgendamentoInline, ChecklistCarroInline]
    
    readonly_fields = (
        'duracao_display', 'quilometragem_percorrida', 'carro_link',
        'status_display'
    )
    raw_id_fields = ('carro',)
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': (
                'carro_link', 'funcionario', 'cm', 
                'data_hora_agenda', 'data_hora_devolucao', 'duracao_display'
            )
        }),
        ('Status e Controle', {
            'fields': (
                'status', 'cancelar_agenda', 'motivo_cancelamento', 
                'responsavel', 'assinatura'
            )
        }),
        ('Dados do Veículo', {
            'fields': (
                'km_inicial', 'km_final', 'quilometragem_percorrida',
                'pedagio', 'abastecimento'
            )
        }),
        ('Registros', {
            'fields': ('descricao', 'ocorrencia', 'foto_principal'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['finalizar_agendamento', 'cancelar_agendamento']
    
    def carro_link(self, obj):
        url = reverse("admin:automovel_carro_change", args=[obj.carro.id])
        return format_html('<a href="{}">{}</a>', url, obj.carro)
    carro_link.short_description = 'Veículo'
    
    def status_display(self, obj):
        colors = {
            'agendado': 'blue',
            'em_andamento': 'orange',
            'concluido': 'green',
            'cancelado': 'red'
        }
        return format_html(
            '<span style="color: {};">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def duracao_display(self, obj):
        if obj.data_hora_devolucao and obj.data_hora_agenda:
            duration = obj.data_hora_devolucao - obj.data_hora_agenda
            return str(duration)
        return "Agendamento em andamento"
    duracao_display.short_description = 'Duração'
    
    def quilometragem_percorrida(self, obj):
        if obj.km_final and obj.km_inicial:  # Corrigido de km_initial para km_inicial
            return f"{obj.km_final - obj.km_inicial} km"
        return "Não finalizado"
    quilometragem_percorrida.short_description = 'Km Percorridos'
    
    def finalizar_agendamento(self, request, queryset):
        for agendamento in queryset.filter(status='em_andamento'):
            agendamento.status = 'concluido'
            agendamento.save()
    finalizar_agendamento.short_description = "Finalizar agendamentos selecionados"
    
    def cancelar_agendamento(self, request, queryset):
        queryset.update(
            status='cancelado',
            cancelar_agenda=True,
            motivo_cancelamento="Cancelado pelo admin"
        )
    cancelar_agendamento.short_description = "Cancelar agendamentos selecionados"

@admin.register(Checklist_Carro)
class ChecklistCarroAdmin(admin.ModelAdmin):
    list_display = ('id', 'agendamento', 'tipo', 'agendamento_link', 'tipo_display', 'data_criacao', 'usuario')
    list_filter = ('tipo', 'data_criacao')
    readonly_fields = ('foto_frontal_preview', 'foto_trazeira_preview', 
                      'foto_lado_motorista_preview', 'foto_lado_passageiro_preview')
    search_fields = (
        'id', 'agendamento__carro__placa',
        'agendamento__funcionario', 'usuario__username'
    )
    date_hierarchy = 'data_criacao'
    raw_id_fields = ('agendamento', 'usuario')
    form = ChecklistCarroForm
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('agendamento', 'usuario', 'tipo', 'confirmacao')
        }),
        ('Quilometragem', {
            'fields': ('km_inicial', 'km_final')
        }),
        ('Checklist Frontal', {
            'fields': (
                'revisao_frontal_status', 'foto_frontal', 
                'foto_frontal_preview', 'coordenadas_avaria_frontal'
            )
        }),
        ('Checklist Traseiro', {
            'fields': (
                'revisao_trazeira_status', 'foto_trazeira',
                'foto_trazeira_preview', 'coordenadas_avaria_trazeira'
            )
        }),
        ('Checklist Lateral Motorista', {
            'fields': (
                'revisao_lado_motorista_status', 'foto_lado_motorista',
                'foto_lado_motorista_preview', 'coordenadas_avaria_lado_motorista'
            )
        }),
        ('Checklist Lateral Passageiro', {
            'fields': (
                'revisao_lado_passageiro_status', 'foto_lado_passageiro',
                'foto_lado_passageiro_preview', 'coordenadas_lado_passageiro'
            )
        }),
        ('Observações e Anexos', {
            'fields': ('observacoes_gerais', 'anexo_ocorrencia', 'assinatura'),
            'classes': ('collapse',)
        }),
    )

    class Media:
        js = ('admin/js/checklist_validation.js',)

    def agendamento_link(self, obj):
        if obj.agendamento:
            url = reverse("admin:automovel_agendamento_change", args=[obj.agendamento.id])
            return format_html('<a href="{}">{}</a>', url, obj.agendamento)
        return "-"
    agendamento_link.short_description = 'Agendamento'

    def tipo_display(self, obj):
        color = 'blue' if obj.tipo == 'saida' else 'green'
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_tipo_display()
        )
    tipo_display.short_description = 'Tipo'

    def foto_frontal_preview(self, obj):
        if obj.foto_frontal and hasattr(obj.foto_frontal, 'url'):
            return format_html(
                '<img src="{}" width="200" style="border: 1px solid #ddd; padding: 5px;"/>',
                obj.foto_frontal.url
            )
        return "-"
    foto_frontal_preview.short_description = 'Prévia Foto Frontal'

    def foto_trazeira_preview(self, obj):
        if obj.foto_trazeira and hasattr(obj.foto_trazeira, 'url'):
            return format_html(
                '<img src="{}" width="200" style="border: 1px solid #ddd; padding: 5px;"/>',
                obj.foto_trazeira.url
            )
        return "-"
    foto_trazeira_preview.short_description = 'Prévia Foto Traseira'

    def foto_lado_motorista_preview(self, obj):
        if obj.foto_lado_motorista and hasattr(obj.foto_lado_motorista, 'url'):
            return format_html(
                '<img src="{}" width="200" style="border: 1px solid #ddd; padding: 5px;"/>',
                obj.foto_lado_motorista.url
            )
        return "-"
    foto_lado_motorista_preview.short_description = 'Prévia Lado Motorista'

    def foto_lado_passageiro_preview(self, obj):
        if obj.foto_lado_passageiro and hasattr(obj.foto_lado_passageiro, 'url'):
            return format_html(
                '<img src="{}" width="200" style="border: 1px solid #ddd; padding: 5px;"/>',
                obj.foto_lado_passageiro.url
            )
        return "-"
    foto_lado_passageiro_preview.short_description = 'Prévia Lado Passageiro'

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.confirmacao:
            return [field.name for field in obj._meta.fields if field.name != 'id']
        return super().get_readonly_fields(request, obj)

    def save_model(self, request, obj, form, change):
        """
        Método customizado para salvar o modelo com validação adicional
        """
        try:
            # Validação da quilometragem
            if obj.km_final is not None and obj.km_inicial is not None:
                if obj.km_final < obj.km_inicial:
                    raise ValidationError(
                        {'km_final': 'A quilometragem final não pode ser menor que a inicial'}
                    )
            
            # Validação para checklist de retorno
            if obj.tipo == 'retorno' and obj.km_final is None:
                raise ValidationError(
                    {'km_final': 'Checklist de retorno requer quilometragem final'}
                )
            
            # Validação dos campos de coordenadas
            campos_coordenadas = [
                'coordenadas_avaria_frontal',
                'coordenadas_avaria_trazeira',
                'coordenadas_avaria_lado_motorista',
                'coordenadas_lado_passageiro'
            ]
            
            for campo in campos_coordenadas:
                valor = getattr(obj, campo)
                if valor and not self._validar_coordenadas(valor):
                    raise ValidationError(f'Formato inválido para {campo}')
            
            # Salva normalmente se passar nas validações
            super().save_model(request, obj, form, change)
            
        except ValidationError as e:
            # Adiciona os erros ao formulário para exibição
            for field, messages in e.message_dict.items():
                for message in messages:
                    form.add_error(field, message)
            raise

    def _validar_coordenadas(self, valor):
        """Valida o formato das coordenadas"""
        try:
            if isinstance(valor, str):
                # Verifica se tem o formato x,y
                parts = valor.split(',')
                if len(parts) == 2:
                    float(parts[0])  # tenta converter para float
                    float(parts[1])
                    return True
            return False
        except (ValueError, AttributeError):
            return False