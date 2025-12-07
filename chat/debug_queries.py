
# debug_queries.py - Para testar as queries
from django.contrib.auth import get_user_model
from chat.models import ChatRoom
from django.db import connection

User = get_user_model()

def test_room_queries(user_id=2):  # Use o ID do seu usuário
    """Testa queries das salas sem SQL bruto."""
    
    try:
        user = User.objects.get(id=user_id)
        print(f"✅ Usuário encontrado: {user.username}")
        
        # Teste 1: Buscar salas do usuário
        rooms = ChatRoom.objects.filter(participants=user)
        print(f"✅ Salas encontradas: {rooms.count()}")
        
        # Teste 2: Buscar participantes de cada sala
        for room in rooms:
            participants = room.participants.all()
            participant_names = [p.username for p in participants]
            print(f"✅ Sala {room.id}: {participant_names}")
        
        print("✅ Todos os testes passaram - queries ORM funcionando!")
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_room_queries()

