from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import Cliente
from core.admin import FilialAdminMixin

@admin.register(Cliente)
class ClienteAdmin(FilialAdminMixin, admin.ModelAdmin):
    list_display = (
        'nome',
        'cnpj_formatado',
        'contrato',
        'filial',
        'logradouro_link',
        'status_badge',
    )
    list_filter = ('estatus', 'filial', 'logradouro__cidade', 'data_de_inicio')
    search_fields = ('nome', 'razao_social', 'cnpj', 'contrato')
    readonly_fields = ('data_cadastro', 'data_atualizacao')
    actions = ['ativar_clientes', 'desativar_clientes']
    
    fieldsets = (
        (None, {
            'fields': ('nome', 'razao_social', 'estatus')
        }),
        (_('Contrato e Documentos'), {
            'fields': ('cnpj', 'contrato', 'inscricao_estadual', 'inscricao_municipal')
        }),
        (_('Localização e Contato'), {
            'fields': ('logradouro', 'telefone', 'email')
        }),
        (_('Datas Importantes'), {
            'fields': ('data_de_inicio', 'data_encerramento')
        }),
        (_('Auditoria'), {
            'fields': ('data_cadastro', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('logradouro')

    @admin.display(description=_('CNPJ'), ordering='cnpj')
    def cnpj_formatado(self, obj):
        return obj.cnpj_formatado

    @admin.display(description=_('Status'), ordering='estatus')
    def status_badge(self, obj):
        color = 'green' if obj.estatus else 'red'
        text = _('Ativo') if obj.estatus else _('Inativo')
        return format_html(
            '<span style="color: white; background-color: {}; padding: 3px 8px; border-radius: 5px;">{}</span>',
            color, text
        )

    @admin.display(description=_('Endereço'))
    def logradouro_link(self, obj):
        if obj.logradouro:
            url = reverse("admin:logradouro_logradouro_change", args=[obj.logradouro.pk])
            return format_html('<a href="{}">{}</a>', url, obj.logradouro)
        return "—"

    @admin.action(description=_('Ativar clientes selecionados'))
    def ativar_clientes(self, request, queryset):
        updated = queryset.update(estatus=True)
        self.message_user(request, _(f'{updated} clientes foram ativados com sucesso.'))

    @admin.action(description=_('Desativar clientes selecionados'))
    def desativar_clientes(self, request, queryset):
        updated = queryset.update(estatus=False)
        self.message_user(request, _(f'{updated} clientes foram desativados com sucesso.'))