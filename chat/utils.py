
# Adicione a nova linha
from django.urls import reverse

def seu_processador_de_urls(request):
    return {
        'chatUrls': {
            'create_group_url': reverse('chat:create_group'),
            'user_list': reverse('chat:user_list'),
            'task_list': reverse('chat:task_list'),
            'start_dm_base': reverse('chat:start_dm_base'),
            'get_task_chat_base': reverse('chat:get_task_chat_base'),
            'upload_image_url': reverse('chat:upload_image') 
        }
    }
