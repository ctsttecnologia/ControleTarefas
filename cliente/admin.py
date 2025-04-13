
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import Cliente, ClienteCliente

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = (
        'nome', 
        'cnpj_formatado', 
        'logradouro_link', 
        'tempo_contrato_meses', 
        'status_badge',
        'data_de_inicio'
    )
    list_filter = (
        'estatus', 
        'data_de_inicio', 
        ('logradouro', admin.RelatedOnlyFieldListFilter)
    )
    search_fields = (
        'nome', 
        'razao_social', 
        'cnpj', 
        'contrato',
        'logradouro__endereco'
    )
    raw_id_fields = ('logradouro',)
    list_editable = ('data_de_inicio',)
    date_hierarchy = 'data_de_inicio'
    readonly_fields = (
        'data_cadastro', 
        'data_atualizacao', 
        'cnpj_formatado',
        'tempo_contrato_meses'
    )
    actions = ['ativar_clientes', 'desativar_clientes']
    fieldsets = (
        (_('Informações Básicas'), {
            'fields': (
                'nome', 
                'razao_social',
                'cnpj',
                'cnpj_formatado',
                'contrato'
            )
        }),
        (_('Endereço'), {
            'fields': ('logradouro',)
        }),
        (_('Contato'), {
            'fields': ('telefone',)
        }),
        (_('Datas'), {
            'fields': (
                'data_de_inicio',
                'tempo_contrato_meses',
                'estatus'
            )
        }),
        (_('Auditoria'), {
            'fields': (
                'data_cadastro',
                'data_atualizacao'
            ),
            'classes': ('collapse',)
        }),
    )

    def cnpj_formatado(self, obj):
        return obj.cnpj_formatado
    cnpj_formatado.short_description = _('CNPJ Formatado')

    def tempo_contrato_meses(self, obj):
        return f"{obj.tempo_contrato} meses"
    tempo_contrato_meses.short_description = _('Tempo de Contrato')

    def status_badge(self, obj):
        color = 'green' if obj.estatus else 'red'
        text = _('Ativo') if obj.estatus else _('Inativo')
        return format_html(
            '<span style="color: white; background-color: {}; padding: 3px 8px; border-radius: 10px;">{}</span>',
            color, text
        )
    status_badge.short_description = _('Status')
    status_badge.admin_order_field = 'estatus'

    def logradouro_link(self, obj):
        if obj.logradouro:
            url = f"/admin/logradouro/logradouro/{obj.logradouro.id}/change/"
            return format_html('<a href="{}">{}</a>', url, obj.logradouro)
        return "-"
    logradouro_link.short_description = _('Endereço')
    logradouro_link.allow_tags = True

    def ativar_clientes(self, request, queryset):
        updated = queryset.update(estatus=True)
        self.message_user(request, _('{} clientes ativados com sucesso.').format(updated))
    ativar_clientes.short_description = _('Ativar clientes selecionados')

    def desativar_clientes(self, request, queryset):
        updated = queryset.update(estatus=False)
        self.message_user(request, _('{} clientes desativados com sucesso.').format(updated))
    desativar_clientes.short_description = _('Desativar clientes selecionados')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('logradouro')

@admin.register(ClienteCliente)
class ClienteClienteAdmin(admin.ModelAdmin):
    list_display = (
        'nome_completo',
        'cliente_link',
        'codigo',
        'status_badge',
        'data_criacao', 'ativa'
    )
    list_filter = (
        'ativa',
        'cliente',
        'data_criacao'
    )
    search_fields = (
        'nome',
        'codigo',
        'cliente__nome',
        'cliente__razao_social'
    )
    raw_id_fields = ('cliente',)
    list_editable = ('codigo', 'ativa')
    date_hierarchy = 'data_criacao'
    readonly_fields = ('data_criacao', 'nome_completo')
    actions = ['ativar_unidades', 'desativar_unidades']

    def nome_completo(self, obj):
        return obj.nome_completo
    nome_completo.short_description = _('Unidade')

    def cliente_link(self, obj):
        url = f"/admin/clientes/cliente/{obj.cliente.id}/change/"
        return format_html('<a href="{}">{}</a>', url, obj.cliente.nome)
    cliente_link.short_description = _('Cliente Matriz')
    cliente_link.allow_tags = True

    def status_badge(self, obj):
        color = 'green' if obj.ativa else 'red'
        text = _('Ativa') if obj.ativa else _('Inativa')
        return format_html(
            '<span style="color: white; background-color: {}; padding: 3px 8px; border-radius: 10px;">{}</span>',
            color, text
        )
    status_badge.short_description = _('Status')
    status_badge.admin_order_field = 'ativa'

    def ativar_unidades(self, request, queryset):
        updated = queryset.update(ativa=True)
        self.message_user(request, _('{} unidades ativadas com sucesso.').format(updated))
    ativar_unidades.short_description = _('Ativar unidades selecionadas')

    def desativar_unidades(self, request, queryset):
        updated = queryset.update(ativa=False)
        self.message_user(request, _('{} unidades desativadas com sucesso.').format(updated))
    desativar_unidades.short_description = _('Desativar unidades selecionadas')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('cliente')

