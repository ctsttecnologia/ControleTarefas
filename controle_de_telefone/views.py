# controle_de_telefone/views.py

import os
import json
import zipfile
from django.http import HttpResponse
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
from departamento_pessoal.models import Documento
from notifications.models import Notificacao
from .forms import VinculoForm
from .forms import VinculoAssinaturaForm # Precisamos criar este formulário
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
)
from core.mixins import ViewFilialScopedMixin, FilialCreateMixin
from .forms import (
    AparelhoForm, LinhaTelefonicaForm, VinculoForm, MarcaForm,
    ModeloForm, OperadoraForm, PlanoForm, Vinculo
)
from .models import (
    Aparelho, LinhaTelefonica, Vinculo, Marca, Modelo, Operadora, Plano,  
)
from django.core.mail import send_mail
from django.template.loader import render_to_string
import base64
from .pdf_utils import gerar_termo_pdf_assinado
from io import BytesIO
from django.conf import settings
from weasyprint import HTML
from xhtml2pdf import pisa  # Garanta que você tem o xhtml2pdf instalado
from .utils import get_logo_base64


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
class VinculoListView(LoginRequiredMixin, PermissionRequiredMixin, ViewFilialScopedMixin, ListView):
    # Mantenha esta view como está
    model = Vinculo
    permission_required = 'controle_de_telefone.view_vinculo'
    template_name = 'controle_de_telefone/vinculo_list.html'
    context_object_name = 'vinculos'
    paginate_by = 20


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

class VinculoDetailView(LoginRequiredMixin, PermissionRequiredMixin, ViewFilialScopedMixin, DetailView):
    # Mantenha esta view como está
    model = Vinculo
    permission_required = 'controle_de_telefone.view_vinculo'
    template_name = 'controle_de_telefone/vinculo_detail.html'
    context_object_name = 'vinculo'

    def get_queryset(self):
        filial_id = self.request.session.get('active_filial_id')
        if not filial_id:
            return Vinculo.objects.none()
        return Vinculo.objects.filter(funcionario__filial_id=filial_id).select_related(
            'funcionario', 'aparelho__modelo__marca', 'linha__plano__operadora'
        )

def enviar_notificacao_de_assinatura(request, vinculo):
    raise NotImplementedError

class VinculoCreateView(LoginRequiredMixin, PermissionRequiredMixin, FilialCreateMixin, SuccessMessageMixin, CreateView):
    model = Vinculo
    form_class = VinculoForm
    permission_required = 'controle_de_telefone.add_vinculo'
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:vinculo_list')
    success_message = "Vínculo criado! O funcionário foi notificado para assinar o termo."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['filial_id'] = self.request.session.get('active_filial_id')
        return kwargs

    def form_valid(self, form):
        # 1. Salve o objeto chamando form.save() antes de super()
        # Isso te dá acesso à instância do objeto recém-criado.
        self.object = form.save()

        # 2. Execute sua lógica customizada.
        if self.object.funcionario.usuario:
            url_assinatura = self.request.build_absolute_uri(
                reverse('controle_de_telefone:vinculo_assinar', args=[self.object.pk])
            )
            Notificacao.objects.create(
                usuario=self.object.funcionario.usuario,
                mensagem=f"Você tem um novo Termo de Responsabilidade para o aparelho {self.object.aparelho} pendente de assinatura.",
                url_destino=url_assinatura
            )
        
        # 3. Chame o super().form_valid(form) para que a lógica padrão do Django
        # seja executada, incluindo o redirecionamento para o success_url.
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Criar Novo Vínculo'
        context['voltar_url'] = self.success_url
        return context

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
    """
    def get(self, request, *args, **kwargs):
        vinculo = get_object_or_404(Vinculo, pk=self.kwargs.get('pk'))
        
        # Lógica de permissão... (mantida como está, parece correta)
        is_owner = request.user == vinculo.funcionario.usuario
        is_manager = request.user.has_perm('controle_de_telefone.view_vinculo')
        
        if not is_owner and not is_manager:
            return HttpResponseForbidden("Você não tem permissão para acessar este arquivo.")
        
        if is_manager:
            filial_id = request.session.get('active_filial_id')
            if vinculo.funcionario.filial_id != filial_id:
                return HttpResponseForbidden("Acesso negado a arquivos de outra filial.")

        # A LÓGICA ABAIXO FOI REVISADA
        # Verifica se o termo assinado existe, caso contrário, verifica o termo não assinado
        file_to_download = None
        if vinculo.termo_assinado_upload and vinculo.termo_assinado_upload.name:
            file_to_download = vinculo.termo_assinado_upload
        elif vinculo.termo_gerado and vinculo.termo_gerado.name:
            file_to_download = vinculo.termo_gerado

        if not file_to_download or not os.path.exists(file_to_download.path):
            raise Http404("Nenhum termo de responsabilidade encontrado para este vínculo. Tente regenerar o termo.")

        return FileResponse(open(file_to_download.path, 'rb'), as_attachment=True, filename=os.path.basename(file_to_download.path))
    
# Daunload de todos os termos

class DownloadTermosAssinadosView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'controle_de_telefone.view_vinculo'

    def get(self, request, *args, **kwargs):
        # A nova URL que você criou
        filial_id = request.session.get('active_filial_id')
        
        # Filtra os vínculos que foram assinados e que pertencem à filial do usuário
        vinculos_assinados = Vinculo.objects.filter(
            foi_assinado=True, 
            termo_assinado_upload__isnull=False,
            funcionario__filial_id=filial_id
        )
        
        if not vinculos_assinados.exists():
            return HttpResponse("Nenhum termo assinado encontrado para download.", status=404)

        # Cria um buffer de memória para o arquivo ZIP
        buffer = BytesIO()
        zip_file = zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED)
        
        for vinculo in vinculos_assinados:
            # Pega o caminho do arquivo PDF assinado
            file_path = vinculo.termo_assinado_upload.path
            
            # Adiciona o arquivo ao ZIP com um nome amigável
            file_name = f'termo_{vinculo.funcionario.nome_completo}_{vinculo.aparelho}.pdf'
            zip_file.write(file_path, file_name)

        zip_file.close()
        buffer.seek(0)
        
        # Cria a resposta HTTP com o arquivo ZIP
        response = HttpResponse(buffer, content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="termos_assinados.zip"'
        return response


class RegenerarTermoView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Regera o arquivo PDF do termo de responsabilidade para um vínculo.
    """
    permission_required = 'controle_de_telefone.change_vinculo'
    raise_exception = True

    def post(self, request, *args, **kwargs):
        vinculo = get_object_or_404(Vinculo, pk=self.kwargs.get('pk'))
        try:
            pdf_buffer = gerar_termo_pdf_assinado(vinculo)
            
            # Use o campo correto dependendo se o termo foi assinado ou não
            if vinculo.foi_assinado:
                file_name = f"termo_assinado_{vinculo.pk}.pdf"
                vinculo.termo_assinado_upload.save(file_name, ContentFile(pdf_buffer.getvalue()), save=True)
            else:
                file_name = f"termo_gerado_{vinculo.pk}.pdf"
                vinculo.termo_gerado.save(file_name, ContentFile(pdf_buffer.getvalue()), save=True)
            
            messages.success(request, f"Termo para {vinculo.funcionario.nome_completo} foi gerado com sucesso!")
        except Exception as e:
            messages.error(request, f"Ocorreu um erro ao gerar o termo: {e}")
        
        return redirect('controle_de_telefone:vinculo_detail', pk=vinculo.pk)


def gerar_termo_pdf(vinculo):
    """
    Gera o PDF do termo de responsabilidade, buscando todos os dados necessários.
    """
    context = {'vinculo': vinculo}

    # 1. Busca a Logo
    context['logo_base64'] = get_logo_base64()

    # 2. Busca o RG do funcionário
    try:
        rg_doc = Documento.objects.get(funcionario=vinculo.funcionario, tipo_documento='RG')
        context['rg_numero'] = rg_doc.numero
    except Documento.DoesNotExist:
        context['rg_numero'] = "Documento não encontrado"

    # 3. Busca o caminho ABSOLUTO da assinatura digital
    if vinculo.assinatura_digital and hasattr(vinculo.assinatura_digital, 'path'):
        context['assinatura_path'] = vinculo.assinatura_digital.path
    else:
        context['assinatura_path'] = None

    # Renderiza o template do PDF com o contexto completo
    html = render_to_string('controle_de_telefone/termo_pdf.html', context)
    
    # Cria o PDF
    buffer = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=buffer)

    if pisa_status.err:
        return None # Ou levante uma exceção
    
    buffer.seek(0)
    return buffer

def form_valid(self, form):
    # Primeiro, salva o formulário. O método save() customizado do form
    # já cuida de salvar a imagem da assinatura.
    vinculo = form.save(commit=False)
    vinculo.foi_assinado = True
    vinculo.data_assinatura = timezone.now()
    vinculo.save() # Salva o vinculo com os dados e a assinatura

    try:
        # AGORA, com o vínculo salvo e a assinatura no lugar, geramos o PDF.
        pdf_buffer = gerar_termo_pdf(vinculo)
        if pdf_buffer:
            pdf_filename = f'termo_assinado_{vinculo.pk}.pdf'
            vinculo.termo_assinado_upload.save(pdf_filename, ContentFile(pdf_buffer.getvalue()), save=True)
            messages.success(self.request, "Termo assinado e PDF gerado com sucesso!")
        else:
            messages.error(self.request, "Assinatura salva, mas houve um erro ao gerar o PDF.")

    except Exception as e:
        messages.error(self.request, f"Assinatura salva, mas houve um erro ao gerar o PDF final: {e}")

    return redirect(self.get_success_url())
   

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

def get_logo_base64():
    """Lê o arquivo da logo e retorna seu conteúdo codificado em Base64."""
    logo_path = os.path.join(settings.STATICFILES_DIRS[0], 'images', 'logocetest.png')
    try:
        with open(logo_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except FileNotFoundError:
        return None

class AssinarTermoView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Vinculo
    form_class = VinculoAssinaturaForm
    template_name = 'controle_de_telefone/termo_assinar_form.html'
    context_object_name = 'vinculo'
    success_message = "Termo de Responsabilidade assinado com sucesso!"

    def get_success_url(self):
        # Redireciona para os detalhes do vínculo que foi assinado
        return reverse('controle_de_telefone:vinculo_detail', kwargs={'pk': self.object.pk})

    def dispatch(self, request, *args, **kwargs):
        vinculo = self.get_object()
        # Valida se o usuário logado é o dono do vínculo
        if not request.user == vinculo.funcionario.usuario:
            messages.error(request, "Você não tem permissão para assinar este termo.")
            return redirect('controle_de_telefone:vinculo_list')
        # Valida se o termo já foi assinado previamente
        if vinculo.foi_assinado:
            messages.info(request, "Este termo já foi assinado.")
            return redirect(self.get_success_url())
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """
        Processa os dados do formulário após a submissão (POST).
        """
        vinculo = form.instance

        # Lê os dados da assinatura diretamente do request
        signature_type = self.request.POST.get('signature_type')
        assinatura_salva = False

        # Processa a assinatura desenhada (base64)
        if signature_type == 'draw':
            base64_data = self.request.POST.get('assinatura_base64')
            if base64_data and ';base64,' in base64_data:
                try:
                    format, imgstr = base64_data.split(';base64,')
                    ext = format.split('/')[-1]
                    file_name = f"assinatura_{vinculo.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}.{ext}"
                    data = ContentFile(base64.b64decode(imgstr), name=file_name)
                    vinculo.assinatura_digital = data
                    assinatura_salva = True
                except Exception as e:
                    messages.error(self.request, f"Erro ao decodificar a assinatura: {e}")
                    return self.form_invalid(form)

        # Processa a assinatura via upload de imagem
        elif signature_type == 'upload':
            image_file = self.request.FILES.get('assinatura_imagem_upload')
            if image_file:
                vinculo.assinatura_digital = image_file
                assinatura_salva = True
        
        if not assinatura_salva:
            messages.error(self.request, "Assinatura não fornecida. Por favor, desenhe ou faça o upload.")
            return self.form_invalid(form)

        # Define as flags de assinatura
        vinculo.foi_assinado = True
        vinculo.data_assinatura = timezone.now()
        
        # Salva o vínculo com a nova imagem da assinatura no disco
        vinculo.save()

        # Tenta gerar o PDF assinado
        try:
            pdf_buffer = gerar_termo_pdf_assinado(vinculo)
            pdf_filename = f'termo_assinado_{vinculo.pk}_{timezone.now().strftime("%Y%m%d")}.pdf'
            vinculo.termo_assinado_upload.save(pdf_filename, ContentFile(pdf_buffer.getvalue()), save=True)
            
        except Exception as e:
            messages.error(self.request, f"Assinatura salva, mas houve um erro ao gerar o PDF final: {e}")

        # Finaliza o processo, exibindo a mensagem de sucesso e redirecionando
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """
        Adiciona dados extras ao contexto para renderizar o template (GET).
        """
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Assinar Termo de Responsabilidade'
        
        # Adiciona a logo em base64, se a função existir
        if 'get_logo_base64' in globals():
            context['logo_base64'] = get_logo_base64()
        
        try:
            # CORREÇÃO: Usar 'self.object' para se referir à instância do vínculo
            rg_doc = Documento.objects.get(funcionario=self.object.funcionario, tipo_documento='RG')
            context['rg_numero'] = rg_doc.numero
        except Documento.DoesNotExist:
            context['rg_numero'] = "RG não encontrado"
        
        return context
    
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

        context['marcas_data_json'] = json.dumps([item['total'] for item in aparelhos_por_marca])

        # Gráfico: Linhas por Operadora
        linhas_por_operadora = LinhaTelefonica.objects.values('plano__operadora__nome').annotate(total=Count('id')).order_by('-total')
        context['operadoras_labels_json'] = json.dumps([item['plano__operadora__nome'] for item in linhas_por_operadora])
        context['operadoras_data_json'] = json.dumps([item['total'] for item in linhas_por_operadora])

        # Gráfico: Vínculos Ativos vs. Inativos
        vinculos_ativos = context['total_vinculos'] # Reutiliza a contagem já feita
        vinculos_inativos = Vinculo.objects.filter(data_devolucao__isnull=False).count()
        context['vinculos_status_data_json'] = json.dumps([vinculos_ativos, vinculos_inativos])

        # Gráfico: Linhas por Operadora
        linhas_por_operadora = LinhaTelefonica.objects.values('plano__operadora__nome').annotate(total=Count('id')).order_by('-total')
        context['operadoras_labels_json'] = json.dumps([item['plano__operadora__nome'] for item in linhas_por_operadora])
        context['operadoras_data_json'] = json.dumps([item['total'] for item in linhas_por_operadora])

        # Gráfico: Vínculos Ativos vs. Inativos
        vinculos_ativos = context['total_vinculos'] # Reutiliza a contagem já feita
        vinculos_inativos = Vinculo.objects.filter(data_devolucao__isnull=False).count()
        context['vinculos_status_data_json'] = json.dumps([vinculos_ativos, vinculos_inativos])

        return context




