from django.contrib import admin
from django.utils.html import format_html
from .models import EPI, FichaEPI, ItemEPI
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

@admin.register(EPI)
class EPIAdmin(admin.ModelAdmin):
    list_display = (
        'nome',
        'tipo_formatado',
        'certificado',
        'estoque_status',
        'vida_util',
        'estoque_minimo',
        'ativo_badge'
    )
    
    list_filter = (
        'tipo',
        'ativo',
        'unidade',
    )
    
    search_fields = (
        'nome',
        'certificado',
        'descricao',
    )
    
    list_editable = (
        'estoque_minimo',
    )
    
    readonly_fields = (
        'data_cadastro',
        'data_atualizacao',
        'precisa_reponer',
    )
    
    fieldsets = (
        (None, {
            'fields': (
                'nome',
                'descricao',
                'tipo',
            )
        }),
        (_('Certificação'), {
            'fields': (
                'certificado',
                'vida_util',
            )
        }),
        (_('Estoque'), {
            'fields': (
                'unidade',
                'estoque_minimo',
                'estoque_atual',
                'precisa_reponer',
            )
        }),
        (_('Status'), {
            'fields': (
                'ativo',
            )
        }),
        (_('Auditoria'), {
            'fields': (
                'data_cadastro',
                'data_atualizacao',
            ),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'ativar_epis',
        'desativar_epis',
        'repor_estoque_minimo',
    ]

    def tipo_formatado(self, obj):
        return dict(EPI.TIPO_EPI_CHOICES).get(obj.tipo, obj.tipo)
    tipo_formatado.short_description = _('Tipo')
    
    def estoque_status(self, obj):
        if obj.precisa_repor():
            color = 'red'
            text = f"{obj.estoque_atual}/{obj.estoque_minimo}"
        else:
            color = 'green'
            text = f"{obj.estoque_atual}"
        return format_html(
            '<span style="color: white; background-color: {}; padding: 2px 6px; border-radius: 10px;">{}</span>',
            color, text
        )
    estoque_status.short_description = _('Estoque')
    estoque_status.admin_order_field = 'estoque_atual'
    
    def ativo_badge(self, obj):
        color = 'green' if obj.ativo else 'red'
        text = _('Ativo') if obj.ativo else _('Inativo')
        return format_html(
            '<span style="color: white; background-color: {}; padding: 2px 6px; border-radius: 10px;">{}</span>',
            color, text
        )
    ativo_badge.short_description = _('Status')
    ativo_badge.admin_order_field = 'ativo'
    
    def precisa_reponer(self, obj):
        return obj.precisa_repor()
    precisa_reponer.boolean = True
    precisa_reponer.short_description = _('Precisa repor?')
    
    def ativar_epis(self, request, queryset):
        updated = queryset.update(ativo=True)
        self.message_user(request, _('%d EPIs ativados') % updated)
    ativar_epis.short_description = _('Ativar EPIs selecionados')
    
    def desativar_epis(self, request, queryset):
        updated = queryset.update(ativo=False)
        self.message_user(request, _('%d EPIs desativados') % updated)
    desativar_epis.short_description = _('Desativar EPIs selecionados')
    
    def repor_estoque_minimo(self, request, queryset):
        for epi in queryset:
            epi.estoque_atual = epi.estoque_minimo
            epi.save()
        self.message_user(request, _('Estoque reposto para os EPIs selecionados'))
    repor_estoque_minimo.short_description = _('Repor estoque mínimo')

@admin.register(FichaEPI)
class FichaEPIAdmin(admin.ModelAdmin):
    list_display = (
        'empregado_link',
        'cargo',
        'registro',
        'status_badge',
        'admissao_formatada',
        'total_itens',
        'assinatura_preview',
    )
    
    list_filter = (
        'status',
        'cargo',
        'contrato',
    )
    
    search_fields = (
        'empregado__first_name',
        'empregado__last_name',
        'registro',
        'contrato',
    )
    
    raw_id_fields = ('empregado',)
    
    date_hierarchy = 'admissao'
    
    readonly_fields = (
        'criado_em',
        'atualizado_em',
        'total_itens',
    )
    
    fieldsets = (
        (_('Funcionário'), {
            'fields': (
                'empregado',
                'cargo',
                'registro',
                'status',
            )
        }),
        (_('Contrato'), {
            'fields': (
                'admissao',
                'demissao',
                'contrato',
            )
        }),
        (_('Documento'), {
            'fields': (
                'local_data',
                'assinatura',
                'total_itens',
            )
        }),
        (_('Auditoria'), {
            'fields': (
                'criado_em',
                'atualizado_em',
            ),
            'classes': ('collapse',)
        }),
    )
    
    def empregado_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.empregado.id])
        return format_html('<a href="{}">{}</a>', url, obj.empregado.get_full_name())
    empregado_link.short_description = _('Empregado')
    empregado_link.admin_order_field = 'empregado__first_name'
    
    def status_badge(self, obj):
        colors = {
            'ATIVO': 'green',
            'INATIVO': 'red',
            'AFASTADO': 'orange',
        }
        return format_html(
            '<span style="color: white; background-color: {}; padding: 2px 6px; border-radius: 10px;">{}</span>',
            colors.get(obj.status, 'gray'), obj.get_status_display()
        )
    status_badge.short_description = _('Status')
    status_badge.admin_order_field = 'status'
    
    def admissao_formatada(self, obj):
        return obj.admissao.strftime('%d/%m/%Y')
    admissao_formatada.short_description = _('Admissão')
    admissao_formatada.admin_order_field = 'admissao'
    
    def total_itens(self, obj):
        return obj.itens.count()
    total_itens.short_description = _('Itens')
    
    def assinatura_preview(self, obj):
        if obj.assinatura:
            return format_html('<img src="{}" width="50" height="auto" />', obj.assinatura.url)
        return "-"
    assinatura_preview.short_description = _('Assinatura')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('empregado')

@admin.register(ItemEPI)
class ItemEPIAdmin(admin.ModelAdmin):
    list_display = (
        'ficha_link',
        'epi_link',
        'quantidade',
        'data_recebimento_formatada',
        'status_badge',
        'validade_formatada',
    )
    
    list_filter = (
        'epi',
        'epi__tipo',
        'data_recebimento',
    )
    
    search_fields = (
        'ficha__empregado__first_name',
        'ficha__empregado__last_name',
        'ficha__registro',
        'epi__nome',
    )
    
    raw_id_fields = ('ficha', 'epi')
    
    date_hierarchy = 'data_recebimento'
    
    readonly_fields = (
        'criado_em',
    )
    
    def ficha_link(self, obj):
        url = reverse('admin:epi_fichaepi_change', args=[obj.ficha.id])
        return format_html('<a href="{}">{}</a>', url, obj.ficha)
    ficha_link.short_description = _('Ficha')
    ficha_link.admin_order_field = 'ficha__empregado__first_name'
    
    def epi_link(self, obj):
        url = reverse('admin:epi_epi_change', args=[obj.epi.id])
        return format_html('<a href="{}">{}</a>', url, obj.epi.nome)
    epi_link.short_description = _('EPI')
    epi_link.admin_order_field = 'epi__nome'
    
    def data_recebimento_formatada(self, obj):
        return obj.data_recebimento.strftime('%d/%m/%Y')
    data_recebimento_formatada.short_description = _('Recebimento')
    data_recebimento_formatada.admin_order_field = 'data_recebimento'
    
    def validade_formatada(self, obj):
        if obj.data_validade:
            return obj.data_validade.strftime('%d/%m/%Y')
        return "-"
    validade_formatada.short_description = _('Validade')
    validade_formatada.admin_order_field = 'data_validade'
    
    def status_badge(self, obj):
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
    status_badge.short_description = _('Status')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('ficha__empregado', 'epi')
