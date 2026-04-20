
# chat/views.py

import json
import logging
import os
import uuid
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.storage import default_storage
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.decorators.http import require_GET, require_POST
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from core.decorators import app_permission_required
from core.mixins import AppPermissionMixin
from .models import ChatRoom, Message

logger = logging.getLogger(__name__)

User = get_user_model()

_APP = 'chat'


# =============================================================================
# HELPER — Verificação de participante
# =============================================================================

def _get_room_for_user(user, room_id):
    """Retorna a sala se o usuário for participante, ou None."""
    return ChatRoom.objects.filter(
        id=room_id,
        participants=user,
    ).first()


# =============================================================================
# LISTA DE USUÁRIOS
# =============================================================================

@login_required                     # 3º — checa login primeiro (mais externo)
@app_permission_required('chat')    # 2º — checa permissão do app
@require_GET                        # 1º — valida método HTTP (mais interno)
def get_user_list(request):
    """Lista usuários para criar grupos/DMs."""
    try:
        qs = User.objects.filter(
            is_active=True
        ).exclude(
            id=request.user.id
        ).only('id', 'username', 'first_name', 'last_name')

        user_list = []
        for user in qs:
            full_name = f"{user.first_name} {user.last_name}".strip()
            user_list.append({
                'id': user.id,
                'username': user.username,
                'display_name': full_name or user.username,
            })

        return JsonResponse({
            'status': 'success',
            'users': user_list,
            'count': len(user_list),
        })

    except Exception as e:
        logger.exception("Erro get_user_list")
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


# =============================================================================
# HISTÓRICO DE MENSAGENS
# =============================================================================

@login_required
@app_permission_required('chat')
@require_GET
def get_chat_history(request, room_id):
    """Retorna o histórico de mensagens de uma sala."""
    try:
        room = _get_room_for_user(request.user, room_id)

        if not room:
            return JsonResponse({
                'status': 'error',
                'error': 'Sala não encontrada ou acesso negado',
            }, status=404)

        messages_qs = Message.objects.filter(
            room=room
        ).select_related('user').order_by('timestamp')[:100]

        messages_data = []
        for msg in messages_qs:
            message_dict = {
                'id': str(msg.id),
                'message': msg.content or '',
                'content': msg.content or '',
                'username': msg.user.get_full_name() or msg.user.username,
                'user_id': msg.user.id,
                'timestamp': msg.timestamp.isoformat(),
                'is_edited': msg.is_edited,
            }

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

        logger.debug("Retornando %d mensagens para sala %s", len(messages_data), room_id)

        return JsonResponse({
            'status': 'success',
            'messages': messages_data,
            'room_id': str(room_id),
            'room_name': room.get_room_display_name(request.user),
        })

    except Exception as e:
        logger.exception("Erro get_chat_history sala=%s", room_id)
        return JsonResponse({
            'status': 'error',
            'error': str(e),
        }, status=500)


# =============================================================================
# LISTA DE TAREFAS
# =============================================================================

@login_required
@app_permission_required('chat')
@require_GET
def get_task_list(request):
    """Lista tarefas do usuário."""
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
                'descricao': (task.descricao[:100] + '...') if len(task.descricao or '') > 100 else task.descricao,
                'status': getattr(task, 'status', 'EM_ANDAMENTO'),
            })

        return JsonResponse({
            'status': 'success',
            'tasks': tasks_data,
            'count': len(tasks_data),
        })

    except ImportError:
        return JsonResponse({
            'status': 'success',
            'tasks': [],
            'count': 0,
            'message': 'Módulo tarefas não disponível',
        })
    except Exception as e:
        logger.exception("Erro get_task_list")
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


# =============================================================================
# LISTA DE SALAS ATIVAS
# =============================================================================

@login_required
@app_permission_required('chat')
@require_GET
def get_active_room_list(request):
    """Retorna lista de salas ativas do usuário."""
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
            'rooms': rooms_data,
        })

    except Exception as e:
        logger.exception("Erro get_active_room_list")
        return JsonResponse({
            'status': 'error',
            'error': str(e),
        }, status=500)


# =============================================================================
# DM
# =============================================================================

@login_required
@app_permission_required('chat')
@require_GET
def start_or_get_dm_chat(request, user_id):
    """Inicia ou busca chat DM com outro usuário."""
    try:
        other_user = get_object_or_404(User, id=user_id)

        if request.user.id == other_user.id:
            return JsonResponse({
                'status': 'error',
                'error': 'Não pode enviar DM para si mesmo',
            }, status=400)

        room = ChatRoom.objects.filter(
            room_type='DM',
            is_group_chat=False,
            participants=request.user,
        ).filter(
            participants=other_user,
        ).annotate(
            count_participants=Count('participants')
        ).filter(
            count_participants=2
        ).first()

        is_new_room = False

        if not room:
            room = ChatRoom.objects.create(
                name=f"DM: {request.user.username} & {other_user.username}",
                room_type='DM',
                is_group_chat=False,
            )
            room.participants.add(request.user, other_user)
            is_new_room = True

        if is_new_room:
            try:
                channel_layer = get_channel_layer()
                notification_data = {
                    'type': 'new_chat_notification',
                    'room_id': str(room.id),
                    'room_name': (
                        f"{request.user.first_name} {request.user.last_name}".strip()
                        or request.user.username
                    ),
                    'initiator_id': request.user.id,
                }
                async_to_sync(channel_layer.group_send)(
                    f"notifications_{other_user.id}",
                    notification_data,
                )
            except Exception as e:
                logger.warning("Falha ao notificar novo DM: %s", e)

        return JsonResponse({
            'status': 'success',
            'room_id': str(room.id),
            'room_name': (
                f"{other_user.first_name} {other_user.last_name}".strip()
                or other_user.username
            ),
        })

    except Exception as e:
        logger.exception("Erro start_or_get_dm_chat user_id=%s", user_id)
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


# =============================================================================
# GRUPO
# =============================================================================

@login_required
@app_permission_required('chat')
@require_POST
def create_group_chat(request):
    """Cria chat em grupo."""
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        name = data.get('name', '').strip()
        participant_ids = data.get('participants', [])

        if not name:
            return JsonResponse({
                'status': 'error',
                'error': 'Nome obrigatório',
            }, status=400)

        all_ids = {request.user.id} | {int(uid) for uid in participant_ids if uid}
        users = User.objects.filter(id__in=all_ids)

        if users.count() < 2:
            return JsonResponse({
                'status': 'error',
                'error': 'Mínimo 2 pessoas',
            }, status=400)

        room = ChatRoom.objects.create(
            name=name,
            room_type='GROUP',
            is_group_chat=True,
        )
        room.participants.set(users)

        return JsonResponse({
            'status': 'success',
            'room_id': str(room.id),
            'room_name': room.name,
        })

    except Exception as e:
        logger.exception("Erro create_group_chat")
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


# =============================================================================
# TAREFA
# =============================================================================

@login_required
@app_permission_required('chat')
def get_or_create_task_chat(request, task_id):
    """Chat de tarefa."""
    try:
        from tarefas.models import Tarefas
        task = get_object_or_404(Tarefas, id=task_id)

        room, created = ChatRoom.objects.get_or_create(
            tarefa_id=task.id,
            room_type='TASK',
            defaults={
                'name': f"Tarefa: {task.titulo}",
                'is_group_chat': True,
            }
        )

        participants = {request.user}
        if hasattr(task, 'usuario') and task.usuario:
            participants.add(task.usuario)
        if hasattr(task, 'responsavel') and task.responsavel:
            participants.add(task.responsavel)

        room.participants.add(*participants)

        return JsonResponse({
            'status': 'success',
            'room_id': str(room.id),
            'room_name': room.name,
        })

    except Exception as e:
        logger.exception("Erro get_or_create_task_chat task_id=%s", task_id)
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


# =============================================================================
# UPLOAD — Imagens (CBV) — já tinha AppPermissionMixin ✅
# =============================================================================

class ChatImageUploadView(LoginRequiredMixin, AppPermissionMixin, View):
    """Upload de imagens para o chat."""
    app_label_required = _APP

    def post(self, request):
        try:
            if 'image' not in request.FILES:
                return JsonResponse({'error': 'Nenhuma imagem'}, status=400)

            image_file = request.FILES['image']

            if image_file.size > 5 * 1024 * 1024:
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
                'message': 'Imagem enviada',
            })

        except Exception as e:
            logger.exception("Erro upload imagem")
            return JsonResponse({'error': str(e)}, status=500)


# =============================================================================
# UPLOAD — Arquivos (FBV)
# =============================================================================

@login_required
@app_permission_required('chat')
@require_POST
def chat_file_upload(request):
    """Upload de arquivo para o chat."""
    try:
        file = request.FILES.get('file')
        room_id = request.POST.get('room_id')

        if not file:
            return JsonResponse({
                'status': 'error',
                'error': 'Nenhum arquivo enviado',
            }, status=400)

        if not room_id:
            return JsonResponse({
                'status': 'error',
                'error': 'room_id é obrigatório',
            }, status=400)

        room = _get_room_for_user(request.user, room_id)
        if not room:
            return JsonResponse({
                'status': 'error',
                'error': 'Sala não encontrada ou acesso negado',
            }, status=403)

        max_size = 10 * 1024 * 1024
        if file.size > max_size:
            return JsonResponse({
                'status': 'error',
                'error': 'Arquivo muito grande (máximo 10MB)',
            }, status=400)

        ext = os.path.splitext(file.name)[1]
        unique_name = f"{uuid.uuid4()}{ext}"
        file_path = f"chat_uploads/{room_id}/{unique_name}"

        saved_path = default_storage.save(file_path, file)
        file_url = default_storage.url(saved_path)

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
                },
            },
        })

    except Exception as e:
        logger.exception("Erro chat_file_upload")
        return JsonResponse({
            'status': 'error',
            'error': str(e),
        }, status=500)


