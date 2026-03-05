# documentos/views.py

import os
import mimetypes

from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, CreateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.http import FileResponse, HttpResponseForbidden, Http404
from django.contrib import messages

from .models import Documento
from .forms import DocumentoForm


class DocumentoListView(LoginRequiredMixin, ListView):
    model = Documento
    template_name = 'documentos/documento_list.html'
    context_object_name = 'documentos'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        base_qs = Documento.objects.for_request(self.request).select_related(
            'responsavel', 'content_type', 'filial'
        )

        if not user.is_staff and not user.is_superuser:
            base_qs = base_qs.filter(responsavel=user)

        filtro = self.request.GET.get('filtro', 'pendentes')

        if filtro == 'pendentes':
            base_qs = base_qs.filter(
                status__in=[Documento.StatusChoices.VENCIDO, Documento.StatusChoices.A_VENCER]
            )
        elif filtro == 'vigentes':
            base_qs = base_qs.filter(status=Documento.StatusChoices.VIGENTE)
        elif filtro == 'renovados':
            base_qs = base_qs.filter(status=Documento.StatusChoices.RENOVADO)

        return base_qs.order_by('data_vencimento')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filtro_ativo'] = self.request.GET.get('filtro', 'pendentes')
        context['titulo_pagina'] = 'Gestão de Documentos'
        return context


class DocumentoDownloadView(LoginRequiredMixin, View):
    """Serve arquivo privado com Content-Type correto."""

    def get(self, request, *args, **kwargs):
        documento = get_object_or_404(Documento, pk=self.kwargs['pk'])

        if not (
            request.user == documento.responsavel
            or request.user.is_staff
            or request.user.is_superuser
        ):
            return HttpResponseForbidden("Você não tem permissão para acessar este documento.")

        file_path = documento.arquivo.path

        if not os.path.exists(file_path):
            raise Http404("Arquivo não encontrado no servidor.")

        content_type, _ = mimetypes.guess_type(file_path)
        if content_type is None:
            content_type = 'application/octet-stream'

        filename = os.path.basename(file_path)

        response = FileResponse(
            open(file_path, 'rb'),
            content_type=content_type,
        )

        if content_type == 'application/pdf':
            response['Content-Disposition'] = f'inline; filename="{filename}"'
        else:
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response


class DocumentoCreateView(LoginRequiredMixin, CreateView):
    model = Documento
    form_class = DocumentoForm
    template_name = 'documentos/documento_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Adicionar Novo Documento'

        try:
            ct = ContentType.objects.get(pk=self.kwargs['ct_id'])
            obj = ct.get_object_for_this_type(pk=self.kwargs['obj_id'])
            context['objeto_pai'] = obj
            context['objeto_pai_tipo'] = ct.name.capitalize()
        except Exception:
            pass

        return context

    def form_valid(self, form):
        try:
            ct_id = self.kwargs['ct_id']
            obj_id = self.kwargs['obj_id']

            form.instance.content_type = get_object_or_404(ContentType, pk=ct_id)
            form.instance.object_id = obj_id
            form.instance.responsavel = self.request.user

            # Filial ativa (padrão do projeto)
            filial_ativa = getattr(self.request.user, 'filial_ativa', None)
            if filial_ativa:
                form.instance.filial = filial_ativa
            elif self.request.session.get('active_filial_id'):
                from usuario.models import Filial
                form.instance.filial = Filial.objects.get(
                    pk=self.request.session['active_filial_id']
                )

        except KeyError:
            return HttpResponseForbidden("URL inválida. Faltam parâmetros de anexo.")

        messages.success(self.request, f'Documento "{form.instance.nome}" adicionado com sucesso!')
        return super().form_valid(form)

    def get_success_url(self):
        obj = self.object.content_object
        if obj and hasattr(obj, 'get_absolute_url'):
            return obj.get_absolute_url()
        return reverse('documentos:lista')


class DocumentoRenewView(LoginRequiredMixin, CreateView):
    model = Documento
    form_class = DocumentoForm
    template_name = 'documentos/documento_form.html'

    def get_old_doc(self):
        if not hasattr(self, '_old_doc'):
            self._old_doc = get_object_or_404(Documento, pk=self.kwargs['pk'])
        return self._old_doc

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        old_doc = self.get_old_doc()
        context['titulo_pagina'] = f'Renovar: {old_doc.nome}'
        context['documento_antigo'] = old_doc
        return context

    def get_initial(self):
        old_doc = self.get_old_doc()
        return {'nome': old_doc.nome}

    def form_valid(self, form):
        old_doc = self.get_old_doc()

        new_doc = form.save(commit=False)
        new_doc.content_type = old_doc.content_type
        new_doc.object_id = old_doc.object_id
        new_doc.responsavel = self.request.user
        new_doc.filial = old_doc.filial
        new_doc.substitui = old_doc
        new_doc.save()

        old_doc.status = Documento.StatusChoices.RENOVADO
        old_doc.save(update_fields=['status'])

        self.object = new_doc
        messages.success(self.request, f'Documento "{old_doc.nome}" renovado com sucesso!')
        return redirect(self.get_success_url())

    def get_success_url(self):
        obj = self.object.content_object
        if obj and hasattr(obj, 'get_absolute_url'):
            return obj.get_absolute_url()
        return reverse('documentos:lista')


class DocumentoDeleteView(LoginRequiredMixin, DeleteView):
    model = Documento
    template_name = 'documentos/documento_confirm_delete.html'
    context_object_name = 'documento'

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_superuser or self.request.user.is_staff:
            return qs
        return qs.filter(responsavel=self.request.user)

    def form_valid(self, form):
        nome = self.object.nome
        response = super().form_valid(form)
        messages.success(self.request, f'Documento "{nome}" excluído com sucesso.')
        return response

    def get_success_url(self):
        obj = self.object.content_object
        if obj and hasattr(obj, 'get_absolute_url'):
            return obj.get_absolute_url()
        return reverse('documentos:lista')

    