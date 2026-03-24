
# usuario/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin, GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import Group
from django.db.models import Count
from .models import Usuario, GrupoProxy, PermissaoProxy, Filial, GroupCardPermissions
from django.forms import CheckboxSelectMultiple
from .forms import GroupCardPermissionsForm 

# -----------------------------------------------------------------------------
# Admin para Filial (Necessário para o autocomplete no UsuarioAdmin)
# -----------------------------------------------------------------------------
@admin.register(Filial)
class FilialAdmin(admin.ModelAdmin):
    list_display = ('nome',)
    search_fields = ('nome',)

# -----------------------------------------------------------------------------
# Admin para Usuario (Versão final e refatorada)
# -----------------------------------------------------------------------------
@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    """
    Admin customizado para o modelo Usuario, com gerenciamento de filiais,
    melhor performance e organização aprimorada.
    """
    # --- Configurações da LISTA de Usuários ---
    list_display = (
        'email',
        'get_full_name',
        'filial_ativa',
        'is_staff',
        'is_active',
    )
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups', 'filial_ativa')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('first_name', 'last_name')
    list_select_related = ('filial_ativa',)

    # --- Configurações do FORMULÁRIO de Edição ---
    # Usamos os fieldsets da classe base e adicionamos o nosso.
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Informações Pessoais', {'fields': ('first_name', 'last_name', 'email')}),
        ('Acesso a Filiais', {'fields': ('filial_ativa', 'filiais_permitidas')}), # Nosso fieldset customizado
        ('Permissões', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Datas Importantes', {'fields': ('last_login', 'date_joined')}),
    )

    filter_horizontal = ('groups', 'user_permissions', 'filiais_permitidas')
    autocomplete_fields = ('filial_ativa',)

# -----------------------------------------------------------------------------
# Admin para Grupos (Usando Proxy)
# -----------------------------------------------------------------------------
admin.site.unregister(Group) # Desregistra o original

@admin.register(GrupoProxy)
class GrupoProxyAdmin(BaseGroupAdmin):
    """
    Admin para o Proxy de Grupo. Herda de GroupAdmin para manter
    funcionalidades essenciais e adiciona a contagem de usuários.
    """
    list_display = ('name', 'user_count')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(users_count=Count('user'))

    @admin.display(description='Nº de Usuários', ordering='users_count')
    def user_count(self, obj):
        return obj.users_count

# -----------------------------------------------------------------------------
# Admin para Permissões (Usando Proxy, sem alterações)
# -----------------------------------------------------------------------------
@admin.register(PermissaoProxy)
class PermissaoProxyAdmin(admin.ModelAdmin):
    list_display = ('name', 'content_type_pt', 'codename')
    list_filter = ('content_type',)
    search_fields = ('name', 'codename')
    ordering = ('content_type__app_label', 'content_type__model', 'name')

    @admin.display(description='Tipo de Conteúdo')
    def content_type_pt(self, obj):
        return obj.content_type
    
# -----------------------------------------------------------------------------
# No seu admin.py
# -----------------------------------------------------------------------------

@admin.register(GroupCardPermissions)
class GroupCardPermissionsAdmin(admin.ModelAdmin):

    form = GroupCardPermissionsForm
    list_display = ('group',)
    search_fields = ('group__name',)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        ALL_CARD_CHOICES = [
            ('tarefas', 'Tarefas'),
            ('clientes', 'Clientes'),
            ('dp', 'Departamento Pessoal'),
            ('sst', 'Segurança do Trabalho'),
            ('endereco', 'Logradouro'),
            ('veiculos', 'Veículos'),
            ('operacao', 'Operação'),
            ('main_dashboard', 'Dashboard Integrado'),
            # ═══ Novos cards ═══
            ('ata_reuniao', 'Atas de Reunião'),
            ('suprimentos', 'Suprimentos'),
            ('documentos', 'Documentos'),
            ('telefones', 'Controle de Telefones'),
            ('estoque', 'Estoque'),
        ]

        form.base_fields['cards_visiveis'].widget = CheckboxSelectMultiple(
            choices=ALL_CARD_CHOICES
        )
        return form

