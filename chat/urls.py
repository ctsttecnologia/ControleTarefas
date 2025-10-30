
# chat/urls.py
from django.urls import path
from . import views

app_name = 'chat' # Define um namespace para as URLs

urlpatterns = [
    path('', views.chat_list, name='chat_list'), # Lista de salas
    path('<uuid:room_id>/', views.room_view, name='room_view'), # Sala específica por UUID
    path('create/individual/', views.create_individual_chat, name='create_individual_chat'),
    path('create/group/', views.create_group_chat, name='create_group_chat'),
    path('create/task/<int:task_id>/', views.create_task_chat, name='create_task_chat'),
    path('admin/delete-old-messages/', views.delete_old_messages, name='delete_old_messages'),
    path('usuarios/', views.get_user_list, name='get_user_list'),
    path('start_chat/<int:user_id>/', views.start_or_get_chat, name='start_or_get_chat'),

    path('historico/<uuid:room_id>/', views.get_chat_history, name='get_chat_history'),

]

