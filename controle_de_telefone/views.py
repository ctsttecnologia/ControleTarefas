# controle_de_telefone/views.py

import os
import json
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.files.base import ContentFile
from django.db.models import Count, ProtectedError, Q
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View

from notifications.models import Notificacao
from .forms import VinculoForm
from .forms import VinculoAssinaturaForm # Precisamos criar este formulário
import base64
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
)
from core.mixins import ViewFilialScopedMixin, FilialCreateMixin
from .forms import (
    AparelhoForm, LinhaTelefonicaForm, VinculoForm, MarcaForm,
    ModeloForm, OperadoraForm, PlanoForm
)
from .models import (
    Aparelho, LinhaTelefonica, Vinculo, Marca, Modelo, Operadora, Plano,
   
)
from .pdf_generator import gerar_termo_responsabilidade_pdf  
from django.core.mail import send_mail
from django.template.loader import render_to_string



class StaffRequiredMixin(PermissionRequiredMixin):
    """
    Mixin que garante que o usuário tem permissão para acessar
    as views do departamento pessoal.
    """
    permission_required = 'auth.view_user'
    raise_exception = True

# --- CRUD para Aparelhos ---
class AparelhoListView(LoginRequiredMixin, PermissionRequiredMixin, ViewFilialScopedMixin, ListView):
    model = Aparelho
    permission_required = 'controle_de_telefone.view_aparelho'
    template_name = 'controle_de_telefone/aparelho_list.html'
    context_object_name = 'aparelhos'
    paginate_by = 10

class AparelhoDetailView(LoginRequiredMixin, PermissionRequiredMixin, ViewFilialScopedMixin, DetailView):
    model = Aparelho
    permission_required = 'controle_de_telefone.view_aparelho'
    template_name = 'controle_de_telefone/aparelho_detail.html'

class AparelhoCreateView(LoginRequiredMixin, PermissionRequiredMixin, FilialCreateMixin, CreateView):
    model = Aparelho
    form_class = AparelhoForm
    permission_required = 'controle_de_telefone.add_aparelho'
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:aparelho_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastrar Novo Aparelho'
        context['voltar_url'] = reverse_lazy('controle_de_telefone:aparelho_list')
        return context

class AparelhoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, ViewFilialScopedMixin, UpdateView):
    model = Aparelho
    form_class = AparelhoForm
    permission_required = 'controle_de_telefone.change_aparelho'
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:aparelho_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Aparelho'
        context['voltar_url'] = reverse_lazy('controle_de_telefone:aparelho_list')
        return context

class AparelhoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, ViewFilialScopedMixin, DeleteView):
    model = Aparelho
    permission_required = 'controle_de_telefone.delete_aparelho'
    template_name = 'controle_de_telefone/generic_confirm_delete.html'
    success_url = reverse_lazy('controle_de_telefone:aparelho_list')

# --- CRUD para LinhaTelefonica ---
class LinhaTelefonicaListView(LoginRequiredMixin, PermissionRequiredMixin, ViewFilialScopedMixin, ListView):
    model = LinhaTelefonica
    permission_required = 'controle_de_telefone.view_linhatelefonica'
    template_name = 'controle_de_telefone/linhatelefonica_list.html'
    context_object_name = 'linhas'
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset().select_related('plano', 'plano__operadora', 'filial')
        search_query = self.request.GET.get('q', None)
        if search_query:
            queryset = queryset.filter(
                Q(numero__icontains=search_query) |
                Q(plano__nome__icontains=search_query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context

class LinhaTelefonicaDetailView(LoginRequiredMixin, PermissionRequiredMixin, ViewFilialScopedMixin, DetailView):
    model = LinhaTelefonica
    permission_required = 'controle_de_telefone.view_linhatelefonica'
    template_name = 'controle_de_telefone/linhatelefonica_detail.html'

    def get_queryset(self):
        return super().get_queryset().select_related('plano', 'plano__operadora', 'filial')

class LinhaTelefonicaCreateView(LoginRequiredMixin, PermissionRequiredMixin, FilialCreateMixin, SuccessMessageMixin, CreateView):
    model = LinhaTelefonica
    form_class = LinhaTelefonicaForm
    permission_required = 'controle_de_telefone.add_linhatelefonica'
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:linhatelefonica_list')
    success_message = "Linha telefônica cadastrada com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastrar Nova Linha Telefônica'
        context['voltar_url'] = self.success_url
        return context

class LinhaTelefonicaUpdateView(LoginRequiredMixin, PermissionRequiredMixin, ViewFilialScopedMixin, SuccessMessageMixin, UpdateView):
    model = LinhaTelefonica
    form_class = LinhaTelefonicaForm
    permission_required = 'controle_de_telefone.change_linhatelefonica'
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:linhatelefonica_list')
    success_message = "Linha telefônica atualizada com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Linha Telefônica'
        context['voltar_url'] = self.success_url
        return context

class LinhaTelefonicaDeleteView(LoginRequiredMixin, PermissionRequiredMixin, ViewFilialScopedMixin, DeleteView):
    model = LinhaTelefonica
    permission_required = 'controle_de_telefone.delete_linhatelefonica'
    template_name = 'controle_de_telefone/generic_confirm_delete.html'
    success_url = reverse_lazy('controle_de_telefone:linhatelefonica_list')

    def post(self, request, *args, **kwargs):
        try:
            response = super().delete(request, *args, **kwargs)
            messages.success(request, "Linha telefônica excluída com sucesso!")
            return response
        except ProtectedError:
            messages.error(request, "Erro: Esta linha não pode ser excluída pois está vinculada a um ou mais colaboradores.")
            # Redireciona para a página de confirmação de exclusão para mostrar o erro
            return redirect(reverse_lazy('controle_de_telefone:linhatelefonica_delete', kwargs={'pk': self.kwargs.get('pk')}))


# --- CRUDs para Modelos de Apoio (Marca, Modelo, Operadora, Plano) ---
class MarcaListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Marca
    permission_required = 'controle_de_telefone.view_marca'
    template_name = 'controle_de_telefone/marca_list.html'
    context_object_name = 'marcas'
    paginate_by = 15

class MarcaCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = Marca
    form_class = MarcaForm
    permission_required = 'controle_de_telefone.add_marca'
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:marca_list')
    success_message = "Marca criada com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastrar Nova Marca'
        context['voltar_url'] = self.success_url
        return context

class MarcaUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Marca
    form_class = MarcaForm
    permission_required = 'controle_de_telefone.change_marca'
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:marca_list')
    success_message = "Marca atualizada com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Marca'
        context['voltar_url'] = self.success_url
        return context

class MarcaDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Marca
    permission_required = 'controle_de_telefone.delete_marca'
    template_name = 'controle_de_telefone/generic_confirm_delete.html'
    success_url = reverse_lazy('controle_de_telefone:marca_list')

class ModeloListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Modelo
    permission_required = 'controle_de_telefone.view_modelo'
    template_name = 'controle_de_telefone/modelo_list.html'
    context_object_name = 'modelos'
    paginate_by = 15

class ModeloCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = Modelo
    form_class = ModeloForm
    permission_required = 'controle_de_telefone.add_modelo'
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:modelo_list')
    success_message = "Modelo criado com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastrar Novo Modelo'
        context['voltar_url'] = self.success_url
        return context

class ModeloUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Modelo
    form_class = ModeloForm
    permission_required = 'controle_de_telefone.change_modelo'
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:modelo_list')
    success_message = "Modelo atualizado com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Modelo'
        context['voltar_url'] = self.success_url
        return context

class ModeloDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Modelo
    permission_required = 'controle_de_telefone.delete_modelo'
    template_name = 'controle_de_telefone/generic_confirm_delete.html'
    success_url = reverse_lazy('controle_de_telefone:modelo_list')

class OperadoraListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Operadora
    permission_required = 'controle_de_telefone.view_operadora'
    template_name = 'controle_de_telefone/operadora_list.html'
    context_object_name = 'operadoras'
    paginate_by = 15

class OperadoraCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = Operadora
    form_class = OperadoraForm
    permission_required = 'controle_de_telefone.add_operadora'
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:operadora_list')
    success_message = "Operadora criada com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastrar Nova Operadora'
        context['voltar_url'] = self.success_url
        return context

class OperadoraUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Operadora
    form_class = OperadoraForm
    permission_required = 'controle_de_telefone.change_operadora'
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:operadora_list')
    success_message = "Operadora atualizada com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Operadora'
        context['voltar_url'] = self.success_url
        return context

class OperadoraDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Operadora
    permission_required = 'controle_de_telefone.delete_operadora'
    template_name = 'controle_de_telefone/generic_confirm_delete.html'
    success_url = reverse_lazy('controle_de_telefone:operadora_list')

class PlanoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Plano
    permission_required = 'controle_de_telefone.view_plano'
    template_name = 'controle_de_telefone/plano_list.html'
    context_object_name = 'planos'
    paginate_by = 15

class PlanoCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = Plano
    form_class = PlanoForm
    permission_required = 'controle_de_telefone.add_plano'
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:plano_list')
    success_message = "Plano criado com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastrar Novo Plano'
        context['voltar_url'] = self.success_url
        return context

class PlanoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Plano
    form_class = PlanoForm
    permission_required = 'controle_de_telefone.change_plano'
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:plano_list')
    success_message = "Plano atualizado com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Plano'
        context['voltar_url'] = self.success_url
        return context

class PlanoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Plano
    permission_required = 'controle_de_telefone.delete_plano'
    template_name = 'controle_de_telefone/generic_confirm_delete.html'
    success_url = reverse_lazy('controle_de_telefone:plano_list')

# --- CRUD para Vinculo ---
class VinculoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Vinculo
    permission_required = 'controle_de_telefone.view_vinculo'
    template_name = 'controle_de_telefone/vinculo_list.html'
    context_object_name = 'vinculos'
    paginate_by = 10

    def get_queryset(self):
        filial_id = self.request.session.get('active_filial_id')
        if not filial_id:
            return Vinculo.objects.none()
        
        queryset = Vinculo.objects.filter(funcionario__filial_id=filial_id).select_related(
            'funcionario', 'aparelho__modelo__marca', 'linha__plano__operadora'
        )
        search_query = self.request.GET.get('q', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(funcionario__nome_completo__icontains=search_query) |
                Q(funcionario__matricula__icontains=search_query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context

class VinculoDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Vinculo
    permission_required = 'controle_de_telefone.view_vinculo'
    template_name = 'controle_de_telefone/vinculo_detail.html'

    def get_queryset(self):
        filial_id = self.request.session.get('active_filial_id')
        if not filial_id:
            return Vinculo.objects.none()
        return Vinculo.objects.filter(funcionario__filial_id=filial_id).select_related(
            'funcionario', 'aparelho__modelo__marca', 'linha__plano__operadora'
        )

def enviar_notificacao_de_assinatura(request, vinculo):
    raise NotImplementedError

class VinculoCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = Vinculo
    form_class = VinculoForm
    permission_required = 'controle_de_telefone.add_vinculo'
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:vinculo_list')
    success_message = "Vínculo criado com sucesso! O Termo de Responsabilidade foi gerado."

    # Este método agora passa o 'filial_id' para o formulário.
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['filial_id'] = self.request.session.get('active_filial_id')
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Criar Novo Vínculo'
        context['voltar_url'] = self.success_url
        return context

    def form_valid(self, form):
        self.object = form.save()
        try:
            pdf_buffer = gerar_termo_responsabilidade_pdf(self.object)
            file_name = f"termo_{self.object.funcionario.id}_{self.object.id}.pdf"
            self.object.termo_gerado.save(file_name, ContentFile(pdf_buffer.getvalue()), save=True)
            
            enviar_notificacao_de_assinatura(self.request, self.object)
            messages.success(self.request, self.success_message)
        except Exception as e:
            messages.error(self.request, f"O vínculo foi criado, mas ocorreu um erro ao gerar o termo ou notificar: {e}")
        
        return redirect(self.get_success_url())

class VinculoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Vinculo
    form_class = VinculoForm
    permission_required = 'controle_de_telefone.change_vinculo'
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:vinculo_list')
    success_message = "Vínculo atualizado com sucesso!"

    def get_queryset(self):
        filial_id = self.request.session.get('active_filial_id')
        if filial_id:
            return Vinculo.objects.filter(funcionario__filial_id=filial_id)
        return Vinculo.objects.none()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['filial_id'] = self.request.session.get('active_filial_id')
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Vínculo'
        context['voltar_url'] = self.success_url
        return context

    def form_valid(self, form):
        messages.success(self.request, self.success_message)
        return super().form_valid(form)

def editar_vinculo(request, pk):
    objeto = get_object_or_404(Vinculo, pk=pk)
    if request.method == 'POST':
        form = VinculoForm(request.POST, instance=objeto)
        if form.is_valid():
            form.save()
            return redirect('pagina_de_sucesso') # Redireciona após salvar
    else:
        form = VinculoForm(instance=objeto) # O formulário é instanciado com o objeto
    
    return render(request, 'seu_app/template_de_edicao.html', {'form': form, 'object': objeto})

    
class VinculoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Vinculo
    permission_required = 'controle_de_telefone.delete_vinculo'
    template_name = 'controle_de_telefone/generic_confirm_delete.html'
    success_url = reverse_lazy('controle_de_telefone:vinculo_list')

    def get_queryset(self):
        filial_id = self.request.session.get('active_filial_id')
        if not filial_id:
            return Vinculo.objects.none()
        return Vinculo.objects.filter(funcionario__filial_id=filial_id)

    def form_valid(self, form):
        messages.success(self.request, "Vínculo excluído com sucesso!")
        return super().form_valid(form)
    
class DownloadTermoView(LoginRequiredMixin, View):
    """
    Fornece o download seguro do termo de responsabilidade (PDF).
    Verifica se o usuário é o dono do vínculo ou se tem permissão de gestor.
    """
    def get(self, request, *args, **kwargs):
        vinculo_id = self.kwargs.get('pk')
        vinculo = get_object_or_404(Vinculo, pk=vinculo_id)

        # Regras de permissão
        is_owner = request.user == vinculo.funcionario.usuario
        is_manager = request.user.has_perm('controle_de_telefone.view_vinculo')
        
        if not is_owner and not is_manager:
            return HttpResponseForbidden("Você não tem permissão para acessar este arquivo.")
        
        # Gestor só pode ver arquivos da sua filial
        if is_manager:
            filial_id = request.session.get('active_filial_id')
            if vinculo.funcionario.filial_id != filial_id:
                return HttpResponseForbidden("Acesso negado a arquivos de outra filial.")

        if not vinculo.termo_gerado or not hasattr(vinculo.termo_gerado, 'path'):
            raise Http404("Nenhum termo de responsabilidade encontrado para este vínculo.")

        file_path = vinculo.termo_gerado.path
        if not os.path.exists(file_path):
            raise Http404("Arquivo não encontrado no servidor. Tente regenerar o termo.")

        return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=os.path.basename(file_path))


class RegenerarTermoView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Regera o arquivo PDF do termo de responsabilidade para um vínculo.
    """
    permission_required = 'controle_de_telefone.change_vinculo'
    raise_exception = True

    def post(self, request, *args, **kwargs):
        vinculo = get_object_or_404(Vinculo, pk=self.kwargs.get('pk'))
        try:
            pdf_buffer = gerar_termo_responsabilidade_pdf(vinculo)
            file_name = f"termo_regenerado_{vinculo.funcionario.id}_{vinculo.id}.pdf"
            vinculo.termo_gerado.save(file_name, ContentFile(pdf_buffer.getvalue()), save=True)
            messages.success(request, f"Termo para {vinculo.funcionario.nome_completo} foi gerado com sucesso!")
        except Exception as e:
            messages.error(request, f"Ocorreu um erro ao gerar o termo: {e}")
        return redirect('controle_de_telefone:vinculo_list')

class NotificarAssinaturaView(View):
    def post(self, request, *args, **kwargs):
        vinculo = get_object_or_404(Vinculo, pk=kwargs.get('pk'))
        usuario_a_notificar = vinculo.funcionario.usuario

        if not usuario_a_notificar:
            messages.error(request, "Este funcionário não possui um usuário de sistema.")
            return redirect('alguma_url_de_fallback') # Ajuste

        # Gera a URL única para a assinatura
        url_assinatura = request.build_absolute_uri(
            reverse('controle_de_telefone:vinculo_assinar', args=[vinculo.pk])
        )
        
        mensagem_notificacao = f"Você tem um Termo de Responsabilidade para o aparelho {vinculo.aparelho} pendente de assinatura."

        # --- AÇÃO 1: CRIAR NOTIFICAÇÃO PARA O SINO ---
        Notificacao.objects.create(
            usuario=usuario_a_notificar,
            mensagem=mensagem_notificacao,
            url_destino=url_assinatura
        )

        # --- AÇÃO 2: ENVIAR O E-MAIL ---
        if usuario_a_notificar.email:
            assunto = "Lembrete: Termo de Responsabilidade Pendente"
            contexto_email = {
                'nome_usuario': usuario_a_notificar.first_name or usuario_a_notificar.username,
                'nome_aparelho': str(vinculo.aparelho),
                'url_assinatura': url_assinatura,
            }
            corpo_html = render_to_string('email/notificacao_assinatura.html', contexto_email)
            
            send_mail(
                subject=assunto, message='',
                from_email='nao-responda@suaempresa.com',
                recipient_list=[usuario_a_notificar.email],
                html_message=corpo_html
            )
            messages.success(request, f"Notificação por e-mail e no sistema enviada para {usuario_a_notificar.get_full_name()}.")
        else:
            messages.warning(request, "Notificação criada no sistema, mas o funcionário não possui e-mail cadastrado.")
            
        return redirect(request.META.get('HTTP_REFERER', '/'))


class AssinarTermoView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """
    Página onde o funcionário logado pode visualizar e assinar o termo.
    """
    model = Vinculo
    form_class = VinculoAssinaturaForm
    template_name = 'controle_de_telefone/vinculo_assinatura.html'
    context_object_name = 'vinculo'
    success_url = reverse_lazy('controle_de_telefone:vinculo_list')
    success_message = "Termo de Responsabilidade assinado com sucesso!"

    def get_success_url(self):
        messages.success(self.request, "Termo de responsabilidade assinado e enviado com sucesso!")
        # Redireciona para uma página de sucesso ou de detalhes do vínculo
        return reverse('controle_de_telefone:dashboard')


    def dispatch(self, request, *args, **kwargs):
        vinculo = self.get_object()
        if not request.user == vinculo.funcionario.usuario:
            messages.error(request, "Você não tem permissão para assinar este termo.")
            return redirect('controle_de_telefone:vinculo_list')
        if vinculo.foi_assinado:
            messages.info(request, "Este termo já foi assinado.")
            return redirect('controle_de_telefone:vinculo_list')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Assinar Termo de Responsabilidade'
        context['termo_clauses'] = {
            'Cláusula 1': "A CETEST MINAS ENGENHARIA E SERVIÇOS S.A NÃO autoriza o portador, ao qual este equipamento se encontra sob responsabilidade por intermédio deste termo, seja em comunicação de voz ou em transmissão de dados, receber e enviar conteúdo considerado inadequado ou ilegal, sob o ponto de vista da ética e da legislação. [cite: 13]",
            'Cláusula 2': "Será de responsabilidade do usuário, signatário deste termo, responder por qualquer forma de comunicação que demonstre atitude de preconceito e racismo, exploração do trabalho escravo, depreciação de entidades públicas e seus servidores, assédio sexual e moral, participação em negócios exclusos aos propósitos desta empresa, descumprimento de legislação e normas reguladoras da competição saudável de mercado. [cite: 14]",
            'Cláusula 3': f"Fica aos cuidados do(a) Sr.(a) {self.object.funcionario.nome_completo} a guarda e conservação do aparelho e respectivos acessórios entregues nesta data, devendo restituí-los sempre que for solicitado pela empresa ou em caso de rescisão do contrato de trabalho, sob pena de responsabilizar-se pelo pagamento de eventuais danos materiais. [cite: 15]",
            'Cláusula 4': "Fica vedado ao Usuário permutar o equipamento, ou qualquer um de seus acessórios, com outro usuário. [cite: 16] [cite_start]É proibida a troca do e-mail e senha fornecida pela empresa. [cite: 17]",
            'Cláusula 5': "A qualquer momento e sem prévio aviso, a empresa CETEST MINAS ENGENHARIA E SERVIÇOS S.A poderá solicitar a devolução imediata da linha e do aparelho. [cite: 18]"
        }
        return context

    def form_valid(self, form):
        # 1. Salva o formulário. Isso executará o método .save() customizado no forms.py,
        # que decodifica a assinatura e a salva no campo 'assinatura_digital'.
        vinculo = form.save(commit=False) # commit=False para podermos adicionar o PDF
        vinculo.foi_assinado = True
        vinculo.data_assinatura = timezone.now()
        vinculo.save() # Salva o vínculo com a imagem da assinatura

        # 2. Gera o PDF. A função agora terá acesso ao 'vinculo.assinatura_digital'
        # que acabamos de salvar.
        pdf_buffer = gerar_termo_responsabilidade_pdf(vinculo)
        
        # 3. Salva o PDF gerado (com a assinatura) no campo de upload
        pdf_filename = f'termo_assinado_{vinculo.pk}.pdf'
        vinculo.termo_assinado_upload.save(pdf_filename, ContentFile(pdf_buffer.read()), save=True)

        # O form.save() original é chamado implicitamente pelas ações acima.
        # Nós redirecionamos para a success_url.
        return super().form_valid(form)
    
# --- Dashboard e Views de Ação ---

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'controle_de_telefone/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # --- 1. DADOS PARA OS CARDS DE RESUMO ---
        context['total_aparelhos'] = Aparelho.objects.count()
        context['total_linhas'] = LinhaTelefonica.objects.count()
        context['total_vinculos'] = Vinculo.objects.filter(data_devolucao__isnull=True).count()

        # --- [INÍCIO DA CORREÇÃO] Adiciona a contagem para os cadastros auxiliares ---
        context['total_marcas'] = Marca.objects.count()
        context['total_modelos'] = Modelo.objects.count()
        context['total_operadoras'] = Operadora.objects.count()
        context['total_planos'] = Plano.objects.count()
    

        # Gráfico: Aparelhos por Marca
        aparelhos_por_marca = Aparelho.objects.values('modelo__marca__nome').annotate(total=Count('id')).order_by('-total')
        context['marcas_labels_json'] = json.dumps([item['modelo__marca__nome'] for item in aparelhos_por_marca])
        context['marcas_data_json'] = json.dumps([item['total'] for item in aparelhos_por_marca])

        # Gráfico: Linhas por Operadora
        linhas_por_operadora = LinhaTelefonica.objects.values('plano__operadora__nome').annotate(total=Count('id')).order_by('-total')
        context['operadoras_labels_json'] = json.dumps([item['plano__operadora__nome'] for item in linhas_por_operadora])
        context['operadoras_data_json'] = json.dumps([item['total'] for item in linhas_por_operadora])

        # Gráfico: Vínculos Ativos vs. Inativos
        vinculos_ativos = context['total_vinculos'] # Reutiliza a contagem já feita
        vinculos_inativos = Vinculo.objects.filter(data_devolucao__isnull=False).count()
        context['vinculos_status_data_json'] = json.dumps([vinculos_ativos, vinculos_inativos])

        return context
        context['marcas_data_json'] = json.dumps([item['total'] for item in aparelhos_por_marca])

        # Gráfico: Linhas por Operadora
        linhas_por_operadora = LinhaTelefonica.objects.values('plano__operadora__nome').annotate(total=Count('id')).order_by('-total')
        context['operadoras_labels_json'] = json.dumps([item['plano__operadora__nome'] for item in linhas_por_operadora])
        context['operadoras_data_json'] = json.dumps([item['total'] for item in linhas_por_operadora])

        # Gráfico: Vínculos Ativos vs. Inativos
        vinculos_ativos = context['total_vinculos'] # Reutiliza a contagem já feita
        vinculos_inativos = Vinculo.objects.filter(data_devolucao__isnull=False).count()
        context['vinculos_status_data_json'] = json.dumps([vinculos_ativos, vinculos_inativos])

        return context

        # Gráfico: Linhas por Operadora
        linhas_por_operadora = LinhaTelefonica.objects.values('plano__operadora__nome').annotate(total=Count('id')).order_by('-total')
        context['operadoras_labels_json'] = json.dumps([item['plano__operadora__nome'] for item in linhas_por_operadora])
        context['operadoras_data_json'] = json.dumps([item['total'] for item in linhas_por_operadora])

        # Gráfico: Vínculos Ativos vs. Inativos
        vinculos_ativos = context['total_vinculos'] # Reutiliza a contagem já feita
        vinculos_inativos = Vinculo.objects.filter(data_devolucao__isnull=False).count()
        context['vinculos_status_data_json'] = json.dumps([vinculos_ativos, vinculos_inativos])

        return context




