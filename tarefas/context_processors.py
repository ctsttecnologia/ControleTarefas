
from django.utils import timezone
from datetime import timedelta
from .models import Tarefas

def notification_processor(request):
    # O processador só deve rodar para usuários autenticados
    if not request.user.is_authenticated:
        return {}

    now = timezone.now()
    
    # Critério 1: Tarefas com lembrete para a data de HOJE.
    tasks_with_reminder_today = Tarefas.objects.filter(
        responsavel=request.user,
        data_lembrete__date=now.date()  
    )

    # Critério 2: Tarefas ATRASADAS ou com prazo para as PRÓXIMAS 24 HORAS.
    # Usar __lte (menor ou igual a) com um dia no futuro é mais útil
    # do que apenas verificar tarefas já atrasadas.
    tasks_due_soon_or_overdue = Tarefas.objects.filter(
        responsavel=request.user,
        prazo__lte=now + timedelta(days=1)
    )
    
    # Une as duas consultas e remove as duplicadas, 
    # e o mais IMPORTANTE: exclui as que já foram finalizadas.
    all_notification_tasks = (tasks_with_reminder_today | tasks_due_soon_or_overdue).exclude(
        status__in=['concluida', 'cancelada']
    ).distinct()

    return {
        'notification_count': all_notification_tasks.count(),
        'notification_tasks': all_notification_tasks,
        'now': now # Passa a data atual para o template, útil para comparações
    }
