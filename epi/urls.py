from django.urls import path
from . import views

urlpatterns = [
    path('fichas/', views.listar_fichas, name='listar_fichas'),
    path('fichas/nova/', views.criar_ficha, name='criar_ficha'),
    path('fichas/visualizar/<int:ficha_id>/', views.visualizar_ficha, name='visualizar_ficha'),
    path('fichas/pdf/<int:ficha_id>/', views.gerar_pdf, name='gerar_pdf'),
    path('fichas/word/<int:ficha_id>/', views.gerar_word, name='gerar_word'),
]