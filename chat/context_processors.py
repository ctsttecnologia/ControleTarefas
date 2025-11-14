# Em chat/context_processors.py (ARQUIVO CORRIGIDO)

import json
from django.urls import reverse, NoReverseMatch
from django.conf import settings
from chat.models import ChatRoom
from asgiref.sync import sync_to_async

# Novo para o template:
def get_user_chat_rooms_sync(user):
    """ Função síncrona para buscar as salas de chat (para ser chamada no template). """
    from chat.models import ChatRoom
    if not user.is_authenticated:
        return []
    try:
        # AQUI está a lógica de banco de dados
        return list(ChatRoom.objects.filter(participants=user).distinct().order_by('-created_at'))
    except Exception:
        return []


def chat_global_data(request):
    """
    Injeta dados globais do chat (como URLs) em todos os templates.
    """    
    if not request.user.is_authenticated:
        
        return {'chat_urls_json': json.dumps({})}

    # 2. LÓGICA DAS SALAS DE CHAT (MOVIDA PARA CÁ)
    try:
        user_rooms = ChatRoom.objects.filter(
            participants=request.user
        ).distinct().order_by('-created_at')
        
    except Exception as e:
        
        user_rooms = []

    urls = {}
    try:
        # ===================================================================
        # Renomeando as chaves para bater com o chat.js
        # ===================================================================
        
        urls['active_room_list'] = reverse('chat:get_active_chat_rooms')
        urls['create_group_url'] = reverse('chat:create_group')        # RENOMEADO
        urls['user_list'] = reverse('chat:get_user_list')           # RENOMEADO
        urls['task_list'] = reverse('chat:get_task_list')           # RENOMEADO
        urls['upload_image_url'] = reverse('chat:chat_image_upload')
        
        uuid_placeholder = '00000000-0000-0000-0000-000000000000'
        id_placeholder = 0
        
        urls['start_dm_base'] = reverse('chat:start_dm', args=[id_placeholder]) # RENOMEADO
        urls['get_task_chat_base'] = reverse('chat:get_task_chat', args=[id_placeholder]) # RENOMEADO
        urls['get_chat_history'] = reverse('chat:get_chat_history', args=[uuid_placeholder])
        
    except NoReverseMatch as e:
          
        return {'chat_urls_json': json.dumps({})} # Retorna vazio

    # Retorna o dicionário completo
    return {
        'chat_urls_json': json.dumps(urls),
        'get_user_chat_rooms': get_user_chat_rooms_sync
    }


