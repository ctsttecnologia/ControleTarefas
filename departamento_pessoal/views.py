from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required


@login_required # retrição de autenticação
def departamento_pessoal(request):
    return render(request, 'departamento_pessoal/departamento_pessoal.html') 