
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, Permission # Importe Permission
from .models import Usuario, GrupoProxy, PermissaoProxy
from .forms import UsuarioCreationForm, UsuarioChangeForm, GrupoForm

# ---
# Configuração do Admin de Usuário
# ---

# É uma boa prática garantir que o modelo seja desregistrado antes de definir seu admin,
# especialmente se você estiver recarregando arquivos de admin durante o desenvolvimento.
if admin.site.is_registered(Usuario):
    admin.site.unregister(Usuario)

class UsuarioAdmin(BaseUserAdmin):
    form = UsuarioChangeForm
    add_form = UsuarioCreationForm

    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)
    filter_horizontal = ('groups', 'user_permissions',)

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Informações pessoais', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissões', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Datas importantes', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'first_name', 'last_name'),
        }),
    )

# Registre Usuario apenas uma vez
admin.site.register(Usuario, UsuarioAdmin)

# ---
# Configuração do Admin de Grupo
# ---

# Desregistre o admin padrão do Django para Group, se estiver registrado
if admin.site.is_registered(Group):
    admin.site.unregister(Group)

class GrupoAdmin(admin.ModelAdmin):
    form = GrupoForm
    filter_horizontal = ['permissions']
    list_display = ('name', 'count_users')

    def count_users(self, obj):
        return obj.user_set.count()
    count_users.short_description = 'Número de Usuários'

# Registre seu GrupoProxy personalizado com GrupoAdmin
# Adicionei a verificação para GrupoProxy aqui, caso seja necessário
if admin.site.is_registered(GrupoProxy):
    admin.site.unregister(GrupoProxy)
admin.site.register(GrupoProxy, GrupoAdmin)

# ---
# Configuração do Admin de Permissão
# ---

# Desregistre o admin padrão do Django para Permission, se estiver registrado
if admin.site.is_registered(Permission): # Certifique-se de que Permission foi importado
    admin.site.unregister(Permission)

class PermissaoAdmin(admin.ModelAdmin):
    list_display = ('name', 'content_type', 'codename')
    list_filter = ('content_type',)
    search_fields = ('name', 'codename')

# Registre seu PermissaoProxy personalizado com PermissaoAdmin
# ATENÇÃO: Adicionei a verificação para PermissaoProxy aqui!
if admin.site.is_registered(PermissaoProxy):
    admin.site.unregister(PermissaoProxy)
admin.site.register(PermissaoProxy, PermissaoAdmin)


