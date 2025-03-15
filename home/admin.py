from django.contrib import admin
from .models import MinhaImagem

#Segurança: Em produção, nunca sirva arquivos de mídia diretamente pelo Django. Use um servidor web como Nginx ou Apache para servir esses arquivos.

admin.site.register(MinhaImagem)
