
from datetime import timedelta, timezone
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import Tarefas, Comentario, HistoricoStatus

class ComentarioInline(admin.StackedInline):
    model = Comentario
    extra = 0
    fields = ('autor', 'texto', 'anexo', 'criado_em')
    readonly_fields = ('criado_em', 'atualizado_em')
    classes = ('collapse',)

class HistoricoStatusInline(admin.TabularInline):
    model = HistoricoStatus
    extra = 0
    fields = ('data_alteracao', 'status_anterior', 'novo_status', 'alterado_por', 'observacao')
    readonly_fields = ('data_alteracao', 'alterado_por')
    classes = ('collapse',)

@admin.register(Tarefas)
class TarefasAdmin(admin.ModelAdmin):
    list_display = (
        'titulo', 
        'usuario_link',
        'responsavel_link',
        'status_badge',
        'prioridade_badge',
        'prazo_formatado',
        'progresso_bar',
        'atrasada_flag'
    )
    list_filter = ('status', 'prioridade', 'usuario', 'projeto')
    search_fields = ('titulo', 'descricao', 'projeto')
    readonly_fields = ('data_criacao', 'data_atualizacao', 'progresso_display')
    fieldsets = (
        (None, {
            'fields': ('titulo', 'descricao', 'projeto')
        }),
        (_('Responsáveis'), {
            'fields': ('usuario', 'responsavel')
        }),
        (_('Tempo'), {
            'fields': ('data_inicio', 'prazo', 'duracao_prevista', 'tempo_gasto', 'dias_lembrete')
        }),
        (_('Status'), {
            'fields': ('status', 'prioridade', 'concluida_em')
        }),
        (_('Auditoria'), {
            'fields': ('data_criacao', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )
    inlines = [ComentarioInline, HistoricoStatusInline]
    actions = ['marcar_como_concluidas']

    def usuario_link(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:auth_user_change', args=[obj.usuario.id]),
            obj.usuario
        )
    usuario_link.short_description = _('Criado por')

    def responsavel_link(self, obj):
        if obj.responsavel:
            return format_html(
                '<a href="{}">{}</a>',
                reverse('admin:auth_user_change', args=[obj.responsavel.id]),
                obj.responsavel
            )
        return "-"
    responsavel_link.short_description = _('Responsável')

    def status_badge(self, obj):
        colors = {
            'pendente': 'gray', 
            'andamento': 'blue',
            'concluida': 'green',
            'cancelada': 'red',
            'pausada': 'orange',
            'atrasada': 'darkred'
        }
        return format_html(
            '<span style="color:white;background:{};padding:2px 6px;border-radius:10px">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )
    status_badge.short_description = _('Status')

    def prioridade_badge(self, obj):
        colors = {'alta': 'red', 'media': 'orange', 'baixa': 'green'}
        return format_html(
            '<span style="color:white;background:{};padding:2px 6px;border-radius:10px">{}</span>',
            colors.get(obj.prioridade, 'gray'),
            obj.get_prioridade_display()
        )
    prioridade_badge.short_description = _('Prioridade')

    def prazo_formatado(self, obj):
        return obj.prazo.strftime('%d/%m/%Y') if obj.prazo else "-"
    prazo_formatado.short_description = _('Prazo')

    def progresso_bar(self, obj):
        return format_html(
            '<div style="width:100px;background:#ddd;border-radius:3px">'
            '<div style="width:{}%;background:#4CAF50;height:20px;border-radius:3px;'
            'text-align:center;color:white">{}%</div></div>',
            obj.progresso, obj.progresso
        )
    progresso_bar.short_description = _('Progresso')

    def atrasada_flag(self, obj):
        return "⏰" if obj.esta_atrasada() else ""
    atrasada_flag.short_description = _('Atraso')

    def progresso_display(self, obj):
        return f"{obj.progresso}%"
    progresso_display.short_description = _('Progresso')

    def marcar_como_concluidas(self, request, queryset):
        updated = queryset.update(status='concluida', concluida_em=timezone.now())
        self.message_user(request, _('%d tarefas marcadas como concluídas') % updated)
    marcar_como_concluidas.short_description = _('Marcar como concluídas')

    def save_model(self, request, obj, form, change):
        if obj.duracao_prevista and obj.duracao_prevista > timedelta(days=30):
            obj.duracao_prevista = timedelta(days=30)
        if obj.tempo_gasto and obj.tempo_gasto > timedelta(days=30):
            obj.tempo_gasto = timedelta(days=30)
        super().save_model(request, obj, form, change)

@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    list_display = ('tarefa_link', 'autor_link', 'texto_resumido', 'anexo_info', 'criado_em_formatado')
    list_filter = ('autor', 'criado_em')
    search_fields = ('texto', 'tarefa__titulo')
    readonly_fields = ('anexo_detalhes', 'criado_em', 'atualizado_em')

    def tarefa_link(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:tarefas_tarefas_change', args=[obj.tarefa.id]),
            obj.tarefa
        )
    tarefa_link.short_description = _('Tarefa')

    def autor_link(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:auth_user_change', args=[obj.autor.id]),
            obj.autor
        )
    autor_link.short_description = _('Autor')

    def texto_resumido(self, obj):
        return obj.texto[:50] + '...' if len(obj.texto) > 50 else obj.texto
    texto_resumido.short_description = _('Comentário')

    def anexo_info(self, obj):
        if obj.anexo:
            warning = "⚠" if obj.extensao_anexo in ['doc', 'docx'] else ""
            return format_html(
                "{} {} ({}MB)",
                warning,
                obj.nome_anexo,
                obj.tamanho_anexo_mb
            )
        return "-"
    anexo_info.short_description = _('Anexo')

    def anexo_detalhes(self, obj):
        if obj.anexo:
            return format_html(
                """
                <div style="border:1px solid #eee;padding:10px;margin:10px 0">
                    <strong>Nome:</strong> {}<br>
                    <strong>Tipo:</strong> {}<br>
                    <strong>Tamanho:</strong> {} MB<br>
                    <strong style="color:red">Aviso:</strong> Verifique a procedência antes de abrir
                </div>
                """,
                obj.nome_anexo,
                obj.extensao_anexo,
                obj.tamanho_anexo_mb
            )
        return _("Nenhum arquivo anexado")
    anexo_detalhes.short_description = _('Detalhes do Anexo')

    def criado_em_formatado(self, obj):
        return obj.criado_em.strftime('%d/%m/%Y %H:%M')
    criado_em_formatado.short_description = _('Criado em')

@admin.register(HistoricoStatus)
class HistoricoStatusAdmin(admin.ModelAdmin):
    list_display = ('tarefa_link', 'status_anterior', 'novo_status', 'alterado_por_link', 'data_alteracao_formatada')
    list_filter = ('novo_status', 'alterado_por')
    search_fields = ('tarefa__titulo', 'alterado_por__username')
    readonly_fields = ('tarefa_link', 'status_anterior', 'novo_status', 'alterado_por_link', 'data_alteracao_formatada')

    def tarefa_link(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:tarefas_tarefas_change', args=[obj.tarefa.id]),
            obj.tarefa
        )
    tarefa_link.short_description = _('Tarefa')

    def alterado_por_link(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:auth_user_change', args=[obj.alterado_por.id]),
            obj.alterado_por
        )
    alterado_por_link.short_description = _('Alterado por')

    def data_alteracao_formatada(self, obj):
        return obj.data_alteracao.strftime('%d/%m/%Y %H:%M')
    data_alteracao_formatada.short_description = _('Data da Alteração')

