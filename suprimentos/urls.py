
# suprimentos/urls.py
from django.urls import path
from . import views

app_name = 'suprimentos'

urlpatterns = [
    # URL para a lista de parceiros (ex: /suprimentos/)
    path('', views.ParceiroListView.as_view(), name='parceiro_list'),

    # URL para criar um novo parceiro (ex: /suprimentos/novo/)
    path('novo/', views.ParceiroCreateView.as_view(), name='parceiro_create'),

    # URL para ver os detalhes de um parceiro (ex: /suprimentos/1/)
    path('<int:pk>/', views.ParceiroDetailView.as_view(), name='parceiro_detail'),

    # URL para editar um parceiro (ex: /suprimentos/1/editar/)
    path('<int:pk>/editar/', views.ParceiroUpdateView.as_view(), name='parceiro_update'),

    # URL para deletar um parceiro (ex: /suprimentos/1/deletar/)
    path('<int:pk>/deletar/', views.ParceiroDeleteView.as_view(), name='parceiro_delete'),
]
