from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
       
    # APIs
    path('create_group/', views.create_group_chat, name='create_group'),
    path('get_users/', views.get_user_list, name='get_user_list'),
    path('get_tasks/', views.get_task_list, name='get_task_list'),
    path('dm/<int:user_id>/', views.start_or_get_dm_chat, name='start_dm'),
    path('task/<int:task_id>/', views.get_or_create_task_chat, name='get_task_chat'),

    path('api/history/<uuid:room_id>/', views.get_chat_history, name='get_chat_history'),
 
    path('upload_image_url/', views.ChatImageUploadView.as_view(), name='chat_image_upload'),

]
