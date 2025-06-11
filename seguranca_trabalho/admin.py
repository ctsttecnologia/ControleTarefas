from django.contrib import admin
from django.utils.html import format_html
from .models import (EPIEquipamentoSeguranca)
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from .models import ItemEquipamentoSeguranca

@admin.register(EPIEquipamentoSeguranca)
class EquipamentosSegurancaAdmin(admin.ModelAdmin):
    list_display = (
        'nome_equipamento',
        'tipo_formatado',
        'codigo_ca',
        'estoque_status',
        'estoque_minimo',
        'validade_status',
        'status_badge',
        'acoes_personalizadas',
        'quantidade_estoque',
        
    )
    
    list_filter = (
        'tipo',
        'ativo',
    )
    
    search_fields = (
        'nome_equipamento',
        'codigo_ca',
        'descricao'
    )
    
    list_editable = (
        'quantidade_estoque',
        'estoque_minimo',
    )
    
    readonly_fields = (
        'data_cadastro',
        'data_atualizacao',
        'status_formatado',
        'tipo_formatado',
    )
    
    fieldsets = (
        (_('Identificação'), {
            'fields': (
                'nome_equipamento',
                'tipo',
                'codigo_ca',
                'descricao'
            )
        }),
        (_('Estoque'), {
            'fields': (
                'quantidade_estoque',
                'estoque_minimo',
                'precisa_repor'
            )
        }),
        (_('Validade'), {
            'fields': (
                'data_validade',
                'validade_status'
            )
        }),
        (_('Status'), {
            'fields': (
                'ativo',
                'status_formatado'
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
    
    actions = [
        'ativar_equipamentos',
        'desativar_equipamentos',
        'repor_estoque_minimo',
    ]
    
    # Métodos de exibição
    def tipo_formatado(self, obj):
        return obj.tipo_formatado
    tipo_formatado.short_description = _('Tipo')
    
    def estoque_status(self, obj):
        if obj.precisa_repor:
            color = 'red'
            text = f"{obj.quantidade_estoque}/{obj.estoque_minimo}"
        else:
            color = 'green'
            text = f"{obj.quantidade_estoque}"
        return format_html(
            '<span style="color: white; background-color: {}; padding: 2px 6px; border-radius: 10px;">{}</span>',
            color, text
        )
    estoque_status.short_description = _('Estoque')
    estoque_status.admin_order_field = 'quantidade_estoque'
    
    def validade_status(self, obj):
        if obj.data_validade:
            if obj.data_validade < timezone.now().date():
                color = 'red'
                status = _('Vencido')
            else:
                color = 'blue'
                status = obj.data_validade.strftime('%d/%m/%Y')
            return format_html(
                '<span style="color: white; background-color: {}; padding: 2px 6px; border-radius: 10px;">{}</span>',
                color, status
            )
        return _("Não informado")
    validade_status.short_description = _('Validade')
    
    def status_badge(self, obj):
        color = 'green' if obj.ativo == 1 else 'red'
        text = _('Ativo') if obj.ativo == 1 else _('Inativo')
        return format_html(
            '<span style="color: white; background-color: {}; padding: 2px 6px; border-radius: 10px;">{}</span>',
            color, text
        )
    status_badge.short_description = _('Status')
    status_badge.admin_order_field = 'ativo'
    
    def acoes_personalizadas(self, obj):
        return format_html(
            '<a href="/admin/equipamentos/itensequipamentoseguranca/?equipamento__id__exact={}" class="button">Ver Entregas</a>',
            obj.id
        )
    acoes_personalizadas.short_description = _('Ações')
    
    # Ações personalizadas
    def ativar_equipamentos(self, request, queryset):
        updated = queryset.update(ativo=1)
        self.message_user(request, _('%d equipamentos ativados') % updated)
    ativar_equipamentos.short_description = _('Ativar equipamentos selecionados')
    
    def desativar_equipamentos(self, request, queryset):
        updated = queryset.update(ativo=0)
        self.message_user(request, _('%d equipamentos desativados') % updated)
    desativar_equipamentos.short_description = _('Desativar equipamentos selecionados')
    
    def repor_estoque_minimo(self, request, queryset):
        for equipamento in queryset:
            equipamento.quantidade_estoque = equipamento.estoque_minimo
            equipamento.save()
        self.message_user(request, _('Estoque reposto para os equipamentos selecionados'))
    repor_estoque_minimo.short_description = _('Repor estoque mínimo')


@admin.register(ItemEquipamentoSeguranca)
class ItemEquipamentoSegurancaAdmin(admin.ModelAdmin):
    list_display = (
        'equipamento',
        'ficha_link',
        'quantidade',
        'data_entrega_formatada',
        'status_entrega',
        'responsavel_entrega'
    )
    
    list_filter = (
        'equipamento__tipo',
        'data_entrega',
    )
    
    search_fields = (
        'equipamento__nome_equipamento',
        'ficha__empregado__first_name',
        'ficha__empregado__last_name',
    )
    
    raw_id_fields = ('ficha', 'equipamento')
    
    date_hierarchy = 'data_entrega'
    
    def ficha_link(self, obj):
        url = reverse('admin:epi_fichaepi_change', args=[obj.ficha.id])
        return format_html('<a href="{}">{}</a>', url, obj.ficha)
    ficha_link.short_description = _('Ficha EPI')
    
    def data_entrega_formatada(self, obj):
        return obj.data_entrega.strftime('%d/%m/%Y')
    data_entrega_formatada.short_description = _('Data de Entrega')
    
    def status_entrega(self, obj):
        if obj.data_devolucao:
            color = 'gray'
            text = _('Devolvido')
        else:
            color = 'blue'
            text = _('Ativo')
        return format_html(
            '<span style="color: white; background-color: {}; padding: 2px 6px; border-radius: 10px;">{}</span>',
            color, text
        )
    status_entrega.short_description = _('Status')

    