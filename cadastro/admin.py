
from django.db import models
from django.utils import timezone
from .models import Logradouro
from django.contrib import admin

@admin.register(Logradouro)
class LogradouroAdmin(admin.ModelAdmin):
    list_display = ('endereco', 'numero', 'bairro', 'cidade', 'estado_uf', 'pais')
    list_filter = ('estados', 'cidade', 'bairro')
    search_fields = ('endereco', 'numero', 'cep', 'bairro', 'cidade')
    list_per_page = 20
    
    def estado_uf(self, obj):
        return obj.get_estados_display()
    estado_uf.short_description = 'Estados'
    
 