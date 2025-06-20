
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.models import Group 
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.views import (
    PasswordResetView, 
    PasswordResetDoneView, 
    PasswordResetConfirmView,
    PasswordResetCompleteView
)

from .forms import UsuarioCreationForm, UsuarioChangeForm, GrupoForm
from .models import Usuario 


def login(request):
    if request.method == 'POST':
        # Instanciar AuthenticationForm com os dados do POST
        form = AuthenticationForm(request, data=request.POST) 
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                auth_login(request, user)
                # CORREÇÃO: Redirecionamento após login bem-sucedido
                return redirect('usuario:profile') 
            # Se o usuário for None, isso não deve acontecer se form.is_valid()
            # e authenticate() retornam None apenas para credenciais inválidas.
            # messages.error(request, 'Credenciais inválidas') # Removido, o form.errors já lida
        else:
            # Se o formulário não for válido, as mensagens de erro serão exibidas pelo form.
            messages.error(request, 'Usuário ou senha inválidos.')
    else:
        # Para requisições GET, instanciar um formulário de login vazio
        form = AuthenticationForm()
    
    # Passar a instância do formulário para o template
    return render(request, 'usuario/login.html', {'form': form})

def logout(request):
    auth_logout(request)
    # Redirecionamento para a página de login após o logout
    return redirect('usuario:login')

@login_required 
def perfil_view(request):
    # Sua lógica de view aqui
    return render(request, 'usuario/profile.html')


def cadastrar_usuario(request):
    if request.method == 'POST':
        form = UsuarioCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuário cadastrado com sucesso!')
            # CORREÇÃO: Redirecionamento após o cadastro para o nome de URL correto
            return redirect('usuario:lista_usuarios') 
    else:
        form = UsuarioCreationForm()
    # Seu template 'usuario/form.html' é usado para criação/edição.
    # Se você tem um template específico para cadastro de usuário (e.g., 'usuario/cadastrar.html'), use-o aqui.
    return render(request, 'usuario/form.html', {'form': form})

@login_required
@permission_required('auth.view_user')
def lista_usuarios(request):
    usuarios = Usuario.objects.all()
    return render(request, 'usuario/lista_usuarios.html', {'usuarios': usuarios})

# Alterar senha para usuário logado

def alterar_senha(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    
    # Verifica se o usuário tem permissão para alterar a senha
    if not (request.user.is_superuser or request.user == usuario):
        messages.error(request, "Você não tem permissão para alterar esta senha.")
        return redirect('usuario:lista_usuarios')
    
    if request.method == 'POST':
        form = PasswordChangeForm(usuario, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Mantém o usuário logado
            messages.success(request, 'Senha alterada com sucesso!')
            return redirect('usuario:lista_usuarios')
    else:
        form = PasswordChangeForm(usuario)
    
    return render(request, 'usuario/alterar_senha.html', {
        'form': form,
        'usuario': usuario
    })

# Esqueci a Senha
class CustomPasswordResetView(PasswordResetView):
    template_name = 'usuario/password_reset_form.html'
    email_template_name = 'usuario/password_reset_email.html'
    subject_template_name = 'usuario/password_reset_subject.txt'
    success_url = reverse_lazy('usuario:password_reset_done')

class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'usuario/password_reset_done.html'

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'usuario/password_reset_confirm.html'
    success_url = reverse_lazy('usuario:password_reset_complete')

class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'usuario/password_reset_complete.html'    

@login_required
@permission_required('auth.change_user', raise_exception=True)
def desativar_usuario(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    
    if request.user == usuario:
        messages.error(request, "Você não pode desativar a si mesmo.")
    else:
        usuario.is_active = False
        usuario.save()
        messages.success(request, f"Usuário {usuario.username} desativado com sucesso.")
    
    return redirect('usuario:lista_usuarios')

@login_required
@permission_required('auth.change_user', raise_exception=True)
def ativar_usuario(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    usuario.is_active = True
    usuario.save()
    messages.success(request, f"Usuário {usuario.username} ativado com sucesso.")
    return redirect('usuario:lista_usuarios')

class UsuarioCreateView(CreateView):
    model = Usuario
    form_class = UsuarioCreationForm
    template_name = 'usuario/form.html'
    # CORREÇÃO: success_url usando o nome de URL correto e namespace
    success_url = reverse_lazy('usuario:lista_usuarios')

class UsuarioUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Usuario
    form_class = UsuarioChangeForm
    template_name = 'usuario/form.html'
    success_url = reverse_lazy('usuario:lista_usuarios')
    
    def test_func(self):
        """Verifica se o usuário tem permissão para editar"""
        usuario = self.get_object()
        return (
            self.request.user.is_superuser or  # Superusuário pode editar qualquer um
            self.request.user == usuario  # Usuário pode editar a si mesmo
        )
    
    def get_context_data(self, **kwargs):
        """Adiciona contexto adicional ao template"""
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f"Editar Usuário: {self.object.email}"
        context['botao_submit'] = "Atualizar"
        return context

@login_required
@permission_required('auth.change_group')
def gerenciar_grupos_usuario(request, pk):
    # CORREÇÃO: Importar get_object_or_404 e usá-lo corretamente
    usuario = get_object_or_404(Usuario, pk=pk) 
    
    if request.method == 'POST':
        grupo_pk = request.POST.get('grupo')
        acao = request.POST.get('acao')
        
        if grupo_pk and acao:
            # CORREÇÃO: Usar grupo_id (da request.POST) em vez de grupo_pk (inexistente)
            grupo = get_object_or_404(Group, pk=grupo_pk) # Use get_object_or_404 para o grupo também
            
            if acao == 'adicionar':
                usuario.groups.add(grupo)
                messages.success(request, f"Grupo '{grupo.name}' adicionado ao usuário.")
            elif acao == 'remover':
                usuario.groups.remove(grupo)
                messages.success(request, f"Grupo '{grupo.name}' removido do usuário.")
            else:
                messages.error(request, "Ação inválida.")
        else:
            messages.error(request, "Dados inválidos para gerenciar grupos.")
            
        # Após a ação, redirecione ou apenas renderize a página novamente com os dados atualizados
        # return redirect('usuario:gerenciar_grupos_usuario', pk=pk) # Opcional: redirecionar para evitar reenvio do form
        
    grupos_usuario = usuario.groups.all()
    grupos_disponiveis = Group.objects.exclude(pk__in=grupos_usuario.values_list('pk', flat=True))
    
    return render(request, 'usuario/gerenciar_grupos_usuario.html', {
        'usuario': usuario,
        'grupos_usuario': grupos_usuario,
        'grupos_disponiveis': grupos_disponiveis
    })

class GrupoDeleteView(DeleteView):
    model = Group
    template_name = 'usuario/grupo_confirmar_exclusao.html'
    success_url = reverse_lazy('usuario:grupo_lista')

class GrupoListView(ListView):
    model = Group
    template_name = 'usuario/grupo_lista.html'
    context_object_name = 'grupos'

class GrupoCreateView(CreateView):
    model = Group
    form_class = GrupoForm
    template_name = 'usuario/grupo_form.html'
    # CORREÇÃO: success_url usando o nome de URL correto e namespace
    success_url = reverse_lazy('usuario:grupo_lista')

class GrupoUpdateView(UpdateView):
    model = Group
    form_class = GrupoForm
    template_name = 'usuario/grupo_form.html'
    # CORREÇÃO: success_url usando o nome de URL correto e namespace
    success_url = reverse_lazy('usuario:grupo_lista')


