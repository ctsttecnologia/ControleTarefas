from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
       
    # APIs
    path('api/users/', views.get_user_list, name='get_user_list'),
    path('api/tasks/', views.get_task_list, name='get_task_list'),
    path('api/dm/start/<int:user_id>/', views.start_or_get_dm_chat, name='start_dm'),
    path('api/group/create/', views.create_group_chat, name='create_group'),
    path('api/task/<int:task_id>/', views.get_or_create_task_chat, name='get_task_chat'),
    path('api/history/<uuid:room_id>/', views.get_chat_history, name='get_history'),
    path('api/upload/', views.ChatImageUploadView.as_view(), name='upload_image'),
]
