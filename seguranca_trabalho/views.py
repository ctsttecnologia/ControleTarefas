from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required


@login_required # retrição de autenticação

#def seguranca_trabalho(request):
#    return HttpResponse("Página de Segurança do Trabalho")

def seguranca_trabalho(request):
    return render(request, 'seguranca_trabalho/seguranca_trabalho.html')