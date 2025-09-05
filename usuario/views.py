
# usuario/views.py

from django.db.models import Q
from django.urls import reverse, reverse_lazy
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
from django.db.models import ProtectedError



class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff

class SuperuserRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser


# =============================================================================
# == VIEWS DE AUTENTICAÇÃO E SELEÇÃO DE FILIAL
# =============================================================================

class CustomLoginView(LoginView):
    template_name = 'usuario/login.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        """
        << CORREÇÃO CRÍTICA >>
        Após o login bem-sucedido, define a filial ativa do usuário na sessão.
        """
        # Executa o processo de login padrão primeiro
        response = super().form_valid(form)
        
        user = self.request.user
        filial_ativa = None

        # 1. Prioridade: Usa a filial ativa já definida no perfil do usuário.
        if hasattr(user, 'filial_ativa') and user.filial_ativa:
            filial_ativa = user.filial_ativa
        # 2. Alternativa: Se não houver, pega a primeira filial da lista de permitidas.
        elif hasattr(user, 'filiais_permitidas') and user.filiais_permitidas.exists():
            filial_ativa = user.filiais_permitidas.first()
            # Atualiza o perfil do usuário para referência futura
            user.filial_ativa = filial_ativa
            user.save()

        # Armazena a ID da filial na sessão para ser usada em todo o sistema
        if filial_ativa:
            self.request.session['active_filial_id'] = filial_ativa.id
            messages.info(self.request, f"Você está conectado na filial: {filial_ativa.nome}")
        else:
            # Se o usuário não tem filial, limpa a sessão e envia mensagem de erro
            messages.error(self.request, "Você não está associado a nenhuma filial. Contate o administrador.")
            # Desloga o usuário se ele não tiver filial para operar
            from django.contrib.auth import logout
            logout(self.request)
            return redirect('usuario:login')

        return response

class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('usuario:login')

class SelecionarFilialView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        filial_id_str = request.POST.get('filial_id')

        # Caso especial para Superusuário limpando o filtro ("Todas as Filiais")
        if filial_id_str == '0' and request.user.is_superuser:
            if 'active_filial_id' in request.session:
                del request.session['active_filial_id'] # Remove a chave da sessão
            
            # Limpa também a filial ativa do perfil para consistência
            request.user.filial_ativa = None
            request.user.save()
            messages.success(request, "Exibindo dados de todas as filiais.")

        elif filial_id_str:
            try:
                filial_id = int(filial_id_str)
                filial_selecionada = request.user.filiais_permitidas.get(pk=filial_id)
                
                request.session['active_filial_id'] = filial_selecionada.id
                request.user.filial_ativa = filial_selecionada
                request.user.save()
                messages.success(request, f"Filial alterada para: {filial_selecionada.nome}")

            except (Filial.DoesNotExist, ValueError):
                messages.error(request, "Seleção inválida ou você não tem permissão para acessar esta filial.")

        # Redireciona para a página anterior ou para o dashboard
        return redirect(request.POST.get('next', reverse('usuario:profile')))


# =============================================================================
# == VIEWS DE PERFIL E SENHA (SEM ALTERAÇÕES SIGNIFICATIVAS)
# =============================================================================

class ProfileView(LoginRequiredMixin, DetailView):
    model = Usuario
    template_name = 'usuario/profile.html'
    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # 1. Defina a estrutura de todos os cards possíveis
        all_cards = [
            {
                'id': 'tarefas',
                'title': 'Tarefas',
                'permission': 'tarefas.view_tarefa',  # Permissão necessária
                'icon': 'images/tarefa.gif',
                'links': [
                    {'url': 'tarefas:listar_tarefas', 'text': 'Minhas Tarefas'},
                    {'url': 'tarefas:calendario_tarefas', 'text': 'Agenda'},
                    {'url': 'tarefas:dashboard_analitico', 'text': 'Dashboard Analítico'},
                ]
            },
            {
                'id': 'clientes',
                'title': 'Clientes',
                'permission': 'cliente.view_cliente', 
                'icon': 'images/cliente.gif',
                'links': [
                    {'url': 'cliente:lista_clientes', 'text': 'Lista de Clientes'},
                    {'url': 'cliente:cadastro_cliente', 'text': 'Cadastrar Cliente'},
                ]
            },
            {
                'id': 'dp',
                'title': 'Departamento Pessoal',
                'permission': 'departamento_pessoal.departamento_pessoal', 
                'icon': 'images/dp.gif',
                'links': [
                    {'url': 'departamento_pessoal:painel_dp', 'text': 'Painel DP'},
                    {'url': 'departamento_pessoal:lista_funcionarios', 'text': 'Funcionários'},
                    {'url': 'departamento_pessoal:lista_cargo', 'text': 'Cargos'},
                    {'url': 'departamento_pessoal:lista_departamento', 'text': 'Departamentos'},
                ]
            },
            {
                'id': 'sst',
                'title': 'Segurança do Trabalho',
                'permission': 'seguranca_trabalho.view_fichaepi', 
                'icon': 'images/tst.gif',
                'links': [
                    {'url': 'seguranca_trabalho:dashboard', 'text': 'Dashboard'},
                    {'url': 'seguranca_trabalho:ficha_list', 'text': 'Fichas de EPI'},
                    {'url': 'gestao_riscos:agendar_inspecao', 'text': 'Agendar Inspeção'},
                ]
            },
            {
                'id': 'endereco',
                'title': 'Logradouro',
                'permission': 'logradouro.view_logradouro', 
                'icon': 'images/cadastro.gif',
                'links': [
                    {'url': 'logradouro:listar_logradouros', 'text': 'Lista de Logradouros'},
                    {'url': 'logradouro:cadastrar_logradouro', 'text': 'Cadastrar Logradouro'},
                ]
            },
            {
                'id': 'ga',
                'title': 'Gestão Administrativa',
                'permission': 'ata_reuniao.ata_reuniao',
                'icon': 'images/reuniao.png',
                'links': [
                    {'url': 'ata_reuniao:ata_reuniao_list', 'text': 'Ata de Reunião'},
                    {'url': 'controle_de_telefone:dashboard', 'text': 'Controle de Telefones'},
                    {'url': 'treinamentos:dashboard', 'text': 'Treinamentos'},
                ]
            },
            {
                'id': 'veiculos',
                'title': 'Veículos',
                'permission': 'automovel.view_carro',
                'icon': 'images/carro.gif',
                'links': [
                    {'url': 'automovel:carro_list', 'text': 'Frota'},
                    {'url': 'automovel:agendamento_list', 'text': 'Agendamentos'},
                    {'url': 'automovel:dashboard', 'text': 'Relatórios'},
                    {'url': 'automovel:calendario', 'text': 'Calendário'},
                ]
            },
            {
                'id': 'operacao',
                'title': 'Operação',
                'permission': 'ferramentas.view_ferramentas',
                'icon': 'images/serviço.gif',
                'links': [
                    {'url': 'ferramentas:dashboard', 'text': 'Controle de Ferramentas'},
                ]
            },
        ]

        # 2. Filtre os cards com base nas permissões do usuário
        allowed_cards = []
        for card in all_cards:
            # Superusuários veem tudo. Ou, verifique a permissão específica.
            if user.is_superuser or user.has_perm(card['permission']):
                allowed_cards.append(card)

        # 3. Passe a lista de cards permitidos para o template
        context['allowed_cards'] = allowed_cards
        return context


class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    form_class = CustomPasswordChangeForm
    template_name = 'usuario/alterar_senha.html'
    success_url = reverse_lazy('usuario:profile')
    def form_valid(self, form):
        messages.success(self.request, 'Sua senha foi alterada com sucesso!')
        return super().form_valid(form)
   

# =============================================================================
# == VIEWS DE CRUD DE USUÁRIOS (Apenas para Staff/Superuser)
# =============================================================================

class UserListView(StaffRequiredMixin, ListView):
    model = Usuario
    template_name = 'usuario/lista_usuarios.html'
    context_object_name = 'usuarios'
    paginate_by = 10

    def get_queryset(self):
        """
        << CORREÇÃO >>
        Filtra os usuários para mostrar apenas aqueles que pertencem à filial ativa do admin.
        Isso é mais explícito e seguro que o mixin genérico.
        """
        qs = super().get_queryset().order_by('first_name')
        active_filial_id = self.request.session.get('active_filial_id')

        # Superusuários veem todos; outros staffs veem apenas os da sua filial ativa.
        if not self.request.user.is_superuser and active_filial_id:
            qs = qs.filter(filiais_permitidas__id=active_filial_id)

        search_query = self.request.GET.get('q', '')
        if search_query:
            qs = qs.filter(
                Q(username__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query)
            )
        return qs

class UserCreateView(StaffRequiredMixin, CreateView):
    model = Usuario
    form_class = CustomUserCreationForm
    template_name = 'usuario/form_usuario.html'
    success_url = reverse_lazy('usuario:lista_usuarios')
    # ... resto da view sem alterações

class UserUpdateView(StaffRequiredMixin, UpdateView):
    model = Usuario
    form_class = CustomUserChangeForm
    template_name = 'usuario/form_usuario.html'
    success_url = reverse_lazy('usuario:lista_usuarios')
    # ... resto da view sem alterações

class UserToggleActiveView(StaffRequiredMixin, View):
    # ... view sem alterações ...
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
        
