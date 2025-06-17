from datetime import timezone
from django.contrib import admin
from .models import Tarefas
from django.utils.html import format_html
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import Tarefas, Comentario, HistoricoStatus
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from usuario.models import Usuario



class ComentarioInline(admin.StackedInline):
    model = Comentario
    extra = 0
    readonly_fields = ('autor', 'criado_em', 'atualizado_em')
    fields = ('autor', 'texto', 'anexo', 'criado_em')
    classes = ('collapse',)

class HistoricoStatusInline(admin.TabularInline):
    model = HistoricoStatus
    extra = 0
    readonly_fields = ('status_anterior', 'novo_status', 'alterado_por', 'data_alteracao')
    fields = ('data_alteracao', 'status_anterior', 'novo_status', 'alterado_por', 'observacao')
    classes = ('collapse',)

@admin.register(Tarefas)
class TarefasAdmin(admin.ModelAdmin):
    list_display = (
        'titulo',
        'usuario_link',
        'responsavel_link',
        'status_badge',
        'prioridade',
        'dias_restantes_display',
        'prazo_formatado',
        'progresso_bar',
        'atrasada_flag',
        'progresso_display',  # Usando método customizado
        'dias_lembrete'
    )
    # Adicionando novos campos para edição rápida
    list_editable = ('prioridade', 'dias_lembrete')
    
    list_filter = (
        'status',
        'prioridade',
        'usuario',
        'responsavel',
        'projeto',
        'data_inicio',
        'prazo'
    )
    
    search_fields = (
        'titulo',
        'descricao',
        'usuario__username',
        'responsavel__username',
        'projeto'
    )
    
    # Campos readonly devem ser campos reais ou métodos do admin
    readonly_fields = (
        'data_criacao',
        'data_atualizacao',
        'concluida_em',
        'atrasada_flag_admin',
        'progresso_display'  # Método customizado
    )
    
    fieldsets = (
        (_('Informações Básicas'), {
            'fields': (
                'titulo',
                'descricao',
                'projeto'
            )
        }),
        (_('Responsáveis'), {
            'fields': (
                'usuario',
                'responsavel'
            )
        }),
        (_('Tempo e Datas'), {
            'fields': (
                'data_inicio',
                'prazo',
                'duracao_prevista',
                'tempo_gasto',
                'progresso'
            )
        }),
        (_('Status'), {
            'fields': (
                'status',
                'prioridade',
                'atrasada_flag_admin',
                'concluida_em'
            )
        }),
        (_('Auditoria'), {
            'fields': (
                'data_criacao',
                'data_atualizacao'
            ),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [ComentarioInline, HistoricoStatusInline]
    
    actions = [
        'marcar_como_concluidas',
        'redefinir_prioridade_media',
        'exportar_tarefas_csv'
    ]

    # Adicione estes métodos:
    def progresso_display(self, obj):
        return f"{obj.progresso}%"
    progresso_display.short_description = _('Progresso')
    
    def get_progresso(self, obj):
        return obj.progresso
    get_progresso.short_description = _('Progresso (%)')
    
    # Métodos de exibição
    def usuario_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.usuario.id])
        return format_html('<a href="{}">{}</a>', url, obj.usuario)
    usuario_link.short_description = _('Criado por')
    usuario_link.admin_order_field = 'usuario'
    
    def responsavel_link(self, obj):
        if obj.responsavel:
            url = reverse('admin:auth_user_change', args=[obj.responsavel.id])
            return format_html('<a href="{}">{}</a>', url, obj.responsavel)
        return _("Não definido")
    responsavel_link.short_description = _('Responsável')
    responsavel_link.admin_order_field = 'responsavel'
    
    def status_badge(self, obj):
        colors = {
            'pendente': 'gray',
            'em_andamento': 'blue',
            'concluida': 'green',
            'cancelada': 'red',
            'pausada': 'orange'
        }
        return format_html(
            '<span style="color: white; background-color: {}; padding: 2px 6px; border-radius: 10px;">{}</span>',
            colors.get(obj.status, 'gray'), obj.get_status_display()
        )
    status_badge.short_description = _('Status')
    status_badge.admin_order_field = 'status'
    
    def prioridade_badge(self, obj):
        colors = {
            'alta': 'red',
            'media': 'orange',
            'baixa': 'green'
        }
        return format_html(
            '<span style="color: white; background-color: {}; padding: 2px 6px; border-radius: 10px;">{}</span>',
            colors.get(obj.prioridade, 'gray'), obj.get_prioridade_display()
        )
    prioridade_badge.short_description = _('Prioridade')
    prioridade_badge.admin_order_field = 'prioridade'
    
    def prazo_formatado(self, obj):
        if obj.prazo:
            return obj.prazo.strftime('%d/%m/%Y')
        return _("Não definido")
    prazo_formatado.short_description = _('Prazo')
    prazo_formatado.admin_order_field = 'prazo'
    
    def progresso_bar(self, obj):
        return format_html(
            '<div style="width: 100px; background-color: #ddd; border-radius: 3px;">'
            '<div style="width: {}%; background-color: #4CAF50; height: 20px; border-radius: 3px; text-align: center; color: white;">{}%</div>'
            '</div>',
            obj.progresso, obj.progresso
        )
    progresso_bar.short_description = _('Progresso')
    
    def atrasada_flag(self, obj):
        if obj.atrasada:
            return format_html(
                '<span style="color: red;">⏰</span>'
            )
        return ""
    atrasada_flag.short_description = _('Atraso')
    
    def atrasada_flag_admin(self, obj):
        if obj.atrasada:
            return _("Sim (Tarefa atrasada)")
        return _("Não")
    atrasada_flag_admin.short_description = _('Atrasada?')
    atrasada_flag_admin.boolean = True
    
    # Ações personalizadas
    def marcar_como_concluidas(self, request, queryset):
        updated = queryset.update(status='concluida', concluida_em=timezone.now())
        for tarefa in queryset:
            HistoricoStatus.objects.create(
                tarefa=tarefa,
                status_anterior=tarefa.status,
                novo_status='concluida',
                alterado_por=request.user
            )
        self.message_user(request, _('%d tarefas marcadas como concluídas') % updated)
    marcar_como_concluidas.short_description = _('Marcar como concluídas')
    
    def redefinir_prioridade_media(self, request, queryset):
        updated = queryset.update(prioridade='media')
        self.message_user(request, _('%d tarefas com prioridade média') % updated)
    redefinir_prioridade_media.short_description = _('Redefinir prioridade para média')
    
    def exportar_tarefas_csv(self, request, queryset):
        # Implementação simplificada - na prática use o módulo csv
        self.message_user(request, _('Exportação iniciada para %d tarefas') % queryset.count())
    exportar_tarefas_csv.short_description = _('Exportar tarefas selecionadas (CSV)')
    
    # Sobrescreve save_model para registrar histórico
    def save_model(self, request, obj, form, change):
        if change and 'status' in form.changed_data:
            status_anterior = form.initial.get('status', 'pendente')
            obj.registrar_historico(request.user, status_anterior)
        super().save_model(request, obj, form, change)

    # Novo método para exibir dias restantes
    def dias_restantes_display(self, obj):
        days = obj.dias_restantes
        if days is None:
            return _("Sem prazo")
        color = "green" if days > 3 else "orange" if days > 0 else "red"
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color,
            days,
            _("dias") if days != 1 else _("dia")
        )
    dias_restantes_display.short_description = _('Dias Restantes')
    dias_restantes_display.admin_order_field = 'prazo'

@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    list_display = (
        'tarefa_link',
        'autor_link',
        'texto_resumido',
        'criado_em_formatado',
        'tempo_decorrido'
    )
    
    list_filter = (
        'autor',
        'criado_em',
    )
    
    search_fields = (
        'texto',
        'tarefa__titulo',
        'autor__username'
    )
    
    readonly_fields = (
        'criado_em',
        'atualizado_em',
    )
    
    def tarefa_link(self, obj):
        url = reverse('admin:gerenciamento_tarefas_change', args=[obj.tarefa.id])
        return format_html('<a href="{}">{}</a>', url, obj.tarefa)
    tarefa_link.short_description = _('Tarefa')
    tarefa_link.admin_order_field = 'tarefa'
    
    def autor_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.autor.id])
        return format_html('<a href="{}">{}</a>', url, obj.autor)
    autor_link.short_description = _('Autor')
    autor_link.admin_order_field = 'autor'
    
    def texto_resumido(self, obj):
        return obj.texto_resumido
    texto_resumido.short_description = _('Comentário')
    
    def criado_em_formatado(self, obj):
        return obj.criado_em.strftime('%d/%m/%Y %H:%M')
    criado_em_formatado.short_description = _('Criado em')
    criado_em_formatado.admin_order_field = 'criado_em'
    
    def tempo_decorrido(self, obj):
        delta = timezone.now() - obj.criado_em
        if delta.days > 0:
            return _('%d dias atrás') % delta.days
        elif delta.seconds > 3600:
            return _('%d horas atrás') % (delta.seconds // 3600)
        elif delta.seconds > 60:
            return _('%d minutos atrás') % (delta.seconds // 60)
        return _('Agora mesmo')
    tempo_decorrido.short_description = _('Tempo decorrido')

@admin.register(HistoricoStatus)
class HistoricoStatusAdmin(admin.ModelAdmin):
    list_display = (
        'tarefa_link',
        'status_anterior_formatado',
        'novo_status_formatado',
        'alterado_por_link',
        'data_alteracao_formatada'
    )
    
    list_filter = (
        'novo_status',
        'alterado_por',
        'data_alteracao',
    )
    
    search_fields = (
        'tarefa__titulo',
        'alterado_por__username'
    )
    
    readonly_fields = (
        'tarefa',
        'status_anterior',
        'novo_status',
        'alterado_por',
        'data_alteracao',
        'observacao'
    )
    
    def tarefa_link(self, obj):
        url = reverse('admin:gerenciamento_tarefas_change', args=[obj.tarefa.id])
        return format_html('<a href="{}">{}</a>', url, obj.tarefa)
    tarefa_link.short_description = _('Tarefa')
    tarefa_link.admin_order_field = 'tarefa'
    
    def status_anterior_formatado(self, obj):
        return dict(Tarefas.STATUS_CHOICES).get(obj.status_anterior, obj.status_anterior)
    status_anterior_formatado.short_description = _('Status Anterior')
    
    def novo_status_formatado(self, obj):
        return dict(Tarefas.STATUS_CHOICES).get(obj.novo_status, obj.novo_status)
    novo_status_formatado.short_description = _('Novo Status')
    
    def alterado_por_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.alterado_por.id])
        return format_html('<a href="{}">{}</a>', url, obj.alterado_por)
    alterado_por_link.short_description = _('Alterado por')
    alterado_por_link.admin_order_field = 'alterado_por'
    
    def data_alteracao_formatada(self, obj):
        return obj.data_alteracao.strftime('%d/%m/%Y %H:%M')
    data_alteracao_formatada.short_description = _('Data da Alteração')
    data_alteracao_formatada.admin_order_field = 'data_alteracao'
    