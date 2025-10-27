
# chat/views.py
from multiprocessing import context
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import ChatRoom, ChatMessage, Tarefas 
from django.contrib.auth import get_user_model
User = get_user_model()
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.http import require_POST
import json


@login_required
def chat_list(request):
    # Obtém todas as salas de chat onde o usuário é participante
    # Isso é para salas de grupo ou tarefas
    user_group_rooms = ChatRoom.objects.filter(
    Q(participants=request.user) | 
    Q(task__responsavel=request.user)

).distinct().order_by('-updated_at')

    # Obtém salas individuais (DMs) onde o usuário é user1 ou user2
    user_individual_rooms = ChatRoom.objects.filter(
        room_type='individual'
    ).filter(
        Q(user1=request.user) | Q(user2=request.user)
    ).order_by('-updated_at')

    all_rooms = list(user_group_rooms) + list(user_individual_rooms)
    # Remover duplicatas e ordenar se necessário, ou manter separado
    
    context = {
        'group_rooms': user_group_rooms.filter(room_type='group'),
        'task_rooms': user_group_rooms.filter(room_type='task'),
        'individual_rooms': user_individual_rooms,
        'all_users': User.objects.exclude(id=request.user.id), # Para criar DMs
        'request': request, # Adicione 'request' ao contexto para o parcial
    }
    return render(request, 'chat/chat_list.html', context)


@login_required
def room_view(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id)

    # Verifica permissão do usuário
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Se for um request AJAX (do modal), renderiza SÓ o parcial
        return render(request, 'chat/_chat_list_content.html', context)

    messages = ChatMessage.objects.filter(room=room).order_by('timestamp')[:50] # Últimas 50
    
    return render(request, 'chat/room.html', {
        'room': room,
        'messages': messages,
        'current_user_id': request.user.id, # Para JS distinguir mensagens
    })

@login_required
@require_POST
def create_individual_chat(request):
    # Cria uma sala de chat individual (DM)
    target_user_id = request.POST.get('target_user_id')
    if not target_user_id:
        return HttpResponseBadRequest("ID do usuário alvo não fornecido.")

    target_user = get_object_or_404(User, id=target_user_id)

    # Garante que user1 e user2 estejam sempre em ordem para evitar duplicatas
    user1 = request.user if request.user.id < target_user.id else target_user
    user2 = target_user if request.user.id < target_user.id else request.user

    room, created = ChatRoom.objects.get_or_create(
        user1=user1, 
        user2=user2, 
        room_type='individual',
        defaults={'name': f"DM_{user1.username}_{user2.username}"} # Nome de fallback
    )
    # Adiciona participantes explicitamente caso a DM seja tratada como grupo
    if created:
        room.participants.add(user1, user2)

    return redirect('chat:room_view', room_id=room.id)

@login_required
@require_POST
def create_group_chat(request):
    # Cria uma sala de chat de grupo
    name = request.POST.get('name')
    participant_ids = request.POST.getlist('participants') # Lista de IDs
    
    if not name or not participant_ids:
        return HttpResponseBadRequest("Nome da sala e participantes são necessários.")

    room = ChatRoom.objects.create(name=name, room_type='group')
    room.participants.add(request.user) # O criador é um participante
    for user_id in participant_ids:
        try:
            user = User.objects.get(id=user_id)
            room.participants.add(user)
        except User.DoesNotExist:
            pass # Ignora IDs de usuário inválidos

    return redirect('chat:room_view', room_id=room.id)


@login_required
def create_task_chat(request, task_id):
    # View para criar um chat para uma tarefa específica
    task = get_object_or_404(Tarefas, id=task_id)

    # Verifica se a tarefa já tem um chat
    if hasattr(task, 'chat_room'):
        return redirect('chat:room_view', room_id=task.chat_room.id)

    # Cria a sala de chat do tipo 'task'
    room = ChatRoom.objects.create(
        name=f"Chat da Tarefa: {task.titulo}", 
        room_type='task', 
        task=task
    )
    
    # Adiciona responsável e participantes da tarefa à sala de chat
    room.participants.add(task.responsavel)
    room.participants.add(*task.participantes.all())
    room.participants.add(request.user) # Se o criador não for responsável/participante
    
    return redirect('chat:room_view', room_id=room.id)

@login_required
@require_POST
def delete_old_messages(request):
    # Opção para o administrador excluir conversas antigas
    # Você pode adicionar um campo 'last_activity' na sala para facilitar
    # Ou simplesmente deletar mensagens mais antigas que X dias
    
    if not request.user.is_superuser: # Apenas superusuários podem deletar
        return HttpResponseForbidden("Você não tem permissão para realizar esta ação.")
    
    # Exemplo: deletar mensagens mais antigas que 30 dias
    from datetime import datetime, timedelta
    cutoff_date = datetime.now() - timedelta(days=30)
    deleted_count, _ = ChatMessage.objects.filter(timestamp__lt=cutoff_date).delete()

    return JsonResponse({'status': 'success', 'deleted_count': deleted_count})
