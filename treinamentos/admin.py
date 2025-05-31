from django.contrib import admin
from django.apps import apps
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    TipoTreinamento, 
    Treinamento, 
    TreinamentoDisponivel, 
    Colaborador, 
    TreinamentoColaborador
)

@admin.register(TipoTreinamento)
class TipoTreinamentoAdmin(admin.ModelAdmin):
    list_display = (
        'nome', 
        'modalidade_formatada', 
        'area_formatada', 
        'validade_meses', 
        'certificado', 
        'ativo'
    )
    list_filter = ('modalidade', 'area', 'ativo')
    search_fields = ('nome', 'descricao')
    list_editable = ('ativo',)
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome', 'modalidade', 'area', 'descricao')
        }),
        ('Configurações', {
            'fields': ('validade_meses', 'certificado', 'ativo')
        }),
    )
    readonly_fields = ('data_cadastro', 'data_atualizacao')

    def modalidade_formatada(self, obj):
        return obj.modalidade_formatada
    modalidade_formatada.short_description = 'Modalidade'

    def area_formatada(self, obj):
        return obj.area_formatada
    area_formatada.short_description = 'Área'


@admin.register(Treinamento)
class TreinamentoAdmin(admin.ModelAdmin):
    list_display = (
        'nome',
        'tipo_treinamento',
        'data_inicio_formatada',
        'data_vencimento_formatada',
        'status_formatado',
        'local',
        'custo_total_estimado'
    )
    list_filter = ('tipo_treinamento', 'status')
    search_fields = ('nome', 'descricao', 'local')
    date_hierarchy = 'data_inicio'
    raw_id_fields = ('tipo_treinamento',)
    list_select_related = ('tipo_treinamento',)
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('tipo_treinamento', 'nome', 'descricao', 'status')
        }),
        ('Datas e Horários', {
            'fields': ('data_inicio', 'data_vencimento', 'duracao', 'hxh')
        }),
        ('Organização', {
            'fields': ('funcionario', 'cm', 'palestrante', 'local')
        }),
        ('Financeiro', {
            'fields': ('custo', 'participantes_previstos')
        }),
    )

    def data_inicio_formatada(self, obj):
        return obj.data_inicio.strftime('%d/%m/%Y %H:%M')
    data_inicio_formatada.short_description = 'Início'
    data_inicio_formatada.admin_order_field = 'data_inicio'

    def data_vencimento_formatada(self, obj):
        return obj.data_vencimento.strftime('%d/%m/%Y')
    data_vencimento_formatada.short_description = 'Vencimento'
    data_vencimento_formatada.admin_order_field = 'data_vencimento'

    def status_formatado(self, obj):
        status_map = {
            'P': 'secondary',
            'A': 'info',
            'E': 'warning',
            'C': 'success',
            'X': 'danger'
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            status_map.get(obj.status, 'secondary'),
            obj.status_formatado
        )
    status_formatado.short_description = 'Status'


@admin.register(TreinamentoDisponivel)
class TreinamentoDisponivelAdmin(admin.ModelAdmin):
    list_display = (
        'codigo',
        'nome',
        'modalidade_display',
        'tipo_display',
        'carga_horaria',
        'validade_meses',
        'ativo'
    )
    list_filter = ('modalidade', 'tipo', 'ativo')
    search_fields = ('codigo', 'nome', 'descricao')
    list_editable = ('ativo',)
    ordering = ('nome',)

    def modalidade_display(self, obj):
        return dict(obj.MODALIDADE_CHOICES).get(obj.modalidade, obj.modalidade)
    modalidade_display.short_description = 'Modalidade'

    def tipo_display(self, obj):
        return dict(obj.TIPO_CHOICES).get(obj.tipo, obj.tipo)
    tipo_display.short_description = 'Tipo'


@admin.register(Colaborador)
class ColaboradorAdmin(admin.ModelAdmin):
    list_display = (
        'matricula',
        'nome_completo',
        'departamento',
        'cargo',
        'data_admissao_formatada',
        'ativo',
        'link_para_user'
    )
    list_filter = ('departamento', 'cargo', 'ativo')
    search_fields = ('matricula', 'user__first_name', 'user__last_name')
    raw_id_fields = ('user',)
    list_editable = ('ativo',)
    fieldsets = (
        ('Informações do Usuário', {
            'fields': ('user',)
        }),
        ('Informações do Colaborador', {
            'fields': ('matricula', 'departamento', 'cargo', 'data_admissao', 'ativo')
        }),
    )

    def nome_completo(self, obj):
        return obj.user.get_full_name()
    nome_completo.short_description = 'Nome'
    nome_completo.admin_order_field = 'user__last_name'

    def data_admissao_formatada(self, obj):
        return obj.data_admissao.strftime('%d/%m/%Y')
    data_admissao_formatada.short_description = 'Admissão'
    data_admissao_formatada.admin_order_field = 'data_admissao'

    def link_para_user(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html('<a href="{}">Editar Usuário</a>', url)
    link_para_user.short_description = 'Usuário'


@admin.register(TreinamentoColaborador)
class TreinamentoColaboradorAdmin(admin.ModelAdmin):
    list_display = (
        'colaborador',
        'treinamento',
        'data_realizacao_formatada',
        'data_validade_formatada',
        'dias_para_vencer',
        'status_colorido',
        'link_certificado'
    )
    list_filter = ('status', 'treinamento__tipo_treinamento')
    search_fields = (
        'colaborador__user__first_name',
        'colaborador__user__last_name',
        'colaborador__matricula',
        'treinamento__nome'
    )
    date_hierarchy = 'data_validade'
    raw_id_fields = ('colaborador', 'treinamento')
    list_select_related = ('colaborador__user', 'treinamento')

    def data_realizacao_formatada(self, obj):
        return obj.data_realizacao.strftime('%d/%m/%Y')
    data_realizacao_formatada.short_description = 'Realização'
    data_realizacao_formatada.admin_order_field = 'data_realizacao'

    def data_validade_formatada(self, obj):
        return obj.data_validade.strftime('%d/%m/%Y')
    data_validade_formatada.short_description = 'Validade'
    data_validade_formatada.admin_order_field = 'data_validade'

    def status_colorido(self, obj):
        status_map = {
            'ativo': 'success',
            'proximo': 'warning',
            'expirado': 'danger'
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            status_map.get(obj.status, 'secondary'),
            obj.get_status_display()
        )
    status_colorido.short_description = 'Status'

    def link_certificado(self, obj):
        if obj.certificado:
            return format_html(
                '<a href="{}" target="_blank">Ver Certificado</a>',
                obj.certificado.url
            )
        return "-"
    link_certificado.short_description = 'Certificado'