from django.contrib import admin
from django.utils.html import format_html
from .models import (Documentos, Cbos, Cargos,
    Departamentos, Admissao, Funcionarios
)

@admin.register(Documentos)
class DocumentosAdmin(admin.ModelAdmin):
    list_display = ('cpf', 'pis', 'ctps', 'rg')
    search_fields = ('cpf', 'pis', 'ctps', 'rg')

@admin.register(Cbos)
class CbosAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'descricao')
    search_fields = ('codigo', 'descricao')

@admin.register(Cargos)
class CargosAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cbo', 'descricao')
    list_filter = ('cbo',)
    raw_id_fields = ('cbo',)
    search_fields = ('nome', 'descricao')

@admin.register(Departamentos)
class DepartamentosAdmin(admin.ModelAdmin):
    list_display = ('nome',)
    search_fields = ('nome',)

@admin.register(Admissao)
class AdmissaoAdmin(admin.ModelAdmin):
    list_display = ('matricula', 'cargo', 'departamento', 'data_admissao', 'salario')
    list_filter = ('cargo', 'departamento', 'data_admissao')
    raw_id_fields = ('cargo', 'departamento')
    date_hierarchy = 'data_admissao'

@admin.register(Funcionarios)
class FuncionariosAdmin(admin.ModelAdmin):
    list_display = ('nome', 'documentos', 'admissao', 'email', 'estatus')
    list_filter = ('admissao', 'estatus', 'logradouro')
    search_fields = ('nome', 'email', 'documentos__cpf')
    raw_id_fields = ('logradouro', 'documentos', 'admissao')
    date_hierarchy = 'data_admissao'
    list_per_page = 50
