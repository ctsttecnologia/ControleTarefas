# usuario/views.py

import datetime
from django.db.models import Q
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import (
    LoginView, LogoutView,
    PasswordChangeView,
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView
)
from django.contrib.auth.forms import SetPasswordForm
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, FormView
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import ProtectedError

from usuario.models import Usuario, Group, Filial, GroupCardPermissions
from usuario.forms import (
    CustomUserCreationForm, CustomUserChangeForm,
    GrupoForm, CustomPasswordChangeForm, FilialForm
)


# =============================================================================
# MIXINS DE PERMISSÃO
# =============================================================================

class StaffRequiredMixin(UserPassesTestMixin):
    """Restringe acesso a usuários staff."""
    def test_func(self):
        return self.request.user.is_staff


class SuperuserRequiredMixin(UserPassesTestMixin):
    """Restringe acesso a superusuários."""
    def test_func(self):
        return self.request.user.is_superuser


class AdminOrManagerMixin(UserPassesTestMixin):
    """Restringe acesso a superusuários, gerentes ou administradores."""
    def test_func(self):
        user = self.request.user
        return user.is_superuser or user.is_gerente or user.is_administrador


# =============================================================================
# AUTENTICAÇÃO (Login / Logout / Seleção de Filial)
# =============================================================================

class CustomLoginView(LoginView):
    """Login com gerenciamento automático de filial ativa na sessão."""
    template_name = 'usuario/login.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        filial_ativa = self._determinar_filial_ativa()

        if filial_ativa:
            self._registrar_filial_na_sessao(filial_ativa)
        else:
            return self._handle_usuario_sem_filial()

        return response

    def _determinar_filial_ativa(self):
        user = self.request.user
        if user.filial_ativa:
            return user.filial_ativa
        if user.filiais_permitidas.exists():
            return user.filiais_permitidas.only('id', 'nome').first()
        return None

    def _registrar_filial_na_sessao(self, filial):
        self.request.session['active_filial_id'] = filial.id
        messages.info(self.request, f"Você está conectado na filial: {filial.nome}")

    def _handle_usuario_sem_filial(self):
        messages.error(
            self.request,
            "Você não está associado a nenhuma filial. Contate o administrador."
        )
        logout(self.request)
        return redirect('usuario:login')


class CustomLogoutView(LogoutView):
    """Logout com limpeza da sessão de filial."""
    next_page = reverse_lazy('usuario:login')

    def dispatch(self, request, *args, **kwargs):
        request.session.pop('active_filial_id', None)
        return super().dispatch(request, *args, **kwargs)


class SelecionarFilialView(LoginRequiredMixin, View):
    """Permite ao usuário trocar a filial ativa."""

    def post(self, request, *args, **kwargs):
        filial_id_str = request.POST.get('filial_id')

        # Superusuário limpando filtro ("Todas as Filiais")
        if filial_id_str == '0' and request.user.is_superuser:
            request.session.pop('active_filial_id', None)
            request.user.filial_ativa = None
            request.user.save(update_fields=['filial_ativa'])
            messages.success(request, "Exibindo dados de todas as filiais.")

        elif filial_id_str:
            try:
                filial_id = int(filial_id_str)
                filial_selecionada = request.user.filiais_permitidas.get(pk=filial_id)

                request.session['active_filial_id'] = filial_selecionada.id
                request.user.filial_ativa = filial_selecionada
                request.user.save(update_fields=['filial_ativa'])
                messages.success(request, f"Filial alterada para: {filial_selecionada.nome}")

            except (Filial.DoesNotExist, ValueError):
                messages.error(request, "Seleção inválida ou sem permissão para esta filial.")

        return redirect(request.POST.get('next', reverse('usuario:profile')))


# =============================================================================
# PERFIL E SENHA DO USUÁRIO LOGADO
# =============================================================================

class ProfileView(LoginRequiredMixin, DetailView):
    """Página inicial do usuário com cards de acesso rápido."""
    model = Usuario
    template_name = 'usuario/profile.html'

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        all_cards = self._get_all_cards()
        allowed_card_ids = self._get_allowed_card_ids(user)

        context['allowed_cards'] = [
            card for card in all_cards
            if user.is_superuser
            or user.has_perm(card['permission'])
            or card['id'] in allowed_card_ids
        ]
        return context

    def _get_allowed_card_ids(self, user):
        """Retorna IDs de cards permitidos pelos grupos do usuário."""
        if user.is_superuser:
            return [c['id'] for c in self._get_all_cards()]

        ids = []
        perms = GroupCardPermissions.objects.filter(
            group__in=user.groups.all()
        ).values_list('cards_visiveis', flat=True)

        for cards_list in perms:
            if cards_list:
                ids.extend(cards_list)
        return ids

    def _get_all_cards(self):
        """Definição centralizada de todos os cards do sistema."""
        return [
            {
                'id': 'clientes',
                'title': 'Clientes',
                'permission': 'cliente.view_cliente',
                'icon': 'images/cliente.gif',
                'links': [
                    {'url': 'cliente:lista_clientes', 'text': 'Lista de Clientes'},
                    {'url': 'cliente:cliente_create', 'text': 'Cadastrar Cliente'},
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
                    {'url': 'treinamentos:dashboard', 'text': 'Treinamentos'},
                ]
            },
            {
                'id': 'sst',
                'title': 'Segurança do Trabalho',
                'permission': 'seguranca_trabalho.view_fichaepi',
                'icon': 'images/tst.gif',
                'links': [
                    {'url': 'seguranca_trabalho:dashboard', 'text': 'Painel SST'},
                    {'url': 'seguranca_trabalho:ficha_list', 'text': 'Fichas de EPI'},
                    {'url': 'gestao_riscos:lista_riscos', 'text': 'Gestão de Riscos'},
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
                    {'url': 'suprimentos:dashboard', 'text': 'Suprimentos'},
                    {'url': 'seguranca_trabalho:equipamento_list', 'text': 'Estoque'},
                    {'url': 'documentos:lista', 'text': 'Documentos'},
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
                    {'url': 'tarefas:dashboard', 'text': 'Tarefas'},
                    {'url': 'ferramentas:dashboard', 'text': 'Controle de Ferramentas'},
                ]
            },
            {
                'id': 'main_dashboard',
                'title': 'Dashboard Integrado',
                'permission': 'GARANT_ALL',
                'icon': 'images/favicon.ico',
                'links': [
                    {'url': 'dashboard:dashboard_geral', 'text': 'Visão Geral'},
                ]
            },
        ]


class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    """Alteração de senha do próprio usuário logado."""
    form_class = CustomPasswordChangeForm
    template_name = 'usuario/alterar_senha.html'
    success_url = reverse_lazy('usuario:profile')

    def form_valid(self, form):
        messages.success(self.request, 'Sua senha foi alterada com sucesso!')
        return super().form_valid(form)


# =============================================================================
# CRUD DE USUÁRIOS (Staff/Admin)
# =============================================================================

class UserListView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    """Lista de usuários com busca e filtro por filial ativa."""
    model = Usuario
    template_name = 'usuario/lista_usuarios.html'
    context_object_name = 'usuarios'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('filial_ativa').order_by('first_name')
        active_filial_id = self.request.session.get('active_filial_id')

        if not self.request.user.is_superuser and active_filial_id:
            qs = qs.filter(filiais_permitidas__id=active_filial_id).distinct()

        search = self.request.GET.get('q', '').strip()
        if search:
            qs = qs.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )
        return qs


class UserCreateView(LoginRequiredMixin, AdminOrManagerMixin, CreateView):
    """Criação de novo usuário."""
    model = Usuario
    form_class = CustomUserCreationForm
    template_name = 'usuario/form_usuario.html'
    success_url = reverse_lazy('usuario:lista_usuarios')

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.object

        # Define a primeira filial permitida como ativa
        primeira_filial = user.filiais_permitidas.first()
        if primeira_filial:
            user.filial_ativa = primeira_filial
            user.save(update_fields=['filial_ativa'])

        messages.success(self.request, f"Usuário '{user.username}' criado com sucesso.")
        return response


class UserUpdateView(LoginRequiredMixin, AdminOrManagerMixin, UpdateView):
    """Edição de usuário existente."""
    model = Usuario
    form_class = CustomUserChangeForm
    template_name = 'usuario/form_usuario.html'
    success_url = reverse_lazy('usuario:lista_usuarios')

    def get_queryset(self):
        return super().get_queryset().select_related('filial_ativa')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.object:
            kwargs['filiais_permitidas_qs'] = self.object.filiais_permitidas.all()
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f"Usuário '{form.instance.username}' atualizado com sucesso.")
        return super().form_valid(form)


class UserToggleActiveView(LoginRequiredMixin, AdminOrManagerMixin, View):
    """Ativar/desativar um usuário."""

    def post(self, request, *args, **kwargs):
        user_to_toggle = get_object_or_404(Usuario, pk=self.kwargs.get('pk'))

        if user_to_toggle == request.user:
            messages.error(request, "Você não pode desativar a si mesmo.")
            return redirect('usuario:lista_usuarios')

        # Staff não pode desativar superusuários
        if user_to_toggle.is_superuser and not request.user.is_superuser:
            messages.error(request, "Apenas superusuários podem desativar outros superusuários.")
            return redirect('usuario:lista_usuarios')

        user_to_toggle.is_active = not user_to_toggle.is_active
        user_to_toggle.save(update_fields=['is_active'])

        status = "ativado" if user_to_toggle.is_active else "desativado"
        messages.success(request, f"Usuário '{user_to_toggle.username}' {status} com sucesso.")
        return redirect('usuario:lista_usuarios')


class UserSetPasswordView(LoginRequiredMixin, SuperuserRequiredMixin, FormView):
    """Permite superusuário definir nova senha para outro usuário."""
    form_class = SetPasswordForm
    template_name = 'usuario/definir_senha_form.html'
    success_url = reverse_lazy('usuario:lista_usuarios')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = get_object_or_404(Usuario, pk=self.kwargs['pk'])
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, f"Senha de '{form.user.username}' redefinida com sucesso.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['usuario_alvo'] = get_object_or_404(Usuario, pk=self.kwargs['pk'])
        return context


# =============================================================================
# CRUD DE GRUPOS (Superusuário)
# =============================================================================

class GroupListView(LoginRequiredMixin, SuperuserRequiredMixin, ListView):
    model = Group
    template_name = 'usuario/grupo_lista.html'
    context_object_name = 'grupos'


class GroupCreateView(LoginRequiredMixin, SuperuserRequiredMixin, CreateView):
    model = Group
    form_class = GrupoForm
    template_name = 'usuario/grupo_form.html'
    success_url = reverse_lazy('usuario:grupo_lista')

    def form_valid(self, form):
        messages.success(self.request, f"Grupo '{form.instance.name}' criado com sucesso.")
        return super().form_valid(form)


class GroupUpdateView(LoginRequiredMixin, SuperuserRequiredMixin, UpdateView):
    model = Group
    form_class = GrupoForm
    template_name = 'usuario/grupo_form.html'
    success_url = reverse_lazy('usuario:grupo_lista')

    def form_valid(self, form):
        messages.success(self.request, f"Grupo '{form.instance.name}' atualizado com sucesso.")
        return super().form_valid(form)


class GroupDeleteView(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = Group
    template_name = 'usuario/grupo_confirmar_exclusao.html'
    success_url = reverse_lazy('usuario:grupo_lista')

    def form_valid(self, form):
        messages.success(self.request, f"Grupo excluído com sucesso.")
        return super().form_valid(form)


class GerenciarGruposUsuarioView(LoginRequiredMixin, SuperuserRequiredMixin, View):
    """Adicionar/remover grupos de um usuário específico."""
    template_name = 'usuario/gerenciar_grupos_usuario.html'

    def get(self, request, *args, **kwargs):
        usuario = get_object_or_404(Usuario, pk=self.kwargs.get('pk'))
        grupos_usuario = usuario.groups.all()
        context = {
            'usuario_alvo': usuario,
            'grupos_usuario': grupos_usuario,
            'grupos_disponiveis': Group.objects.exclude(pk__in=grupos_usuario),
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
                messages.success(request, f"Grupo '{grupo.name}' adicionado a '{usuario.username}'.")
            elif acao == 'remover':
                usuario.groups.remove(grupo)
                messages.success(request, f"Grupo '{grupo.name}' removido de '{usuario.username}'.")

        return redirect('usuario:gerenciar_grupos_usuario', pk=usuario.pk)


# =============================================================================
# CRUD DE FILIAIS (Superusuário)
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
            messages.error(
                request,
                'Esta filial não pode ser excluída pois existem registros associados a ela.'
            )
            return redirect('usuario:filial_list')


# =============================================================================
# GERENCIAMENTO DE CARDS POR GRUPO
# =============================================================================

class ManageCardPermissionsView(LoginRequiredMixin, SuperuserRequiredMixin, View):
    """Configura quais cards cada grupo pode ver."""
    template_name = 'usuario/gerenciar_cards.html'

    ALL_CARDS = [
        {'id': 'clientes', 'title': 'Clientes'},
        {'id': 'dp', 'title': 'Departamento Pessoal'},
        {'id': 'sst', 'title': 'Segurança do Trabalho'},
        {'id': 'endereco', 'title': 'Logradouro'},
        {'id': 'ga', 'title': 'Gestão Administrativa'},
        {'id': 'veiculos', 'title': 'Veículos'},
        {'id': 'operacao', 'title': 'Operação'},
        {'id': 'main_dashboard', 'title': 'Dashboard Integrado'},
    ]

    def get(self, request, *args, **kwargs):
        context = {
            'grupos': Group.objects.all().order_by('name'),
            'todos_os_cards': self.ALL_CARDS,
            'permissoes_por_grupo': {
                p.group_id: p.cards_visiveis
                for p in GroupCardPermissions.objects.all()
            },
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        card_ids = [c['id'] for c in self.ALL_CARDS]

        for group in Group.objects.all():
            cards_selecionados = [
                cid for cid in card_ids
                if f'group_{group.id}_{cid}' in request.POST
            ]
            GroupCardPermissions.objects.update_or_create(
                group=group,
                defaults={'cards_visiveis': cards_selecionados}
            )

        messages.success(request, "Permissões de cards atualizadas com sucesso!")
        return redirect('usuario:gerenciar_cards')


# =============================================================================
# RECUPERAÇÃO DE SENHA
# =============================================================================

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
