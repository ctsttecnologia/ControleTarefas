
# tarefas/admin.py

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .models import Tarefas, Comentario, HistoricoStatus

# --- INLINES (sem alterações) ---
class ComentarioInline(admin.TabularInline):
    model = Comentario
    extra = 0
    fields = ('texto', 'autor', 'criado_em')
    readonly_fields = ('autor', 'criado_em')
    classes = ('collapse',)

class HistoricoStatusInline(admin.TabularInline):
    model = HistoricoStatus
    extra = 0
    fields = ('data_alteracao', 'status_anterior', 'novo_status', 'alterado_por')
    readonly_fields = fields
    can_delete = False
    classes = ('collapse',)
    
    def has_add_permission(self, request, obj=None):
        return False

# --- ADMIN PRINCIPAL DE TAREFAS (COM AS MUDANÇAS) ---

@admin.register(Tarefas)
class TarefasAdmin(admin.ModelAdmin):
    class Media:
        css = {'all': ('css/admin_extra.css',)}

    list_display = (
        'titulo', 
        'responsavel_link',
        'status_badge',
        'prioridade_badge',
        'prazo_formatado',
        'recorrente_info', # NOVO
        'atrasada_flag'
    )
    # ADICIONADO 'recorrente' ao filtro
    list_filter = ('recorrente', 'status', 'prioridade', 'responsavel', 'projeto')
    search_fields = ('titulo', 'descricao', 'projeto')
    # ADICIONADO campos de recorrência e concluída_em como readonly
    readonly_fields = ('data_criacao', 'data_atualizacao', 'usuario', 'concluida_em', 'link_para_tarefa_pai')

    fieldsets = (
        (None, {'fields': ('titulo', 'descricao', 'projeto')}),
        (_('Organização'), {'fields': ('status', 'prioridade')}),
        (_('Responsáveis'), {'fields': ('usuario', 'responsavel')}),
        (_('Prazos e Duração'), {'fields': ('data_inicio', 'prazo', 'concluida_em')}),
        # NOVO FIELDSET PARA RECORRÊNCIA
        (_('Recorrência'), {
            'classes': ('collapse',), # Começa recolhido
            'fields': ('recorrente', 'frequencia_recorrencia', 'data_fim_recorrencia', 'link_para_tarefa_pai'),
        }),
    )
    inlines = [ComentarioInline, HistoricoStatusInline]
    actions = ['marcar_como_concluidas']

    # --- MÉTODOS DE EXIBIÇÃO (COM ADIÇÕES) ---

    @admin.display(description=_('Recorrente'), boolean=True)
    def recorrente_info(self, obj):
        # Exibe um ícone se a tarefa for recorrente
        if obj.recorrente:
            return format_html('🔄 Sim')
        return "Não"

    @admin.display(description=_('Tarefa Pai'))
    def link_para_tarefa_pai(self, obj):
        # Cria um link para a tarefa pai, se existir
        if obj.tarefa_pai:
            url = reverse('admin:tarefas_tarefas_change', args=[obj.tarefa_pai.id])
            return format_html('<a href="{}">{}</a>', url, obj.tarefa_pai.titulo)
        return "N/A"

    # ... (Seus outros métodos de display como status_badge, etc., continuam iguais) ...
    @admin.display(description=_('Responsável'), ordering='responsavel__username')
    def responsavel_link(self, obj):
        if obj.responsavel:
            url = reverse('admin:auth_user_change', args=[obj.responsavel.id])
            return format_html('<a href="{}">{}</a>', url, obj.responsavel.username)
        return "-"

    @admin.display(description=_('Status'), ordering='status')
    def status_badge(self, obj):
        return format_html('<span class="badge-admin status-{}">{}</span>', obj.status, obj.get_status_display())

    @admin.display(description=_('Prioridade'), ordering='prioridade')
    def prioridade_badge(self, obj):
        return format_html('<span class="badge-admin priority-{}">{}</span>', obj.prioridade, obj.get_prioridade_display())

    @admin.display(description=_('Prazo'), ordering='prazo')
    def prazo_formatado(self, obj):
        if not obj.prazo: return "-"
        return obj.prazo.strftime('%d/%m/%Y %H:%M')

    @admin.display(description='!', ordering='prazo')
    def atrasada_flag(self, obj):
        return "⏰" if obj.atrasada else ""


    # --- AÇÕES E MÉTODOS DE SALVAMENTO (sem alterações necessárias aqui) ---

    @admin.action(description=_('Marcar selecionadas como concluídas'))
    def marcar_como_concluidas(self, request, queryset):
        for tarefa in queryset:
            tarefa.status = 'concluida'
            tarefa.save() # Chama o save() do modelo, que agora contém toda a lógica
        self.message_user(request, _(f'{queryset.count()} tarefas marcadas como concluídas.'))

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.usuario = request.user
        obj._user = request.user # Para o histórico
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