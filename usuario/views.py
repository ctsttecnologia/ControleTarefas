
# usuario/views.py

from django.db.models import Q
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import (
    LoginView, LogoutView, 
    PasswordChangeView,
    PasswordResetView, PasswordResetDoneView, 
    PasswordResetConfirmView, PasswordResetCompleteView
)
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, FormView
from django.shortcuts import get_object_or_404, redirect, render

from .models import Usuario, Group, Filial
from .forms import CustomUserCreationForm, CustomUserChangeForm, GrupoForm, CustomPasswordChangeForm, FilialForm
from django.contrib.auth.forms import SetPasswordForm
from django.views.generic import View
from django.db.models import ProtectedError

# --- Views de Autenticação ---

class CustomLoginView(LoginView):
    template_name = 'usuario/login.html'
    redirect_authenticated_user = True # Redireciona se o usuário já estiver logado

class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('usuario:login')


# --- Views de Perfil e Senha ---

class ProfileView(LoginRequiredMixin, DetailView):
    model = Usuario
    template_name = 'usuario/profile.html'
    
    def get_object(self, queryset=None):
        # Retorna o usuário logado
        return self.request.user

class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    form_class = CustomPasswordChangeForm
    template_name = 'usuario/alterar_senha.html'
    success_url = reverse_lazy('usuario:profile')

    def form_valid(self, form):
        messages.success(self.request, 'Sua senha foi alterada com sucesso!')
        return super().form_valid(form)


# --- Views de CRUD de Usuários (Apenas para Staff/Superuser) ---

class StaffRequiredMixin(UserPassesTestMixin):
    """ Mixin para garantir que o usuário é staff ou superuser. """
    def test_func(self):
        return self.request.user.is_staff

class UserListView(StaffRequiredMixin, ListView):
    model = Usuario
    template_name = 'usuario/lista_usuarios.html'
    context_object_name = 'usuarios'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().order_by('first_name')
        search_query = self.request.GET.get('q', '')
        if search_query:
            queryset = queryset.filter(
                Q(username__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query)
            )
        return queryset

class UserCreateView(StaffRequiredMixin, CreateView):
    model = Usuario
    form_class = CustomUserCreationForm
    template_name = 'usuario/form_usuario.html'
    success_url = reverse_lazy('usuario:lista_usuarios')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Cadastrar Novo Usuário'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Usuário cadastrado com sucesso!')
        return super().form_valid(form)

class UserUpdateView(StaffRequiredMixin, UpdateView):
    model = Usuario
    form_class = CustomUserChangeForm
    template_name = 'usuario/form_usuario.html'
    success_url = reverse_lazy('usuario:lista_usuarios')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f'Editar Usuário: {self.object.username}'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Usuário atualizado com sucesso!')
        return super().form_valid(form)

class UserToggleActiveView(StaffRequiredMixin, View):
    """ View para ativar ou desativar um usuário com um POST. """
    def post(self, request, *args, **kwargs):
        user_to_toggle = get_object_or_404(Usuario, pk=self.kwargs.get('pk'))
        if user_to_toggle == request.user:
            messages.error(request, "Você não pode desativar a si mesmo.")
            return redirect('usuario:lista_usuarios')
        
        user_to_toggle.is_active = not user_to_toggle.is_active
        user_to_toggle.save()
        
        action_text = "ativado" if user_to_toggle.is_active else "desativado"
        messages.success(request, f"Usuário {user_to_toggle.username} {action_text} com sucesso.")
        return redirect('usuario:lista_usuarios')


# --- Views de CRUD de Grupos (Apenas para Superuser) ---

class SuperuserRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser

class GroupListView(SuperuserRequiredMixin, ListView):
    model = Group
    template_name = 'usuario/grupo_lista.html'
    context_object_name = 'grupos'

class GroupCreateView(SuperuserRequiredMixin, CreateView):
    model = Group
    form_class = GrupoForm
    template_name = 'usuario/grupo_form.html'
    success_url = reverse_lazy('usuario:grupo_lista')

class GroupUpdateView(SuperuserRequiredMixin, UpdateView):
    model = Group
    form_class = GrupoForm
    template_name = 'usuario/grupo_form.html'
    success_url = reverse_lazy('usuario:grupo_lista')

class GroupDeleteView(SuperuserRequiredMixin, DeleteView):
    model = Group
    template_name = 'usuario/grupo_confirmar_exclusao.html'
    success_url = reverse_lazy('usuario:grupo_lista')


# --- Views de Recuperação de Senha (usando as do Django com templates customizados) ---

class CustomPasswordResetView(PasswordResetView):
    template_name = 'usuario/password_reset/form.html'
    email_template_name = 'usuario/password_reset/email.html'
    subject_template_name = 'usuario/password_reset/subject.txt'
    success_url = reverse_lazy('usuario:password_reset_done')

class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'usuario/password_reset/done.html'

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'usuario/password_reset/confirm.html'
    success_url = reverse_lazy('usuario:password_reset_complete')

class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'usuario/password_reset/complete.html'

# --- Senha redefinidas pelo administrador ---

class UserSetPasswordView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    """
    View para um admin definir uma nova senha para outro usuário.
    """
    form_class = SetPasswordForm
    template_name = 'usuario/definir_senha_form.html' # <-- CAMINHO CORRIGIDO
    success_url = reverse_lazy('usuario:lista_usuarios')

    def test_func(self):
        # Garante que apenas superusuários podem acessar esta página
        return self.request.user.is_superuser

    def get_form_kwargs(self):
        # Passa o usuário-alvo para o formulário
        kwargs = super().get_form_kwargs()
        kwargs['user'] = get_object_or_404(Usuario, pk=self.kwargs['pk'])
        return kwargs

    def form_valid(self, form):
        # Salva a nova senha e exibe mensagem de sucesso
        form.save()
        messages.success(self.request, f"A senha para o usuário {form.user.username} foi definida com sucesso.")
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        # Adiciona o usuário-alvo ao contexto para usar no template
        context = super().get_context_data(**kwargs)
        context['usuario_alvo'] = get_object_or_404(Usuario, pk=self.kwargs['pk'])
        return context
    
# ---Remover usuário de um grupo ---

class GerenciarGruposUsuarioView(SuperuserRequiredMixin, View):
    template_name = 'usuario/gerenciar_grupos_usuario.html'

    def get(self, request, *args, **kwargs):
        usuario = get_object_or_404(Usuario, pk=self.kwargs.get('pk'))
        grupos_usuario = usuario.groups.all()
        grupos_disponiveis = Group.objects.exclude(pk__in=grupos_usuario.values_list('pk', flat=True))
        context = {
            'usuario_alvo': usuario,
            'grupos_usuario': grupos_usuario,
            'grupos_disponiveis': grupos_disponiveis
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        usuario = get_object_or_404(Usuario, pk=self.kwargs.get('pk'))
        grupo_id = request.POST.get('grupo')
        acao = request.POST.get('acao')
        
        if grupo_id and acao:
            grupo = get_object_or_404(Group, pk=grupo_id)
            if acao == 'adicionar':
                usuario.groups.add(grupo)
                messages.success(request, f"Grupo '{grupo.name}' adicionado ao usuário {usuario.username}.")
            elif acao == 'remover':
                usuario.groups.remove(grupo)
                messages.success(request, f"Grupo '{grupo.name}' removido do usuário {usuario.username}.")
        
        return redirect('usuario:gerenciar_grupos_usuario', pk=usuario.pk)
    
    # =============================================================================
# == VIEWS DE CRUD DE FILIAIS (Apenas para Superuser)
# =============================================================================

class FilialListView(LoginRequiredMixin, SuperuserRequiredMixin, ListView):
    model = Filial
    template_name = 'usuario/filial_list.html'
    context_object_name = 'filiais'

class FilialCreateView(LoginRequiredMixin, SuperuserRequiredMixin, CreateView):
    model = Filial
    form_class = FilialForm
    template_name = 'usuario/filial_form.html'
    success_url = reverse_lazy('usuario:filial_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Adicionar Nova Filial'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Filial cadastrada com sucesso!')
        return super().form_valid(form)

class FilialUpdateView(LoginRequiredMixin, SuperuserRequiredMixin, UpdateView):
    model = Filial
    form_class = FilialForm
    template_name = 'usuario/filial_form.html'
    success_url = reverse_lazy('usuario:filial_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f'Editar Filial: {self.object.nome}'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Filial atualizada com sucesso!')
        return super().form_valid(form)

class FilialDeleteView(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = Filial
    template_name = 'usuario/filial_confirm_delete.html'
    success_url = reverse_lazy('usuario:filial_list')

    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            messages.success(request, 'Filial excluída com sucesso!')
            return response
        except ProtectedError:
            messages.error(self.request, 'Esta filial não pode ser excluída, pois existem usuários ou ferramentas associados a ela.')
            return redirect('usuario:filial_list')