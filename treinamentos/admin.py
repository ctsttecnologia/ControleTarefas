# G:\Projetos\treinamentos\admin.py

from django.contrib import admin
from treinamentos.forms import ParticipanteForm
from .models import TipoCurso, Treinamento, Participante
from core.mixins import FilialScopedQuerysetMixin

@admin.register(TipoCurso)
class TipoCursoAdmin(admin.ModelAdmin):
    """Configuração da interface de admin para o modelo TipoCurso."""
    list_display = ('nome', 'filial', 'modalidade', 'area', 'validade_meses', 'ativo')
    list_filter = ('modalidade', 'filial', 'area', 'ativo')
    search_fields = ('nome', 'descricao')
    list_editable = ('ativo',)
    ordering = ('nome',)

class ParticipanteInline(admin.TabularInline):
    """
    Permite a edição de participantes diretamente na página de um treinamento.
    """
    model = Participante
    form = ParticipanteForm # Usa o formulário customizado
    extra = 1 # Quantidade de linhas extras para novos participantes
    autocomplete_fields = ['funcionario'] # Melhora a UX para selecionar usuários
    fields = ('funcionario', 'presente', 'nota_avaliacao', 'certificado_emitido')
    verbose_name = "Participante"
    verbose_name_plural = "Participantes do Treinamento"


@admin.register(Treinamento)
class TreinamentoAdmin(FilialScopedQuerysetMixin, admin.ModelAdmin):
    """Configuração da interface de admin para o modelo Treinamento."""
    # Adiciona o inline de participantes
    inlines = [ParticipanteInline]

    list_display = ('nome', 'filial', 'tipo_curso', 'data_inicio', 'responsavel', 'status', 'local')
    list_filter = ('status', 'tipo_curso__nome', 'data_inicio', 'responsavel')
    # Corrigido para buscar em campos de modelos relacionados
    search_fields = (
        'nome', 'descricao', 'palestrante', 'responsavel__first_name', 
        'responsavel__last_name', 'tipo_curso__nome'
    )
    date_hierarchy = 'data_inicio'
    ordering = ('-data_inicio',)
    
    # Melhora a usabilidade para campos com muitos registros
    autocomplete_fields = ['tipo_curso', 'responsavel']
    
    # Organiza a página de edição em seções lógicas
    fieldsets = (
        ('Informações Principais', {
            'fields': ('nome', 'tipo_curso', 'status', 'responsavel', 'palestrante', 'local')
        }),
        ('Datas e Prazos', {
            'fields': ('data_inicio', 'data_vencimento', 'duracao')
        }),
        ('Detalhes Operacionais e Custos', {
            'classes': ('collapse',), # Começa a seção recolhida
            'fields': ('participantes_previstos', 'custo', 'hxh', 'cm')
        }),
        ('Descrição do Treinamento', {
            'classes': ('collapse',),
            'fields': ('atividade', 'descricao')
        }),
        ('Datas de Controle', {
            'fields': ('data_cadastro', 'data_atualizacao')
        }),
    )

    readonly_fields = ('data_cadastro', 'data_atualizacao')

    def save_formset(self, request, form, formset, change):
        """Garante que o treinamento seja salvo antes do formset."""
        # Se for um novo treinamento, ele precisa de um ID antes de salvar os participantes.
        if not form.instance.pk:
            form.save()
        super().save_formset(request, form, formset, change)
