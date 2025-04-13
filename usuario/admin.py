from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group, Permission
from .models import Usuario, UsuarioCustomuser, CustomUserGroup, CustomUserPermission

# Configuração para o modelo Usuario
@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('nome', 'sobrenome', 'email')
    search_fields = ('nome', 'sobrenome', 'email')
    list_filter = ('nome', 'email')
    ordering = ('nome',)

# Configuração personalizada para UsuarioCustomuser (extendendo UserAdmin)
class CustomUserAdmin(UserAdmin):
    model = UsuarioCustomuser
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'matricula')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'matricula')
    ordering = ('username',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Informações Pessoais', {'fields': ('first_name', 'last_name', 'email', 'matricula')}),
        ('Permissões', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Datas Importantes', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'email', 'first_name', 'last_name', 'matricula', 'is_staff', 'is_active'),
        }),
    )

# Registrando o modelo customizado
admin.site.register(UsuarioCustomuser, CustomUserAdmin)

# Configuração para as tabelas de relacionamento
@admin.register(CustomUserGroup)
class UsuarioCustomuserGroupsAdmin(admin.ModelAdmin):
    list_display = ('customuser', 'group')
    list_filter = ('group',)
    search_fields = ('customuser__username', 'group__name')

@admin.register(CustomUserPermission)
class UsuarioCustomuserUserPermissionsAdmin(admin.ModelAdmin):
    list_display = ('customuser', 'permission')
    list_filter = ('permission__content_type',)
    search_fields = ('customuser__username', 'permission__name')

# Melhorando a exibição padrão do Group
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    filter_horizontal = ('permissions',)

# Re-registrando Group com a configuração personalizada
admin.site.unregister(Group)
admin.site.register(Group, GroupAdmin)