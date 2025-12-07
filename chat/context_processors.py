# Em chat/context_processors.py (ARQUIVO CORRIGIDO)

from django.urls import reverse, NoReverseMatch
from django.conf import settings
from chat.models import ChatRoom
from asgiref.sync import sync_to_async
import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required



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

@login_required
def active_room_list(request):
    """Retorna lista de salas ativas do usuário"""
    try:
        # Sua lógica para buscar salas ativas
        rooms = []  # Substitua pela sua lógica
        return JsonResponse({
            'status': 'success',
            'rooms': rooms
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        })
@login_required
def get_user_list(request):
    """Retorna lista de usuários para DM"""
    try:
        from django.contrib.auth.models import User
        users = User.objects.exclude(id=request.user.id)
        user_data = [
            {
                'id': user.id,
                'name': user.get_full_name() or user.username,
                'email': user.email
            }
            for user in users
        ]
        return JsonResponse({
            'status': 'success',
            'users': user_data
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        })
    
@login_required
def task_list(request):
    """Retorna lista de tarefas"""
    try:
        # Sua lógica para buscar tarefas
        tasks = []  # Substitua pela sua lógica
        return JsonResponse({
            'status': 'success',
            'tasks': tasks
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        })

def chat_global_data(request):
    """Injeta dados globais do chat em todos os templates."""
    
    if not request.user.is_authenticated:
        return {'chat_urls': {}}

    urls = {}
    try:
        # URLs CORRETAS - sem duplicação
        urls['active_room_list'] = reverse('chat:get_active_room_list')
        urls['create_group_url'] = reverse('chat:create_group')
        urls['user_list'] = reverse('chat:get_user_list')
        urls['task_list'] = reverse('chat:get_task_list')
        urls['upload_image_url'] = reverse('chat:chat_image_upload')
        
        # Placeholders para URLs dinâmicas
        uuid_placeholder = '00000000-0000-0000-0000-000000000000'
        id_placeholder = 0
        
        urls['start_dm_base'] = reverse('chat:start_dm', args=[id_placeholder])
        urls['get_chat_history'] = reverse('chat:get_chat_history', args=[uuid_placeholder])
        
        # URL condicional de tarefas
        try:
            urls['get_task_chat_base'] = reverse('chat:get_task_chat', args=[id_placeholder])
        except NoReverseMatch:
            urls['get_task_chat_base'] = None
            
    except NoReverseMatch as e:
        print(f"❌ Erro nas URLs do chat: {e}")
        return {'chat_urls': {}}

    return {'chat_urls': urls}

def chat_urls(request):
    return {
        'active_room_list': '/chat/api/active-rooms/',  # Ou sua URL real
        # outras URLs do chat...
    }


