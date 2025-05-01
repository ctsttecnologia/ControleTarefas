
# automovel/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.contrib.auth.admin import UserAdmin

from .models import Carro, Agendamento, FotoAgendamento, Checklist_Carro


class CarroAdmin(admin.ModelAdmin):
    list_display = ('marca', 'modelo', 'placa', 'ano', 'cor', 'status_display', 'ativo')
    list_filter = ('marca', 'modelo', 'ativo', 'cor')
    search_fields = ('placa', 'modelo', 'marca', 'renavan')
    ordering = ('marca', 'modelo')
    list_per_page = 20
    date_hierarchy = 'data_ultima_manutencao'
    readonly_fields = ('status_display', 'idade')
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('marca', 'modelo', 'ano', 'cor', 'placa', 'renavan')
        }),
        ('Status e Manutenção', {
            'fields': ('status', 'ativo', 'data_ultima_manutencao', 
                      'data_proxima_manutencao', 'status_display')
        }),
        ('Outras Informações', {
            'fields': ('observacoes', 'idade'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['marcar_como_disponivel', 'marcar_como_manutencao']
    
    def status_display(self, obj):
        colors = {
            'disponivel': 'green',
            'manutencao': 'orange',
            'locado': 'red'
        }
        return format_html(
            '<span style="color: {};">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def marcar_como_disponivel(self, request, queryset):
        queryset.update(status='disponivel')
    marcar_como_disponivel.short_description = "Marcar como Disponível"
    
    def marcar_como_manutencao(self, request, queryset):
        queryset.update(status='manutencao')
    marcar_como_manutencao.short_description = "Marcar como em Manutenção"

class FotoAgendamentoInline(admin.TabularInline):
    model = FotoAgendamento
    extra = 1
    fields = ('imagem', 'observacao', 'data_criacao')
    readonly_fields = ('data_criacao',)

class ChecklistCarroInline(admin.TabularInline):
    model = Checklist_Carro
    extra = 0
    fields = ('tipo', 'data_criacao', 'revisao_frontal_status', 'confirmacao')
    readonly_fields = ('data_criacao',)
    max_num = 2  # Máximo de checklists (saída e retorno)

class AgendamentoAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'carro_link', 'funcionario', 'data_hora_agenda', 
        'status_display', 'km_inicial', 'km_final'
    )
    list_filter = ('status', 'carro__marca', 'data_hora_agenda', 'pedagio', 'abastecimento')
    search_fields = (
        'carro__placa', 'funcionario', 'cm', 'responsavel', 
        'carro__modelo', 'carro__marca'
    )
    date_hierarchy = 'data_hora_agenda'
    ordering = ('-data_hora_agenda',)
    readonly_fields = (
        'duracao_display', 'quilometragem_percorrida', 'carro_link',
        'status_display'
    )
    raw_id_fields = ('carro', 'carro')
    inlines = [FotoAgendamentoInline, ChecklistCarroInline]
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': (
                'carro_link', 'funcionario', 'cm', 
                'data_hora_agenda', 'data_hora_devolucao', 'duracao_display'
            )
        }),
        ('Status e Controle', {
            'fields': (
                'status', 'cancelar_agenda', 'motivo_cancelamento', 
                'responsavel', 'assinatura'
            )
        }),
        ('Dados do Veículo', {
            'fields': (
                'km_inicial', 'km_final', 'quilometragem_percorrida',
                'pedagio', 'abastecimento'
            )
        }),
        ('Registros', {
            'fields': ('descricao', 'ocorrencia', 'foto_principal'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['finalizar_agendamento', 'cancelar_agendamento']
    
    def carro_link(self, obj):
        url = reverse("admin:lista_carros", args=[obj.carro.id])
        return mark_safe(f'<a href="{url}">{obj.carro}</a>')
    carro_link.short_description = 'Veículo'
    
    def status_display(self, obj):
        colors = {
            'agendado': 'blue',
            'em_andamento': 'orange',
            'concluido': 'green',
            'cancelado': 'red'
        }
        return format_html(
            '<span style="color: {};">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def duracao_display(self, obj):
        if obj.duracao_agendamento():
            return str(obj.duracao_agendamento())
        return "Agendamento em andamento"
    duracao_display.short_description = 'Duração'
    
    def quilometragem_percorrida(self, obj):
        if obj.calcular_quilometragem_percorrida():
            return f"{obj.calcular_quilometragem_percorrida()} km"
        return "Não finalizado"
    quilometragem_percorrida.short_description = 'Km Percorridos'
    
    def finalizar_agendamento(self, request, queryset):
        for agendamento in queryset.filter(status='em_andamento'):
            agendamento.finalizar_agendamento(
                km_final=agendamento.carro.km_atual,
                ocorrencia="Finalizado pelo admin"
            )
    finalizar_agendamento.short_description = "Finalizar agendamentos selecionados"
    
    def cancelar_agendamento(self, request, queryset):
        queryset.update(
            status='cancelado',
            cancelar_agenda=True,
            motivo_cancelamento="Cancelado pelo admin"
        )
    cancelar_agendamento.short_description = "Cancelar agendamentos selecionados"

class ChecklistCarroAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'agendamento_link', 'tipo_display', 'data_criacao', 
        'km_inicial', 'km_final', 'confirmacao'
    )
    list_filter = ('tipo', 'confirmacao', 'data_criacao')
    search_fields = (
        'agendamento__carro__placa', 'agendamento__funcionario',
        'usuario__username'
    )
    date_hierarchy = 'data_criacao'
    readonly_fields = (
        'agendamento_link', 'data_criacao', 'foto_frontal_preview',
        'foto_trazeira_preview', 'foto_lado_motorista_preview',
        'foto_lado_passageiro_preview'
    )
    raw_id_fields = ('agendamento', 'usuario')
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': (
                'agendamento_link', 'usuario', 'tipo', 'data_criacao', 
                'confirmacao', 'assinatura'
            )
        }),
        ('Quilometragem', {
            'fields': ('km_inicial', 'km_final')
        }),
        ('Checklist Frontal', {
            'fields': (
                'revisao_frontal_status', 'foto_frontal', 
                'foto_frontal_preview', 'coordenadas_avaria_frontal'
            )
        }),
        ('Checklist Traseiro', {
            'fields': (
                'revisao_trazeira_status', 'foto_trazeira',
                'foto_trazeira_preview', 'coordenadas_avaria_trazeira'
            )
        }),
        ('Checklist Lateral', {
            'fields': (
                'revisao_lado_motorista_status', 'foto_lado_motorista',
                'foto_lado_motorista_preview', 'coordenadas_avaria_lado_motorista',
                'revisao_lado_passageiro_status', 'foto_lado_passageiro',
                'foto_lado_passageiro_preview', 'coordenadas_lado_passageiro'
            )
        }),
        ('Observações', {
            'fields': ('observacoes_gerais',),
            'classes': ('collapse',)
        }),
    )
    
    def agendamento_link(self, obj):
        url = reverse("admin:frota_agendamento_change", args=[obj.agendamento.id])
        return mark_safe(f'<a href="{url}">{obj.agendamento}</a>')
    agendamento_link.short_description = 'Agendamento'
    
    def tipo_display(self, obj):
        colors = {
            'saida': 'blue',
            'retorno': 'green'
        }
        return format_html(
            '<span style="color: {};">{}</span>',
            colors.get(obj.tipo, 'black'),
            obj.get_tipo_display()
        )
    tipo_display.short_description = 'Tipo'
    
    def foto_frontal_preview(self, obj):
        if obj.foto_frontal:
            return mark_safe(f'<img src="{obj.foto_frontal.url}" width="200" />')
        return "-"
    foto_frontal_preview.short_description = 'Prévia Foto Frontal'
    
    # Criar métodos similares para as outras fotos (trazeira, lado_motorista, lado_passageiro)
    def foto_trazeira_preview(self, obj):
        if obj.foto_trazeira:
            return mark_safe(f'<img src="{obj.foto_trazeira.url}" width="200" />')
        return "-"
    foto_trazeira_preview.short_description = 'Prévia Foto Traseira'
    
    def foto_lado_motorista_preview(self, obj):
        if obj.foto_lado_motorista:
            return mark_safe(f'<img src="{obj.foto_lado_motorista.url}" width="200" />')
        return "-"
    foto_lado_motorista_preview.short_description = 'Prévia Lado Motorista'
    
    def foto_lado_passageiro_preview(self, obj):
        if obj.foto_lado_passageiro:
            return mark_safe(f'<img src="{obj.foto_lado_passageiro.url}" width="200" />')
        return "-"
    foto_lado_passageiro_preview.short_description = 'Prévia Lado Passageiro'

# Registro dos modelos no admin
admin.site.register(Carro, CarroAdmin)
admin.site.register(Agendamento, AgendamentoAdmin)
admin.site.register(Checklist_Carro, ChecklistCarroAdmin)


