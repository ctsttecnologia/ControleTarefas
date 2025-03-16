from django.urls import path
from . import views

app_name = 'seguranca_trabalho'

urlpatterns = [
    path('seguranca_trabalho/', views.seguranca_trabalho, name='seguranca_trabalho'),
    path('pesquisar_ficha/', views.pesquisar_ficha, name='pesquisar_ficha'),
    path('cadastrar_ficha_epi/', views.cadastrar_ficha_epi, name='cadastrar_ficha_epi'),
    path('editar_ficha_epi/<int:id>/', views.editar_ficha_epi, name='editar_ficha_epi'),
    path('deletar_ficha_epi/<int:id>/', views.deletar_ficha_epi, name='deletar_ficha_epi'),

    path('listar_equipamentos/', views.listar_equipamentos, name='listar_equipamentos'),
    path('cadastrar_equipamento/', views.cadastrar_equipamento, name='cadastrar_equipamento'),
    path('editar_equipamento/<int:id>/', views.editar_equipamento, name='editar_equipamento'),
    path('excluir_equipamento/<int:id>/', views.excluir_equipamento, name='excluir_equipamento'),
    
    path('ficha-epi/cadastrar/', views.cadastrar_ficha_epi, name='cadastrar_ficha_epi'),
    path('ficha-epi/gerar-pdf/', views.gerar_pdf, name='gerar_pdf'),
    path('ficha-epi/gerar-excel/', views.gerar_excel, name='gerar_excel'),
 

]