# tarefas/admin.py

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .models import Tarefas, Comentario, HistoricoStatus
from core.mixins import AdminFilialScopedMixin, ChangeFilialAdminMixin

# --- INLINES ---
class ComentarioInline(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.TabularInline):
    model = Comentario
    extra = 0
    # Adicionado 'filial' para que o campo seja exibido
    fields = ('autor', 'texto', 'filial',)
    readonly_fields = ('filial',)
    can_delete = True
    verbose_name = "Comentário"
    verbose_name_plural = "Comentários"

class HistoricoStatusInline(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.TabularInline):
    model = HistoricoStatus
    extra = 0
    # Adicionado 'filial' para que o campo seja exibido
    fields = ('novo_status', 'data_alteracao', 'alterado_por', 'filial',)
    readonly_fields = ('filial', 'data_alteracao', 'alterado_por', 'novo_status')
    can_delete = False
    verbose_name = "Histórico de Status"
    verbose_name_plural = "Histórico de Status"
   
# --- ADMIN PRINCIPAL DE TAREFAS (Refatorado) ---

@admin.register(Tarefas)
class TarefasAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    """
    Administração customizada para o modelo de Tarefas.
    Foco em performance, UX e organização.
    """
    # --- Configurações da LIST VIEW ---
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
    )
    list_select_related = ('responsavel', 'filial', 'tarefa_pai')
    
    # --- Configurações da ÁREA DE PESQUISA ---
    search_fields = ('titulo', 'descricao',)
    search_help_text = "Busque por título, descrição ou nome do projeto."

    # --- Configurações do FORMULÁRIO DE EDIÇÃO ---
    fieldsets = (
        (None, {'fields': ('titulo', 'descricao')}),
        (_('Organização'), {'fields': ('status', 'prioridade')}),
        (_('Responsáveis'), {'fields': ('usuario', 'responsavel')}),
        (_('Prazos e Duração'), {'fields': ('data_inicio', 'prazo', 'concluida_em')}),
        (_('Recorrência'), {
            'classes': ('collapse',),
            'fields': ('recorrente', 'frequencia_recorrencia', 'data_fim_recorrencia', 'tarefa_pai'),
        }),
    )
    readonly_fields = ('usuario', 'data_criacao', 'data_atualizacao', 'concluida_em', 'link_para_tarefa_pai_display')
    
    # Este campo agora funcionará corretamente
    autocomplete_fields = ['responsavel', 'tarefa_pai']
    
    # --- Configurações de INLINES e AÇÕES ---
    inlines = [ComentarioInline, HistoricoStatusInline]
    actions = ['marcar_como_concluidas', 'marcar_como_pendente']

    class Media:
        css = {'all': ('css/admin_extra.css',)}

    # ... (resto dos seus métodos @admin.display, @admin.action e save) ...
    # O restante do código da resposta anterior pode ser mantido como está.
    @admin.display(description=_('Status'), ordering='status')
    def status_badge(self, obj):
        return format_html('<span class="badge-admin status-{}">{}</span>', obj.status, obj.get_status_display())

    @admin.display(description=_('Prioridade'), ordering='prioridade')
    def prioridade_badge(self, obj):
        return format_html('<span class="badge-admin priority-{}">{}</span>', obj.prioridade, obj.get_prioridade_display())

    @admin.display(description=_('Responsável'), ordering='responsavel__first_name')
    def responsavel_link(self, obj):
        if not obj.responsavel:
            return "-"
        url = reverse('admin:usuario_usuario_change', args=[obj.responsavel.id])
        return format_html('<a href="{}">{}</a>', url, obj.responsavel.get_full_name())

    @admin.display(description=_('Prazo'), ordering='prazo')
    def prazo_colorido(self, obj):
        if not obj.prazo:
            return "-"
        if obj.atrasada:
            return format_html('<strong style="color: #e53935;">{}</strong>', obj.prazo.strftime('%d/%m/%Y %H:%M'))
        return obj.prazo.strftime('%d/%m/%Y %H:%M')

    @admin.display(description='!', boolean=True)
    def atrasada_flag(self, obj):
        return obj.atrasada
        
    @admin.display(description=_('Rec.'), boolean=True)
    def recorrente_info(self, obj):
        return obj.recorrente

    @admin.display(description=_('Tarefa Pai'))
    def link_para_tarefa_pai_display(self, obj):
        if obj.tarefa_pai:
            url = reverse('admin:tarefas_tarefas_change', args=[obj.tarefa_pai.id])
            return format_html('<a href="{}">{}</a>', url, obj.tarefa_pai.titulo)
        return "N/A"

    @admin.action(description=_('Marcar selecionadas como: CONCLUÍDA'))
    def marcar_como_concluidas(self, request, queryset):
        updated = queryset.update(status='concluida', concluida_em=timezone.now())
        self.message_user(request, _(f'{updated} tarefas marcadas como concluídas.'))

    @admin.action(description=_('Marcar selecionadas como: PENDENTE'))
    def marcar_como_pendente(self, request, queryset):
        updated = queryset.update(status='pendente', concluida_em=None)
        self.message_user(request, _(f'{updated} tarefas marcadas como pendentes.'))

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

