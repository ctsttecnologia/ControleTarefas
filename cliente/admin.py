from django.contrib import admin

from django.contrib import admin
from .models import Cliente

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    
    list_display = ('contrato', 'razao_social')