# tarefas/admin.py

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .models import Tarefas, Comentario, HistoricoTarefa, HistoricoStatus
from core.mixins import AdminFilialScopedMixin, ChangeFilialAdminMixin


# =============================================================================
# INLINES
# =============================================================================

class ComentarioInline(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.TabularInline):
    model = Comentario
    fk_name = 'tarefa'
    extra = 0
    fields = ('autor', 'texto', 'filial',)
    readonly_fields = ('filial',)
    can_delete = True
    verbose_name = "Comentário"
    verbose_name_plural = "Comentários"


class HistoricoTarefaInline(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.TabularInline):
    """
    Histórico v2 — campos compatíveis com o modelo atual HistoricoTarefa.
    """
    model = HistoricoTarefa
    fk_name = 'tarefa'
    extra = 0
    fields = (
        'data_alteracao',
        'alterado_por',
        'campo_alterado',
        'valor_anterior',
        'valor_novo',
        'descricao',
    )
    readonly_fields = (
        'data_alteracao',
        'alterado_por',
        'campo_alterado',
        'valor_anterior',
        'valor_novo',
        'descricao',
    )
    can_delete = False
    verbose_name = "Histórico"
    verbose_name_plural = "Histórico de Alterações"

    def has_add_permission(self, request, obj=None):
        # Histórico é gerado automaticamente, não permite adição manual
        return False


# =============================================================================
# ADMIN PRINCIPAL — TAREFAS
# =============================================================================

@admin.register(Tarefas)
class TarefasAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    """
    Administração customizada para o modelo de Tarefas.
    """
    list_display = (
        'titulo',
        'status_badge',
        'prioridade_badge',
        'responsavel_link',
        'prazo_colorido',
        'filial',
        'recorrente_info',
        'atrasada_flag',
    )
    list_filter = (
        'status',
        'prioridade',
        'filial',
        ('responsavel', admin.RelatedOnlyFieldListFilter),
        'recorrente',
        'recorrencia_encerrada',
    )
    list_select_related = ('responsavel', 'filial', 'tarefa_recorrencia_pai')

    search_fields = ('titulo', 'descricao', 'projeto',)
    search_help_text = "Busque por título, descrição ou nome do projeto."

    fieldsets = (
        (None, {'fields': ('titulo', 'descricao', 'ata_reuniao')}),
        (_('Organização'), {'fields': ('projeto', 'status', 'prioridade')}),
        (_('Responsáveis'), {'fields': ('usuario', 'responsavel', 'participantes')}),
        (_('Prazos e Duração'), {
            'fields': ('data_inicio', 'prazo', 'concluida_em', 'duracao_prevista', 'tempo_gasto'),
        }),
        (_('Lembrete'), {
            'classes': ('collapse',),
            'fields': ('dias_lembrete', 'lembrete_enviado_em'),
        }),
        (_('Recorrência'), {
            'classes': ('collapse',),
            'fields': (
                'recorrente',
                'frequencia_recorrencia',
                'data_fim_recorrencia',
                'tarefa_recorrencia_pai',
                'dias_aviso_fim_recorrencia',
                'aviso_fim_enviado_em',
                'recorrencia_encerrada',
                'link_para_tarefa_pai_display',
            ),
        }),
    )
    readonly_fields = (
        'usuario',
        'data_criacao',
        'data_atualizacao',
        'concluida_em',
        'lembrete_enviado_em',
        'aviso_fim_enviado_em',
        'link_para_tarefa_pai_display',
    )

    autocomplete_fields = ['responsavel', 'tarefa_recorrencia_pai']
    filter_horizontal = ('participantes',)

    inlines = [ComentarioInline, HistoricoTarefaInline]
    actions = ['marcar_como_concluidas', 'marcar_como_pendente']

    class Media:
        css = {'all': ('css/admin_extra.css',)}

    # ---------- DISPLAYS ----------

    @admin.display(description=_('Status'), ordering='status')
    def status_badge(self, obj):
        return format_html(
            '<span class="badge-admin status-{}">{}</span>',
            obj.status, obj.get_status_display()
        )

    @admin.display(description=_('Prioridade'), ordering='prioridade')
    def prioridade_badge(self, obj):
        return format_html(
            '<span class="badge-admin priority-{}">{}</span>',
            obj.prioridade, obj.get_prioridade_display()
        )

    @admin.display(description=_('Responsável'), ordering='responsavel__first_name')
    def responsavel_link(self, obj):
        if not obj.responsavel:
            return "-"
        try:
            url = reverse('admin:usuario_usuario_change', args=[obj.responsavel.id])
            return format_html('<a href="{}">{}</a>', url, obj.responsavel.get_full_name() or obj.responsavel.username)
        except Exception:
            return obj.responsavel.get_full_name() or obj.responsavel.username

    @admin.display(description=_('Prazo'), ordering='prazo')
    def prazo_colorido(self, obj):
        if not obj.prazo:
            return "-"
        if obj.atrasada:
            return format_html(
                '<strong style="color: #e53935;">{}</strong>',
                obj.prazo.strftime('%d/%m/%Y %H:%M')
            )
        return obj.prazo.strftime('%d/%m/%Y %H:%M')

    @admin.display(description='!', boolean=True)
    def atrasada_flag(self, obj):
        return obj.atrasada

    @admin.display(description=_('Rec.'), boolean=True)
    def recorrente_info(self, obj):
        return obj.recorrente

    @admin.display(description=_('Tarefa-Raiz da Recorrência'))
    def link_para_tarefa_pai_display(self, obj):
        if obj.tarefa_recorrencia_pai:
            url = reverse('admin:tarefas_tarefas_change', args=[obj.tarefa_recorrencia_pai.id])
            return format_html('<a href="{}">{}</a>', url, obj.tarefa_recorrencia_pai.titulo)
        return "—"

    # ---------- ACTIONS ----------

    @admin.action(description=_('Marcar selecionadas como: CONCLUÍDA'))
    def marcar_como_concluidas(self, request, queryset):
        updated = queryset.update(status='concluida', concluida_em=timezone.now())
        self.message_user(request, _(f'{updated} tarefas marcadas como concluídas.'))

    @admin.action(description=_('Marcar selecionadas como: PENDENTE'))
    def marcar_como_pendente(self, request, queryset):
        updated = queryset.update(status='pendente', concluida_em=None)
        self.message_user(request, _(f'{updated} tarefas marcadas como pendentes.'))

    # ---------- SAVE HOOKS ----------

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.usuario = request.user
        obj._user = request.user
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        if formset.model == Comentario:
            instances = formset.save(commit=False)
            for instance in instances:
                if not instance.pk:
                    instance.autor = request.user
                instance.save()
            formset.save_m2m()
        else:
            super().save_formset(request, form, formset, change)


# =============================================================================
# ADMIN — HISTÓRICO V2 (HistoricoTarefa)
# =============================================================================

@admin.register(HistoricoTarefa)
class HistoricoTarefaAdmin(admin.ModelAdmin):
    list_display = [
        'tarefa',
        'campo_alterado',
        'alterado_por',
        'valor_anterior',
        'valor_novo',
        'data_alteracao',
    ]
    list_filter = ['data_alteracao', 'campo_alterado']
    search_fields = [
        'tarefa__titulo',
        'descricao',
        'alterado_por__username',
        'campo_alterado',
    ]
    readonly_fields = [
        'tarefa',
        'alterado_por',
        'campo_alterado',
        'valor_anterior',
        'valor_novo',
        'descricao',
        'data_alteracao',
    ]
    date_hierarchy = 'data_alteracao'

    def has_add_permission(self, request):
        return False


# =============================================================================
# ADMIN — HISTÓRICO LEGADO (HistoricoStatus)
# =============================================================================

@admin.register(HistoricoStatus)
class HistoricoStatusAdmin(admin.ModelAdmin):
    """Admin do histórico legado — somente leitura."""
    list_display = [
        'tarefa',
        'status_anterior',
        'novo_status',
        'alterado_por',
        'filial',
        'data_alteracao',
    ]
    list_filter = ['novo_status', 'data_alteracao', 'filial']
    search_fields = ['tarefa__titulo', 'alterado_por__username']
    readonly_fields = [
        'tarefa',
        'status_anterior',
        'novo_status',
        'alterado_por',
        'filial',
        'data_alteracao',
    ]
    date_hierarchy = 'data_alteracao'

    def has_add_permission(self, request):
        return False

