from django.urls import path
from . import views




urlpatterns = [
    path('seguranca_trabalho/', views.seguranca_trabalho, name='seguranca_trabalho'),
    path('pesquisar_ficha/', views.pesquisar_ficha, name='pesquisar_ficha'),
    path('cadastrar_ficha_epi/', views.cadastrar_ficha_epi, name='cadastrar_ficha_epi'),
    path('editar_ficha_epi/<int:id>/', views.editar_ficha_epi, name='editar_ficha_epi'),
    path('deletar_ficha_epi/<int:id>/', views.deletar_ficha_epi, name='deletar_ficha_epi'),

    path('equipamentos/', views.listar_equipamentos, name='listar_equipamentos'),
    path('equipamentos/cadastrar/', views.cadastrar_equipamento, name='cadastrar_equipamento'),
    path('equipamentos/editar/<int:id>/', views.editar_equipamento, name='editar_equipamento'),
    path('equipamentos/excluir/<int:id>/', views.excluir_equipamento, name='excluir_equipamento'),
]