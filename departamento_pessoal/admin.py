from django.contrib import admin
from django.utils.html import format_html
from .models import (Documentos, Cbos, Cargos,
    Departamentos, Admissao, Funcionarios
)
from django.utils.translation import gettext_lazy as _
from django.urls import reverse


@admin.register(Documentos)
class DocumentosAdmin(admin.ModelAdmin):
    list_display = ('cpf_formatado', 'rg', 'pis', 'ctps', 'funcionario', 'nome', 'sigla')
    search_fields = ('cpf', 'rg', 'pis', 'ctps', 'funcionario__nome')
    readonly_fields = ('cpf_formatado',)
    list_select_related = ( 'admissao__cargo', 'admissao__departamento', 'documentos') 
    list_per_page = 20
    raw_id_fields = ('funcionario',)

    def cpf_formatado(self, obj):
        return obj.cpf_formatado
    cpf_formatado.short_description = _('CPF')

@admin.register(Cbos)
class CbosAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'descricao', 'total_cargos')
    search_fields = ('codigo', 'descricao')
    list_per_page = 20

    def total_cargos(self, obj):
        return obj.cargos.count()
    total_cargos.short_description = _('Cargos Associados')

@admin.register(Cargos)
class CargosAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cbo_link', 'salario_base', 'funcionarios_ativos_count', 'ativo')
    list_filter = ('ativo', 'cbo')
    search_fields = ('nome', 'descricao')
    raw_id_fields = ('cbo',)
    actions = ['ativar_cargos', 'desativar_cargos']
    list_per_page = 20

    def cbo_link(self, obj):
        url = f"/admin/rh/cbos/{obj.cbo.id}/change/"
        return format_html('<a href="{}">{}</a>', url, obj.cbo.codigo)
    cbo_link.short_description = _('CBO')

    def funcionarios_ativos_count(self, obj):
        return obj.funcionarios_ativos()
    funcionarios_ativos_count.short_description = _('Funcionários Ativos')

    def ativar_cargos(self, request, queryset):
        updated = queryset.update(ativo=True)
        self.message_user(request, _('%d cargos ativados') % updated)
    ativar_cargos.short_description = _('Ativar cargos selecionados')

    def desativar_cargos(self, request, queryset):
        updated = queryset.update(ativo=False)
        self.message_user(request, _('%d cargos desativados') % updated)
    desativar_cargos.short_description = _('Desativar cargos selecionados')


class AdmissaoAdmin(admin.ModelAdmin):
    list_display = ('matricula', 'funcionario', 'cargo', 'data_admissao', 'salario_formatado')
    list_filter = ('cargo', 'departamento', 'tipo_contrato')
    search_fields = ('matricula', 'funcionario__nome')
    readonly_fields = ('tempo_empresa_display',)
    fieldsets = (
        (None, {
            'fields': ('funcionario', 'matricula', 'data_admissao', 'data_demissao')
        }),
        ('Cargo e Departamento', {
            'fields': ('cargo', 'departamento', 'tipo_contrato')
        }),
        ('Remuneração', {
            'fields': ('salario',)
        }),
        ('Horários', {
            'fields': ('hora_entrada', 'hora_saida', 'dias_semana')
        }),
    )

    def salario_formatado(self, obj):
        return f"R$ {obj.salario:,.2f}"
    salario_formatado.short_description = 'Salário'

    def tempo_empresa_display(self, obj):
        return f"{obj.tempo_empresa} meses"
    tempo_empresa_display.short_description = 'Tempo na Empresa'


@admin.register(Funcionarios)
class FuncionariosAdmin(admin.ModelAdmin):
    list_display = (
        'nome', 
        'idade', 
        'sexo', 
        'status_badge', 
        'cargo_atual', 
        'departamento_atual',
        'data_admissao'
    )
    list_filter = ('estatus', 'sexo', 'admissao__cargo', 'admissao__departamento')
    search_fields = ('nome', 'documentos__cpf', 'email')
    raw_id_fields = ('logradouro',)
    readonly_fields = ('idade', 'status_formatado')
    date_hierarchy = ('admissao__data_admissao')
    actions = ['promover_funcionarios']
    list_per_page = 50

    def status_formatado(self, obj):
        return "Ativo" if obj.ativo else "Inativo"
    status_formatado.short_description = 'Status'

    def status_badge(self, obj):
        colors = {1: 'green', 2: 'orange', 3: 'red', 4: 'blue'}
        return format_html(
            '<span style="color: white; background-color: {}; padding: 3px 8px; border-radius: 10px;">{}</span>',
            colors.get(obj.estatus, 'gray'),
            obj.get_estatus_display()
        )
    status_badge.short_description = _('Status')
    status_badge.admin_order_field = 'estatus'

    def cargo_atual(self, obj):
        if hasattr(obj, 'admissao'):
            return obj.admissao.cargo.nome
        return "-"
    cargo_atual.short_description = _('Cargo')

    def departamento_atual(self, obj):
        if hasattr(obj, 'admissao'):
            return obj.admissao.departamento.nome
        return "-"
    departamento_atual.short_description = _('Departamento')

    def data_admissao(self, obj):
        if hasattr(obj, 'admissao'):
            return obj.admissao.data_admissao
        return "-"
    data_admissao.short_description = _('Admitido em')
    data_admissao.admin_order_field = 'admissao__data_admissao'

    def promover_funcionarios(self, request, queryset):
        # Implementação da ação de promoção
        pass
    promover_funcionarios.short_description = _('Promover funcionários selecionados')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'admissao__cargo', 
            'admissao__departamento',
            'documentos'
        )
@admin.register(Departamentos)
class DepartamentosAdmin(admin.ModelAdmin):
    list_display = (
        'nome_completo',
        'sigla',
        'tipo_formatado',
        'status_badge',
        'data_criacao_formatada', 
        'tipo'
    )
    
    list_filter = (
        'tipo',
        'ativo',
        'data_criacao',
    )
    
    search_fields = (
        'nome',
        'sigla',
        'centro_custo',
    )
    
    list_editable = ('sigla', 'tipo')
    
    date_hierarchy = 'data_criacao'
    
    readonly_fields = (
        'data_atualizacao',
        'data_criacao_formatada'
    )
    
    actions = [
        'ativar_departamentos',
        'desativar_departamentos',
        'migrar_para_tecnologia'
    ]
    
    fieldsets = (
        (_('Identificação'), {
            'fields': (
                'nome',
                'sigla',
                'tipo',
                'centro_custo'
            )
        }),
        (_('Status'), {
            'fields': (
                'ativo',
            )
        }),
        (_('Datas'), {
            'fields': (
                'data_criacao',
                'data_atualizacao',
            ),
            'classes': ('collapse',)
        }),
    )

    # Métodos de exibição
    def nome_completo(self, obj):
        return obj.nome
    nome_completo.short_description = _('Departamento')
    nome_completo.admin_order_field = 'nome'

    def tipo_formatado(self, obj):
        tipo_dict = dict(self.model.TIPO_DEPARTAMENTO_CHOICES)
        return tipo_dict.get(obj.tipo, obj.tipo)
    tipo_formatado.short_description = _('Tipo')

    def status_badge(self, obj):
        color = 'green' if obj.ativo else 'red'
        text = _('Ativo') if obj.ativo else _('Inativo')
        return format_html(
            '<span style="color: white; background-color: {}; padding: 3px 8px; border-radius: 10px;">{}</span>',
            color, text
        )
    status_badge.short_description = _('Status')
    status_badge.admin_order_field = 'ativo'

    def total_funcionarios_link(self, obj):
        count = obj.total_funcionarios
        url = (
            reverse('admin:funcionarios_funcionarios_changelist') +
            f'?admissao__departamento__id__exact={obj.id}'
        )
        return format_html(
            '<a href="{}">{} funcionário(s)</a>',
            url, count
        )
    total_funcionarios_link.short_description = _('Funcionários')

    def data_criacao_formatada(self, obj):
        return obj.data_criacao.strftime('%d/%m/%Y')
    data_criacao_formatada.short_description = _('Criado em')
    data_criacao_formatada.admin_order_field = 'data_criacao'

    # Ações personalizadas
    def ativar_departamentos(self, request, queryset):
        updated = queryset.update(ativo=True)
        self.message_user(
            request,
            _('{} departamentos ativados com sucesso.').format(updated)
        )
    ativar_departamentos.short_description = _('Ativar departamentos selecionados')

    def desativar_departamentos(self, request, queryset):
        updated = queryset.update(ativo=False)
        self.message_user(
            request,
            _('{} departamentos desativados com sucesso.').format(updated)
        )
    desativar_departamentos.short_description = _('Desativar departamentos selecionados')

    def migrar_para_tecnologia(self, request, queryset):
        updated = queryset.update(tipo='TEC')
        self.message_user(
            request,
            _('{} departamentos migrados para Tecnologia.').format(updated)
        )
    migrar_para_tecnologia.short_description = _('Migrar para Tecnologia')



