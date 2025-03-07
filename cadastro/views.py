from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

@login_required
def cadastro(request):
    return render(request, 'cadastro.html')

