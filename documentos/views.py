from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, CreateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse_lazy, reverse
from django.http import HttpResponseForbidden, Http404
from django.db.models import Q
from .models import Documento
from .forms import DocumentoForm


# Tenta usar django-sendfile2 se estiver instalado. Caso não esteja,
# fornece um fallback simples baseado em django.http.FileResponse.
try:
    # django-sendfile2 is distributed as 'django-sendfile2' but imported as 'sendfile'
    from sendfile import sendfile  # type: ignore
except ImportError:
    from django.http import FileResponse
    import os
    from django.http import Http404

    def sendfile(request, path, attachment=True):
        """Fallback to serve files when django-sendfile2 isn't installed."""
        if not os.path.exists(path):
            raise Http404("File not found")
        resp = FileResponse(open(path, "rb"))
        if attachment:
            resp["Content-Disposition"] = f'attachment; filename="{os.path.basename(path)}"'
        return resp

class DocumentoListView(LoginRequiredMixin, ListView):
    """
    Lista todos os documentos pendentes (Vencidos ou A Vencer)
    pelos quais o usuário logado é responsável.
    """
    model = Documento
    template_name = 'documentos/documento_list.html'
    context_object_name = 'documentos'
    paginate_by = 20

    def get_queryset(self):
        # O usuário pode ser admin/gerente e ver tudo, 
        # ou apenas ver os seus.
        # Simplificação: Apenas os do responsável.
        # Adapte a lógica de permissão conforme necessário.
        
        base_qs = Documento.objects.filter(
            responsavel=self.request.user
        ).select_related('responsavel', 'content_type')

        # O 'filtro' vem da URL (?filtro=...)
        filtro = self.request.GET.get('filtro', 'pendentes')

        if filtro == 'pendentes':
            # Status de Vencido ou A Vencer
            query = base_qs.filter(
                status__in=[Documento.StatusChoices.VENCIDO, Documento.StatusChoices.A_VENCER]
            )
        elif filtro == 'vigentes':
            query = base_qs.filter(status=Documento.StatusChoices.VIGENTE)
        elif filtro == 'renovados':
            query = base_qs.filter(status=Documento.StatusChoices.RENOVADO)
        else: # 'todos'
            query = base_qs

        return query.order_by('data_vencimento')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filtro_ativo'] = self.request.GET.get('filtro', 'pendentes')
        context['titulo_pagina'] = 'Gestão de Documentos'
        return context


class DocumentoDownloadView(LoginRequiredMixin, View):
    """
    Serve um ficheiro privado do 'private_media' de forma segura.
    Verifica se o usuário é o responsável pelo doc ou superusuário.
    """
    def get(self, request, *args, **kwargs):
        documento = get_object_or_404(Documento, pk=self.kwargs['pk'])

        # Lógica de Permissão
        if not (request.user == documento.responsavel or request.user.is_superuser):
            return HttpResponseForbidden("Você não tem permissão para aceder a este documento.")

        try:
            # Usa django-sendfile2 para servir o ficheiro
            # (muito eficiente, delega o trabalho para Nginx/Apache)
            return sendfile(request, documento.arquivo.path, attachment=True)
        except Exception as e:
            # Fallback se o ficheiro não existir no disco
            raise Http404(f"Erro ao servir o ficheiro: {e}")


class DocumentoCreateView(LoginRequiredMixin, CreateView):
    """
    View genérica para criar um documento e anexá-lo a qualquer objeto
    usando ContentType (GFK).
    """
    model = Documento
    form_class = DocumentoForm
    template_name = 'documentos/documento_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Adicionar Novo Documento'
        return context

    def form_valid(self, form):
        try:
            # Obtém o ContentType e o ID do Objeto da URL
            ct_id = self.kwargs['ct_id']
            obj_id = self.kwargs['obj_id']
            
            form.instance.content_type = get_object_or_404(ContentType, pk=ct_id)
            form.instance.object_id = obj_id
            
            # Define o usuário logado como responsável
            form.instance.responsavel = self.request.user
            
        except KeyError:
            return HttpResponseForbidden("URL inválida. Faltam parâmetros de anexo.")
        
        return super().form_valid(form)

    def get_success_url(self):
        # Retorna para a página do objeto-pai (ex: detalhe do funcionário)
        obj = self.object.content_object
        if hasattr(obj, 'get_absolute_url'):
            return obj.get_absolute_url()
        return reverse('documentos:lista')


class DocumentoRenewView(LoginRequiredMixin, CreateView):
    """
    View para "Renovar" um documento.
    Basicamente, cria um novo documento e atualiza o antigo.
    """
    model = Documento
    form_class = DocumentoForm
    template_name = 'documentos/documento_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.old_doc = get_object_or_404(Documento, pk=self.kwargs['pk'])
        context['titulo_pagina'] = f'Renovar Documento: {self.old_doc.nome}'
        context['documento_antigo'] = self.old_doc
        return context

    def form_valid(self, form):
        old_doc = get_object_or_404(Documento, pk=self.kwargs['pk'])

        # 1. Configura o novo documento
        new_doc = form.save(commit=False)
        new_doc.content_type = old_doc.content_type
        new_doc.object_id = old_doc.object_id
        new_doc.responsavel = self.request.user
        new_doc.substitui = old_doc # Linka o novo doc com o antigo
        new_doc.save()

        # 2. Atualiza o documento antigo
        old_doc.status = Documento.StatusChoices.RENOVADO
        old_doc.save(update_fields=['status'])

        self.object = new_doc
        return redirect(self.get_success_url())

    def get_success_url(self):
        # Retorna para a página do objeto-pai (ex: detalhe do funcionário)
        obj = self.object.content_object
        if hasattr(obj, 'get_absolute_url'):
            return obj.get_absolute_url()
        return reverse('documentos:lista')


class DocumentoDeleteView(LoginRequiredMixin, DeleteView):
    model = Documento
    template_name = 'documentos/documento_confirm_delete.html'
    context_object_name = 'documento'
    
    def get_success_url(self):
        # Tenta retornar para o objeto-pai
        obj = self.object.content_object
        if hasattr(obj, 'get_absolute_url'):
            return obj.get_absolute_url()
        return reverse('documentos:lista')

    def get_queryset(self):
        # Garante que só o responsável ou admin possa deletar
        qs = super().get_queryset()
        if self.request.user.is_superuser:
            return qs
        return qs.filter(responsavel=self.request.user)
    

    