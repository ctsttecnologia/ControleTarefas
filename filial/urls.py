
from django.urls import path
from .views import SetFilialView

app_name = 'filial'

urlpatterns = [
    path('set/', SetFilialView.as_view(), name='set_filial'),
]
