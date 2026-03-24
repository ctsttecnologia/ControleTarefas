# controle_de_telefone/views.py

import os
import json
import base64
import zipfile
from io import BytesIO

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.db.models import Count, ProtectedError, Q, Sum
from django.http import FileResponse, Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView,
)
from xhtml2pdf import pisa

from core.mixins import ViewFilialScopedMixin, AppPermissionMixin
from departamento_pessoal.models import Documento
from notifications.models import Notificacao

from .forms import (
    AparelhoForm, LinhaTelefonicaForm, VinculoForm, VinculoAssinaturaForm,
    MarcaForm, ModeloForm, OperadoraForm, PlanoForm,
    RecargaCreditoForm, RecargaCreditoRealizarForm,
)
from .models import (
    Aparelho, LinhaTelefonica, Vinculo, Marca, Modelo, Operadora, Plano,
    RecargaCredito,
)
from .pdf_utils import gerar_termo_pdf_assinado
from .utils import get_logo_base64


_APP = 'controle_de_telefone'

# =============================================================================
# CONSTANTE: CHAVE DE SESSÃO PARA FILIAL
# Usar SEMPRE esta constante para evitar inconsistência entre views.
# =============================================================================
_FILIAL_SESSION_KEY = 'active_filial_id'


def _get_filial_id(request):
    """Helper centralizado para obter o ID da filial ativa da sessão."""
    return request.session.get(_FILIAL_SESSION_KEY)


# =============================================================================
# APARELHO CRUD
# =============================================================================

class AparelhoListView(AppPermissionMixin, ViewFilialScopedMixin, ListView):
    app_label_required = _APP
    model = Aparelho
    template_name = 'controle_de_telefone/aparelho_list.html'
    context_object_name = 'aparelhos'
    paginate_by = 10


class AparelhoDetailView(AppPermissionMixin, ViewFilialScopedMixin, DetailView):
    app_label_required = _APP
    model = Aparelho
    template_name = 'controle_de_telefone/aparelho_detail.html'


class AparelhoCreateView(AppPermissionMixin, SuccessMessageMixin, CreateView):
    app_label_required = _APP
    model = Aparelho
    form_class = AparelhoForm
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:aparelho_list')
    success_message = "Aparelho cadastrado com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastrar Novo Aparelho'
        context['voltar_url'] = self.success_url
        return context

    def form_valid(self, form):
        form.instance.filial_id = _get_filial_id(self.request)
        return super().form_valid(form)


class AparelhoUpdateView(AppPermissionMixin, ViewFilialScopedMixin, SuccessMessageMixin, UpdateView):
    app_label_required = _APP
    model = Aparelho
    form_class = AparelhoForm
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:aparelho_list')
    success_message = "Aparelho atualizado com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Aparelho'
        context['voltar_url'] = self.success_url
        return context


class AparelhoDeleteView(AppPermissionMixin, ViewFilialScopedMixin, DeleteView):
    app_label_required = _APP
    model = Aparelho
    template_name = 'controle_de_telefone/generic_confirm_delete.html'
    success_url = reverse_lazy('controle_de_telefone:aparelho_list')

    def form_valid(self, form):
        messages.success(self.request, "Aparelho excluído com sucesso!")
        return super().form_valid(form)


# =============================================================================
# LINHA TELEFÔNICA CRUD
# =============================================================================

class LinhaTelefonicaListView(AppPermissionMixin, ViewFilialScopedMixin, ListView):
    app_label_required = _APP
    model = LinhaTelefonica
    template_name = 'controle_de_telefone/linhatelefonica_list.html'
    context_object_name = 'linhas'
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset().select_related('plano', 'plano__operadora', 'filial')
        search_query = self.request.GET.get('q', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(numero__icontains=search_query)
                | Q(plano__nome__icontains=search_query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context


class LinhaTelefonicaDetailView(AppPermissionMixin, ViewFilialScopedMixin, DetailView):
    app_label_required = _APP
    model = LinhaTelefonica
    template_name = 'controle_de_telefone/linhatelefonica_detail.html'

    def get_queryset(self):
        return super().get_queryset().select_related('plano', 'plano__operadora', 'filial')


class LinhaTelefonicaCreateView(AppPermissionMixin, SuccessMessageMixin, CreateView):
    app_label_required = _APP
    model = LinhaTelefonica
    form_class = LinhaTelefonicaForm
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:linhatelefonica_list')
    success_message = "Linha telefônica cadastrada com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastrar Nova Linha Telefônica'
        context['voltar_url'] = self.success_url
        return context

    def form_valid(self, form):
        form.instance.filial_id = _get_filial_id(self.request)
        return super().form_valid(form)


class LinhaTelefonicaUpdateView(AppPermissionMixin, ViewFilialScopedMixin, SuccessMessageMixin, UpdateView):
    app_label_required = _APP
    model = LinhaTelefonica
    form_class = LinhaTelefonicaForm
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:linhatelefonica_list')
    success_message = "Linha telefônica atualizada com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Linha Telefônica'
        context['voltar_url'] = self.success_url
        return context


class LinhaTelefonicaDeleteView(AppPermissionMixin, ViewFilialScopedMixin, DeleteView):
    app_label_required = _APP
    model = LinhaTelefonica
    template_name = 'controle_de_telefone/generic_confirm_delete.html'
    success_url = reverse_lazy('controle_de_telefone:linhatelefonica_list')

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Linha telefônica excluída com sucesso!")
            return response
        except ProtectedError:
            messages.error(
                self.request,
                "Erro: Esta linha não pode ser excluída pois está vinculada a um ou mais colaboradores.",
            )
            return redirect(
                'controle_de_telefone:linhatelefonica_delete',
                pk=self.kwargs.get('pk'),
            )


# =============================================================================
# MARCA CRUD
# =============================================================================

class MarcaListView(AppPermissionMixin, ListView):
    app_label_required = _APP
    model = Marca
    template_name = 'controle_de_telefone/marca_list.html'
    context_object_name = 'marcas'
    paginate_by = 15


class MarcaCreateView(AppPermissionMixin, SuccessMessageMixin, CreateView):
    app_label_required = _APP
    model = Marca
    form_class = MarcaForm
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:marca_list')
    success_message = "Marca criada com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastrar Nova Marca'
        context['voltar_url'] = self.success_url
        return context


class MarcaUpdateView(AppPermissionMixin, SuccessMessageMixin, UpdateView):
    app_label_required = _APP
    model = Marca
    form_class = MarcaForm
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:marca_list')
    success_message = "Marca atualizada com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Marca'
        context['voltar_url'] = self.success_url
        return context


class MarcaDeleteView(AppPermissionMixin, DeleteView):
    app_label_required = _APP
    model = Marca
    template_name = 'controle_de_telefone/generic_confirm_delete.html'
    success_url = reverse_lazy('controle_de_telefone:marca_list')


# =============================================================================
# MODELO CRUD
# =============================================================================

class ModeloListView(AppPermissionMixin, ListView):
    app_label_required = _APP
    model = Modelo
    template_name = 'controle_de_telefone/modelo_list.html'
    context_object_name = 'modelos'
    paginate_by = 15


class ModeloCreateView(AppPermissionMixin, SuccessMessageMixin, CreateView):
    app_label_required = _APP
    model = Modelo
    form_class = ModeloForm
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:modelo_list')
    success_message = "Modelo criado com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastrar Novo Modelo'
        context['voltar_url'] = self.success_url
        return context


class ModeloUpdateView(AppPermissionMixin, SuccessMessageMixin, UpdateView):
    app_label_required = _APP
    model = Modelo
    form_class = ModeloForm
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:modelo_list')
    success_message = "Modelo atualizado com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Modelo'
        context['voltar_url'] = self.success_url
        return context


class ModeloDeleteView(AppPermissionMixin, DeleteView):
    app_label_required = _APP
    model = Modelo
    template_name = 'controle_de_telefone/generic_confirm_delete.html'
    success_url = reverse_lazy('controle_de_telefone:modelo_list')


# =============================================================================
# OPERADORA CRUD
# =============================================================================

class OperadoraListView(AppPermissionMixin, ListView):
    app_label_required = _APP
    model = Operadora
    template_name = 'controle_de_telefone/operadora_list.html'
    context_object_name = 'operadoras'
    paginate_by = 15


class OperadoraCreateView(AppPermissionMixin, SuccessMessageMixin, CreateView):
    app_label_required = _APP
    model = Operadora
    form_class = OperadoraForm
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:operadora_list')
    success_message = "Operadora criada com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastrar Nova Operadora'
        context['voltar_url'] = self.success_url
        return context


class OperadoraUpdateView(AppPermissionMixin, SuccessMessageMixin, UpdateView):
    app_label_required = _APP
    model = Operadora
    form_class = OperadoraForm
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:operadora_list')
    success_message = "Operadora atualizada com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Operadora'
        context['voltar_url'] = self.success_url
        return context


class OperadoraDeleteView(AppPermissionMixin, DeleteView):
    app_label_required = _APP
    model = Operadora
    template_name = 'controle_de_telefone/generic_confirm_delete.html'
    success_url = reverse_lazy('controle_de_telefone:operadora_list')


# =============================================================================
# PLANO CRUD
# =============================================================================

class PlanoListView(AppPermissionMixin, ListView):
    app_label_required = _APP
    model = Plano
    template_name = 'controle_de_telefone/plano_list.html'
    context_object_name = 'planos'
    paginate_by = 15


class PlanoCreateView(AppPermissionMixin, SuccessMessageMixin, CreateView):
    app_label_required = _APP
    model = Plano
    form_class = PlanoForm
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:plano_list')
    success_message = "Plano criado com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastrar Novo Plano'
        context['voltar_url'] = self.success_url
        return context


class PlanoUpdateView(AppPermissionMixin, SuccessMessageMixin, UpdateView):
    app_label_required = _APP
    model = Plano
    form_class = PlanoForm
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:plano_list')
    success_message = "Plano atualizado com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Plano'
        context['voltar_url'] = self.success_url
        return context


class PlanoDeleteView(AppPermissionMixin, DeleteView):
    app_label_required = _APP
    model = Plano
    template_name = 'controle_de_telefone/generic_confirm_delete.html'
    success_url = reverse_lazy('controle_de_telefone:plano_list')


# =============================================================================
# VÍNCULO CRUD
# =============================================================================

class _VinculoFilialQuerysetMixin:
    """Mixin para filtrar vínculos pela filial do funcionário."""

    def get_queryset(self):
        filial_id = _get_filial_id(self.request)
        if not filial_id:
            return Vinculo.objects.none()
        return Vinculo.objects.filter(
            funcionario__filial_id=filial_id
        ).select_related(
            'funcionario', 'aparelho__modelo__marca', 'linha__plano__operadora'
        )


class VinculoListView(AppPermissionMixin, _VinculoFilialQuerysetMixin, ListView):
    app_label_required = _APP
    model = Vinculo
    template_name = 'controle_de_telefone/vinculo_list.html'
    context_object_name = 'vinculos'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('q', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(funcionario__nome_completo__icontains=search_query)
                | Q(funcionario__matricula__icontains=search_query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context


class VinculoDetailView(AppPermissionMixin, _VinculoFilialQuerysetMixin, DetailView):
    app_label_required = _APP
    model = Vinculo
    template_name = 'controle_de_telefone/vinculo_detail.html'
    context_object_name = 'vinculo'


class VinculoCreateView(AppPermissionMixin, SuccessMessageMixin, CreateView):
    app_label_required = _APP
    model = Vinculo
    form_class = VinculoForm
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:vinculo_list')
    success_message = "Vínculo criado! O funcionário foi notificado para assinar o termo."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['filial_id'] = _get_filial_id(self.request)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Criar Novo Vínculo'
        context['voltar_url'] = self.success_url
        return context

    def form_valid(self, form):
        # Salva e obtém self.object via super()
        response = super().form_valid(form)

        # Notifica o funcionário
        vinculo = self.object
        if vinculo.funcionario.usuario:
            url_assinatura = self.request.build_absolute_uri(
                reverse('controle_de_telefone:vinculo_assinar', args=[vinculo.pk])
            )
            Notificacao.objects.create(
                usuario=vinculo.funcionario.usuario,
                mensagem=(
                    f"Você tem um novo Termo de Responsabilidade para o "
                    f"aparelho {vinculo.aparelho} pendente de assinatura."
                ),
                url_destino=url_assinatura,
            )

        return response


class VinculoUpdateView(AppPermissionMixin, _VinculoFilialQuerysetMixin, SuccessMessageMixin, UpdateView):
    app_label_required = _APP
    model = Vinculo
    form_class = VinculoForm
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:vinculo_list')
    success_message = "Vínculo atualizado com sucesso!"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['filial_id'] = _get_filial_id(self.request)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Vínculo'
        context['voltar_url'] = self.success_url
        return context


class VinculoDeleteView(AppPermissionMixin, _VinculoFilialQuerysetMixin, DeleteView):
    app_label_required = _APP
    model = Vinculo
    template_name = 'controle_de_telefone/generic_confirm_delete.html'
    success_url = reverse_lazy('controle_de_telefone:vinculo_list')

    def form_valid(self, form):
        messages.success(self.request, "Vínculo excluído com sucesso!")
        return super().form_valid(form)


# =============================================================================
# TERMO DE RESPONSABILIDADE (Assinatura, Download, Regeneração)
# =============================================================================

def _gerar_termo_pdf(vinculo):
    """
    Gera o PDF do termo de responsabilidade usando xhtml2pdf.
    Função utilitária usada por AssinarTermoView e RegenerarTermoView.
    """
    context = {'vinculo': vinculo, 'logo_base64': get_logo_base64()}

    try:
        rg_doc = Documento.objects.get(
            funcionario=vinculo.funcionario, tipo_documento='RG'
        )
        context['rg_numero'] = rg_doc.numero
    except Documento.DoesNotExist:
        context['rg_numero'] = "Documento não encontrado"

    if vinculo.assinatura_digital and hasattr(vinculo.assinatura_digital, 'path'):
        context['assinatura_path'] = vinculo.assinatura_digital.path
    else:
        context['assinatura_path'] = None

    html = render_to_string('controle_de_telefone/termo_pdf.html', context)
    buffer = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=buffer)

    if pisa_status.err:
        return None

    buffer.seek(0)
    return buffer


class AssinarTermoView(AppPermissionMixin, SuccessMessageMixin, UpdateView):
    app_label_required = _APP
    model = Vinculo
    form_class = VinculoAssinaturaForm
    template_name = 'controle_de_telefone/termo_assinar_form.html'
    context_object_name = 'vinculo'
    success_message = "Termo de Responsabilidade assinado com sucesso!"

    def get_success_url(self):
        return reverse('controle_de_telefone:vinculo_detail', kwargs={'pk': self.object.pk})

    def dispatch(self, request, *args, **kwargs):
        vinculo = self.get_object()

        if request.user != vinculo.funcionario.usuario:
            messages.error(request, "Você não tem permissão para assinar este termo.")
            return redirect('controle_de_telefone:vinculo_list')

        if vinculo.foi_assinado:
            messages.info(request, "Este termo já foi assinado.")
            return redirect(self.get_success_url())

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        vinculo = form.instance
        signature_type = self.request.POST.get('signature_type')
        assinatura_salva = False

        if signature_type == 'draw':
            base64_data = self.request.POST.get('assinatura_base64')
            if base64_data and ';base64,' in base64_data:
                try:
                    fmt, imgstr = base64_data.split(';base64,')
                    ext = fmt.split('/')[-1]
                    file_name = (
                        f"assinatura_{vinculo.id}_"
                        f"{timezone.now().strftime('%Y%m%d%H%M%S')}.{ext}"
                    )
                    vinculo.assinatura_digital = ContentFile(
                        base64.b64decode(imgstr), name=file_name
                    )
                    assinatura_salva = True
                except Exception as e:
                    messages.error(self.request, f"Erro ao decodificar a assinatura: {e}")
                    return self.form_invalid(form)

        elif signature_type == 'upload':
            image_file = self.request.FILES.get('assinatura_imagem_upload')
            if image_file:
                vinculo.assinatura_digital = image_file
                assinatura_salva = True

        if not assinatura_salva:
            messages.error(
                self.request,
                "Assinatura não fornecida. Por favor, desenhe ou faça o upload.",
            )
            return self.form_invalid(form)

        vinculo.foi_assinado = True
        vinculo.data_assinatura = timezone.now()
        vinculo.save()

        # Gera o PDF assinado
        try:
            pdf_buffer = gerar_termo_pdf_assinado(vinculo)
            pdf_filename = (
                f"termo_assinado_{vinculo.pk}_"
                f"{timezone.now().strftime('%Y%m%d')}.pdf"
            )
            vinculo.termo_assinado_upload.save(
                pdf_filename, ContentFile(pdf_buffer.getvalue()), save=True
            )
        except Exception as e:
            messages.error(
                self.request,
                f"Assinatura salva, mas houve um erro ao gerar o PDF final: {e}",
            )

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Assinar Termo de Responsabilidade'
        context['logo_base64'] = get_logo_base64()

        try:
            rg_doc = Documento.objects.get(
                funcionario=self.object.funcionario, tipo_documento='RG'
            )
            context['rg_numero'] = rg_doc.numero
        except Documento.DoesNotExist:
            context['rg_numero'] = "RG não encontrado"

        return context


class DownloadTermoView(AppPermissionMixin, View):
    app_label_required = _APP

    def get(self, request, *args, **kwargs):
        vinculo = get_object_or_404(Vinculo, pk=self.kwargs.get('pk'))

        is_owner = request.user == vinculo.funcionario.usuario
        is_manager = request.user.has_perm('controle_de_telefone.view_vinculo')

        if not is_owner and not is_manager:
            return HttpResponseForbidden("Você não tem permissão para acessar este arquivo.")

        if is_manager:
            filial_id = _get_filial_id(request)
            if vinculo.funcionario.filial_id != filial_id:
                return HttpResponseForbidden("Acesso negado a arquivos de outra filial.")

        # Prioriza termo assinado, depois o gerado
        file_to_download = None
        if vinculo.termo_assinado_upload and vinculo.termo_assinado_upload.name:
            file_to_download = vinculo.termo_assinado_upload
        elif vinculo.termo_gerado and vinculo.termo_gerado.name:
            file_to_download = vinculo.termo_gerado

        if not file_to_download or not os.path.exists(file_to_download.path):
            raise Http404(
                "Nenhum termo de responsabilidade encontrado. Tente regenerar o termo."
            )

        return FileResponse(
            open(file_to_download.path, 'rb'),
            as_attachment=True,
            filename=os.path.basename(file_to_download.path),
        )


class DownloadTermosAssinadosView(AppPermissionMixin, View):
    app_label_required = _APP

    def get(self, request, *args, **kwargs):
        filial_id = _get_filial_id(request)

        vinculos_assinados = Vinculo.objects.filter(
            foi_assinado=True,
            termo_assinado_upload__isnull=False,
            funcionario__filial_id=filial_id,
        )

        if not vinculos_assinados.exists():
            return HttpResponse(
                "Nenhum termo assinado encontrado para download.", status=404
            )

        buffer = BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for vinculo in vinculos_assinados:
                file_path = vinculo.termo_assinado_upload.path
                file_name = (
                    f"termo_{vinculo.funcionario.nome_completo}_{vinculo.aparelho}.pdf"
                )
                zip_file.write(file_path, file_name)

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="termos_assinados.zip"'
        return response


class RegenerarTermoView(AppPermissionMixin, View):
    app_label_required = _APP

    def post(self, request, *args, **kwargs):
        vinculo = get_object_or_404(Vinculo, pk=self.kwargs.get('pk'))
        try:
            pdf_buffer = gerar_termo_pdf_assinado(vinculo)

            if vinculo.foi_assinado:
                file_name = f"termo_assinado_{vinculo.pk}.pdf"
                vinculo.termo_assinado_upload.save(
                    file_name, ContentFile(pdf_buffer.getvalue()), save=True
                )
            else:
                file_name = f"termo_gerado_{vinculo.pk}.pdf"
                vinculo.termo_gerado.save(
                    file_name, ContentFile(pdf_buffer.getvalue()), save=True
                )

            messages.success(
                request,
                f"Termo para {vinculo.funcionario.nome_completo} foi gerado com sucesso!",
            )
        except Exception as e:
            messages.error(request, f"Ocorreu um erro ao gerar o termo: {e}")

        return redirect('controle_de_telefone:vinculo_detail', pk=vinculo.pk)


class NotificarAssinaturaView(AppPermissionMixin, View):
    app_label_required = _APP

    def post(self, request, *args, **kwargs):
        vinculo = get_object_or_404(Vinculo, pk=kwargs.get('pk'))
        usuario_a_notificar = vinculo.funcionario.usuario

        if not usuario_a_notificar:
            messages.error(request, "Este funcionário não possui um usuário de sistema.")
            return redirect(request.META.get('HTTP_REFERER', '/'))

        url_assinatura = request.build_absolute_uri(
            reverse('controle_de_telefone:vinculo_assinar', args=[vinculo.pk])
        )

        mensagem = (
            f"Você tem um Termo de Responsabilidade para o aparelho "
            f"{vinculo.aparelho} pendente de assinatura."
        )

        # Notificação interna (sino)
        Notificacao.objects.create(
            usuario=usuario_a_notificar,
            mensagem=mensagem,
            url_destino=url_assinatura,
        )

        # E-mail
        if usuario_a_notificar.email:
            contexto_email = {
                'nome_usuario': (
                    usuario_a_notificar.first_name or usuario_a_notificar.username
                ),
                'nome_aparelho': str(vinculo.aparelho),
                'url_assinatura': url_assinatura,
            }
            corpo_html = render_to_string(
                'email/notificacao_assinatura.html', contexto_email
            )
            send_mail(
                subject="Lembrete: Termo de Responsabilidade Pendente",
                message='',
                from_email='nao-responda@suaempresa.com',
                recipient_list=[usuario_a_notificar.email],
                html_message=corpo_html,
            )
            messages.success(
                request,
                f"Notificação por e-mail e no sistema enviada para "
                f"{usuario_a_notificar.get_full_name()}.",
            )
        else:
            messages.warning(
                request,
                "Notificação criada no sistema, mas o funcionário não possui e-mail.",
            )

        return redirect(request.META.get('HTTP_REFERER', '/'))


# =============================================================================
# DASHBOARD
# =============================================================================

class DashboardView(AppPermissionMixin, TemplateView):
    app_label_required = _APP
    template_name = 'controle_de_telefone/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filial_id = _get_filial_id(self.request)

        # Querysets filtrados por filial
        aparelhos_qs = Aparelho.objects.filter(filial_id=filial_id) if filial_id else Aparelho.objects.none()
        linhas_qs = LinhaTelefonica.objects.filter(filial_id=filial_id) if filial_id else LinhaTelefonica.objects.none()
        vinculos_qs = Vinculo.objects.filter(funcionario__filial_id=filial_id) if filial_id else Vinculo.objects.none()

        # Cards de resumo (FILTRADOS POR FILIAL)
        context['total_aparelhos'] = aparelhos_qs.count()
        context['total_linhas'] = linhas_qs.count()
        vinculos_ativos = vinculos_qs.filter(data_devolucao__isnull=True).count()
        vinculos_inativos = vinculos_qs.filter(data_devolucao__isnull=False).count()
        context['total_vinculos'] = vinculos_ativos

        # Cadastros auxiliares (estes geralmente são globais, sem filial)
        context['total_marcas'] = Marca.objects.count()
        context['total_modelos'] = Modelo.objects.count()
        context['total_operadoras'] = Operadora.objects.count()
        context['total_planos'] = Plano.objects.count()

        # Gráfico: Aparelhos por Marca (FILTRADO)
        aparelhos_por_marca = (
            aparelhos_qs
            .values('modelo__marca__nome')
            .annotate(total=Count('id'))
            .order_by('-total')
        )
        context['marcas_labels_json'] = json.dumps(
            [item['modelo__marca__nome'] for item in aparelhos_por_marca]
        )
        context['marcas_data_json'] = json.dumps(
            [item['total'] for item in aparelhos_por_marca]
        )

        # Gráfico: Linhas por Operadora (FILTRADO)
        linhas_por_operadora = (
            linhas_qs
            .values('plano__operadora__nome')
            .annotate(total=Count('id'))
            .order_by('-total')
        )
        context['operadoras_labels_json'] = json.dumps(
            [item['plano__operadora__nome'] for item in linhas_por_operadora]
        )
        context['operadoras_data_json'] = json.dumps(
            [item['total'] for item in linhas_por_operadora]
        )

        # Gráfico: Vínculos Ativos vs Inativos (FILTRADO)
        context['vinculos_status_data_json'] = json.dumps(
            [vinculos_ativos, vinculos_inativos]
        )

        return context


# =============================================================================
# RECARGA DE CRÉDITO CRUD
# =============================================================================

class RecargaCreditoListView(AppPermissionMixin, ListView):
    app_label_required = _APP
    model = RecargaCredito
    template_name = 'controle_de_telefone/recarga_list.html'
    context_object_name = 'recargas'
    paginate_by = 20

    def get_queryset(self):
        filial_id = _get_filial_id(self.request)
        qs = RecargaCredito.objects.filter(filial_id=filial_id).select_related(
            'linha', 'linha__plano__operadora', 'responsavel', 'usuario_credito',
        ).order_by('-data_solicitacao')

        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)

        linha = self.request.GET.get('linha')
        if linha:
            qs = qs.filter(linha_id=linha)

        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(
                Q(linha__numero__icontains=q)
                | Q(usuario_credito__nome_completo__icontains=q)
                | Q(responsavel__nome_completo__icontains=q)
                | Q(codigo_transacao__icontains=q)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filial_id = _get_filial_id(self.request)

        qs_filial = RecargaCredito.objects.filter(filial_id=filial_id)
        context['total_recargas'] = qs_filial.count()
        context['total_pendentes'] = qs_filial.filter(status='pendente').count()
        context['total_mes'] = qs_filial.filter(
            data_recarga__month=timezone.now().month,
            data_recarga__year=timezone.now().year,
        ).aggregate(total=Sum('valor'))['total'] or 0

        context['linhas'] = LinhaTelefonica.objects.filter(filial_id=filial_id)
        context['status_choices'] = RecargaCredito.StatusRecarga.choices
        context['search_query'] = self.request.GET.get('q', '')
        context['status_filtro'] = self.request.GET.get('status', '')

        return context


class RecargaCreditoCreateView(AppPermissionMixin, SuccessMessageMixin, CreateView):
    app_label_required = _APP
    model = RecargaCredito
    form_class = RecargaCreditoForm
    template_name = 'controle_de_telefone/recarga_form.html'
    success_url = reverse_lazy('controle_de_telefone:recarga_list')
    success_message = "Recarga cadastrada com sucesso!"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['filial_id'] = _get_filial_id(self.request)
        return kwargs

    def form_valid(self, form):
        form.instance.filial_id = _get_filial_id(self.request)
        form.instance.criado_por = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nova Recarga de Crédito'
        return context


class RecargaCreditoUpdateView(AppPermissionMixin, SuccessMessageMixin, UpdateView):
    app_label_required = _APP
    model = RecargaCredito
    form_class = RecargaCreditoForm
    template_name = 'controle_de_telefone/recarga_form.html'
    success_url = reverse_lazy('controle_de_telefone:recarga_list')
    success_message = "Recarga atualizada com sucesso!"

    def get_queryset(self):
        filial_id = _get_filial_id(self.request)
        return RecargaCredito.objects.filter(filial_id=filial_id)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['filial_id'] = _get_filial_id(self.request)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = f'Editar Recarga — {self.object.linha.numero}'
        return context


class RecargaCreditoDetailView(AppPermissionMixin, DetailView):
    app_label_required = _APP
    model = RecargaCredito
    template_name = 'controle_de_telefone/recarga_detail.html'
    context_object_name = 'recarga'

    def get_queryset(self):
        filial_id = _get_filial_id(self.request)
        return RecargaCredito.objects.filter(filial_id=filial_id).select_related(
            'linha', 'linha__plano__operadora',
            'responsavel', 'usuario_credito', 'criado_por',
        )


class RecargaCreditoDeleteView(AppPermissionMixin, DeleteView):
    app_label_required = _APP
    model = RecargaCredito
    template_name = 'controle_de_telefone/recarga_confirm_delete.html'
    success_url = reverse_lazy('controle_de_telefone:recarga_list')

    def get_queryset(self):
        filial_id = _get_filial_id(self.request)
        return RecargaCredito.objects.filter(filial_id=filial_id)

    def form_valid(self, form):
        messages.success(self.request, 'Recarga excluída com sucesso!')
        return super().form_valid(form)


# =============================================================================
# AÇÕES DE RECARGA (FBVs)
# =============================================================================

@login_required
def recarga_aprovar(request, pk):
    """Aprovar uma recarga pendente."""
    filial_id = _get_filial_id(request)
    recarga = get_object_or_404(RecargaCredito, pk=pk, filial_id=filial_id)

    if recarga.status != RecargaCredito.StatusRecarga.PENDENTE:
        messages.error(request, 'Esta recarga não pode ser aprovada.')
        return redirect('controle_de_telefone:recarga_detail', pk=pk)

    if not request.user.has_perm('controle_de_telefone.aprovar_recarga'):
        messages.error(request, 'Você não tem permissão para aprovar recargas.')
        return redirect('controle_de_telefone:recarga_detail', pk=pk)

    recarga.aprovar(user=request.user)
    messages.success(request, 'Recarga aprovada com sucesso!')
    return redirect('controle_de_telefone:recarga_detail', pk=pk)


@login_required
def recarga_realizar(request, pk):
    """Marcar recarga como realizada."""
    filial_id = _get_filial_id(request)
    recarga = get_object_or_404(RecargaCredito, pk=pk, filial_id=filial_id)

    valid_statuses = [
        RecargaCredito.StatusRecarga.PENDENTE,
        RecargaCredito.StatusRecarga.APROVADA,
    ]
    if recarga.status not in valid_statuses:
        messages.error(request, 'Esta recarga não pode ser marcada como realizada.')
        return redirect('controle_de_telefone:recarga_detail', pk=pk)

    if request.method == 'POST':
        form = RecargaCreditoRealizarForm(request.POST, request.FILES, instance=recarga)
        if form.is_valid():
            recarga = form.save(commit=False)
            recarga.status = RecargaCredito.StatusRecarga.REALIZADA
            recarga.save()
            messages.success(request, 'Recarga marcada como realizada!')
            return redirect('controle_de_telefone:recarga_detail', pk=pk)
    else:
        form = RecargaCreditoRealizarForm(instance=recarga)

    return render(request, 'controle_de_telefone/recarga_realizar.html', {
        'form': form,
        'recarga': recarga,
    })


@login_required
def recarga_cancelar(request, pk):
    """Cancelar uma recarga."""
    filial_id = _get_filial_id(request)
    recarga = get_object_or_404(RecargaCredito, pk=pk, filial_id=filial_id)

    if recarga.status == RecargaCredito.StatusRecarga.REALIZADA:
        messages.error(request, 'Recargas realizadas não podem ser canceladas.')
        return redirect('controle_de_telefone:recarga_detail', pk=pk)

    if not request.user.has_perm('controle_de_telefone.cancelar_recarga'):
        messages.error(request, 'Você não tem permissão para cancelar recargas.')
        return redirect('controle_de_telefone:recarga_detail', pk=pk)

    if request.method == 'POST':
        motivo = request.POST.get('motivo_cancelamento', '')
        recarga.cancelar(motivo_cancelamento=motivo, user=request.user)
        messages.success(request, 'Recarga cancelada com sucesso!')
        return redirect('controle_de_telefone:recarga_list')

    return render(request, 'controle_de_telefone/recarga_cancelar.html', {
        'recarga': recarga,
    })

