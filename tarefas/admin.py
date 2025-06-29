
from datetime import timedelta
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .models import Tarefas, Comentario, HistoricoStatus

# --- INLINES OTIMIZADOS ---

class ComentarioInline(admin.TabularInline): # Trocado para Tabular, mais compacto
    model = Comentario
    extra = 0
    fields = ('texto', 'anexo', 'autor', 'criado_em')
    readonly_fields = ('autor', 'criado_em') # Autor será definido automaticamente
    classes = ('collapse',)

    def has_change_permission(self, request, obj=None):
        return False # Comentários não devem ser editados aqui, apenas vistos

class HistoricoStatusInline(admin.TabularInline):
    model = HistoricoStatus
    extra = 0
    fields = ('data_alteracao', 'status_anterior', 'novo_status', 'alterado_por')
    readonly_fields = ('data_alteracao', 'status_anterior', 'novo_status', 'alterado_por')
    classes = ('collapse',)
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False # Histórico é apenas para leitura

# --- ADMIN PRINCIPAL DE TAREFAS ---

@admin.register(Tarefas)
class TarefasAdmin(admin.ModelAdmin):
    # Definindo a Media para carregar nosso CSS customizado
    class Media:
        css = {
            'all': ('css/admin_extra.css',)
        }

    list_display = (
        'titulo', 
        'responsavel_link',
        'status_badge',
        'prioridade_badge',
        'prazo_formatado',
        'progresso_bar',
        'atrasada_flag'
    )
    list_filter = ('status', 'prioridade', 'responsavel', 'projeto')
    search_fields = ('titulo', 'descricao', 'projeto')
    readonly_fields = ('data_criacao', 'data_atualizacao', 'usuario') # 'usuario' é definido no save
    
    fieldsets = (
        (None, {'fields': ('titulo', 'descricao', 'projeto')}),
        (_('Organização'), {'fields': ('status', 'prioridade')}),
        (_('Responsáveis'), {'fields': ('usuario', 'responsavel')}),
        (_('Prazos e Duração'), {'fields': ('data_inicio', 'prazo', 'concluida_em', 'duracao_prevista', 'tempo_gasto')}),
    )
    inlines = [ComentarioInline, HistoricoStatusInline]
    actions = ['marcar_como_concluidas']

    # --- MÉTODOS DE EXIBIÇÃO OTIMIZADOS (usando classes CSS) ---

    @admin.display(description=_('Responsável'), ordering='responsavel__username')
    def responsavel_link(self, obj):
        if obj.responsavel:
            url = reverse('admin:auth_user_change', args=[obj.responsavel.id])
            return format_html('<a href="{}">{}</a>', url, obj.responsavel.username)
        return "-"

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

    @admin.display(description=_('Prazo'), ordering='prazo')
    def prazo_formatado(self, obj):
        if not obj.prazo: return "-"
        return obj.prazo.strftime('%d/%m/%Y %H:%M')

    @admin.display(description=_('Progresso'))
    def progresso_bar(self, obj):
        progresso = obj.progresso
        return format_html(
            '<div class="progress-bar-container">'
            '<div class="progress-bar-fill" style="width:{}%;">{}%</div></div>',
            progresso, progresso
        )

    @admin.display(description='!', ordering='prazo')
    def atrasada_flag(self, obj):
        return "⏰" if obj.atrasada else ""

    # --- AÇÕES E MÉTODOS DE SALVAMENTO ---

    def marcar_como_concluidas(self, request, queryset):
        updated = queryset.update(status='concluida', concluida_em=timezone.now())
        self.message_user(request, _('%(count)d tarefas marcadas como concluídas.') % {'count': updated})
    marcar_como_concluidas.short_description = _('Marcar selecionadas como concluídas')

    def save_model(self, request, obj, form, change):
        """
        Sobrescreve o método save para definir o criador da tarefa (se for nova)
        e para anexar o usuário ao objeto para o log de histórico.
        """
        # CORREÇÃO CRÍTICA: Define o usuário criador na primeira vez que a tarefa é salva
        if not obj.pk:
            obj.usuario = request.user
        
        # Anexa o usuário ao objeto para ser usado no método save() do modelo
        obj._user = request.user
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        """
        Sobrescreve o método para definir o autor do comentário automaticamente.
        """
        # OTIMIZAÇÃO: Define o autor de novos comentários como o usuário logado
        if formset.model == Comentario:
            instances = formset.save(commit=False)
            for instance in instances:
                if not instance.pk and hasattr(request, 'user'):
                    instance.autor = request.user
                instance.save()
            formset.save_m2m()
        else:
            super().save_formset(request, form, formset, change)

# --- ADMINS DOS OUTROS MODELOS ---
# ... Seus ComentarioAdmin e HistoricoStatusAdmin podem ser mantidos, 
# mas registrá-los separadamente não é mais necessário se você só os usa como inlines.
# Se você quiser uma página separada para eles, mantenha o @admin.register.
