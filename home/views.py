from django.shortcuts import render
from django.http import HttpResponse

#def home(request):
#    return HttpResponse("Página Inicial")

def home(request):
    return render(request, 'home/home.html')

#def home(request):
#    context = {
#        'name': 'Nome do Usuário',  # Exemplo de variável
#    }
#    return render(request, 'home/home.html', context)

