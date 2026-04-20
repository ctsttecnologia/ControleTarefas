# chat/urls.py
from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    # APIs básicas do Chat
    path('api/rooms/', views.get_active_room_list, name='get_active_room_list'),
    path('api/users/', views.get_user_list, name='get_user_list'),
    path('api/history/<uuid:room_id>/', views.get_chat_history, name='get_chat_history'),
    path('api/tasks/', views.get_task_list, name='get_task_list'),

    # Ações do Chat
    path('api/start-dm/<int:user_id>/', views.start_or_get_dm_chat, name='start_dm'),
    path('api/create-group/', views.create_group_chat, name='create_group'),

    # Upload
    path('api/upload/', views.chat_file_upload, name='chat_image_upload'),
]

# URL condicional para tarefas
try:
    from tarefas.models import Tarefas
    urlpatterns.append(
        path('api/task/<int:task_id>/', views.get_or_create_task_chat, name='get_task_chat')
    )
except ImportError:
    pass
pass








