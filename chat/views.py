
# chat/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import ChatRoom, ChatMessage, Tarefas # <-- Assegure que Tarefas esteja importado
from django.contrib.auth import get_user_model
from chat import models
User = get_user_model()
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.http import require_POST
import json
from .models import ChatRoom, ChatMessage
from django.http import JsonResponse


User = get_user_model()


# VIEW 1: Retorna a lista de usuários para o Modal
def get_user_list(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Não autorizado"}, status=401)
        
    # Pega todos os usuários, exceto o próprio usuário logado
    users = User.objects.exclude(id=request.user.id)
    
    # Renderiza um template *parcial* (apenas o HTML da lista)
    return render(request, 'partials/user_list.html', {'users': users})

# VIEW 2: Inicia um chat (ou encontra um existente)
def start_or_get_chat(request, user_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Não autorizado"}, status=401)

    try:
        target_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({"error": "Usuário não encontrado"}, status=404)

    # Impede que o usuário inicie um chat consigo mesmo
    if request.user.id == target_user.id:
        return JsonResponse({"error": "Não é possível iniciar um chat consigo mesmo."}, status=400)

    # Procura uma sala individual (DM) existente entre os dois usuários
    # (user1=eu, user2=ele) OU (user1=ele, user2=eu)
    room = ChatRoom.objects.filter(
        Q(user1=request.user, user2=target_user) |  # Argumento posicional (Q)
        Q(user1=target_user, user2=request.user),
        room_type='individual'   # Argumento de palavra-chave (vem depois)
    ).first()

    # Se a sala não existe, crie uma
    if not room:
        room = ChatRoom.objects.create(
            room_type='individual',
            user1=request.user,
            user2=target_user
        )

    # Retorna o ID da sala (UUID) e o nome do outro usuário
    return JsonResponse({
        "room_id": room.id,
        "room_name": target_user.get_full_name() or target_user.username
    })

@login_required
def chat_list(request):
    """
    Renderiza o template parcial com a lista de chats.
    """
    # Salas onde o usuário é participante, excluindo DMs para evitar duplicatas
    user_group_and_task_rooms = ChatRoom.objects.filter(
        Q(participants=request.user),
        Q(room_type__in=['group', 'task']) 
    ).distinct().order_by('-updated_at')

    # Salas individuais (DMs)
    user_individual_rooms = ChatRoom.objects.filter(
        room_type='individual'
    ).filter(
        Q(user1=request.user) | Q(user2=request.user)
    ).order_by('-updated_at')

    # Dicionário de contexto corrigido
    context = {
        # Filtra os tipos de sala para o template
        'group_rooms': user_group_and_task_rooms.filter(room_type='group'),
        'task_rooms': user_group_and_task_rooms.filter(room_type='task'),
        'individual_rooms': user_individual_rooms,
        'all_users': User.objects.exclude(id=request.user.id), # Para criar DMs
        # 'request': request, # O template engine do Django já injeta 'request' por padrão.
    }
    
    # Renderiza o parcial do chat (este é o template que será puxado via AJAX)
    # Se você está renderizando isso em um modal/drawer, deve ser o parcial.
    return render(request, 'chat/_chat_list_content.html', context)


@login_required
def room_view(request, room_id):
    """
    Renderiza a página principal de um chat específico.
    """
    room = get_object_or_404(ChatRoom, id=room_id)
    
    # 1. Verifica se o usuário é participante
    is_participant = False
    if room.room_type == 'individual':
        is_participant = (request.user == room.user1 or request.user == room.user2)
    else:
        is_participant = room.participants.filter(id=request.user.id).exists()
    
    if not is_participant:
        return HttpResponseForbidden("Você não tem permissão para acessar este chat.")

    # 2. Carrega as 50 últimas mensagens
    messages = ChatMessage.objects.filter(room=room).order_by('timestamp')[:50]
    
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

# chat/views.py (cole no final)

def get_chat_history(request, room_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Não autorizado"}, status=401)

    try:
        room = ChatRoom.objects.get(id=room_id)
    except ChatRoom.DoesNotExist:
        return JsonResponse({"error": "Sala não encontrada"}, status=404)

    # Segurança: Verifica se o usuário é participante desta sala
    if not room.is_participant(request.user):
        return JsonResponse({"error": "Acesso negado"}, status=403)

    # Pega as últimas 50 mensagens (ou quantas você quiser)
    messages = ChatMessage.objects.filter(room=room).order_by('timestamp')[:50]

    # Transforma as mensagens em um formato JSON
    messages_list = []
    for msg in messages:
        messages_list.append({
            'message': msg.content,
            'username': msg.user.username,
            'timestamp': msg.timestamp.isoformat(),
            'image_url': msg.get_image_url() # Usando o método do seu modelo
        })

    return JsonResponse({'messages': messages_list})