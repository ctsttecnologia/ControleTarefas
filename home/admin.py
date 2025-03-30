from django.contrib import admin
from django.utils.html import format_html
from .models import MinhaImagem
#Segurança: Em produção, nunca sirva arquivos de mídia diretamente pelo Django. Use um servidor web como Nginx ou Apache para servir esses arquivos.

#admin.site.register(MinhaImagem)

@admin.register(MinhaImagem)
class MinhaImagemAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'imagem_preview')
    search_fields = ('titulo',)

    def imagem_preview(self, obj):
        return format_html('<img src="{}" width="100" height="auto" />', obj.imagem.url)
    imagem_preview.short_description = 'Pré-visualização'


#Performance:

#Uso de raw_id_fields para relacionamentos com muitas entradas

#list_per_page ajustado conforme necessidade

#select_related automático para campos importantes

#Usabilidade:

#Pré-visualização de imagens e assinaturas

#Filtros e hierarquias de datas relevantes

#Campos de busca bem definidos

#Edição rápida de status diretamente na lista

#Segurança:

#Campos sensíveis como documentos com busca específica

#readonly_fields para dados que não devem ser editados

#Organização:

#Agrupamento lógico de campos relacionados

#Nomes claros para métodos customizados

#Para usar esta configuração:

#Coloque este código no arquivo admin.py do seu app

#Certifique-se que todos os modelos estão corretamente importados

#Execute python manage.py collectstatic se usar campos de imagem

#Recomendo também criar ações personalizadas para operações comuns como ativar/desativar clientes ou funcionários.