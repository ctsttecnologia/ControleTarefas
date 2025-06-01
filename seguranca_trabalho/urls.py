from django.urls import path
from . import views
from django.views.decorators.csrf import csrf_exempt
from seguranca_trabalho import views
from .views import exportar_equipamentos_excel

app_name = 'seguranca_trabalho'

urlpatterns = [
    path('', views.seguranca_trabalho, name='seguranca_trabalho'),
    path('pesquisar_ficha/', views.pesquisar_ficha, name='pesquisar_ficha'),
    path('ficha-epi/gerar-pdf/', views.gerar_pdf, name='gerar_pdf'),
    path('ficha-epi/gerar-excel/', views.gerar_excel, name='gerar_excel'),

    path('', views.seguranca_trabalho, name='seguranca_trabalho'),
    path('equipamentos/', views.listar_equipamentos, name='listar_equipamentos'),
    path('equipamentos/cadastrar/', views.cadastrar_equipamento, name='cadastrar_equipamento'),
    path('equipamentos/editar/<int:id>/', views.editar_equipamento, name='editar_equipamento'),
    path('equipamentos/excluir/<int:id>/', views.excluir_equipamento, name='excluir_equipamento'),
    path('verificar-codigo-ca/', csrf_exempt(views.verificar_codigo_ca), name='verificar_codigo_ca'),
    path('equipamentos/exportar-excel/', exportar_equipamentos_excel, name='exportar_equipamentos_excel'),
      

]

