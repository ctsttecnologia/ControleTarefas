from django.contrib import admin
from django.utils.html import format_html
from .models import MinhaImagem

@admin.register(MinhaImagem)
class MinhaImagemAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'imagem_preview')
    search_fields = ('titulo',)

    def imagem_preview(self, obj):
        return format_html('<img src="{}" width="100" height="auto" />', obj.imagem.url)
    imagem_preview.short_description = 'Pré-visualização'

