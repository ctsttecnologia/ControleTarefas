from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required


@login_required # retrição de autenticação

def tarefas(request):
    return render(request, 'tarefas/tarefas.html')