
from django.urls import path
from .views import HomeView

app_name = 'home'

urlpatterns = [
    # A rota raiz ('') desta app chama a HomeView e tem o nome 'home'
    path('', HomeView.as_view(), name='home'),
]
