# Em chat/context_processors.py (ARQUIVO CORRIGIDO)

import json
from django.urls import reverse, NoReverseMatch
from django.conf import settings
from chat.models import ChatRoom


def chat_global_data(request):
    """
    Injeta dados globais do chat (como URLs) em todos os templates.
    """
    
    print("\n--- 🚀 [DEBUG] Context Processor INICIADO! ---")
    
    if not request.user.is_authenticated:
        print("--- 🛑 [DEBUG] FALHA: request.user NÃO está autenticado. Retornando {}.")
        return {'chat_urls_json': json.dumps({})}

    print(f"--- ✅ [DEBUG] Usuário autenticado: {request.user.username} ---")

    # 2. LÓGICA DAS SALAS DE CHAT (MOVIDA PARA CÁ)
    try:
        user_rooms = ChatRoom.objects.filter(
            participants=request.user
        ).distinct().order_by('-created_at')
        print(f"--- ✅ [DEBUG] {user_rooms.count()} salas de chat encontradas. ---")
    except Exception as e:
        print(f"--- 🛑 [DEBUG] FALHA ao buscar salas de chat: {e} ---")
        user_rooms = []

    urls = {}
    try:
        # ===================================================================
        # Renomeando as chaves para bater com o chat.js
        # ===================================================================
        
        urls['create_group_url'] = reverse('chat:create_group')        # RENOMEADO
        urls['user_list'] = reverse('chat:get_user_list')           # RENOMEADO
        urls['task_list'] = reverse('chat:get_task_list')           # RENOMEADO
        urls['upload_image_url'] = reverse('chat:chat_image_upload')
        
        uuid_placeholder = '00000000-0000-0000-0000-000000000000'
        id_placeholder = 0
        
        urls['start_dm_base'] = reverse('chat:start_dm', args=[id_placeholder]) # RENOMEADO
        urls['get_task_chat_base'] = reverse('chat:get_task_chat', args=[id_placeholder]) # RENOMEADO
        urls['get_chat_history'] = reverse('chat:get_chat_history', args=[uuid_placeholder])

        print("--- ✅ [DEBUG] URLs do chat resolvidas com SUCESSO. ---")
        
    except NoReverseMatch as e:
        print(f"--- 🛑 [DEBUG] FALHA: NoReverseMatch! Erro: {e}")
       
        return {'chat_urls_json': json.dumps({})} # Retorna vazio

    # Retorna o dicionário completo
    return {
        'chat_urls_json': json.dumps(urls),
        'user_chat_rooms': user_rooms
    }