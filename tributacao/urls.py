
# tributacao/urls.py

from django.urls import path
from . import views

app_name = "tributacao"

urlpatterns = [
    # Dashboard
    path("", views.dashboard, name="dashboard"),

    # NCM
    path("ncm/", views.ncm_list, name="ncm_list"),
    path("ncm/novo/", views.ncm_create, name="ncm_create"),
    path("ncm/<int:pk>/editar/", views.ncm_update, name="ncm_update"),
    path("ncm/<int:pk>/excluir/", views.ncm_delete, name="ncm_delete"),

    # CFOP
    path("cfop/", views.cfop_list, name="cfop_list"),
    path("cfop/novo/", views.cfop_create, name="cfop_create"),
    path("cfop/<int:pk>/editar/", views.cfop_update, name="cfop_update"),
    path("cfop/<int:pk>/excluir/", views.cfop_delete, name="cfop_delete"),

    # CST
    path("cst/", views.cst_list, name="cst_list"),
    path("cst/novo/", views.cst_create, name="cst_create"),
    path("cst/<int:pk>/editar/", views.cst_update, name="cst_update"),
    path("cst/<int:pk>/excluir/", views.cst_delete, name="cst_delete"),

    # Grupo Tributário
    path("grupo/", views.grupo_list, name="grupo_list"),
    path("grupo/novo/", views.grupo_create, name="grupo_create"),
    path("grupo/<int:pk>/", views.grupo_detail, name="grupo_detail"),
    path("grupo/<int:pk>/editar/", views.grupo_update, name="grupo_update"),
    path("grupo/<int:pk>/excluir/", views.grupo_delete, name="grupo_delete"),

    path('api/grupo/<int:pk>/', views.grupo_tributario_api, name='grupo_api'),
    path('api/grupo/<int:pk>/', views.api_grupo_detail, name='api_grupo_detail'),
]

