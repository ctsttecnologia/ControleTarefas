# controle_de_telefone/views.py

import os
import json
import base64
import zipfile
from io import BytesIO

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ObjectDoesNotExist
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
from core.decorators import app_permission_required
from departamento_pessoal.models import Documento
from notifications.models import Notificacao
from usuario.models import Filial

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
_FILIAL_SESSION_KEY = 'active_filial_id'


# ═══════════════════════════════════════════════════════════════════════════════
# MIXIN CENTRAL DE FILIAL
# ═══════════════════════════════════════════════════════════════════════════════

class FilialAtivaMixin:
    """
    Obtém a filial ativa do usuário com prioridade para sessão.
    Fallbacks: user.filial_ativa → funcionario.filial.
    """

    def get_filial_ativa(self):
        filial_id = self.request.session.get(_FILIAL_SESSION_KEY)

        if filial_id:
            try:
                return Filial.objects.get(pk=filial_id)
            except Filial.DoesNotExist:
                pass

        user = self.request.user
        filial_ativa = getattr(user, 'filial_ativa', None)
        if filial_ativa:
            return filial_ativa

        from departamento_pessoal.models import Funcionario
        try:
            funcionario = Funcionario.objects.select_related('filial').get(usuario=user)
            return funcionario.filial
        except Funcionario.DoesNotExist:
            pass

        return None

    def get_filial_ativa_id(self):
        filial = self.get_filial_ativa()
        return filial.id if filial else None


def _get_filial_id(request):
    """Helper para FBVs — prioriza sessão, depois user.filial_ativa."""
    filial_id = request.session.get(_FILIAL_SESSION_KEY)
    if filial_id:
        return filial_id
    filial = getattr(request.user, 'filial_ativa', None)
    return filial.id if filial else None


# ═══════════════════════════════════════════════════════════════════════════════
# MIXIN DE VISIBILIDADE
# ═══════════════════════════════════════════════════════════════════════════════

class TelefoneVisibilityMixin(FilialAtivaMixin):
    """
    Controla visibilidade de Aparelhos, Linhas e Vínculos por perfil.

    Regras:
    ┌─────────────────────────────────────────┬────────────────────────────────┐
    │ Perfil                                  │ Visibilidade                   │
    ├─────────────────────────────────────────┼────────────────────────────────┤
    │ Superuser                               │ Tudo                           │
    │ Perm view_all_<modelo>                  │ Tudo da filial ativa           │
    │ Funcionario comum                       │ Só vínculos/itens próprios     │
    └─────────────────────────────────────────┴────────────────────────────────┘
    """

    def _can_view_all(self, modelo_nome='vinculo'):
        user = self.request.user
        if user.is_superuser:
            return True
        return (
            user.has_perm(f'controle_de_telefone.view_all_{modelo_nome}')
            or user.has_perm(f'controle_de_telefone.view_{modelo_nome}')
        )

    def apply_visibility_vinculo(self, queryset):
        user = self.request.user
        if user.is_superuser:
            return queryset
        if self._can_view_all('vinculo'):
            return queryset
        # Usuário comum → só seus vínculos
        funcionario = getattr(user, 'funcionario', None)
        if funcionario:
            return queryset.filter(funcionario=funcionario)
        return queryset.none()

    def apply_visibility_aparelho(self, queryset):
        user = self.request.user
        if user.is_superuser or self._can_view_all('aparelho'):
            return queryset
        funcionario = getattr(user, 'funcionario', None)
        if funcionario:
            return queryset.filter(vinculos__funcionario=funcionario).distinct()
        return queryset.none()

    def apply_visibility_linha(self, queryset):
        user = self.request.user
        if user.is_superuser or self._can_view_all('linhatelefonica'):
            return queryset
        funcionario = getattr(user, 'funcionario', None)
        if funcionario:
            return queryset.filter(vinculos__funcionario=funcionario).distinct()
        return queryset.none()


# ═══════════════════════════════════════════════════════════════════════════════
# MIXIN BASE
# ═══════════════════════════════════════════════════════════════════════════════

class TelefoneBaseMixin(
    LoginRequiredMixin, AppPermissionMixin,
    TelefoneVisibilityMixin, ViewFilialScopedMixin,
):
    """Mixin base para todas as CBVs do app controle_de_telefone."""
    app_label_required = _APP


# ═══════════════════════════════════════════════════════════════════════════════
# APARELHO CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class AparelhoListView(TelefoneBaseMixin, ListView):
    permission_required = 'controle_de_telefone.view_aparelho'
    model = Aparelho
    template_name = 'controle_de_telefone/aparelho_list.html'
    context_object_name = 'aparelhos'
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset()
        return self.apply_visibility_aparelho(qs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filial_ativa'] = self.get_filial_ativa()
        return context


class AparelhoDetailView(TelefoneBaseMixin, DetailView):
    permission_required = 'controle_de_telefone.view_aparelho'
    model = Aparelho
    template_name = 'controle_de_telefone/aparelho_detail.html'

    def get_queryset(self):
        qs = super().get_queryset()
        return self.apply_visibility_aparelho(qs)


class AparelhoCreateView(TelefoneBaseMixin, SuccessMessageMixin, CreateView):
    permission_required = 'controle_de_telefone.add_aparelho'
    model = Aparelho
    form_class = AparelhoForm
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:aparelho_list')
    success_message = "✅ Aparelho cadastrado com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastrar Novo Aparelho'
        context['voltar_url'] = self.success_url
        context['filial_ativa'] = self.get_filial_ativa()
        return context

    def form_valid(self, form):
        filial = self.get_filial_ativa()
        if not filial and not self.request.user.is_superuser:
            messages.error(
                self.request,
                "Nenhuma filial selecionada. Escolha uma filial no menu superior."
            )
            return self.form_invalid(form)
        if filial:
            form.instance.filial = filial
        return super().form_valid(form)


class AparelhoUpdateView(TelefoneBaseMixin, SuccessMessageMixin, UpdateView):
    permission_required = 'controle_de_telefone.change_aparelho'
    model = Aparelho
    form_class = AparelhoForm
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:aparelho_list')
    success_message = "🔄 Aparelho atualizado com sucesso!"

    def get_queryset(self):
        qs = super().get_queryset()
        return self.apply_visibility_aparelho(qs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Aparelho'
        context['voltar_url'] = self.success_url
        return context


class AparelhoDeleteView(TelefoneBaseMixin, DeleteView):
    permission_required = 'controle_de_telefone.delete_aparelho'
    model = Aparelho
    template_name = 'controle_de_telefone/generic_confirm_delete.html'
    success_url = reverse_lazy('controle_de_telefone:aparelho_list')

    def get_queryset(self):
        qs = super().get_queryset()
        return self.apply_visibility_aparelho(qs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        nome = str(self.object)
        try:
            self.object.delete()
            messages.success(request, f'🗑️ Aparelho "{nome}" excluído com sucesso!')
            return redirect(self.success_url)
        except ProtectedError:
            messages.error(
                request,
                "❌ Não foi possível excluir este aparelho pois há vínculos atrelados a ele."
            )
            return redirect('controle_de_telefone:aparelho_list')


# ═══════════════════════════════════════════════════════════════════════════════
# LINHA TELEFÔNICA CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class LinhaTelefonicaListView(TelefoneBaseMixin, ListView):
    permission_required = 'controle_de_telefone.view_linhatelefonica'
    model = LinhaTelefonica
    template_name = 'controle_de_telefone/linhatelefonica_list.html'
    context_object_name = 'linhas'
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'plano', 'plano__operadora', 'filial'
        )
        queryset = self.apply_visibility_linha(queryset)

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
        context['filial_ativa'] = self.get_filial_ativa()
        return context


class LinhaTelefonicaDetailView(TelefoneBaseMixin, DetailView):
    permission_required = 'controle_de_telefone.view_linhatelefonica'
    model = LinhaTelefonica
    template_name = 'controle_de_telefone/linhatelefonica_detail.html'

    def get_queryset(self):
        qs = super().get_queryset().select_related('plano', 'plano__operadora', 'filial')
        return self.apply_visibility_linha(qs)


class LinhaTelefonicaCreateView(TelefoneBaseMixin, SuccessMessageMixin, CreateView):
    permission_required = 'controle_de_telefone.add_linhatelefonica'
    model = LinhaTelefonica
    form_class = LinhaTelefonicaForm
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:linhatelefonica_list')
    success_message = "✅ Linha telefônica cadastrada com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastrar Nova Linha Telefônica'
        context['voltar_url'] = self.success_url
        context['filial_ativa'] = self.get_filial_ativa()
        return context

    def form_valid(self, form):
        filial = self.get_filial_ativa()
        if not filial and not self.request.user.is_superuser:
            messages.error(
                self.request,
                "Nenhuma filial selecionada. Escolha uma filial no menu superior."
            )
            return self.form_invalid(form)
        if filial:
            form.instance.filial = filial
        return super().form_valid(form)


class LinhaTelefonicaUpdateView(TelefoneBaseMixin, SuccessMessageMixin, UpdateView):
    permission_required = 'controle_de_telefone.change_linhatelefonica'
    model = LinhaTelefonica
    form_class = LinhaTelefonicaForm
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:linhatelefonica_list')
    success_message = "🔄 Linha telefônica atualizada com sucesso!"

    def get_queryset(self):
        qs = super().get_queryset()
        return self.apply_visibility_linha(qs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Linha Telefônica'
        context['voltar_url'] = self.success_url
        return context


class LinhaTelefonicaDeleteView(TelefoneBaseMixin, DeleteView):
    permission_required = 'controle_de_telefone.delete_linhatelefonica'
    model = LinhaTelefonica
    template_name = 'controle_de_telefone/generic_confirm_delete.html'
    success_url = reverse_lazy('controle_de_telefone:linhatelefonica_list')

    def get_queryset(self):
        qs = super().get_queryset()
        return self.apply_visibility_linha(qs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        nome = str(self.object)
        try:
            self.object.delete()
            messages.success(request, f'🗑️ Linha "{nome}" excluída com sucesso!')
            return redirect(self.success_url)
        except ProtectedError:
            messages.error(
                request,
                "❌ Esta linha não pode ser excluída pois está vinculada a um ou mais colaboradores."
            )
            return redirect('controle_de_telefone:linhatelefonica_list')

# ═══════════════════════════════════════════════════════════════════════════════
# CADASTROS AUXILIARES (Marca, Modelo, Operadora, Plano)
# ═══════════════════════════════════════════════════════════════════════════════
# NOTA: Estes são considerados GLOBAIS (sem filial).
# Se precisarem de escopo de filial no futuro, adicione ViewFilialScopedMixin.

class _CadastroAuxiliarBaseMixin(LoginRequiredMixin, AppPermissionMixin, FilialAtivaMixin):
    """Base para CRUDs globais (Marca, Modelo, Operadora, Plano)."""
    app_label_required = _APP


# ── Marca ──
class MarcaListView(_CadastroAuxiliarBaseMixin, ListView):
    permission_required = 'controle_de_telefone.view_marca'
    model = Marca
    template_name = 'controle_de_telefone/marca_list.html'
    context_object_name = 'marcas'
    paginate_by = 15


class MarcaCreateView(_CadastroAuxiliarBaseMixin, SuccessMessageMixin, CreateView):
    permission_required = 'controle_de_telefone.add_marca'
    model = Marca
    form_class = MarcaForm
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:marca_list')
    success_message = "✅ Marca criada com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastrar Nova Marca'
        context['voltar_url'] = self.success_url
        return context


class MarcaUpdateView(_CadastroAuxiliarBaseMixin, SuccessMessageMixin, UpdateView):
    permission_required = 'controle_de_telefone.change_marca'
    model = Marca
    form_class = MarcaForm
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:marca_list')
    success_message = "🔄 Marca atualizada com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Marca'
        context['voltar_url'] = self.success_url
        return context


class MarcaDeleteView(_CadastroAuxiliarBaseMixin, DeleteView):
    permission_required = 'controle_de_telefone.delete_marca'
    model = Marca
    template_name = 'controle_de_telefone/generic_confirm_delete.html'
    success_url = reverse_lazy('controle_de_telefone:marca_list')

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        nome = str(self.object)
        try:
            self.object.delete()
            messages.success(request, f'🗑️ Marca "{nome}" excluída!')
            return redirect(self.success_url)
        except ProtectedError:
            messages.error(request, "❌ Esta marca possui modelos vinculados.")
            return redirect(self.success_url)


# ── Modelo ──
class ModeloListView(_CadastroAuxiliarBaseMixin, ListView):
    permission_required = 'controle_de_telefone.view_modelo'
    model = Modelo
    template_name = 'controle_de_telefone/modelo_list.html'
    context_object_name = 'modelos'
    paginate_by = 15


class ModeloCreateView(_CadastroAuxiliarBaseMixin, SuccessMessageMixin, CreateView):
    permission_required = 'controle_de_telefone.add_modelo'
    model = Modelo
    form_class = ModeloForm
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:modelo_list')
    success_message = "✅ Modelo criado com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastrar Novo Modelo'
        context['voltar_url'] = self.success_url
        return context


class ModeloUpdateView(_CadastroAuxiliarBaseMixin, SuccessMessageMixin, UpdateView):
    permission_required = 'controle_de_telefone.change_modelo'
    model = Modelo
    form_class = ModeloForm
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:modelo_list')
    success_message = "🔄 Modelo atualizado com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Modelo'
        context['voltar_url'] = self.success_url
        return context


class ModeloDeleteView(_CadastroAuxiliarBaseMixin, DeleteView):
    permission_required = 'controle_de_telefone.delete_modelo'
    model = Modelo
    template_name = 'controle_de_telefone/generic_confirm_delete.html'
    success_url = reverse_lazy('controle_de_telefone:modelo_list')

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        nome = str(self.object)
        try:
            self.object.delete()
            messages.success(request, f'🗑️ Modelo "{nome}" excluído!')
            return redirect(self.success_url)
        except ProtectedError:
            messages.error(request, "❌ Este modelo possui aparelhos vinculados.")
            return redirect(self.success_url)


# ── Operadora ──
class OperadoraListView(_CadastroAuxiliarBaseMixin, ListView):
    permission_required = 'controle_de_telefone.view_operadora'
    model = Operadora
    template_name = 'controle_de_telefone/operadora_list.html'
    context_object_name = 'operadoras'
    paginate_by = 15


class OperadoraCreateView(_CadastroAuxiliarBaseMixin, SuccessMessageMixin, CreateView):
    permission_required = 'controle_de_telefone.add_operadora'
    model = Operadora
    form_class = OperadoraForm
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:operadora_list')
    success_message = "✅ Operadora criada com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastrar Nova Operadora'
        context['voltar_url'] = self.success_url
        return context


class OperadoraUpdateView(_CadastroAuxiliarBaseMixin, SuccessMessageMixin, UpdateView):
    permission_required = 'controle_de_telefone.change_operadora'
    model = Operadora
    form_class = OperadoraForm
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:operadora_list')
    success_message = "🔄 Operadora atualizada com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Operadora'
        context['voltar_url'] = self.success_url
        return context


class OperadoraDeleteView(_CadastroAuxiliarBaseMixin, DeleteView):
    permission_required = 'controle_de_telefone.delete_operadora'
    model = Operadora
    template_name = 'controle_de_telefone/generic_confirm_delete.html'
    success_url = reverse_lazy('controle_de_telefone:operadora_list')

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        nome = str(self.object)
        try:
            self.object.delete()
            messages.success(request, f'🗑️ Operadora "{nome}" excluída!')
            return redirect(self.success_url)
        except ProtectedError:
            messages.error(request, "❌ Esta operadora possui planos vinculados.")
            return redirect(self.success_url)


# ── Plano ──
class PlanoListView(_CadastroAuxiliarBaseMixin, ListView):
    permission_required = 'controle_de_telefone.view_plano'
    model = Plano
    template_name = 'controle_de_telefone/plano_list.html'
    context_object_name = 'planos'
    paginate_by = 15


class PlanoCreateView(_CadastroAuxiliarBaseMixin, SuccessMessageMixin, CreateView):
    permission_required = 'controle_de_telefone.add_plano'
    model = Plano
    form_class = PlanoForm
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:plano_list')
    success_message = "✅ Plano criado com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastrar Novo Plano'
        context['voltar_url'] = self.success_url
        return context


class PlanoUpdateView(_CadastroAuxiliarBaseMixin, SuccessMessageMixin, UpdateView):
    permission_required = 'controle_de_telefone.change_plano'
    model = Plano
    form_class = PlanoForm
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:plano_list')
    success_message = "🔄 Plano atualizado com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Plano'
        context['voltar_url'] = self.success_url
        return context


class PlanoDeleteView(_CadastroAuxiliarBaseMixin, DeleteView):
    permission_required = 'controle_de_telefone.delete_plano'
    model = Plano
    template_name = 'controle_de_telefone/generic_confirm_delete.html'
    success_url = reverse_lazy('controle_de_telefone:plano_list')

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        nome = str(self.object)
        try:
            self.object.delete()
            messages.success(request, f'🗑️ Plano "{nome}" excluído!')
            return redirect(self.success_url)
        except ProtectedError:
            messages.error(request, "❌ Este plano possui linhas vinculadas.")
            return redirect(self.success_url)


# ═══════════════════════════════════════════════════════════════════════════════
# VÍNCULO CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class _VinculoBaseMixin(LoginRequiredMixin, AppPermissionMixin, TelefoneVisibilityMixin):
    """Base para CRUD de Vínculos — filtra por filial do funcionário + visibilidade."""
    app_label_required = _APP

    def get_queryset(self):
        filial_id = self.get_filial_ativa_id()
        if not filial_id and not self.request.user.is_superuser:
            return Vinculo.objects.none()

        qs = Vinculo.objects.all()
        if filial_id:
            qs = qs.filter(funcionario__filial_id=filial_id)

        qs = qs.select_related(
            'funcionario', 'aparelho__modelo__marca', 'linha__plano__operadora'
        )
        return self.apply_visibility_vinculo(qs)


class VinculoListView(_VinculoBaseMixin, ListView):
    permission_required = 'controle_de_telefone.view_vinculo'
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
        context['filial_ativa'] = self.get_filial_ativa()
        return context


class VinculoDetailView(_VinculoBaseMixin, DetailView):
    permission_required = 'controle_de_telefone.view_vinculo'
    model = Vinculo
    template_name = 'controle_de_telefone/vinculo_detail.html'
    context_object_name = 'vinculo'


class VinculoCreateView(_VinculoBaseMixin, SuccessMessageMixin, CreateView):
    permission_required = 'controle_de_telefone.add_vinculo'
    model = Vinculo
    form_class = VinculoForm
    template_name = 'controle_de_telefone/vinculo_form.html'
    success_url = reverse_lazy('controle_de_telefone:vinculo_list')
    success_message = "✅ Vínculo criado! O funcionário foi notificado para assinar o termo."

    def get_queryset(self):
        # Para Create não filtra — só usa qs para checks de base
        return Vinculo.objects.all()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        filial_ativa = self.request.session.get('filial_ativa_id')
        kwargs['filial_id'] = filial_ativa
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Criar Novo Vínculo'
        context['voltar_url'] = self.success_url
        context['filial_ativa'] = self.get_filial_ativa()
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
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


class VinculoUpdateView(_VinculoBaseMixin, SuccessMessageMixin, UpdateView):
    permission_required = 'controle_de_telefone.change_vinculo'
    model = Vinculo
    form_class = VinculoForm
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:vinculo_list')
    success_message = "🔄 Vínculo atualizado com sucesso!"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['filial_id'] = self.get_filial_ativa_id()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Vínculo'
        context['voltar_url'] = self.success_url
        return context


class VinculoDeleteView(_VinculoBaseMixin, DeleteView):
    permission_required = 'controle_de_telefone.delete_vinculo'
    model = Vinculo
    template_name = 'controle_de_telefone/generic_confirm_delete.html'
    success_url = reverse_lazy('controle_de_telefone:vinculo_list')

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        nome = str(self.object)
        try:
            self.object.delete()
            messages.success(request, f'🗑️ Vínculo "{nome}" excluído com sucesso!')
            return redirect(self.success_url)
        except ProtectedError:
            messages.error(
                request,
                "❌ Este vínculo não pode ser excluído pois tem registros dependentes."
            )
            return redirect(self.success_url)


# ═══════════════════════════════════════════════════════════════════════════════
# TERMO DE RESPONSABILIDADE
# ═══════════════════════════════════════════════════════════════════════════════

def _gerar_termo_pdf(vinculo):
    """Gera PDF do termo via xhtml2pdf (fallback)."""
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


class AssinarTermoView(LoginRequiredMixin, AppPermissionMixin, SuccessMessageMixin, UpdateView):
    """View para o próprio funcionário assinar seu termo."""
    app_label_required = _APP
    # Sem permission_required — qualquer funcionário autenticado pode
    # assinar SEU PRÓPRIO termo (validação no dispatch)
    model = Vinculo
    form_class = VinculoAssinaturaForm
    template_name = 'controle_de_telefone/termo_assinar_form.html'
    context_object_name = 'vinculo'
    success_message = "✅ Termo de Responsabilidade assinado com sucesso!"

    def get_success_url(self):
        return reverse('controle_de_telefone:vinculo_detail', kwargs={'pk': self.object.pk})

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')

        vinculo = self.get_object()

        # SÓ o dono pode assinar
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
                "Assinatura não fornecida. Por favor, desenhe ou faça o upload."
            )
            return self.form_invalid(form)

        vinculo.foi_assinado = True
        vinculo.data_assinatura = timezone.now()
        vinculo.save()

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
                f"Assinatura salva, mas houve um erro ao gerar o PDF final: {e}"
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


class DownloadTermoView(LoginRequiredMixin, AppPermissionMixin, FilialAtivaMixin, View):
    app_label_required = _APP

    def get(self, request, *args, **kwargs):
        vinculo = get_object_or_404(Vinculo, pk=self.kwargs.get('pk'))

        is_owner = request.user == vinculo.funcionario.usuario
        is_manager = (
            request.user.is_superuser
            or request.user.has_perm('controle_de_telefone.view_vinculo')
        )

        if not is_owner and not is_manager:
            return HttpResponseForbidden("Você não tem permissão para acessar este arquivo.")

        # Manager só acessa arquivos da filial ativa
        if is_manager and not request.user.is_superuser and not is_owner:
            filial_id = self.get_filial_ativa_id()
            if vinculo.funcionario.filial_id != filial_id:
                return HttpResponseForbidden("Acesso negado a arquivos de outra filial.")

        file_to_download = None
        if vinculo.termo_assinado_upload and vinculo.termo_assinado_upload.name:
            file_to_download = vinculo.termo_assinado_upload
        elif vinculo.termo_gerado and vinculo.termo_gerado.name:
            file_to_download = vinculo.termo_gerado

        if not file_to_download or not os.path.exists(file_to_download.path):
            raise Http404("Nenhum termo encontrado. Tente regenerar.")

        return FileResponse(
            open(file_to_download.path, 'rb'),
            as_attachment=True,
            filename=os.path.basename(file_to_download.path),
        )


class DownloadTermosAssinadosView(LoginRequiredMixin, AppPermissionMixin, FilialAtivaMixin, View):
    app_label_required = _APP
    permission_required = 'controle_de_telefone.view_vinculo'

    def get(self, request, *args, **kwargs):
        if not (request.user.is_superuser
                or request.user.has_perm('controle_de_telefone.view_vinculo')):
            return HttpResponseForbidden("Sem permissão.")

        filial_id = self.get_filial_ativa_id()
        if not filial_id and not request.user.is_superuser:
            return HttpResponse("Selecione uma filial.", status=400)

        qs = Vinculo.objects.filter(
            foi_assinado=True,
            termo_assinado_upload__isnull=False,
        )
        if filial_id:
            qs = qs.filter(funcionario__filial_id=filial_id)

        if not qs.exists():
            return HttpResponse("Nenhum termo assinado encontrado.", status=404)

        buffer = BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for vinculo in qs:
                file_path = vinculo.termo_assinado_upload.path
                file_name = (
                    f"termo_{vinculo.funcionario.nome_completo}_{vinculo.aparelho}.pdf"
                )
                zip_file.write(file_path, file_name)

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="termos_assinados.zip"'
        return response


class RegenerarTermoView(LoginRequiredMixin, AppPermissionMixin, FilialAtivaMixin, View):
    app_label_required = _APP

    def post(self, request, *args, **kwargs):
        if not (request.user.is_superuser
                or request.user.has_perm('controle_de_telefone.change_vinculo')):
            return HttpResponseForbidden("Sem permissão.")

        vinculo = get_object_or_404(Vinculo, pk=self.kwargs.get('pk'))

        # Valida filial
        if not request.user.is_superuser:
            filial_id = self.get_filial_ativa_id()
            if vinculo.funcionario.filial_id != filial_id:
                return HttpResponseForbidden("Vínculo fora da sua filial.")

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
                f"Termo para {vinculo.funcionario.nome_completo} gerado com sucesso!"
            )
        except Exception as e:
            messages.error(request, f"Erro ao gerar o termo: {e}")

        return redirect('controle_de_telefone:vinculo_detail', pk=vinculo.pk)


class NotificarAssinaturaView(LoginRequiredMixin, AppPermissionMixin, FilialAtivaMixin, View):
    app_label_required = _APP

    def post(self, request, *args, **kwargs):
        if not (request.user.is_superuser
                or request.user.has_perm('controle_de_telefone.change_vinculo')):
            return HttpResponseForbidden("Sem permissão.")

        vinculo = get_object_or_404(Vinculo, pk=kwargs.get('pk'))

        # Valida filial
        if not request.user.is_superuser:
            filial_id = self.get_filial_ativa_id()
            if vinculo.funcionario.filial_id != filial_id:
                return HttpResponseForbidden("Vínculo fora da sua filial.")

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

        Notificacao.objects.create(
            usuario=usuario_a_notificar,
            mensagem=mensagem,
            url_destino=url_assinatura,
        )

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
                f"Notificação enviada para {usuario_a_notificar.get_full_name()}."
            )
        else:
            messages.warning(
                request,
                "Notificação criada no sistema, mas o funcionário não possui e-mail."
            )

        return redirect(request.META.get('HTTP_REFERER', '/'))

# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

class DashboardView(LoginRequiredMixin, AppPermissionMixin, FilialAtivaMixin, TemplateView):
    app_label_required = _APP
    template_name = 'controle_de_telefone/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filial_id = self.get_filial_ativa_id()

        aparelhos_qs = Aparelho.objects.filter(filial_id=filial_id) if filial_id else Aparelho.objects.none()
        linhas_qs = LinhaTelefonica.objects.filter(filial_id=filial_id) if filial_id else LinhaTelefonica.objects.none()
        vinculos_qs = Vinculo.objects.filter(funcionario__filial_id=filial_id) if filial_id else Vinculo.objects.none()

        if self.request.user.is_superuser and not filial_id:
            aparelhos_qs = Aparelho.objects.all()
            linhas_qs = LinhaTelefonica.objects.all()
            vinculos_qs = Vinculo.objects.all()

        context['filial_ativa'] = self.get_filial_ativa()
        context['total_aparelhos'] = aparelhos_qs.count()
        context['total_linhas'] = linhas_qs.count()

        vinculos_ativos = vinculos_qs.filter(data_devolucao__isnull=True).count()
        vinculos_inativos = vinculos_qs.filter(data_devolucao__isnull=False).count()
        context['total_vinculos'] = vinculos_ativos

        context['total_marcas'] = Marca.objects.count()
        context['total_modelos'] = Modelo.objects.count()
        context['total_operadoras'] = Operadora.objects.count()
        context['total_planos'] = Plano.objects.count()

        aparelhos_por_marca = (
            aparelhos_qs.values('modelo__marca__nome')
            .annotate(total=Count('id')).order_by('-total')
        )
        context['marcas_labels_json'] = json.dumps(
            [item['modelo__marca__nome'] for item in aparelhos_por_marca]
        )
        context['marcas_data_json'] = json.dumps(
            [item['total'] for item in aparelhos_por_marca]
        )

        linhas_por_operadora = (
            linhas_qs.values('plano__operadora__nome')
            .annotate(total=Count('id')).order_by('-total')
        )
        context['operadoras_labels_json'] = json.dumps(
            [item['plano__operadora__nome'] for item in linhas_por_operadora]
        )
        context['operadoras_data_json'] = json.dumps(
            [item['total'] for item in linhas_por_operadora]
        )

        context['vinculos_status_data_json'] = json.dumps(
            [vinculos_ativos, vinculos_inativos]
        )

        return context


# ═══════════════════════════════════════════════════════════════════════════════
# RECARGA DE CRÉDITO CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class _RecargaBaseMixin(LoginRequiredMixin, AppPermissionMixin, FilialAtivaMixin):
    app_label_required = _APP

    def get_queryset_filtered(self):
        filial_id = self.get_filial_ativa_id()
        qs = RecargaCredito.objects.all()
        if filial_id:
            qs = qs.filter(filial_id=filial_id)
        elif not self.request.user.is_superuser:
            return RecargaCredito.objects.none()
        return qs

class RecargaCreditoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = RecargaCredito
    template_name = 'controle_de_telefone/recarga_list.html'
    context_object_name = 'recargas'
    paginate_by = 25
    permission_required = 'controle_de_telefone.view_recargacredito'

    def get_queryset(self):
        qs = super().get_queryset().select_related(
            'linha', 'linha__plano', 'linha__plano__operadora',
            'filial', 'usuario_credito', 'responsavel'
        )
        
        # Filtra por filial ativa (se não for superuser)
        filial_id = self.request.session.get('filial_ativa_id')
        if filial_id and not self.request.user.is_superuser:
            qs = qs.filter(filial_id=filial_id)
        
        # Filtros de busca (query params)
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        
        search = self.request.GET.get('q')
        if search:
            qs = qs.filter(
                Q(linha__numero__icontains=search) |
                Q(usuario_credito__nome_completo__icontains=search) |
                Q(codigo_transacao__icontains=search)
            )
        
        return qs.order_by('-data_solicitacao')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # ═══════════════════════════════════════════════════════════
        # Base do queryset para estatísticas (respeita filial ativa)
        # ═══════════════════════════════════════════════════════════
        qs_filial = RecargaCredito.objects.all()
        filial_id = self.request.session.get('filial_ativa_id')
        if filial_id and not self.request.user.is_superuser:
            qs_filial = qs_filial.filter(filial_id=filial_id)

        # ═══════════════════════════════════════════════════════════
        # Estatísticas com filtros REAIS (não mais ...)
        # ═══════════════════════════════════════════════════════════
        hoje = timezone.now().date()
        primeiro_dia_mes = hoje.replace(day=1)

        # Total do mês corrente (apenas realizadas)
        context['total_mes'] = qs_filial.filter(
            status='realizada',
            data_recarga__gte=primeiro_dia_mes,
            data_recarga__lte=hoje,
        ).aggregate(total=Sum('valor'))['total'] or 0

        # Contadores por status
        context['total_pendentes'] = qs_filial.filter(status='pendente').count()
        context['total_aprovadas'] = qs_filial.filter(status='aprovada').count()
        context['total_realizadas'] = qs_filial.filter(status='realizada').count()
        context['total_canceladas'] = qs_filial.filter(status='cancelada').count()

        # Total geral investido (histórico de realizadas)
        context['total_geral'] = qs_filial.filter(
            status='realizada'
        ).aggregate(total=Sum('valor'))['total'] or 0

        # Recargas vigentes (ativas agora)
        context['total_vigentes'] = qs_filial.filter(
            status='realizada',
            data_inicio__lte=hoje,
            data_termino__gte=hoje,
        ).count()

        # Filtros ativos (para manter na paginação e exibir chips)
        context['status_atual'] = self.request.GET.get('status', '')
        context['search_atual'] = self.request.GET.get('q', '')
        context['titulo'] = 'Recargas de Crédito'

        return context

class RecargaCreditoCreateView(_RecargaBaseMixin, SuccessMessageMixin, CreateView):
    permission_required = 'controle_de_telefone.add_recargacredito'
    model = RecargaCredito
    form_class = RecargaCreditoForm
    template_name = 'controle_de_telefone/recarga_form.html'
    success_url = reverse_lazy('controle_de_telefone:recarga_list')
    success_message = "✅ Recarga cadastrada com sucesso!"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['filial_id'] = self.get_filial_ativa_id()
        return kwargs

    def form_valid(self, form):
        filial = self.get_filial_ativa()
        if not filial and not self.request.user.is_superuser:
            messages.error(
                self.request,
                "Nenhuma filial selecionada. Escolha uma filial no menu superior."
            )
            return self.form_invalid(form)
        if filial:
            form.instance.filial = filial
        form.instance.criado_por = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nova Recarga de Crédito'
        context['filial_ativa'] = self.get_filial_ativa()
        return context


class RecargaCreditoUpdateView(_RecargaBaseMixin, SuccessMessageMixin, UpdateView):
    permission_required = 'controle_de_telefone.change_recargacredito'
    model = RecargaCredito
    form_class = RecargaCreditoForm
    template_name = 'controle_de_telefone/recarga_form.html'
    success_url = reverse_lazy('controle_de_telefone:recarga_list')
    success_message = "🔄 Recarga atualizada com sucesso!"

    def get_queryset(self):
        return self.get_queryset_filtered()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['filial_id'] = self.get_filial_ativa_id()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = f'Editar Recarga — {self.object.linha.numero}'
        return context


class RecargaCreditoDetailView(_RecargaBaseMixin, DetailView):
    permission_required = 'controle_de_telefone.view_recargacredito'
    model = RecargaCredito
    template_name = 'controle_de_telefone/recarga_detail.html'
    context_object_name = 'recarga'

    def get_queryset(self):
        return self.get_queryset_filtered().select_related(
            'linha', 'linha__plano__operadora',
            'responsavel', 'usuario_credito', 'criado_por',
        )


class RecargaCreditoDeleteView(_RecargaBaseMixin, DeleteView):
    permission_required = 'controle_de_telefone.delete_recargacredito'
    model = RecargaCredito
    template_name = 'controle_de_telefone/recarga_confirm_delete.html'
    success_url = reverse_lazy('controle_de_telefone:recarga_list')

    def get_queryset(self):
        return self.get_queryset_filtered()

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            self.object.delete()
            messages.success(request, '🗑️ Recarga excluída com sucesso!')
            return redirect(self.success_url)
        except ProtectedError:
            messages.error(request, "❌ Esta recarga tem registros vinculados.")
            return redirect(self.success_url)


# ═══════════════════════════════════════════════════════════════════════════════
# AÇÕES DE RECARGA (FBVs)
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@app_permission_required(_APP)
def recarga_aprovar(request, pk):
    """Aprovar uma recarga pendente."""
    filial_id = _get_filial_id(request)

    qs = RecargaCredito.objects.all()
    if filial_id:
        qs = qs.filter(filial_id=filial_id)
    elif not request.user.is_superuser:
        return HttpResponseForbidden("Selecione uma filial.")

    recarga = get_object_or_404(qs, pk=pk)

    if recarga.status != RecargaCredito.StatusRecarga.PENDENTE:
        messages.error(request, 'Esta recarga não pode ser aprovada.')
        return redirect('controle_de_telefone:recarga_detail', pk=pk)

    if not request.user.has_perm('controle_de_telefone.aprovar_recarga'):
        messages.error(request, 'Você não tem permissão para aprovar recargas.')
        return redirect('controle_de_telefone:recarga_detail', pk=pk)

    recarga.aprovar(user=request.user)
    messages.success(request, '✅ Recarga aprovada com sucesso!')
    return redirect('controle_de_telefone:recarga_detail', pk=pk)


@login_required
@app_permission_required(_APP)
def recarga_realizar(request, pk):
    """Marcar recarga como realizada."""
    filial_id = _get_filial_id(request)

    qs = RecargaCredito.objects.all()
    if filial_id:
        qs = qs.filter(filial_id=filial_id)
    elif not request.user.is_superuser:
        return HttpResponseForbidden("Selecione uma filial.")

    recarga = get_object_or_404(qs, pk=pk)

    if not request.user.has_perm('controle_de_telefone.change_recargacredito'):
        messages.error(request, 'Sem permissão.')
        return redirect('controle_de_telefone:recarga_detail', pk=pk)

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
            messages.success(request, '✅ Recarga marcada como realizada!')
            return redirect('controle_de_telefone:recarga_detail', pk=pk)
    else:
        form = RecargaCreditoRealizarForm(instance=recarga)

    return render(request, 'controle_de_telefone/recarga_realizar.html', {
        'form': form,
        'recarga': recarga,
    })


@login_required
@app_permission_required(_APP)
def recarga_cancelar(request, pk):
    """Cancelar uma recarga."""
    filial_id = _get_filial_id(request)

    qs = RecargaCredito.objects.all()
    if filial_id:
        qs = qs.filter(filial_id=filial_id)
    elif not request.user.is_superuser:
        return HttpResponseForbidden("Selecione uma filial.")

    recarga = get_object_or_404(qs, pk=pk)

    if recarga.status == RecargaCredito.StatusRecarga.REALIZADA:
        messages.error(request, 'Recargas realizadas não podem ser canceladas.')
        return redirect('controle_de_telefone:recarga_detail', pk=pk)

    if not request.user.has_perm('controle_de_telefone.cancelar_recarga'):
        messages.error(request, 'Você não tem permissão para cancelar recargas.')
        return redirect('controle_de_telefone:recarga_detail', pk=pk)

    if request.method == 'POST':
        motivo = request.POST.get('motivo_cancelamento', '')
        recarga.cancelar(motivo_cancelamento=motivo, user=request.user)
        messages.success(request, '✅ Recarga cancelada com sucesso!')
        return redirect('controle_de_telefone:recarga_list')

    return render(request, 'controle_de_telefone/recarga_cancelar.html', {
        'recarga': recarga,
    })
