# G:\Projetos\treinamentos\admin.py

from django.contrib import admin
from .models import TipoCurso, Treinamento, Participante
from core.mixins import AdminFilialScopedMixin, ChangeFilialAdminMixin

@admin.register(TipoCurso)
class TipoCursoAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    """ Configuração da interface de admin para o modelo TipoCurso. """
    list_display = ('nome', 'filial', 'modalidade', 'area', 'validade_meses', 'ativo')
    list_filter = ('filial', 'area', 'modalidade', 'ativo')
    search_fields = ('nome', 'descricao')
    list_editable = ('ativo',)
    ordering = ('nome',)

    def get_readonly_fields(self, request, obj=None):
        """ MELHORIA: A filial só deve ser somente leitura na EDIÇÃO, não na criação. """
        if obj: # obj is not None, so this is a change page
            return ('filial',)
        return () # On the add page, no fields are readonly

    def save_model(self, request, obj, form, change):
        """ MELHORIA: Atribui a filial do usuário ao criar um novo objeto. """
        if not obj.pk: # Se o objeto está sendo criado
            obj.filial = request.user.filial_ativa
        super().save_model(request, obj, form, change)


class ParticipanteInline(admin.TabularInline):
    """ Permite a edição de participantes diretamente na página de um treinamento. """
    model = Participante
    extra = 1
    autocomplete_fields = ['funcionario']
    
    # MELHORIA: Organiza os campos e adiciona a exibição da filial do funcionário (se houver)
    fields = ('funcionario', 'presente', 'nota_avaliacao', 'certificado_emitido')
    readonly_fields = ('get_funcionario_filial',)
    
    verbose_name = "Participante"
    verbose_name_plural = "Participantes do Treinamento"
    
    @admin.display(description='Filial do Funcionário')
    def get_funcionario_filial(self, obj):
        """ Exibe a filial do funcionário, se disponível. """
        if obj.funcionario and hasattr(obj.funcionario, 'filial_ativa'):
            return obj.funcionario.filial_ativa
        return "N/A"


@admin.register(Treinamento)
class TreinamentoAdmin(AdminFilialScopedMixin, ChangeFilialAdminMixin, admin.ModelAdmin):
    """ Configuração da interface de admin para o modelo Treinamento. """
    inlines = [ParticipanteInline]

    list_display = ('nome', 'filial', 'tipo_curso', 'data_inicio', 'responsavel', 'status', 'contagem_participantes')
    list_filter = ('status', 'filial', 'tipo_curso__nome', 'data_inicio', 'responsavel__username')
    search_fields = (
        'nome', 'descricao', 'palestrante', 'responsavel__username', 
        'tipo_curso__nome'
    )
    date_hierarchy = 'data_inicio'
    ordering = ('-data_inicio',)
    
    autocomplete_fields = ['tipo_curso', 'responsavel']
    
    fieldsets = (
        ('Informações Principais', {
            'fields': ('nome', 'tipo_curso', 'status', 'responsavel', 'palestrante', 'local', 'filial')
        }),
        ('Datas e Prazos', {
            'fields': ('data_inicio', 'data_vencimento', 'duracao')
        }),
        ('Detalhes Operacionais e Custos', {
            'classes': ('collapse',),
            'fields': ('participantes_previstos', 'custo', 'horas_homem', 'centro_custo') # Nomes de campos atualizados
        }),
        ('Descrição do Treinamento', {
            'classes': ('collapse',),
            'fields': ('atividade', 'descricao')
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        """ MELHORIA: A filial só deve ser somente leitura na EDIÇÃO. Datas de controle são sempre readonly. """
        if obj:
            return ('filial', 'data_cadastro', 'data_atualizacao')
        return ('data_cadastro', 'data_atualizacao')
        
    def save_model(self, request, obj, form, change):
        """ MELHORIA: Atribui a filial do usuário ao criar um novo treinamento. """
        if not obj.pk:
            obj.filial = request.user.filial_ativa
        super().save_model(request, obj, form, change)

    @admin.display(description='Nº de Participantes')
    def contagem_participantes(self, obj):
        """ MELHORIA: Exibe a contagem de participantes na lista. """
        return obj.participantes.count()

