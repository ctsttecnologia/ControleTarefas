
# seguranca_trabalho/views.py
import base64
import logging
from pathlib import Path
from django.conf import settings
import io
import json
from datetime import datetime, timedelta
from django.db.models import Sum, Value, IntegerField
from django.db.models.functions import Coalesce
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q, Count, Func
from django.http import Http404, HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView
)
from django.views.generic.edit import FormMixin
from django.views.decorators.http import require_POST
from docx import Document
from weasyprint import HTML, default_url_fetcher

from core.mixins import (
    FilialCreateMixin, HTMXModalFormMixin, SSTPermissionMixin,
    ViewFilialScopedMixin, TecnicoScopeMixin
)
from departamento_pessoal.models import Funcionario
from usuario.models import Filial
from usuario.views import StaffRequiredMixin
from .forms import (
    AssinaturaEntregaForm, AssinaturaTermoForm, EntregaEPIForm, EquipamentoForm,
    FichaEPIForm, FuncaoForm, CargoFuncaoForm
)
from .models import (
    EntregaEPI, Equipamento, FichaEPI, Funcao, MatrizEPI, CargoFuncao, MovimentacaoEstoque
)
from django.utils.safestring import mark_safe


logger = logging.getLogger(__name__)


def custom_url_fetcher(url):
    """Permite que o WeasyPrint acesse arquivos de media locais."""
    if url.startswith(settings.MEDIA_URL):
        path = (settings.MEDIA_ROOT / url[len(settings.MEDIA_URL):]).as_posix()
        return default_url_fetcher(f'file://{path}')
    return default_url_fetcher(url)


# =============================================================================
# CRUD DE EQUIPAMENTOS
# =============================================================================

class EquipamentoListView(LoginRequiredMixin, SSTPermissionMixin, ViewFilialScopedMixin, ListView):
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
            
            # Calcula estoque para cada equipamento da página atual
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


class EquipamentoDetailView(LoginRequiredMixin, SSTPermissionMixin, ViewFilialScopedMixin, DetailView):
    model = Equipamento
    template_name = 'seguranca_trabalho/equipamento_detail.html'
    context_object_name = 'equipamento'
    permission_required = 'seguranca_trabalho.view_equipamento'


class EquipamentoCreateView(LoginRequiredMixin, SSTPermissionMixin, FilialCreateMixin, CreateView):
    model = Equipamento
    form_class = EquipamentoForm
    template_name = 'seguranca_trabalho/equipamento_form.html'
    success_url = reverse_lazy('seguranca_trabalho:equipamento_list')
    permission_required = 'seguranca_trabalho.add_equipamento'

    def form_valid(self, form):
        messages.success(self.request, f"Equipamento '{form.instance.nome}' cadastrado com sucesso!")
        return super().form_valid(form)


class EquipamentoUpdateView(LoginRequiredMixin, SSTPermissionMixin, ViewFilialScopedMixin, UpdateView):
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


class EquipamentoDeleteView(LoginRequiredMixin, SSTPermissionMixin, ViewFilialScopedMixin, DeleteView):
    model = Equipamento
    template_name = 'seguranca_trabalho/confirm_delete.html'
    success_url = reverse_lazy('seguranca_trabalho:equipamento_list')
    context_object_name = 'object'
    permission_required = 'seguranca_trabalho.delete_equipamento'

    def form_valid(self, form):
        messages.success(self.request, "Equipamento excluído com sucesso!")
        return super().form_valid(form)


# =============================================================================
# CRUD DE FICHAS DE EPI
# =============================================================================

class FichaEPIListView(LoginRequiredMixin, SSTPermissionMixin, TecnicoScopeMixin, ViewFilialScopedMixin, ListView):
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


class FichaEPICreateView(LoginRequiredMixin, SSTPermissionMixin, FilialCreateMixin, CreateView):
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
        messages.success(self.request, "Ficha de EPI criada com sucesso!")
        return super().form_valid(form)


class FichaEPIDetailView(LoginRequiredMixin, SSTPermissionMixin, TecnicoScopeMixin, ViewFilialScopedMixin, FormMixin, DetailView):
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
        nova_entrega = form.save(commit=False)
        nova_entrega.ficha = self.object
        nova_entrega.filial = self.object.filial
        nova_entrega.save()
        messages.success(self.request, "Nova entrega de EPI registrada com sucesso!")
        return redirect(self.get_success_url())


class FichaEPIUpdateView(LoginRequiredMixin, SSTPermissionMixin, ViewFilialScopedMixin, UpdateView):
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


class FichaEPIDeleteView(LoginRequiredMixin, SSTPermissionMixin, ViewFilialScopedMixin, DeleteView):
    model = FichaEPI
    template_name = 'seguranca_trabalho/confirm_delete.html'
    success_url = reverse_lazy('seguranca_trabalho:ficha_list')
    context_object_name = 'object'
    permission_required = 'seguranca_trabalho.delete_fichaepi'


# =============================================================================
# AÇÕES DE ENTREGA (Assinatura, Devolução)
# =============================================================================

class AssinarEntregaView(LoginRequiredMixin, SSTPermissionMixin, TecnicoScopeMixin, ViewFilialScopedMixin, UpdateView):
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

        # 1. Assinatura via signature_pad (canvas → base64 no POST)
        assinatura_base64 = self.request.POST.get('assinatura_base64', '').strip()
        if assinatura_base64:
            entrega.assinatura_recebimento = assinatura_base64

        # 2. Assinatura via upload de imagem (vem no FILES)
        if 'assinatura_imagem' in self.request.FILES:
            entrega.assinatura_imagem = self.request.FILES['assinatura_imagem']

        # 3. Marca data da assinatura
        entrega.data_assinatura = timezone.now()
        entrega.save()

        messages.success(self.request, "Assinatura registrada com sucesso!")
        return redirect(self.get_success_url())


class RegistrarDevolucaoView(LoginRequiredMixin, SSTPermissionMixin, TecnicoScopeMixin, View):
    permission_required = 'seguranca_trabalho.change_entregaepi'
    http_method_names = ['post']
    tecnico_scope_lookup = 'ficha__funcionario__usuario'

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        filial_id = request.session.get('active_filial_id')
        qs = EntregaEPI.objects.all()
        qs = self.scope_tecnico_queryset(qs)
        entrega = get_object_or_404(qs, pk=kwargs.get('pk'), filial_id=filial_id)

        if entrega.data_devolucao:
            messages.warning(request, f"O EPI '{entrega.equipamento.nome}' já foi devolvido.")
        else:
            entrega.data_devolucao = timezone.now().date()
            entrega.recebedor_devolucao = request.user
            entrega.save()
            messages.success(request, f"Devolução do EPI '{entrega.equipamento.nome}' registrada.")

        return redirect('seguranca_trabalho:ficha_detail', pk=entrega.ficha.pk)


# =============================================================================
# RELATÓRIOS E PAINÉIS
# =============================================================================

class GerarFichaPDFView(LoginRequiredMixin, SSTPermissionMixin, TecnicoScopeMixin, ViewFilialScopedMixin, DetailView):
    model = FichaEPI
    permission_required = 'seguranca_trabalho.view_fichaepi'
    tecnico_scope_lookup = 'funcionario__usuario'

    @staticmethod
    def _processar_assinatura(entrega):
        """Retorna data URI da assinatura ou None."""
        # 1. TextField do signature_pad
        if entrega.assinatura_recebimento:
            sig = entrega.assinatura_recebimento.strip()
            if sig.startswith('data:image'):
                return mark_safe(sig)
            if len(sig) > 100:
                return mark_safe(f'data:image/png;base64,{sig}')

        # 2. ImageField (upload de arquivo)
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
                print(f"[PDF] ❌ Erro assinatura_imagem #{entrega.pk}: {e}")

        return None

    def _get_logo_base64(self, filial):
        """Logo da filial ou fallback estático."""
        # Filial
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
                print(f"[PDF] ❌ Erro logo filial: {e}")

        # Fallback estático
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

        print(f"\n[PDF] ══════════════════════════════════════")
        print(f"[PDF] Gerando ficha: {ficha.funcionario.nome_completo}")

        entregas = EntregaEPI.objects.filter(
            ficha=ficha
        ).select_related('equipamento').order_by('data_entrega')

        for entrega in entregas:
            entrega.assinatura_base64 = self._processar_assinatura(entrega)
            status = '✅ CONVERTIDO' if entrega.assinatura_base64 else '— sem assinatura'
            print(f"[PDF]   Entrega #{entrega.pk}: {status}")

        logo_base64 = self._get_logo_base64(ficha.filial)
        print(f"[PDF]   Logo: {'✅' if logo_base64 else '❌ usando texto'}")

        # Assinatura do funcionário no termo
        assinatura_funcionario = None
        if ficha.assinatura_funcionario:
            sig = ficha.assinatura_funcionario.strip()
            if sig.startswith('data:image'):
                assinatura_funcionario = mark_safe(sig)
            elif len(sig) > 100:
                assinatura_funcionario = mark_safe(f'data:image/png;base64,{sig}')

        print(f"[PDF]   Assinatura termo: {'✅' if assinatura_funcionario else '— não assinado'}")

        context = {
            'ficha': ficha,
            'entregas': entregas,
            'data_emissao': timezone.now(),
            'logo_base64': logo_base64,
            'assinatura_funcionario': assinatura_funcionario,  # ← NOVO
        }


        html_string = render_to_string(
            'seguranca_trabalho/ficha_pdf_template.html', context
        )

        # Debug: verificar presença das imagens no HTML
        img_count = html_string.count('data:image')
        print(f"[PDF]   data:image no HTML final: {img_count}")

        if settings.DEBUG:
            debug_path = Path(settings.BASE_DIR) / 'debug_ficha.html'
            debug_path.write_text(html_string, encoding='utf-8')
            print(f"[PDF]   Debug HTML: {debug_path}")

        html = HTML(
            string=html_string,
            base_url=request.build_absolute_uri(),
            url_fetcher=custom_url_fetcher,
        )
        pdf = html.write_pdf()
        print(f"[PDF] ✅ PDF gerado ({len(pdf)} bytes)")
        print(f"[PDF] ══════════════════════════════════════\n")

        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="ficha_epi_{ficha.funcionario.matricula}.pdf"'
        )
        return response


class AssinarTermoView(LoginRequiredMixin, SSTPermissionMixin, TecnicoScopeMixin, ViewFilialScopedMixin, UpdateView):
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
    

class DashboardSSTView(LoginRequiredMixin, SSTPermissionMixin, TecnicoScopeMixin, ViewFilialScopedMixin, TemplateView):
    template_name = 'seguranca_trabalho/dashboard.html'
    permission_required = 'seguranca_trabalho.view_fichaepi'
    tecnico_scope_lookup = 'funcionario__usuario'

    def _is_tecnico(self):
        """Verifica se o usuário atual é um técnico."""
        user = self.request.user
        if hasattr(user, 'is_tecnico'):
            return user.is_tecnico
        return not user.is_staff and not user.is_superuser

    def get_queryset_base(self, model_class):
        """Filtra um modelo pela filial ativa."""
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
            logger.error(f"Erro no DashboardSST: {e}")
            equipamentos_da_filial = Equipamento.objects.none()
            fichas_da_filial = FichaEPI.objects.none()
            entregas_da_filial = EntregaEPI.objects.none()
            matriz_da_filial = MatrizEPI.objects.none()

        if self._is_tecnico():
            equipamentos_da_filial = equipamentos_da_filial.none()
            matriz_da_filial = matriz_da_filial.none()
            fichas_da_filial = fichas_da_filial.filter(funcionario__usuario=self.request.user)
            entregas_da_filial = entregas_da_filial.filter(ficha__funcionario__usuario=self.request.user)

        context['total_equipamentos_ativos'] = equipamentos_da_filial.filter(ativo=True).count()
        context['fichas_ativas'] = fichas_da_filial.filter(funcionario__status='ATIVO').count()
        context['entregas_pendentes_assinatura'] = entregas_da_filial.filter(
            data_devolucao__isnull=True,
            data_assinatura__isnull=True
        ).count()

        # EPIs vencendo em 30 dias
        today = timezone.now().date()
        thirty_days = today + timedelta(days=30)
        entregas_ativas = entregas_da_filial.filter(
            data_devolucao__isnull=True,
            data_entrega__isnull=False
        ).select_related('equipamento')

        epis_vencendo = 0
        for entrega in entregas_ativas:
            if entrega.equipamento.vida_util_dias:
                vencimento = entrega.data_entrega + timedelta(days=entrega.equipamento.vida_util_dias)
                if today <= vencimento <= thirty_days:
                    epis_vencendo += 1

        context['epis_vencendo_em_30_dias'] = epis_vencendo

        # Dados para gráficos
        matriz_data = matriz_da_filial.values('funcao__nome').annotate(
            num_epis=Count('equipamento')
        ).order_by('-num_epis')[:10]

        if matriz_data:
            context['matriz_labels'] = json.dumps([m['funcao__nome'] for m in matriz_data])
            context['matriz_data'] = json.dumps([m['num_epis'] for m in matriz_data])

        context['titulo_pagina'] = "Painel de Segurança do Trabalho"
        return context


# =============================================================================
# CRUD DE FUNÇÕES
# =============================================================================

class FuncaoListView(LoginRequiredMixin, SSTPermissionMixin, ViewFilialScopedMixin, ListView):
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


class FuncaoCreateView(LoginRequiredMixin, SSTPermissionMixin, FilialCreateMixin, HTMXModalFormMixin, CreateView):
    model = Funcao
    form_class = FuncaoForm
    success_url = reverse_lazy('seguranca_trabalho:funcao_list')
    permission_required = 'seguranca_trabalho.add_funcao'

    def form_valid(self, form):
        messages.success(self.request, f"Função '{form.instance.nome}' criada com sucesso.")
        return super().form_valid(form)

    def get_template_names(self):
        if self.request.htmx:
            return ['seguranca_trabalho/partials/base_modal.html']
        return ['seguranca_trabalho/funcao_form.html']


class FuncaoUpdateView(LoginRequiredMixin, SSTPermissionMixin, ViewFilialScopedMixin, HTMXModalFormMixin, UpdateView):
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


class FuncaoDeleteView(LoginRequiredMixin, SSTPermissionMixin, ViewFilialScopedMixin, DeleteView):
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

class AssociacaoListView(LoginRequiredMixin, SSTPermissionMixin, ViewFilialScopedMixin, ListView):
    model = CargoFuncao
    template_name = 'seguranca_trabalho/lista_associacoes.html'
    paginate_by = 20
    permission_required = 'seguranca_trabalho.view_cargofuncao'

    def get_queryset(self):
        qs = CargoFuncao.objects.select_related('cargo', 'funcao').all()
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(
                Q(cargo__nome__icontains=q) |
                Q(funcao__nome__icontains=q)
            )
        return qs.order_by('cargo__nome')


class AssociacaoCreateView(LoginRequiredMixin, SSTPermissionMixin, FilialCreateMixin, CreateView):
    model = CargoFuncao
    form_class = CargoFuncaoForm
    template_name = 'seguranca_trabalho/formulario_associacao.html'
    success_url = reverse_lazy('seguranca_trabalho:lista_associacoes')
    permission_required = 'seguranca_trabalho.add_cargofuncao'

    def form_valid(self, form):
        messages.success(self.request, "Associação criada com sucesso!")
        return super().form_valid(form)


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

class ControleEPIPorFuncaoView(LoginRequiredMixin, SSTPermissionMixin, TemplateView):
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

class RelatorioSSTPDFView(LoginRequiredMixin, SSTPermissionMixin, View):
    permission_required = 'seguranca_trabalho.view_fichaepi'

    def get(self, request, *args, **kwargs):
        # CORRIGIDO: Filtrar por filial
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


class ExportarFuncionariosPDFView(LoginRequiredMixin, StaffRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        funcionarios = Funcionario.objects.for_request(request).select_related(
            'cargo', 'departamento'
        ).filter(status='ATIVO')

        context = {
            'funcionarios': funcionarios,
            'data_emissao': timezone.now().strftime('%d/%m/%Y às %H:%M'),
            'nome_filial': getattr(request.user, 'filial', None) or 'Geral'
        }
        html_string = render_to_string('departamento_pessoal/relatorio_funcionarios_pdf.html', context)
        html = HTML(string=html_string, base_url=request.build_absolute_uri())
        pdf_file = html.write_pdf()

        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="relatorio_funcionarios.pdf"'
        return response


class ExportarFuncionariosWordView(LoginRequiredMixin, StaffRequiredMixin, View):
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

