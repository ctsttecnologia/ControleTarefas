
# chat/views.py

import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db import models
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import ChatRoom, Message
from django.contrib.auth import get_user_model
import os
from django.views import View
from django.core.files.storage import default_storage
from django.conf import settings

User = get_user_model()

@login_required
def get_user_list(request):
    """Retorna a lista de usuários para o modal de chat."""
    try:
        users = User.objects.exclude(id=request.user.id).values(
            'id', 'username', 'first_name', 'last_name', 'email'
        )

        user_list = []
        for user in users:
            full_name = f"{user['first_name']} {user['last_name']}".strip()
            display_name = full_name or user['username']
            user_list.append({
                'id': user['id'],
                'name': display_name,
                'email': user['email']
            })
           
        return JsonResponse({'users': user_list})
   
    except Exception as e:
        return JsonResponse({'error': f'Erro ao carregar usuários: {str(e)}'}, status=500)

@login_required
def get_task_list(request):
    """Retorna a lista de tarefas para o modal de chat."""
    try:
        from tarefas.models import Tarefas
       
        tasks = Tarefas.objects.filter(
            models.Q(responsavel=request.user) |
            models.Q(usuario=request.user)
        ).distinct().values('id', 'titulo', 'descricao', 'status', 'prioridade')

        task_data = [{
            'id': t['id'],
            'titulo': t['titulo'],
            'descricao': t.get('descricao') or 'Sem descrição',
            'status': t.get('status', 'pendente'),
            'prioridade': t.get('prioridade', 'baixa')
        } for t in tasks]
       
        return JsonResponse({'tasks': task_data})
   
    except ImportError:
        return JsonResponse({'tasks': [], 'warning': 'App tarefas não encontrado'})
    except Exception as e:
        return JsonResponse({'error': f'Erro ao carregar tarefas: {str(e)}'}, status=500)
    
@login_required
def get_active_chat_rooms(request):
    """
    Retorna as salas de chat (DM, Grupo, Tarefa) 
    nas quais o usuário é participante, para a barra lateral principal.
    """
    try:
        # 1. Pega as salas que o usuário participa
        # (Idealmente, você deve ordenar pela última mensagem no futuro)
        rooms = ChatRoom.objects.filter(
            participants=request.user
        ).distinct().order_by('-created_at')

        room_list = []
        for room in rooms:
            # 2. Formata os dados usando os novos métodos do modelo
            room_list.append({
                'room_id': str(room.id),
                'room_type': room.room_type,
                
                # 3. Define o nome de exibição (ex: "Italo Vieira" para DMs)
                'room_name': room.get_room_display_name(request.user), 
                
                # 4. Pega a última mensagem
                'last_message': room.get_last_message_preview(),
                
                # 5. Adicionar contagem de mensagens não lidas
                'unread_count': 0 
            })
            
        return JsonResponse({'rooms': room_list})
        
    except Exception as e:
        return JsonResponse({'error': f'Erro ao carregar salas de chat: {str(e)}'}, status=500)

@login_required
def start_or_get_dm_chat(request, user_id):
    """Inicia ou retorna um Chat Individual (DM) existente."""
    try:
        other_user = get_object_or_404(User, id=user_id)
        current_user = request.user
       
        if current_user.id == other_user.id:
            return JsonResponse({
                'status': 'error',
                'error': 'Não é possível criar DM consigo mesmo'
            }, status=400)
       
        existing_rooms = ChatRoom.objects.filter(
            participants=current_user
        ).filter(
            participants=other_user
        ).annotate(num_participants=models.Count('participants'))
       
        room = None
        for chat_room in existing_rooms:
            if chat_room.num_participants == 2 and not chat_room.is_group_chat:
                room = chat_room
                break

        if not room:
            room = ChatRoom.objects.create(
                name=f"DM: {current_user.username} & {other_user.username}",
                room_type='DM',
                is_group_chat=False
            )
            room.participants.add(current_user, other_user)
            room.save()

        return JsonResponse({
            'status': 'success',
            'room_id': str(room.id),
            'room_name': room.name
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': f'Erro interno: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def create_group_chat(request):
    """Cria um novo chat de grupo."""
    try:
        if request.content_type == 'application/json':
            import json
            data = json.loads(request.body)
            name = data.get('name')
            participant_ids = data.get('participants', [])
        else:
            name = request.POST.get('name')
            participant_ids = request.POST.getlist('participants[]') or request.POST.getlist('participants')
       
        if not name:
            return JsonResponse({
                'status': 'error',
                'error': 'Nome do grupo é obrigatório.'
            }, status=400)
           
        if not participant_ids:
            return JsonResponse({
                'status': 'error',
                'error': 'Selecione pelo menos um participante.'
            }, status=400)
           
        try:
            participants = [request.user.id] + [int(uid) for uid in participant_ids if uid]
        except (ValueError, TypeError) as e:
            return JsonResponse({
                'status': 'error',
                'error': f'IDs de participantes inválidos: {str(e)}'
            }, status=400)

        users = User.objects.filter(id__in=participants)
       
        if users.count() < 2:
            return JsonResponse({
                'status': 'error',
                'error': 'Um grupo requer pelo menos dois membros (incluindo você).'
            }, status=400)

        room = ChatRoom.objects.create(
            name=name,
            room_type='GROUP',
            is_group_chat=True
        )
        room.participants.set(users)
        room.save()

        return JsonResponse({
            'status': 'success',
            'room_id': str(room.id),
            'room_name': room.name
        })

    except Exception as e:
        print(f"Erro ao criar grupo: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'error': f'Erro ao criar grupo: {str(e)}'
        }, status=500)

@login_required
def get_or_create_task_chat(request, task_id):
    """Cria ou retorna a sala de chat vinculada a uma Tarefa."""
    try:
        from tarefas.models import Tarefas
        from .models import ChatRoom
        
        task = get_object_or_404(Tarefas, id=task_id)
        
        # 1. Verifica se o usuário tem acesso à tarefa
        has_access = (
            task.responsavel == request.user or
            task.usuario == request.user
        )
            
        if not has_access:
            return JsonResponse({
                'status': 'error',
                'error': 'Você não tem acesso a esta tarefa.'
            }, status=403)
        
        # 2. Tenta encontrar a sala. Se não existir, cria.
        room, created = ChatRoom.objects.get_or_create(
            tarefa=task, 
            room_type='TASK',
            defaults={
                'name': f"Tarefa: {task.titulo}",
                'is_group_chat': True
            }
        )

        # 3. Garante que TODOS os participantes estejam na sala
        #    Isso é crucial se a sala já existia (created=False)
        participants_to_add = []
        if task.usuario:
            participants_to_add.append(task.usuario)
        if task.responsavel:
            participants_to_add.append(task.responsavel)
        
        # Adiciona o usuário atual por garantia (embora ele deva ser um dos acima)
        participants_to_add.append(request.user)

        # Usa set() para remover duplicatas
        unique_participants = list(set(participants_to_add))
        
        # Adiciona todos os participantes de uma vez.
        # O Django é inteligente e não adicionará quem já existe.
        room.participants.add(*unique_participants)
        
        return JsonResponse({
            'status': 'success',
            'room_id': str(room.id),
            'room_name': room.name
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': f'Erro ao acessar chat da tarefa: {str(e)}'
        }, status=500)

@login_required
def get_chat_history(request, room_id):
    """Retorna o histórico de mensagens para uma sala."""
    try:
        room = get_object_or_404(ChatRoom, id=room_id)
       
        if not room.participants.filter(id=request.user.id).exists():
            return JsonResponse({
                'status': 'error',
                'error': 'Acesso negado'
            }, status=403)
           
        messages = Message.objects.filter(room=room).select_related('user').order_by('timestamp')
       
        message_list = [{
            'username': m.user.username,
            'message': m.content,
            'image_url': m.image.url if m.image else None,
            'timestamp': m.timestamp.isoformat()
        } for m in messages]
       
        return JsonResponse({
            'status': 'success',
            'messages': message_list
        })
   
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': f'Erro ao carregar histórico: {str(e)}'
        }, status=500)
    


class ChatImageUploadView(View):

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'status': 'error', 'error': 'Não autorizado'}, status=401)

        if 'image_file' not in request.FILES:
            return JsonResponse({'status': 'error', 'error': 'Nenhum arquivo enviado'}, status=400)

        file = request.FILES['image_file']

        # Define um caminho seguro (ex: media/chat_images/nome_do_arquivo.png)
        file_name = default_storage.save(f"chat_images/{file.name}", file)

        # Gera a URL completa
        file_url = os.path.join(settings.MEDIA_URL, file_name)

        return JsonResponse({
            'status': 'success',
            'image_url': file_url
        })
    


