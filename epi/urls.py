# epi/urls.py
from django.urls import path
from . import views

app_name = 'epi'

urlpatterns = [
    path('fichas/', views.listar_fichas, name='listar_fichas'),
    path('fichas/criar_fichas/', views.criar_ficha, name='criar_ficha'),
    path('fichas/<int:ficha_id>/', views.visualizar_ficha, name='visualizar_ficha'),
    path('fichas/<int:ficha_id>/pdf/', views.gerar_pdf, name='gerar_pdf'),
    path('fichas/<int:ficha_id>/word/', views.gerar_word, name='gerar_word'),

    path('api/funcionarios/', views.buscar_funcionario, name='buscar_funcionario'),

]


