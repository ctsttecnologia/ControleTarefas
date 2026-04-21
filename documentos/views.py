
# documentos/views.py

import os
import mimetypes
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse, reverse_lazy
from django.http import FileResponse, HttpResponseForbidden, Http404, HttpResponseRedirect
from django.contrib import messages
from django.conf import settings
from django.db.models import Q

from core.mixins import AppPermissionMixin
from .models import Documento
from .forms import DocumentoAnexoForm, DocumentoEmpresaForm


# ══════════════════════════════════════════════════════════
# MIXIN: QUERYSET SEGURO (filial + bypass global)
# ══════════════════════════════════════════════════════════

class DocumentoScopedQuerysetMixin:
    """
    Filtra o queryset por filial (via manager `for_request`).

    Usuários com `documentos.pode_gerenciar_todos_documentos` ou superuser
    recebem queryset SEM filtro de filial (veem tudo).
    """

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser or user.has_perm('documentos.pode_gerenciar_todos_documentos'):
            qs = Documento.objects.all()
        else:
            qs = Documento.objects.for_request(self.request)

        return qs.select_related('responsavel', 'content_type', 'filial', 'cliente')


# ══════════════════════════════════════════════════════════
# MIXIN BASE — DRY para views de documento empresa
# ══════════════════════════════════════════════════════════

class DocumentoEmpresaBaseMixin:
    """Lógica compartilhada entre Create e Update de documentos avulsos."""
    model = Documento
    form_class = DocumentoEmpresaForm
    template_name = 'documentos/documento_empresa_form.html'
    success_url = reverse_lazy('documentos:lista')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        # 🐛 BUGFIX: flag explícita em vez de checar pk (que já vem preenchido após save)
        acao = 'cadastrado' if self._is_create else 'atualizado'
        form.save(user=self.request.user)
        messages.success(
            self.request,
            f'Documento "{form.instance.nome}" {acao} com sucesso!'
        )
        return redirect(self.success_url)


# ══════════════════════════════════════════════════════════
# LISTA UNIFICADA
# ══════════════════════════════════════════════════════════

class DocumentoListView(LoginRequiredMixin, AppPermissionMixin,
                        DocumentoScopedQuerysetMixin, ListView):
    model = Documento
    template_name = 'documentos/documento_list.html'
    context_object_name = 'documentos'
    paginate_by = 20
    permission_required = 'documentos.view_documento'

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        # 🔒 Usuário comum SÓ vê documentos em que é o responsável.
        # Staff, superuser e gerentes globais veem tudo (dentro da filial, quando aplicável).
        pode_ver_todos = (
            user.is_superuser
            or user.is_staff
            or user.has_perm('documentos.pode_gerenciar_todos_documentos')
        )
        if not pode_ver_todos:
            qs = qs.filter(responsavel=user)

        # Filtro por aba
        filtro = self.request.GET.get('filtro', 'pendentes')
        if filtro == 'pendentes':
            qs = qs.filter(status__in=['VENCIDO', 'A_VENCER'])
        elif filtro == 'vigentes':
            qs = qs.filter(status='VIGENTE')
        elif filtro == 'renovados':
            qs = qs.filter(status__in=['RENOVADO', 'ARQUIVADO'])
        elif filtro == 'avulsos':
            qs = qs.filter(content_type__isnull=True)
        elif filtro == 'anexados':
            qs = qs.filter(content_type__isnull=False)

        # Filtro por tipo
        tipo = self.request.GET.get('tipo')
        if tipo:
            qs = qs.filter(tipo=tipo)

        # Busca textual
        busca = self.request.GET.get('q')
        if busca:
            qs = qs.filter(Q(nome__icontains=busca) | Q(descricao__icontains=busca))

        return qs.order_by('data_vencimento')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filtro_ativo'] = self.request.GET.get('filtro', 'pendentes')
        context['tipo_ativo'] = self.request.GET.get('tipo', '')
        context['busca'] = self.request.GET.get('q', '')
        context['titulo_pagina'] = 'Gestão de Documentos'
        context['tipos_documento'] = Documento.TipoChoices.choices
        return context


# ══════════════════════════════════════════════════════════
# DOCUMENTOS AVULSOS DA EMPRESA
# ══════════════════════════════════════════════════════════

class DocumentoEmpresaCreateView(LoginRequiredMixin, AppPermissionMixin,
                                 DocumentoEmpresaBaseMixin, CreateView):
    """Cria documento avulso (contratos, alvarás, etc.) — sem GenericFK."""
    permission_required = 'documentos.add_documento'
    _is_create = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Novo Documento'
        return context


class DocumentoEmpresaUpdateView(LoginRequiredMixin, AppPermissionMixin,
                                 DocumentoScopedQuerysetMixin,
                                 DocumentoEmpresaBaseMixin, UpdateView):
    """Edita documento avulso da empresa (somente na mesma filial)."""
    permission_required = 'documentos.change_documento'
    _is_create = False

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        # Usuário comum só edita os seus; staff/superuser/gerente global editam qualquer
        if user.is_superuser or user.is_staff \
                or user.has_perm('documentos.pode_gerenciar_todos_documentos'):
            return qs
        return qs.filter(responsavel=user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f'Editar: {self.object.nome}'
        return context


# ══════════════════════════════════════════════════════════
# DOCUMENTOS ANEXADOS (a Funcionário, Treinamento, etc.)
# ══════════════════════════════════════════════════════════

class DocumentoAnexoCreateView(LoginRequiredMixin, AppPermissionMixin, CreateView):
    """Cria documento anexado a outro objeto via GenericFK."""
    model = Documento
    form_class = DocumentoAnexoForm
    template_name = 'documentos/documento_form.html'
    permission_required = 'documentos.add_documento'

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
            ct = get_object_or_404(ContentType, pk=self.kwargs['ct_id'])
            obj_id = self.kwargs['obj_id']

            form.instance.content_type = ct
            form.instance.object_id = obj_id
            # 🔒 Responsável SEMPRE é o usuário atual (obrigatório)
            form.instance.responsavel = self.request.user

            # Filial via atributo do user ou sessão
            filial_ativa = getattr(self.request.user, 'filial_ativa', None)
            if filial_ativa:
                form.instance.filial = filial_ativa
            elif self.request.session.get('active_filial_id'):
                from usuario.models import Filial
                form.instance.filial = Filial.objects.get(
                    pk=self.request.session['active_filial_id']
                )
        except KeyError:
            return HttpResponseForbidden("URL inválida.")

        messages.success(
            self.request,
            f'Documento "{form.instance.nome}" adicionado com sucesso!'
        )
        return super().form_valid(form)

    def get_success_url(self):
        obj = self.object.content_object
        if obj and hasattr(obj, 'get_absolute_url'):
            return obj.get_absolute_url()
        return reverse('documentos:lista')


# ══════════════════════════════════════════════════════════
# DOWNLOAD SEGURO
# ══════════════════════════════════════════════════════════

class DocumentoDownloadView(LoginRequiredMixin, AppPermissionMixin,
                            DocumentoScopedQuerysetMixin, View):
    """Serve arquivo privado com segurança + filtro de filial + bypass global."""
    permission_required = 'documentos.view_documento'

    def get(self, request, *args, **kwargs):
        documento = get_object_or_404(self.get_queryset(), pk=self.kwargs['pk'])

        # 🔒 Apenas responsável, staff, superuser ou gerente global podem baixar
        pode_acessar = (
            request.user == documento.responsavel
            or request.user.is_staff
            or request.user.is_superuser
            or request.user.has_perm('documentos.pode_gerenciar_todos_documentos')
        )
        if not pode_acessar:
            return HttpResponseForbidden(
                "Você não tem permissão para acessar este documento."
            )

        file_field = documento.arquivo
        file_path = file_field.path

        # Tenta arquivo local
        if os.path.exists(file_path):
            content_type, _ = mimetypes.guess_type(file_path)
            content_type = content_type or 'application/octet-stream'
            filename = os.path.basename(file_path)

            response = FileResponse(open(file_path, 'rb'), content_type=content_type)
            if content_type == 'application/pdf':
                response['Content-Disposition'] = f'inline; filename="{filename}"'
            else:
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

        # Fallback: busca no GCS (dev apontando para produção)
        if settings.DEBUG:
            try:
                from storages.backends.gcloud import GoogleCloudStorage

                bucket_name = getattr(settings, 'GS_BUCKET_NAME', None)
                credentials = getattr(settings, 'GS_CREDENTIALS', None)

                if bucket_name:
                    gcs = GoogleCloudStorage(
                        bucket_name=bucket_name,
                        credentials=credentials,
                    )
                    for name in [file_field.name, f'media/{file_field.name}']:
                        if gcs.exists(name):
                            return HttpResponseRedirect(gcs.url(name))
            except (ImportError, Exception):
                pass

        raise Http404("Arquivo não encontrado no servidor.")


# ══════════════════════════════════════════════════════════
# RENOVAÇÃO
# ══════════════════════════════════════════════════════════

class DocumentoRenewView(LoginRequiredMixin, AppPermissionMixin,
                         DocumentoScopedQuerysetMixin, CreateView):
    """Renova um documento existente criando uma nova versão."""
    model = Documento
    form_class = DocumentoAnexoForm
    template_name = 'documentos/documento_form.html'
    permission_required = 'documentos.change_documento'

    def get_queryset(self):
        """
        Usuário comum só pode renovar os próprios documentos.
        Staff/superuser/gerente global renovam qualquer um (dentro da filial).
        """
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or user.is_staff \
                or user.has_perm('documentos.pode_gerenciar_todos_documentos'):
            return qs
        return qs.filter(responsavel=user)

    def get_old_doc(self):
        if not hasattr(self, '_old_doc'):
            self._old_doc = get_object_or_404(self.get_queryset(), pk=self.kwargs['pk'])
        return self._old_doc

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        old_doc = self.get_old_doc()
        context['titulo_pagina'] = f'Renovar: {old_doc.nome}'
        context['documento_antigo'] = old_doc
        return context

    def get_initial(self):
        old_doc = self.get_old_doc()
        hoje = timezone.now().date()
        return {
            'nome': old_doc.nome,
            'tipo': old_doc.tipo,
            'data_emissao': hoje,
        }

    def form_valid(self, form):
        old_doc = self.get_old_doc()
        nova_venc = form.cleaned_data.get('data_vencimento')
        new_doc = form.save(commit=False)
        new_doc.content_type = old_doc.content_type
        new_doc.object_id = old_doc.object_id
        # 🔒 Responsável SEMPRE é o usuário atual (obrigatório)
        new_doc.responsavel = self.request.user
        new_doc.filial = old_doc.filial
        new_doc.cliente = old_doc.cliente
        new_doc.dias_aviso = old_doc.dias_aviso
        new_doc.substitui = old_doc
        new_doc.save()

        old_doc.status = Documento.StatusChoices.RENOVADO
        old_doc.save(update_fields=['status'])

        if nova_venc and old_doc.data_vencimento and nova_venc <= old_doc.data_vencimento:
            form.add_error(
                'data_vencimento',
                f'A nova data deve ser posterior à anterior ({old_doc.data_vencimento:%d/%m/%Y}).'
            )
            return self.form_invalid(form)

        self.object = new_doc
        messages.success(
            self.request,
            f'Documento "{old_doc.nome}" renovado com sucesso!'
        )
        return redirect(self.get_success_url())

    def get_success_url(self):
        obj = self.object.content_object
        if obj and hasattr(obj, 'get_absolute_url'):
            return obj.get_absolute_url()
        return reverse('documentos:lista')


# ══════════════════════════════════════════════════════════
# EXCLUSÃO
# ══════════════════════════════════════════════════════════

class DocumentoDeleteView(LoginRequiredMixin, AppPermissionMixin,
                          DocumentoScopedQuerysetMixin, DeleteView):
    """Exclui documento — sempre filtrado por filial via manager."""
    model = Documento
    template_name = 'documentos/documento_confirm_delete.html'
    context_object_name = 'documento'
    permission_required = 'documentos.delete_documento'

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or user.is_staff \
                or user.has_perm('documentos.pode_gerenciar_todos_documentos'):
            return qs
        return qs.filter(responsavel=user)

    def form_valid(self, form):
        nome = self.object.nome
        response = super().form_valid(form)
        messages.success(self.request, f'Documento "{nome}" excluído com sucesso.')
        return response

    def get_success_url(self):
        return reverse('documentos:lista')

    