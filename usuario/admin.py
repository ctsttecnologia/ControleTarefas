
# usuario/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.db.models import Count
from .models import Usuario, GrupoProxy, PermissaoProxy

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """
    Admin customizado para o modelo Usuario com cabeçalhos em português.
    """
    # Exibe as colunas na lista de usuários
    list_display = ('email', 'username', 'get_full_name', 'staff_status', 'active_status')
    
    # Adiciona a capacidade de filtrar por estes campos
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    
    # Campos que podem ser usados na barra de busca
    search_fields = ('email', 'username', 'first_name', 'last_name')
    
    # Ordem padrão da lista
    ordering = ('first_name', 'last_name')
    
    # Mantém os fieldsets que já tínhamos, eles usam os verbose_name dos modelos
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Informações Pessoais', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissões', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Datas Importantes', {'fields': ('last_login', 'date_joined')}),
    )
    filter_horizontal = ('groups', 'user_permissions',)

    # --- MÉTODOS PARA TRADUZIR CABEÇALHOS ---

    @admin.display(description='Status', boolean=True)
    def active_status(self, obj):
        return obj.is_active

    @admin.display(description='Equipe', boolean=True)
    def staff_status(self, obj):
        return obj.is_staff

# Desregistramos o Group original para usar nosso Proxy
admin.site.unregister(Group)

@admin.register(GrupoProxy)
class GrupoProxyAdmin(admin.ModelAdmin):
    list_display = ('name', 'user_count')
    search_fields = ('name',)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(users_count=Count('user'))

    @admin.display(description='Nº de Usuários')
    def user_count(self, obj):
        return obj.users_count

@admin.register(PermissaoProxy)
class PermissaoProxyAdmin(admin.ModelAdmin):
    # Traduzindo os cabeçalhos aqui também
    list_display = ('name', 'content_type_pt', 'codename')
    list_filter = ('content_type',)
    search_fields = ('name', 'codename')
    ordering = ('content_type__app_label', 'content_type__model', 'name')

    @admin.display(description='Tipo de Conteúdo')
    def content_type_pt(self, obj):
        return obj.content_type