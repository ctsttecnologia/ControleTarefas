from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required


@login_required # retrição de autenticação
def seguranca_trabalho(request):
    return render(request, 'seguranca_trabalho/seguranca_trabalho.html')


@login_required  # Garante que apenas usuários logados acessem o perfil
def profile_view(request):
    return render(request, 'usuario/profile.html')  # Renderiza o template do perfil