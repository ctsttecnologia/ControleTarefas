

# chat/views.py
import json
import uuid
import os
import io
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone
from django.views import View
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.views.decorators.http import require_GET, require_POST
from django.conf import settings
from .models import ChatRoom, Message


# Imports opcionais
try:
    from PIL import Image
except ImportError:
    Image = None

from .models import ChatRoom

User = get_user_model()

# ======================== FUNÇÕES PRINCIPAIS ========================

@csrf_exempt
@require_http_methods(["GET"])
def get_user_list(request):
    """Lista usuários para criar grupos"""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'error': 'Não autenticado'}, status=401)
    
    try:
        users = User.objects.exclude(id=request.user.id).only('id', 'username', 'first_name', 'last_name')
        
        user_list = []
        for user in users:
            full_name = f"{user.first_name} {user.last_name}".strip()
            user_list.append({
                'id': user.id,
                'username': user.username,
                'display_name': full_name or user.username
            })
        
        return JsonResponse({
            'status': 'success',
            'users': user_list,
            'count': len(user_list)
        })
        
    except Exception as e:
        print(f"❌ Erro get_user_list: {e}")
        return JsonResponse({'status': 'error', 'error': str(e)})


@login_required
@require_GET
def get_chat_history(request, room_id):
    """Retorna o histórico de mensagens de uma sala"""
    try:
        # Verifica se a sala existe e o usuário tem acesso
        room = ChatRoom.objects.filter(
            id=room_id,
            participants=request.user
        ).first()
        
        if not room:
            return JsonResponse({
                'status': 'error',
                'error': 'Sala não encontrada ou acesso negado'
            }, status=404)
        
        # Busca as mensagens (últimas 100)
        messages = Message.objects.filter(room=room).select_related('user').order_by('timestamp')[:100]
        
        # Serializa as mensagens
        messages_data = []
        for msg in messages:
            message_dict = {
                'id': str(msg.id),
                'message': msg.content or '',
                'content': msg.content or '',  # Alias para compatibilidade
                'username': msg.user.get_full_name() or msg.user.username,
                'user_id': msg.user.id,
                'timestamp': msg.timestamp.isoformat(),
                'is_edited': msg.is_edited,
            }
            
            # Adiciona dados de arquivo se existir
            if msg.file_attachment:
                message_dict['message_type'] = 'file'
                message_dict['file_data'] = json.dumps({
                    'url': msg.file_attachment.url if msg.file_attachment else None,
                    'name': msg.original_filename or 'arquivo',
                    'size': msg.file_size,
                    'type': msg.file_type,
                })
            elif msg.image:
                message_dict['message_type'] = 'image'
                message_dict['image_url'] = msg.image.url if msg.image else None
            else:
                message_dict['message_type'] = 'text'
            
            messages_data.append(message_dict)
        
        print(f"📜 Retornando {len(messages_data)} mensagens para sala {room_id}")
        
        return JsonResponse({
            'status': 'success',
            'messages': messages_data,
            'room_id': str(room_id),
            'room_name': room.get_room_display_name(request.user),
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_task_list(request):
    """Lista tarefas do usuário"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Não autenticado'}, status=401)
    
    try:
        from tarefas.models import Tarefas
        
        user_tasks = Tarefas.objects.filter(
            Q(responsavel=request.user) | Q(usuario=request.user)
        ).distinct().only('id', 'titulo', 'descricao', 'status')
        
        tasks_data = []
        for task in user_tasks:
            tasks_data.append({
                'id': task.id,
                'titulo': task.titulo,
                'descricao': task.descricao[:100] + '...' if len(task.descricao or '') > 100 else task.descricao,
                'status': getattr(task, 'status', 'EM_ANDAMENTO')
            })
        
        return JsonResponse({
            'status': 'success',
            'tasks': tasks_data,
            'count': len(tasks_data)
        })
        
    except ImportError:
        return JsonResponse({
            'status': 'success',
            'tasks': [],
            'count': 0,
            'message': 'Módulo tarefas não disponível'
        })
    except Exception as e:
        print(f"❌ Erro get_task_list: {e}")
        return JsonResponse({'error': str(e)}, status=500)
    
@login_required
@require_GET
def get_active_room_list(request):
    """Retorna lista de salas ativas do usuário"""
    try:
        rooms = ChatRoom.objects.filter(
            participants=request.user
        ).prefetch_related('participants').order_by('-updated_at')
        
        rooms_data = []
        for room in rooms:
            rooms_data.append({
                'room_id': str(room.id),
                'room_name': room.get_room_display_name(request.user),
                'room_type': room.room_type,
                'last_message': room.get_last_message_preview(),
                'unread_count': room.get_unread_count(request.user),
                'updated_at': room.updated_at.isoformat() if room.updated_at else None,
            })
        
        return JsonResponse({
            'status': 'success',
            'rooms': rooms_data
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)

@login_required
def start_or_get_dm_chat(request, user_id):
    """Inicia ou busca chat DM"""
    try:
        other_user = get_object_or_404(User, id=user_id)
        
        if request.user.id == other_user.id:
            return JsonResponse({'status': 'error', 'error': 'Não pode DM consigo mesmo'}, status=400)
        
        room = ChatRoom.objects.filter(
            participants=request.user
        ).filter(
            participants=other_user
        ).filter(
            room_type='DM',
            is_group_chat=False
        ).annotate(
            count_participants=Count('participants')
        ).filter(
            count_participants=2
        ).first()
        
        if not room:
            room = ChatRoom.objects.create(
                name=f"DM: {request.user.username} & {other_user.username}",
                room_type='DM',
                is_group_chat=False
            )
            room.participants.add(request.user, other_user)
            
        # Se a sala for nova, notifica o outro usuário em tempo real
        is_new_room = False
        # tenta achar DM existente entre os dois usuários
        room = ChatRoom.objects.filter(room_type='DM', participants=request.user).filter(participants=other_user).distinct().first()

        if not room:
            # cria e adiciona participantes
            room = ChatRoom.objects.create(
                name=f"DM: {request.user.username} & {other_user.username}",
                room_type='DM',
                is_group_chat=False
            )
            room.participants.add(request.user, other_user)
            is_new_room = True

        # Se a sala for nova, notifica o outro usuário em tempo real
        if is_new_room:
            channel_layer = get_channel_layer()
            notification_data = {
                'type': 'new_chat_notification',
                'room_id': str(room.id),
                'room_name': f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
                'initiator_id': request.user.id,
            }
            async_to_sync(channel_layer.group_send)(
                f"notifications_{other_user.id}",
                notification_data
            )

        return JsonResponse({
            'status': 'success',
            'room_id': str(room.id),
            'room_name': f"{other_user.first_name} {other_user.last_name}".strip() or other_user.username
        })
        
    except Exception as e:
        print(f"❌ DM erro: {e}")
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@login_required  
def create_group_chat(request):
    """Cria chat em grupo"""
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        name = data.get('name', '').strip()
        participant_ids = data.get('participants', [])
        
        if not name:
            return JsonResponse({'status': 'error', 'error': 'Nome obrigatório'}, status=400)
        
        all_ids = [request.user.id] + [int(uid) for uid in participant_ids if uid]
        users = User.objects.filter(id__in=list(set(all_ids)))
        
        if users.count() < 2:
            return JsonResponse({'status': 'error', 'error': 'Mínimo 2 pessoas'}, status=400)
        
        room = ChatRoom.objects.create(
            name=name,
            room_type='GROUP', 
            is_group_chat=True
        )
        room.participants.set(users)
        
        return JsonResponse({
            'status': 'success',
            'room_id': str(room.id),
            'room_name': room.name
        })
        
    except Exception as e:
        print(f"❌ Grupo erro: {e}")
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)

@login_required
def get_or_create_task_chat(request, task_id):
    """Chat de tarefa"""
    try:
        from tarefas.models import Tarefas
        task = get_object_or_404(Tarefas, id=task_id)
        
        room, created = ChatRoom.objects.get_or_create(
            tarefa_id=task.id,
            room_type='TASK',
            defaults={
                'name': f"Tarefa: {task.titulo}",
                'is_group_chat': True
            }
        )
        
        participants = [request.user]
        if hasattr(task, 'usuario') and task.usuario:
            participants.append(task.usuario)
        if hasattr(task, 'responsavel') and task.responsavel:
            participants.append(task.responsavel)
        
        room.participants.add(*set(participants))
        
        return JsonResponse({
            'status': 'success',
            'room_id': str(room.id),
            'room_name': room.name
        })
        
    except Exception as e:
        print(f"❌ Task erro: {e}")
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)

# ======================== CLASSE DE UPLOAD ========================

class ChatImageUploadView(View):
    """Upload de imagens"""
    
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Não autenticado'}, status=401)
        
        try:
            if 'image' not in request.FILES:
                return JsonResponse({'error': 'Nenhuma imagem'}, status=400)
            
            image_file = request.FILES['image']
            
            if image_file.size > 5 * 1024 * 1024:  # 5MB
                return JsonResponse({'error': 'Muito grande (máx 5MB)'}, status=400)
            
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if image_file.content_type not in allowed_types:
                return JsonResponse({'error': 'Tipo não permitido'}, status=400)
            
            file_extension = os.path.splitext(image_file.name)[1].lower() or '.jpg'
            unique_filename = f"chat_images/{request.user.id}/{uuid.uuid4()}{file_extension}"
            
            file_path = default_storage.save(unique_filename, image_file)
            file_url = default_storage.url(file_path)
            
            return JsonResponse({
                'status': 'success',
                'file_path': file_path,
                'file_url': file_url,
                'file_name': os.path.basename(file_path),
                'file_size': image_file.size,
                'message': 'Imagem enviada'
            })
            
        except Exception as e:
            print(f"❌ Upload erro: {e}")
            return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_POST
def chat_file_upload(request):
    """Upload de arquivo para o chat"""
    try:
        file = request.FILES.get('file')
        room_id = request.POST.get('room_id')
        
        if not file:
            return JsonResponse({
                'status': 'error',
                'error': 'Nenhum arquivo enviado'
            }, status=400)
        
        if not room_id:
            return JsonResponse({
                'status': 'error',
                'error': 'room_id é obrigatório'
            }, status=400)
        
        # Validação de tamanho (10MB)
        max_size = 10 * 1024 * 1024
        if file.size > max_size:
            return JsonResponse({
                'status': 'error',
                'error': 'Arquivo muito grande (máximo 10MB)'
            }, status=400)
        
        # Gera nome único
        ext = os.path.splitext(file.name)[1]
        unique_name = f"{uuid.uuid4()}{ext}"
        file_path = f"chat_uploads/{room_id}/{unique_name}"
        
        # Salva o arquivo
        saved_path = default_storage.save(file_path, file)
        file_url = default_storage.url(saved_path)
        
        # Detecta tipo de arquivo
        content_type = file.content_type or 'application/octet-stream'
        
        return JsonResponse({
            'status': 'success',
            'file_data': {
                'url': file_url,
                'name': file.name,
                'size': file.size,
                'type': content_type,
            },
            'message': {
                'id': str(uuid.uuid4()),
                'message_type': 'file',
                'file_data': {
                    'url': file_url,
                    'name': file.name,
                    'size': file.size,
                    'type': content_type,
                }
            }
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)

