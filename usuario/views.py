from django.shortcuts import render
from django.http import HttpResponse
from django.shortcuts import redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt, csrf_protect, requires_csrf_token
from django.urls import reverse




@requires_csrf_token
def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('usuario:profile')
    else:  # Este else estava indentado errado no seu código original
        form = AuthenticationForm()
    
    # Mostra erros de formulário inválido (tanto para POST inválido quanto GET)
    return render(request, 'usuario/login.html', {'form': form})

def user_register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Faz login automaticamente
            return redirect('usuario:profile')
    else:
        form = UserCreationForm()
    return render(request, 'usuario/register.html', {'form': form})

def user_profile(request):
    if not request.user.is_authenticated:
        return redirect('usuario:register')  # Alterado de 'login' para 'register'
    return render(request, 'usuario/profile.html')

def user_logout(request):
    logout(request)
    return redirect('home')



