
# chat/views.py
import json
import logging
import os
import uuid

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Count, IntegerField, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.decorators.http import require_GET, require_POST

from core.decorators import app_permission_required
from core.mixins import AppPermissionMixin, FuncionarioRequiredMixin

from .models import ChatRoom, Message, MessageRead
from .validators import validate_uploaded_file

logger = logging.getLogger(__name__)
User = get_user_model()

_APP = 'chat'
USERS_CACHE_KEY = 'chat:users:v1'   # invalidada em chat/signals.py
USERS_TTL = 60
HISTORY_LIMIT = 100
MAX_UPLOAD = 10 * 1024 * 1024
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

ERR_INTERNAL = 'Erro interno. Tente novamente.'


# =============================================================================
# HELPERS
# =============================================================================

def _error(msg, status=400):
    return JsonResponse({'status': 'error', 'error': msg}, status=status)


def _display_name(u):
    return f"{u.first_name} {u.last_name}".strip() or u.username


def _get_room_for_user(user, room_id):
    """Sala se o usuário for participante, senão None (id inválido também)."""
    try:
        return ChatRoom.objects.filter(id=room_id, participants=user).first()
    except (ValueError, ValidationError):
        return None


def _group_send(group, payload):
    """Push WS tolerante a falha (Redis offline não derruba a view)."""
    try:
        layer = get_channel_layer()
        if layer:
            async_to_sync(layer.group_send)(group, payload)
    except Exception:
        logger.warning("Falha no push WS group=%s", group, exc_info=True)


def _notify_new_room(room, creator, recipient_ids):
    """Avisa (após commit) os demais participantes de uma nova sala."""
    name = room.name if room.room_type != 'DM' else _display_name(creator)
    rid, cid = str(room.id), creator.id

    def _send():
        for uid in recipient_ids:
            _group_send(f'notifications_{uid}', {
                'type': 'new_chat_notification',
                'room_id': rid,
                'room_name': name,
                'initiator_id': cid,
            })

    transaction.on_commit(_send)


# =============================================================================
# PAYLOADS REUTILIZÁVEIS (usados por views individuais e pelo bootstrap)
# =============================================================================

def _users_payload(user):
    def fetch():
        return [
            {
                'id': u.id,
                'username': u.username,
                'display_name': _display_name(u),
            }
            for u in User.objects.filter(is_active=True)
            .only('id', 'username', 'first_name', 'last_name')
        ]

    all_users = cache.get_or_set(USERS_CACHE_KEY, fetch, USERS_TTL)
    return [u for u in all_users if u['id'] != user.id]


def _tasks_payload(user):
    try:
        from tarefas.models import Tarefas
    except ImportError:
        return []

    qs = (
        Tarefas.objects
        .filter(Q(responsavel=user) | Q(usuario=user))
        .distinct()
        .only('id', 'titulo', 'descricao', 'status')
    )
    out = []
    for t in qs:
        desc = t.descricao or ''
        out.append({
            'id': t.id,
            'titulo': t.titulo,
            'descricao': (desc[:100] + '...') if len(desc) > 100 else desc,
            'status': getattr(t, 'status', 'EM_ANDAMENTO'),
        })
    return out


def _rooms_payload(user):
    """Salas do usuário em UMA query (+1 prefetch), sem N+1."""
    last = Message.objects.filter(room=OuterRef('pk')).order_by('-timestamp')
    unread = (
        Message.objects.filter(room=OuterRef('pk'))
        .exclude(user=user)
        .exclude(message_reads__user=user)
        .order_by()
        .values('room')
        .annotate(c=Count('pk'))
        .values('c')
    )

    rooms = (
        ChatRoom.objects
        .filter(participants=user)
        .prefetch_related('participants')
        .annotate(
            unread=Coalesce(
                Subquery(unread, output_field=IntegerField()), 0,
            ),
            last_content=Subquery(last.values('content')[:1]),
            last_file=Subquery(last.values('file_attachment')[:1]),
            last_image=Subquery(last.values('image')[:1]),
        )
        .order_by('-updated_at')
    )

    data = []
    for r in rooms:
        if r.room_type == 'DM':
            other = next(
                (p for p in r.participants.all() if p.id != user.id), None,
            )
            name = _display_name(other) if other else 'Usuário Desconhecido'
        else:
            name = r.name or 'Chat Geral'

        if r.last_file:
            preview = '📎 Arquivo'
        elif r.last_image:
            preview = '📷 [Imagem]'
        else:
            c = r.last_content or ''
            preview = (c[:40] + '…') if len(c) > 40 else c

        data.append({
            'room_id': str(r.id),
            'room_name': name,
            'room_type': r.room_type,
            'last_message': preview,
            'unread_count': r.unread,
            'updated_at': r.updated_at.isoformat() if r.updated_at else None,
        })
    return data


# =============================================================================
# LISTAS + BOOTSTRAP
# =============================================================================

@app_permission_required(_APP)
@require_GET
def get_user_list(request):
    try:
        users = _users_payload(request.user)
        return JsonResponse({'status': 'success', 'users': users, 'count': len(users)})
    except Exception:
        logger.exception("Erro get_user_list")
        return _error(ERR_INTERNAL, 500)


@app_permission_required(_APP)
@require_GET
def get_task_list(request):
    try:
        tasks = _tasks_payload(request.user)
        return JsonResponse({'status': 'success', 'tasks': tasks, 'count': len(tasks)})
    except Exception:
        logger.exception("Erro get_task_list")
        return _error(ERR_INTERNAL, 500)


@app_permission_required(_APP)
@require_GET
def get_active_room_list(request):
    try:
        return JsonResponse({'status': 'success', 'rooms': _rooms_payload(request.user)})
    except Exception:
        logger.exception("Erro get_active_room_list")
        return _error(ERR_INTERNAL, 500)


@app_permission_required(_APP)
@require_GET
def chat_bootstrap(request):
    """Salas + usuários + tarefas em 1 request (substitui 3 chamadas)."""
    try:
        return JsonResponse({
            'status': 'success',
            'rooms': _rooms_payload(request.user),
            'users': _users_payload(request.user),
            'tasks': _tasks_payload(request.user),
        })
    except Exception:
        logger.exception("Erro chat_bootstrap")
        return _error(ERR_INTERNAL, 500)


# =============================================================================
# HISTÓRICO
# =============================================================================

@app_permission_required(_APP)
@require_GET
def get_chat_history(request, room_id):
    """Últimas HISTORY_LIMIT mensagens, em ordem cronológica."""
    try:
        room = _get_room_for_user(request.user, room_id)
        if not room:
            return _error('Sala não encontrada ou acesso negado', 404)

        rows = list(
            Message.objects.filter(room=room)
            .select_related('user')
            .order_by('-timestamp')[:HISTORY_LIMIT]
        )
        rows.reverse()

        messages = []
        for msg in rows:
            d = {
                'id': str(msg.id),
                'message': msg.content or '',
                'content': msg.content or '',
                'username': msg.user.get_full_name() or msg.user.username,
                'user_id': msg.user_id,
                'timestamp': msg.timestamp.isoformat(),
                'is_edited': msg.is_edited,
            }
            if msg.file_attachment:
                d['message_type'] = 'file'
                d['file_data'] = json.dumps({
                    'url': msg.file_attachment.url,
                    'name': msg.original_filename or 'arquivo',
                    'size': msg.file_size,
                    'type': msg.file_type,
                })
            elif msg.image:
                d['message_type'] = 'image'
                d['image_url'] = msg.image.url
            else:
                d['message_type'] = 'text'
            messages.append(d)

        return JsonResponse({
            'status': 'success',
            'messages': messages,
            'room_id': str(room.id),
            'room_name': room.get_room_display_name(request.user),
        })
    except Exception:
        logger.exception("Erro get_chat_history sala=%s", room_id)
        return _error(ERR_INTERNAL, 500)


# =============================================================================
# DM
# =============================================================================

@app_permission_required(_APP)
@require_GET
def start_or_get_dm_chat(request, user_id):
    """Abre (ou cria) a DM entre o usuário atual e `user_id`."""
    try:
        other = get_object_or_404(User, id=user_id, is_active=True)

        if other.id == request.user.id:
            return _error('Não pode enviar DM para si mesmo')

        with transaction.atomic():
            candidates = (
                ChatRoom.objects
                .filter(room_type='DM', is_group_chat=False, participants=request.user)
                .filter(participants=other)
                .prefetch_related('participants')
            )
            room = next(
                (r for r in candidates if len(r.participants.all()) == 2), None,
            )

            created = room is None
            if created:
                room = ChatRoom.objects.create(
                    name=f"DM: {request.user.username} & {other.username}",
                    room_type='DM',
                    is_group_chat=False,
                )
                room.participants.add(request.user, other)
                _notify_new_room(room, request.user, [other.id])

        return JsonResponse({
            'status': 'success',
            'room_id': str(room.id),
            'room_name': _display_name(other),
            'created': created,
        })
    except Exception:
        logger.exception("Erro start_or_get_dm_chat user_id=%s", user_id)
        return _error(ERR_INTERNAL, 500)


# =============================================================================
# GRUPO
# =============================================================================

@app_permission_required(_APP)
@require_POST
def create_group_chat(request):
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body or '{}')
            raw_ids = data.get('participants', [])
            name = (data.get('name') or '').strip()
        else:
            name = (request.POST.get('name') or '').strip()
            raw_ids = request.POST.getlist('participants')  # FormData: várias chaves

        if not name:
            return _error('Nome obrigatório')
        if len(name) > 150:
            return _error('Nome muito longo (máx 150)')

        try:
            ids = {int(x) for x in raw_ids if str(x).strip()}
        except (TypeError, ValueError):
            return _error('Participantes inválidos')

        ids.add(request.user.id)
        users = list(User.objects.filter(id__in=ids, is_active=True))
        if len(users) < 2:
            return _error('Mínimo 2 pessoas')

        with transaction.atomic():
            room = ChatRoom.objects.create(
                name=name, room_type='GROUP', is_group_chat=True,
            )
            room.participants.set(users)
            _notify_new_room(
                room, request.user,
                [u.id for u in users if u.id != request.user.id],
            )

        return JsonResponse({
            'status': 'success',
            'room_id': str(room.id),
            'room_name': room.name,
        })
    except json.JSONDecodeError:
        return _error('JSON inválido')
    except Exception:
        logger.exception("Erro create_group_chat")
        return _error(ERR_INTERNAL, 500)


# =============================================================================
# TAREFA
# =============================================================================

@app_permission_required(_APP)
@require_GET
def get_or_create_task_chat(request, task_id):
    """Chat da tarefa — só para quem é responsável ou criador dela."""
    try:
        from tarefas.models import Tarefas

        task = get_object_or_404(
            Tarefas.objects.filter(
                Q(responsavel=request.user) | Q(usuario=request.user)
            ).distinct(),
            id=task_id,
        )

        with transaction.atomic():
            room, _ = ChatRoom.objects.get_or_create(
                tarefa_id=task.id,
                room_type='TASK',
                defaults={
                    'name': f"Tarefa: {task.titulo}"[:150],
                    'is_group_chat': True,
                },
            )
            members = {request.user.id}
            for attr in ('usuario_id', 'responsavel_id'):
                v = getattr(task, attr, None)
                if v:
                    members.add(v)
            room.participants.add(*members)

        return JsonResponse({
            'status': 'success',
            'room_id': str(room.id),
            'room_name': room.name,
        })
    except Exception:
        logger.exception("Erro get_or_create_task_chat task_id=%s", task_id)
        return _error(ERR_INTERNAL, 500)


# =============================================================================
# UPLOADS
# =============================================================================

class ChatImageUploadView(FuncionarioRequiredMixin, AppPermissionMixin, View):
    """Upload de imagens para o chat."""
    app_label_required = _APP
    modulo_nome = 'Chat'

    def post(self, request):
        try:
            image = request.FILES.get('image')
            if not image:
                return JsonResponse({'error': 'Nenhuma imagem'}, status=400)
            if image.size > 5 * 1024 * 1024:
                return JsonResponse({'error': 'Muito grande (máx 5MB)'}, status=400)

            ext = os.path.splitext(image.name)[1].lower()
            if ext not in IMAGE_EXTS or not (image.content_type or '').startswith('image/'):
                return JsonResponse({'error': 'Tipo não permitido'}, status=400)

            path = default_storage.save(
                f"chat_images/{request.user.id}/{uuid.uuid4()}{ext}", image,
            )
            return JsonResponse({
                'status': 'success',
                'file_path': path,
                'file_url': default_storage.url(path),
                'file_name': os.path.basename(path),
                'file_size': image.size,
                'message': 'Imagem enviada',
            })
        except Exception:
            logger.exception("Erro upload imagem")
            return JsonResponse({'error': ERR_INTERNAL}, status=500)


@app_permission_required(_APP)
@require_POST
def chat_file_upload(request):
    """Upload de arquivo; o envio da mensagem é feito depois via WebSocket."""
    try:
        file = request.FILES.get('file')
        room_id = request.POST.get('room_id')

        if not file:
            return _error('Nenhum arquivo enviado')
        if not room_id:
            return _error('room_id é obrigatório')

        room = _get_room_for_user(request.user, room_id)
        if not room:
            return _error('Sala não encontrada ou acesso negado', 403)

        if file.size > MAX_UPLOAD:
            return _error('Arquivo muito grande (máximo 10MB)')

        try:
            validate_uploaded_file(file)
        except ValidationError as e:
            return _error('; '.join(e.messages))

        ext = os.path.splitext(file.name)[1].lower()
        saved = default_storage.save(
            f"chat_uploads/{room.id}/{uuid.uuid4()}{ext}", file,
        )
        file_data = {
            'url': default_storage.url(saved),
            'name': os.path.basename(file.name),
            'size': file.size,
            'type': file.content_type or 'application/octet-stream',
        }
        return JsonResponse({
            'status': 'success',
            'file_data': file_data,
            'message': {
                'id': str(uuid.uuid4()),
                'message_type': 'file',
                'file_data': file_data,
            },
        })
    except Exception:
        logger.exception("Erro chat_file_upload")
        return _error(ERR_INTERNAL, 500)


# =============================================================================
# LEITURA
# =============================================================================

@app_permission_required(_APP)
@require_POST
def mark_room_as_read(request, room_id):
    """Marca como lidas as mensagens de outros usuários na sala."""
    room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)

    pending = (
        room.messages
        .exclude(user=request.user)                 # era `sender` (FieldError)
        .exclude(message_reads__user=request.user)
        .values_list('pk', flat=True)
    )
    reads = [MessageRead(message_id=pk, user=request.user) for pk in pending]
    if reads:
        MessageRead.objects.bulk_create(reads, ignore_conflicts=True)
        _group_send(f'notifications_{request.user.id}', {
            'type': 'chat_room_read', 'room_id': str(room.id),
        })

    return JsonResponse({'status': 'ok', 'marked': len(reads)})

