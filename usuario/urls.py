from django.urls import include, path
from . import views
from django.contrib.auth import views as auth_views
from .views import user_login, user_register  # Importe suas views


app_name = 'usuario_login'  # Isso define o namespace

urlpatterns = [

    path('login/', user_login, name='login'),
    path('register/', user_register, name='register'),
    path('profile/', views.user_profile, name='profile'),
    path('logout/', views.user_logout, name='logout'),
    
]