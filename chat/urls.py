
# chat/urls.py
from django.http import HttpResponse
from django.urls import path
from . import views

from django.contrib.staticfiles.views import serve
from django.views.defaults import page_not_found

app_name = 'chat'

urlpatterns = [
    # APIs básicas do Chat
  
    path('api/users/', views.get_user_list, name='get_user_list'),
    path('api/rooms/', views.get_active_chat_rooms, name='get_active_room_list'), 
    path('api/history/<uuid:room_id>/', views.get_chat_history, name='get_chat_history'),
    path('api/tasks/', views.get_task_list, name='get_task_list'),
    
    # Ações do Chat
    path('dm/<int:user_id>/', views.start_or_get_dm_chat, name='start_dm'),
    path('group/create/', views.create_group_chat, name='create_group'),
    
    # Upload de imagens (compatibilidade)
    path('upload/image/', views.ChatImageUploadView.as_view(), name='chat_image_upload'),

    # Ignorar requisição do Chrome DevTools
    path('.well-known/appspecific/com.chrome.devtools.json', 
         lambda request: HttpResponse('{}', content_type='application/json')),
]

# Adiciona URL de tarefa condicionalmente
try:
    from tarefas.models import Tarefas
    urlpatterns.append(
        path('task/<int:task_id>/', views.get_or_create_task_chat, name='get_task_chat')
    )
except ImportError:
    pass



