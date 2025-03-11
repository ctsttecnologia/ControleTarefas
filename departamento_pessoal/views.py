from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required


@login_required # retrição de autenticação
def departamento_pessoal(request):
    return render(request, 'departamento_pessoal/departamento_pessoal.html') 

@login_required  # Garante que apenas usuários logados acessem o perfil
def profile_view(request):
    return render(request, 'usuario/profile.html')  # Renderiza o template do perfil