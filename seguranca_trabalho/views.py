# seguranca_trabalho/views.py

import base64
import io
import json
import logging
import re
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.db.models import Q, Count, Sum, Value, IntegerField, ProtectedError
from django.db.models.functions import Coalesce
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView,
)
from django.views.generic.edit import FormMixin
from django.views.decorators.http import require_POST

from docx import Document
from weasyprint import HTML, default_url_fetcher

from core.mixins import (
    AppPermissionMixin, FilialCreateMixin, HTMXModalFormMixin,
    SSTPermissionMixin, ViewFilialScopedMixin, TecnicoScopeMixin,
)
from departamento_pessoal.models import Funcionario
from usuario.models import Filial

from .forms import (
    AssinaturaEntregaForm, AssinaturaTermoForm, EntregaEPIForm,
    EquipamentoForm, FichaEPIForm, FuncaoForm, CargoFuncaoForm,
    AjusteEstoqueForm,
)
from .models import (
    EntregaEPI, Equipamento, FichaEPI, Funcao, MatrizEPI,
    CargoFuncao, MovimentacaoEstoque,
)

logger = logging.getLogger(__name__)

_APP = 'seguranca_trabalho'


# =============================================================================
# HELPERS
# =============================================================================

def _safe_data_uri(sig):
    pattern = r'^data:image/(png|jpeg|jpg|gif|svg\+xml);base64,[A-Za-z0-9+/=\s]+$'
    if re.match(pattern, sig):
        return mark_safe(sig)
    return ''


def custom_url_fetcher(url):
    """Permite que o WeasyPrint acesse arquivos de media locais."""
    if url.startswith(settings.MEDIA_URL):
        path = (settings.MEDIA_ROOT / url[len(settings.MEDIA_URL):]).as_posix()
        return default_url_fetcher(f'file://{path}')
    return default_url_fetcher(url)


def _estoque_equipamento(equipamento, filial):
    """Calcula estoque atual de um equipamento na filial."""
    mov = MovimentacaoEstoque.objects.filter(equipamento=equipamento, filial=filial)
    entradas = mov.filter(tipo='ENTRADA').aggregate(
        total=Coalesce(Sum('quantidade'), Value(0, output_field=IntegerField()))
    )['total']
    saidas = mov.filter(tipo='SAIDA').aggregate(
        total=Coalesce(Sum('quantidade'), Value(0, output_field=IntegerField()))
    )['total']
    return entradas - saidas


# =============================================================================
# CRUD DE EQUIPAMENTOS
# =============================================================================

class EquipamentoListView(LoginRequiredMixin, AppPermissionMixin, SSTPermissionMixin, ViewFilialScopedMixin, ListView):
    app_label_required = _APP
    model = Equipamento
    template_name = 'seguranca_trabalho/equipamento_list.html'
    context_object_name = 'equipamentos'
    permission_required = 'seguranca_trabalho.view_equipamento'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filial = getattr(self.request.user, 'filial_ativa', None)

        if filial:
            mov = MovimentacaoEstoque.objects.filter(filial=filial)

            for eq in context['equipamentos']:
                entradas = mov.filter(equipamento=eq, tipo='ENTRADA').aggregate(
                    total=Coalesce(Sum('quantidade'), Value(0, output_field=IntegerField()))
                )['total']
                saidas = mov.filter(equipamento=eq, tipo='SAIDA').aggregate(
                    total=Coalesce(Sum('quantidade'), Value(0, output_field=IntegerField()))
                )['total']
                eq.estoque_atual = entradas - saidas
                eq.total_entradas = entradas
                eq.total_saidas = saidas

        return context


class EquipamentoDetailView(LoginRequiredMixin, AppPermissionMixin, SSTPermissionMixin, ViewFilialScopedMixin, DetailView):
    app_label_required = _APP
    model = Equipamento
    template_name = 'seguranca_trabalho/equipamento_detail.html'
    context_object_name = 'equipamento'
    permission_required = 'seguranca_trabalho.view_equipamento'


class EquipamentoCreateView(LoginRequiredMixin, AppPermissionMixin, SSTPermissionMixin, FilialCreateMixin, CreateView):
    app_label_required = _APP
    model = Equipamento
    form_class = EquipamentoForm
    template_name = 'seguranca_trabalho/equipamento_form.html'
    success_url = reverse_lazy('seguranca_trabalho:equipamento_list')
    permission_required = 'seguranca_trabalho.add_equipamento'

    def form_valid(self, form):
        response = super().form_valid(form)

        estoque_inicial = form.cleaned_data.get('estoque_inicial')
        if estoque_inicial and estoque_inicial > 0:
            MovimentacaoEstoque.objects.create(
                equipamento=self.object,
                tipo='ENTRADA',
                quantidade=estoque_inicial,
                justificativa='Carga inicial de estoque (cadastro do equipamento)',
                responsavel=self.request.user,
                filial=self.object.filial,
            )
        return response


class EquipamentoUpdateView(LoginRequiredMixin, AppPermissionMixin, SSTPermissionMixin, ViewFilialScopedMixin, UpdateView):
    app_label_required = _APP
    model = Equipamento
    form_class = EquipamentoForm
    template_name = 'seguranca_trabalho/equipamento_form.html'
    success_url = reverse_lazy('seguranca_trabalho:equipamento_list')
    permission_required = 'seguranca_trabalho.change_equipamento'

    def get_queryset(self):
        return super().get_queryset().select_related('fabricante')

    def form_valid(self, form):
        messages.success(self.request, f"Equipamento '{form.instance.nome}' atualizado com sucesso!")
        return super().form_valid(form)


class EquipamentoDeleteView(LoginRequiredMixin, AppPermissionMixin, SSTPermissionMixin, ViewFilialScopedMixin, DeleteView):
    app_label_required = _APP
    model = Equipamento
    template_name = 'seguranca_trabalho/confirm_delete.html'
    success_url = reverse_lazy('seguranca_trabalho:equipamento_list')
    context_object_name = 'object'
    permission_required = 'seguranca_trabalho.delete_equipamento'

    def form_valid(self, form):
        messages.success(self.request, "Equipamento excluído com sucesso!")
        return super().form_valid(form)


class AjusteEstoqueView(LoginRequiredMixin, AppPermissionMixin, SSTPermissionMixin, View):
    """Permite ajustar o estoque de um equipamento com justificativa."""
    app_label_required = _APP
    permission_required = 'seguranca_trabalho.change_equipamento'

    def _get_equipamento(self, request, pk):
        filial = getattr(request.user, 'filial_ativa', None)
        return get_object_or_404(Equipamento, pk=pk, filial=filial)

    def get(self, request, pk):
        equipamento = self._get_equipamento(request, pk)
        form = AjusteEstoqueForm()
        return render(request, 'seguranca_trabalho/ajuste_estoque.html', {
            'equipamento': equipamento,
            'form': form,
        })

    def post(self, request, pk):
        equipamento = self._get_equipamento(request, pk)
        filial = getattr(request.user, 'filial_ativa', None)
        form = AjusteEstoqueForm(request.POST)

        if form.is_valid():
            tipo = form.cleaned_data['tipo']
            quantidade = form.cleaned_data['quantidade']
            justificativa = form.cleaned_data['justificativa']

            # Calcula estoque atual via helper
            estoque_atual = _estoque_equipamento(equipamento, filial)

            if tipo == 'SAIDA' and quantidade > estoque_atual:
                form.add_error('quantidade', _(
                    f"Estoque insuficiente. Disponível: {estoque_atual}"
                ))
                return render(request, 'seguranca_trabalho/ajuste_estoque.html', {
                    'equipamento': equipamento,
                    'form': form,
                })

            MovimentacaoEstoque.objects.create(
                equipamento=equipamento,
                tipo=tipo,
                quantidade=quantidade,
                justificativa=f"[AJUSTE MANUAL] {justificativa}",
                responsavel=request.user,
                filial=filial,
            )

            tipo_label = "adicionadas ao" if tipo == 'ENTRADA' else "removidas do"
            messages.success(
                request,
                f"{quantidade} unidades {tipo_label} estoque de '{equipamento.nome}'."
            )
            return redirect('seguranca_trabalho:equipamento_detail', pk=equipamento.pk)

        return render(request, 'seguranca_trabalho/ajuste_estoque.html', {
            'equipamento': equipamento,
            'form': form,
        })


# =============================================================================
# CRUD DE FICHAS DE EPI
# =============================================================================

class FichaEPIListView(LoginRequiredMixin, AppPermissionMixin, SSTPermissionMixin, TecnicoScopeMixin, ViewFilialScopedMixin, ListView):
    app_label_required = _APP
    model = FichaEPI
    template_name = 'seguranca_trabalho/ficha_list.html'
    context_object_name = 'fichas'
    paginate_by = 30
    permission_required = 'seguranca_trabalho.view_fichaepi'
    tecnico_scope_lookup = 'funcionario__usuario'

    def get_queryset(self):
        qs = super().get_queryset().select_related('funcionario', 'funcionario__cargo')
        query_text = self.request.GET.get('q')
        if query_text:
            qs = qs.filter(
                Q(funcionario__nome_completo__icontains=query_text) |
                Q(funcionario__matricula__icontains=query_text)
            )
        return qs.order_by('funcionario__nome_completo')


class FichaEPICreateView(LoginRequiredMixin, AppPermissionMixin, SSTPermissionMixin, FilialCreateMixin, CreateView):
    app_label_required = _APP
    model = FichaEPI
    form_class = FichaEPIForm
    template_name = 'seguranca_trabalho/ficha_create.html'
    success_url = reverse_lazy('seguranca_trabalho:ficha_list')
    permission_required = 'seguranca_trabalho.add_fichaepi'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        form.instance.filial = form.cleaned_data['funcionario'].filial
        return super().form_valid(form)


class FichaEPIDetailView(LoginRequiredMixin, AppPermissionMixin, SSTPermissionMixin, TecnicoScopeMixin, ViewFilialScopedMixin, FormMixin, DetailView):
    app_label_required = _APP
    model = FichaEPI
    template_name = 'seguranca_trabalho/ficha_detail.html'
    context_object_name = 'ficha'
    form_class = EntregaEPIForm
    permission_required = 'seguranca_trabalho.view_fichaepi'
    tecnico_scope_lookup = 'funcionario__usuario'

    def get_success_url(self):
        return reverse('seguranca_trabalho:ficha_detail', kwargs={'pk': self.object.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['filial'] = self.get_object().filial
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = self.get_form()
        context['entregas'] = self.object.entregas.select_related('equipamento').order_by('-data_entrega')
        return context

    def post(self, request, *args, **kwargs):
        if not request.user.has_perm('seguranca_trabalho.add_entregaepi'):
            raise PermissionDenied("Você não tem permissão para registrar uma nova entrega.")
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form):
        with transaction.atomic():
            nova_entrega = form.save(commit=False)
            nova_entrega.ficha = self.object
            nova_entrega.filial = self.object.filial
            nova_entrega.save()
            MovimentacaoEstoque.objects.create(
                equipamento=nova_entrega.equipamento,
                tipo='SAIDA',
                quantidade=nova_entrega.quantidade,
                responsavel=self.request.user,
                justificativa=f"Entrega EPI - Ficha #{self.object.pk} ({self.object.funcionario.nome_completo})",
                entrega_associada=nova_entrega,
                filial=nova_entrega.filial,
            )
        messages.success(self.request, "Nova entrega de EPI registrada com sucesso!")
        return redirect(self.get_success_url())


class FichaEPIUpdateView(LoginRequiredMixin, AppPermissionMixin, SSTPermissionMixin, ViewFilialScopedMixin, UpdateView):
    app_label_required = _APP
    model = FichaEPI
    form_class = FichaEPIForm
    template_name = 'seguranca_trabalho/ficha_form.html'
    permission_required = 'seguranca_trabalho.change_fichaepi'

    def get_success_url(self):
        return reverse('seguranca_trabalho:ficha_detail', kwargs={'pk': self.object.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs


class FichaEPIDeleteView(LoginRequiredMixin, AppPermissionMixin, SSTPermissionMixin, ViewFilialScopedMixin, DeleteView):
    app_label_required = _APP
    model = FichaEPI
    template_name = 'seguranca_trabalho/confirm_delete.html'
    success_url = reverse_lazy('seguranca_trabalho:ficha_list')
    context_object_name = 'object'
    permission_required = 'seguranca_trabalho.delete_fichaepi'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ficha = self.get_object()
        entregas = ficha.entregas.select_related('equipamento')
        context['has_entregas'] = entregas.exists()
        context['entregas_count'] = entregas.count()
        return context

    def form_valid(self, form):
        try:
            messages.success(self.request, "Ficha de EPI excluída com sucesso!")
            return super().form_valid(form)
        except ProtectedError:
            ficha = self.get_object()
            count = ficha.entregas.count()
            messages.error(
                self.request,
                f"Não é possível excluir esta ficha. "
                f"Existem {count} entrega(s) de EPI vinculada(s). "
                f"Remova ou devolva todas as entregas antes de excluir a ficha."
            )
            return redirect('seguranca_trabalho:ficha_detail', pk=ficha.pk)


# =============================================================================
# AÇÕES DE ENTREGA (Assinatura, Devolução)
# =============================================================================

class AssinarEntregaView(LoginRequiredMixin, AppPermissionMixin, SSTPermissionMixin, TecnicoScopeMixin, ViewFilialScopedMixin, UpdateView):
    app_label_required = _APP
    model = EntregaEPI
    form_class = AssinaturaEntregaForm
    template_name = 'seguranca_trabalho/entrega_sign.html'
    context_object_name = 'entrega'
    permission_required = 'seguranca_trabalho.assinar_entregaepi'
    tecnico_scope_lookup = 'ficha__funcionario__usuario'

    def get_success_url(self):
        return reverse('seguranca_trabalho:ficha_detail', kwargs={'pk': self.object.ficha.pk})

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.data_devolucao or self.object.data_assinatura:
            messages.info(request, "Esta entrega já foi processada.")
            return redirect(self.get_success_url())
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        entrega = form.save(commit=False)

        assinatura_base64 = self.request.POST.get('assinatura_base64', '').strip()
        if assinatura_base64:
            entrega.assinatura_recebimento = assinatura_base64

        if 'assinatura_imagem' in self.request.FILES:
            entrega.assinatura_imagem = self.request.FILES['assinatura_imagem']

        entrega.data_assinatura = timezone.now()
        entrega.save()

        messages.success(self.request, "Assinatura registrada com sucesso!")
        return redirect(self.get_success_url())


class RegistrarDevolucaoView(LoginRequiredMixin, AppPermissionMixin, SSTPermissionMixin, TecnicoScopeMixin, View):
    app_label_required = _APP
    permission_required = 'seguranca_trabalho.change_entregaepi'
    http_method_names = ['post']
    tecnico_scope_lookup = 'ficha__funcionario__usuario'

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        filial_id = request.session.get('active_filial_id')
        qs = EntregaEPI.objects.all()
        if filial_id:
            qs = qs.filter(filial_id=filial_id)
        qs = self.scope_tecnico_queryset(qs)
        entrega = get_object_or_404(qs, pk=kwargs.get('pk'))

        if entrega.data_devolucao:
            messages.warning(request, f"O EPI '{entrega.equipamento.nome}' já foi devolvido.")
        else:
            entrega.data_devolucao = timezone.now().date()
            entrega.recebedor_devolucao = request.user
            entrega.save()
            MovimentacaoEstoque.objects.create(
                equipamento=entrega.equipamento,
                tipo='ENTRADA',
                quantidade=entrega.quantidade,
                responsavel=request.user,
                justificativa=f"Devolução EPI - Ficha #{entrega.ficha.pk} ({entrega.ficha.funcionario.nome_completo})",
                entrega_associada=entrega,
                filial=entrega.filial,
            )
            messages.success(request, f"Devolução do EPI '{entrega.equipamento.nome}' registrada.")
        return redirect('seguranca_trabalho:ficha_detail', pk=entrega.ficha.pk)


# =============================================================================
# RELATÓRIOS E PAINÉIS
# =============================================================================

class GerarFichaPDFView(LoginRequiredMixin, AppPermissionMixin, SSTPermissionMixin, TecnicoScopeMixin, ViewFilialScopedMixin, DetailView):
    app_label_required = _APP
    model = FichaEPI
    permission_required = 'seguranca_trabalho.view_fichaepi'
    tecnico_scope_lookup = 'funcionario__usuario'

    @staticmethod
    def _processar_assinatura(entrega):
        """Retorna data URI da assinatura ou None."""
        if entrega.assinatura_recebimento:
            sig = entrega.assinatura_recebimento.strip()
            if sig.startswith('data:image'):
                return mark_safe(sig)
            if len(sig) > 100:
                return mark_safe(f'data:image/png;base64,{sig}')

        if entrega.assinatura_imagem and entrega.assinatura_imagem.name:
            try:
                entrega.assinatura_imagem.open('rb')
                content = entrega.assinatura_imagem.read()
                entrega.assinatura_imagem.close()
                if content:
                    mime = 'image/jpeg' if content[:2] == b'\xff\xd8' else 'image/png'
                    encoded = base64.b64encode(content).decode('utf-8')
                    return mark_safe(f'data:{mime};base64,{encoded}')
            except Exception as e:
                logger.warning("Erro assinatura_imagem #%s: %s", entrega.pk, e)

        return None

    def _get_logo_base64(self, filial):
        """Logo da filial ou fallback estático."""
        if filial and hasattr(filial, 'logo') and filial.logo and filial.logo.name:
            try:
                filial.logo.open('rb')
                content = filial.logo.read()
                filial.logo.close()
                if content:
                    mime = 'image/jpeg' if content[:2] == b'\xff\xd8' else 'image/png'
                    encoded = base64.b64encode(content).decode('utf-8')
                    return mark_safe(f'data:{mime};base64,{encoded}')
            except Exception as e:
                logger.warning("Erro logo filial: %s", e)

        for nome in ['logo.png', 'logo.jpg', 'logo_cetest.png']:
            logo_path = Path(settings.BASE_DIR) / 'static' / 'images' / nome
            if logo_path.exists():
                content = logo_path.read_bytes()
                mime = 'image/jpeg' if content[:2] == b'\xff\xd8' else 'image/png'
                encoded = base64.b64encode(content).decode('utf-8')
                return mark_safe(f'data:{mime};base64,{encoded}')

        return None

    def get(self, request, *args, **kwargs):
        ficha = self.get_object()

        logger.info("Gerando ficha PDF: %s", ficha.funcionario.nome_completo)

        entregas = EntregaEPI.objects.filter(
            ficha=ficha
        ).select_related('equipamento').order_by('data_entrega')

        for entrega in entregas:
            entrega.assinatura_base64 = self._processar_assinatura(entrega)

        logo_base64 = self._get_logo_base64(ficha.filial)

        assinatura_funcionario = None
        if ficha.assinatura_funcionario:
            sig = ficha.assinatura_funcionario.strip()
            if sig.startswith('data:image'):
                assinatura_funcionario = mark_safe(sig)
            elif len(sig) > 100:
                assinatura_funcionario = mark_safe(f'data:image/png;base64,{sig}')

        context = {
            'ficha': ficha,
            'entregas': entregas,
            'data_emissao': timezone.now(),
            'logo_base64': logo_base64,
            'assinatura_funcionario': assinatura_funcionario,
        }

        html_string = render_to_string(
            'seguranca_trabalho/ficha_pdf_template.html', context
        )

        if settings.DEBUG:
            debug_path = Path(settings.BASE_DIR) / 'debug_ficha.html'
            debug_path.write_text(html_string, encoding='utf-8')
            logger.debug("Debug HTML: %s", debug_path)

        html = HTML(
            string=html_string,
            base_url=request.build_absolute_uri(),
            url_fetcher=custom_url_fetcher,
        )
        pdf = html.write_pdf()
        logger.info("PDF gerado (%d bytes)", len(pdf))

        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="ficha_epi_{ficha.funcionario.matricula}.pdf"'
        )
        return response


class AssinarTermoView(LoginRequiredMixin, AppPermissionMixin, SSTPermissionMixin, TecnicoScopeMixin, ViewFilialScopedMixin, UpdateView):
    app_label_required = _APP
    model = FichaEPI
    form_class = AssinaturaTermoForm
    template_name = 'seguranca_trabalho/termo_sign.html'
    context_object_name = 'ficha'
    permission_required = 'seguranca_trabalho.change_fichaepi'
    tecnico_scope_lookup = 'funcionario__usuario'

    def get_success_url(self):
        return reverse('seguranca_trabalho:ficha_detail', kwargs={'pk': self.object.pk})

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.assinatura_funcionario:
            messages.info(request, "O termo já foi assinado pelo funcionário.")
            return redirect(self.get_success_url())
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        ficha = form.save(commit=False)

        assinatura_base64 = self.request.POST.get('assinatura_base64', '').strip()
        if not assinatura_base64:
            messages.error(self.request, "Por favor, assine no campo de assinatura.")
            return self.form_invalid(form)

        ficha.assinatura_funcionario = assinatura_base64
        ficha.data_assinatura_termo = timezone.now()
        ficha.save()

        messages.success(self.request, "Termo assinado com sucesso!")
        return redirect(self.get_success_url())


class DashboardSSTView(LoginRequiredMixin, AppPermissionMixin, SSTPermissionMixin, TecnicoScopeMixin, ViewFilialScopedMixin, TemplateView):
    app_label_required = _APP
    template_name = 'seguranca_trabalho/dashboard.html'
    permission_required = 'seguranca_trabalho.view_fichaepi'
    tecnico_scope_lookup = 'funcionario__usuario'

    def _is_tecnico(self):
        user = self.request.user
        if hasattr(user, 'is_tecnico'):
            return user.is_tecnico
        return not user.is_staff and not user.is_superuser

    def get_queryset_base(self, model_class):
        filial_id = self.request.session.get('active_filial_id')
        if not filial_id:
            return model_class.objects.none()

        if hasattr(model_class, 'filial'):
            return model_class.objects.filter(filial_id=filial_id)
        elif hasattr(model_class, 'funcionario'):
            return model_class.objects.filter(funcionario__filial_id=filial_id)
        return model_class.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            equipamentos_da_filial = self.get_queryset_base(Equipamento)
            fichas_da_filial = self.get_queryset_base(FichaEPI)
            entregas_da_filial = self.get_queryset_base(EntregaEPI)
            matriz_da_filial = self.get_queryset_base(MatrizEPI)
        except Exception as e:
            logger.error("Erro no DashboardSST: %s", e)
            equipamentos_da_filial = Equipamento.objects.none()
            fichas_da_filial = FichaEPI.objects.none()
            entregas_da_filial = EntregaEPI.objects.none()
            matriz_da_filial = MatrizEPI.objects.none()

        if self._is_tecnico():
            equipamentos_da_filial = equipamentos_da_filial.none()
            matriz_da_filial = matriz_da_filial.none()
            fichas_da_filial = fichas_da_filial.filter(funcionario__usuario=self.request.user)
            entregas_da_filial = entregas_da_filial.filter(ficha__funcionario__usuario=self.request.user)

        # KPIs
        context['total_equipamentos_ativos'] = equipamentos_da_filial.filter(ativo=True).count()
        context['fichas_ativas'] = fichas_da_filial.filter(funcionario__status='ATIVO').count()
        context['entregas_pendentes_assinatura'] = entregas_da_filial.filter(
            data_devolucao__isnull=True,
            data_assinatura__isnull=True
        ).count()

        # GRÁFICO: Status de Vencimento
        today = timezone.now().date()
        thirty_days = today + timedelta(days=30)
        entregas_ativas = entregas_da_filial.filter(
            data_devolucao__isnull=True,
            data_entrega__isnull=False
        ).select_related('equipamento')

        epis_vencidos = 0
        epis_vencendo = 0
        epis_regulares = 0

        for entrega in entregas_ativas:
            if entrega.equipamento.vida_util_dias:
                vencimento = entrega.data_entrega + timedelta(days=entrega.equipamento.vida_util_dias)
                if vencimento < today:
                    epis_vencidos += 1
                elif today <= vencimento <= thirty_days:
                    epis_vencendo += 1
                else:
                    epis_regulares += 1
            else:
                epis_regulares += 1

        context['epis_vencendo_em_30_dias'] = epis_vencendo
        context['chart_vencimento_labels'] = json.dumps(['Regulares', 'Vencendo (30d)', 'Vencidos'])
        context['chart_vencimento_data'] = json.dumps([epis_regulares, epis_vencendo, epis_vencidos])

        # GRÁFICO: Matriz de EPI
        matriz_data = matriz_da_filial.values('funcao__nome').annotate(
            num_epis=Count('equipamento')
        ).order_by('-num_epis')[:10]

        if matriz_data:
            context['matriz_labels'] = json.dumps([m['funcao__nome'] for m in matriz_data])
            context['matriz_data'] = json.dumps([m['num_epis'] for m in matriz_data])

        # GRÁFICO: Status das Entregas
        entregas_assinadas = entregas_da_filial.filter(data_devolucao__isnull=True, data_assinatura__isnull=False).count()
        entregas_pendentes = context['entregas_pendentes_assinatura']
        entregas_devolvidas = entregas_da_filial.filter(data_devolucao__isnull=False).count()

        context['chart_status_entregas_labels'] = json.dumps(['Assinadas (Ativas)', 'Pendentes', 'Devolvidas'])
        context['chart_status_entregas_data'] = json.dumps([entregas_assinadas, entregas_pendentes, entregas_devolvidas])

        # GRÁFICO: Top 5 EPIs
        top_epis = entregas_da_filial.values('equipamento__nome').annotate(total=Count('id')).order_by('-total')[:5]
        if top_epis:
            context['chart_top_epis_labels'] = json.dumps([e['equipamento__nome'] for e in top_epis])
            context['chart_top_epis_data'] = json.dumps([e['total'] for e in top_epis])

        context['titulo_pagina'] = "Painel de Segurança do Trabalho"
        return context


# =============================================================================
# CRUD DE FUNÇÕES
# =============================================================================

class FuncaoListView(LoginRequiredMixin, AppPermissionMixin, SSTPermissionMixin, ViewFilialScopedMixin, ListView):
    app_label_required = _APP
    model = Funcao
    template_name = 'seguranca_trabalho/funcao_list.html'
    context_object_name = 'funcoes'
    paginate_by = 15
    permission_required = 'seguranca_trabalho.view_funcao'

    def get_queryset(self):
        queryset = super().get_queryset().prefetch_related('funcoes_cargo__cargo')
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(nome__icontains=query) |
                Q(descricao__icontains=query) |
                Q(funcoes_cargo__cargo__nome__icontains=query)
            ).distinct()
        return queryset.order_by('nome')


class FuncaoCreateView(LoginRequiredMixin, AppPermissionMixin, SSTPermissionMixin, FilialCreateMixin, HTMXModalFormMixin, CreateView):
    app_label_required = _APP
    model = Funcao
    form_class = FuncaoForm
    success_url = reverse_lazy('seguranca_trabalho:funcao_list')
    permission_required = 'seguranca_trabalho.add_funcao'

    def get_template_names(self):
        if self.request.htmx:
            return ['seguranca_trabalho/partials/base_modal.html']
        return ['seguranca_trabalho/funcao_form.html']


class FuncaoUpdateView(LoginRequiredMixin, AppPermissionMixin, SSTPermissionMixin, ViewFilialScopedMixin, HTMXModalFormMixin, UpdateView):
    app_label_required = _APP
    model = Funcao
    form_class = FuncaoForm
    success_url = reverse_lazy('seguranca_trabalho:funcao_list')
    permission_required = 'seguranca_trabalho.change_funcao'

    def form_valid(self, form):
        messages.success(self.request, f"Função '{form.instance.nome}' atualizada com sucesso.")
        return super().form_valid(form)

    def get_template_names(self):
        if self.request.htmx:
            return ['seguranca_trabalho/partials/base_modal.html']
        return ['seguranca_trabalho/funcao_form.html']


class FuncaoDeleteView(LoginRequiredMixin, AppPermissionMixin, SSTPermissionMixin, ViewFilialScopedMixin, DeleteView):
    app_label_required = _APP
    model = Funcao
    template_name = 'seguranca_trabalho/funcao_confirm_delete.html'
    success_url = reverse_lazy('seguranca_trabalho:funcao_list')
    permission_required = 'seguranca_trabalho.delete_funcao'
    context_object_name = 'object'

    def form_valid(self, form):
        messages.success(self.request, "Função excluída com sucesso.")
        return super().form_valid(form)


# =============================================================================
# CRUD DE ASSOCIAÇÕES CARGO-FUNÇÃO
# =============================================================================

class AssociacaoListView(LoginRequiredMixin, AppPermissionMixin, SSTPermissionMixin, ViewFilialScopedMixin, ListView):
    app_label_required = _APP
    model = CargoFuncao
    template_name = 'seguranca_trabalho/lista_associacoes.html'
    paginate_by = 20
    permission_required = 'seguranca_trabalho.view_cargofuncao'

    def get_queryset(self):
        # ✅ Usa super() para que ViewFilialScopedMixin filtre por filial
        qs = super().get_queryset().select_related('cargo', 'funcao')
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(
                Q(cargo__nome__icontains=q) |
                Q(funcao__nome__icontains=q)
            )
        return qs.order_by('cargo__nome')


class AssociacaoCreateView(LoginRequiredMixin, AppPermissionMixin, SSTPermissionMixin, FilialCreateMixin, CreateView):
    app_label_required = _APP
    model = CargoFuncao
    form_class = CargoFuncaoForm
    template_name = 'seguranca_trabalho/formulario_associacao.html'
    success_url = reverse_lazy('seguranca_trabalho:lista_associacoes')
    permission_required = 'seguranca_trabalho.add_cargofuncao'

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except IntegrityError:
            cargo = form.cleaned_data.get('cargo')
            funcao = form.cleaned_data.get('funcao')
            messages.error(
                self.request,
                f"A associação entre o cargo '{cargo}' e a função '{funcao}' já existe."
            )
            return self.form_invalid(form)


@login_required
@permission_required('seguranca_trabalho.delete_cargofuncao', raise_exception=True)
@require_POST
def desvincular_funcao_cargo(request, funcao_id, cargo_id):
    """Remove o vínculo entre um cargo e uma função via HTMX."""
    filial_id = request.session.get('active_filial_id')
    associacao = get_object_or_404(
        CargoFuncao,
        funcao_id=funcao_id,
        cargo_id=cargo_id,
        funcao__filial_id=filial_id
    )
    associacao.delete()
    messages.success(request, "Associação removida com sucesso.")
    return HttpResponse("")


# =============================================================================
# MATRIZ DE EPI POR FUNÇÃO
# =============================================================================

class ControleEPIPorFuncaoView(LoginRequiredMixin, AppPermissionMixin, SSTPermissionMixin, TemplateView):
    app_label_required = _APP
    permission_required = 'seguranca_trabalho.change_matrizepi'
    template_name = 'seguranca_trabalho/controle_epi_por_funcao.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        active_filial_id = request.session.get('active_filial_id')
        filial_atual = None

        if active_filial_id:
            try:
                filial_atual = Filial.objects.get(pk=active_filial_id)
            except Filial.DoesNotExist:
                messages.error(request, "A filial selecionada é inválida.")

        if not filial_atual:
            messages.warning(request, "Nenhuma filial selecionada.")
            context.update({
                'titulo_pagina': "Matriz de EPIs",
                'funcoes': [],
                'equipamentos': [],
                'matriz_data': {}
            })
            return context

        funcoes = Funcao.objects.filter(filial=filial_atual, ativo=True).order_by('nome')
        equipamentos = Equipamento.objects.filter(ativo=True).order_by('nome')
        dados_salvos = MatrizEPI.objects.filter(funcao__in=funcoes).select_related('funcao', 'equipamento')

        matriz_data = {}
        for item in dados_salvos:
            if item.funcao_id not in matriz_data:
                matriz_data[item.funcao_id] = {}
            matriz_data[item.funcao_id][item.equipamento_id] = item.frequencia_troca_meses

        context.update({
            'titulo_pagina': f"Matriz de EPIs - {filial_atual.nome}",
            'funcoes': funcoes,
            'equipamentos': equipamentos,
            'matriz_data': matriz_data
        })
        return context

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        active_filial_id = request.session.get('active_filial_id')
        if not active_filial_id:
            messages.error(request, "Sessão expirada ou filial não selecionada.")
            return redirect(request.path_info)

        funcoes_ids = list(Funcao.objects.filter(
            filial_id=active_filial_id, ativo=True
        ).values_list('id', flat=True))
        equipamentos_ids = list(Equipamento.objects.filter(ativo=True).values_list('id', flat=True))

        existentes = MatrizEPI.objects.filter(funcao_id__in=funcoes_ids)
        mapa_existentes = {(item.funcao_id, item.equipamento_id): item for item in existentes}

        entries_to_create = []
        entries_to_update = []
        submitted_keys = set()

        for key, value in request.POST.items():
            if key.startswith('freq_'):
                try:
                    _, funcao_id_str, equipamento_id_str = key.split('_')
                    funcao_id = int(funcao_id_str)
                    equipamento_id = int(equipamento_id_str)

                    if funcao_id not in funcoes_ids or equipamento_id not in equipamentos_ids:
                        continue

                    submitted_keys.add((funcao_id, equipamento_id))
                    frequencia = int(value) if value and value.isdigit() else 0

                    if frequencia <= 0:
                        continue

                    if (funcao_id, equipamento_id) in mapa_existentes:
                        item_existente = mapa_existentes[(funcao_id, equipamento_id)]
                        if item_existente.frequencia_troca_meses != frequencia:
                            item_existente.frequencia_troca_meses = frequencia
                            entries_to_update.append(item_existente)
                    else:
                        entries_to_create.append(
                            MatrizEPI(
                                funcao_id=funcao_id,
                                equipamento_id=equipamento_id,
                                filial_id=active_filial_id,
                                frequencia_troca_meses=frequencia
                            )
                        )
                except (ValueError, IndexError):
                    continue

        keys_to_delete = set(mapa_existentes.keys()) - submitted_keys
        pks_to_delete = [mapa_existentes[key].pk for key in keys_to_delete]

        if entries_to_create:
            MatrizEPI.objects.bulk_create(entries_to_create)
        if entries_to_update:
            MatrizEPI.objects.bulk_update(entries_to_update, ['frequencia_troca_meses'])
        if pks_to_delete:
            MatrizEPI.objects.filter(pk__in=pks_to_delete).delete()

        messages.success(request, "Matriz de EPIs salva com sucesso!")
        return redirect(request.path_info)


# =============================================================================
# RELATÓRIOS PDF/WORD
# =============================================================================

class RelatorioSSTPDFView(LoginRequiredMixin, AppPermissionMixin, SSTPermissionMixin, View):
    app_label_required = _APP
    permission_required = 'seguranca_trabalho.view_fichaepi'

    def get(self, request, *args, **kwargs):
        entregas = EntregaEPI.objects.for_request(request).select_related(
            'ficha__funcionario', 'equipamento'
        )
        context = {
            'data_emissao': timezone.now(),
            'entregas': entregas,
        }
        html_string = render_to_string('seguranca_trabalho/relatorio_geral_pdf.html', context)
        html = HTML(string=html_string, base_url=request.build_absolute_uri())
        pdf = html.write_pdf()
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="relatorio_sst.pdf"'
        return response


class ExportarFuncionariosPDFView(LoginRequiredMixin, AppPermissionMixin, SSTPermissionMixin, View):
    app_label_required = _APP
    permission_required = 'seguranca_trabalho.view_fichaepi'

    def get(self, request, *args, **kwargs):
        funcionarios = Funcionario.objects.for_request(request).select_related(
            'cargo', 'departamento'
        ).filter(status='ATIVO')

        context = {
            'funcionarios': funcionarios,
            'data_emissao': timezone.now().strftime('%d/%m/%Y às %H:%M'),
            'nome_filial': getattr(request.user, 'filial_ativa', None) or 'Geral'
        }
        html_string = render_to_string('departamento_pessoal/relatorio_funcionarios_pdf.html', context)
        html = HTML(string=html_string, base_url=request.build_absolute_uri())
        pdf_file = html.write_pdf()

        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="relatorio_funcionarios.pdf"'
        return response


class ExportarFuncionariosWordView(LoginRequiredMixin, AppPermissionMixin, SSTPermissionMixin, View):
    app_label_required = _APP
    permission_required = 'seguranca_trabalho.view_fichaepi'

    def get(self, request, *args, **kwargs):
        funcionarios = Funcionario.objects.for_request(request).select_related(
            'cargo', 'departamento'
        ).filter(status='ATIVO')

        document = Document()
        document.add_heading('Relatório de Colaboradores', level=1)
        document.add_paragraph(f'Gerado em: {timezone.now().strftime("%d/%m/%Y às %H:%M")}')
        document.add_paragraph()

        table = document.add_table(rows=1, cols=4)
        table.style = 'Table Grid'
        hdr = table.rows[0].cells
        hdr[0].text, hdr[1].text, hdr[2].text, hdr[3].text = 'Nome', 'Cargo', 'Departamento', 'Admissão'

        for f in funcionarios:
            row = table.add_row().cells
            row[0].text = f.nome_completo
            row[1].text = f.cargo.nome if f.cargo else '-'
            row[2].text = f.departamento.nome if f.departamento else '-'
            row[3].text = f.data_admissao.strftime('%d/%m/%Y') if f.data_admissao else '-'

        buffer = io.BytesIO()
        document.save(buffer)
        buffer.seek(0)

        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        response['Content-Disposition'] = 'attachment; filename="relatorio_funcionarios.docx"'
        return response


# =============================================================================
# REDIRECT PARA MINHA FICHA
# =============================================================================

@login_required
def minha_ficha_redirect_view(request):
    """Redireciona o usuário para sua própria ficha de EPI."""
    try:
        funcionario_obj = get_object_or_404(Funcionario, usuario=request.user)
    except Http404:
        messages.error(request, "Seu usuário não está associado a um perfil de funcionário.")
        return redirect('usuario:profile')

    try:
        ficha = get_object_or_404(FichaEPI, funcionario=funcionario_obj)
    except Http404:
        messages.error(request, "Você não possui uma ficha de EPI.")
        return redirect('usuario:profile')

    return redirect('seguranca_trabalho:ficha_detail', pk=ficha.pk)

