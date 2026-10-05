
# treinamentos/views.py

import io
import json
import logging
import os
import random
import traceback
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

import qrcode
import qrcode.image.svg
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Count, FloatField, ProtectedError, Q, Sum
from django.db.models.functions import Coalesce
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import get_template
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.safestring import mark_safe
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView,
)
from num2words import num2words

from core.mixins import TecnicoScopeMixin, ViewFilialScopedMixin

from . import treinamento_generators
from .forms import ParticipanteFormSet, TipoCursoForm, TreinamentoForm
from .models import (
    AlternativaEAD, AulaEAD, AvaliacaoEAD, Assinatura, CertificadoEAD,
    CursoEAD, GabaritoCertificado, MatriculaEAD, Participante,
    ProgressoAulaEAD, RespostaAlunoEAD, TentativaAvaliacaoEAD, TipoCurso,
    Treinamento,
)

logger = logging.getLogger(__name__)

try:
    from weasyprint import CSS, HTML
    WEASYPRINT_DISPONIVEL = True
except ImportError:
    WEASYPRINT_DISPONIVEL = False
    logger.warning("WeasyPrint não instalado. Geração de PDF falhará.")


# =============================================================================
# HELPERS
# =============================================================================

def _get_funcionario(user):
    """Retorna o Funcionario vinculado ao usuário ou None."""
    try:
        return user.funcionario
    except (ObjectDoesNotExist, AttributeError):
        return None


def _montar_gabarito(tentativa):
    """Monta a lista de respostas/gabarito de uma tentativa."""
    respostas = tentativa.respostas_ead.select_related(
        "questao", "alternativa_escolhida",
    ).prefetch_related("questao__alternativas_ead").order_by("questao__ordem")

    gabarito = []
    for resp in respostas:
        alternativas = list(resp.questao.alternativas_ead.all())
        correta = next((a for a in alternativas if a.correta), None)
        gabarito.append({
            "questao": resp.questao,
            "alternativas": alternativas,
            "escolhida": resp.alternativa_escolhida,
            "correta_obj": correta,
            "acertou": bool(
                resp.alternativa_escolhida and resp.alternativa_escolhida.correta
            ),
        })
    return gabarito


class _RateLimitPublicMixin:
    """Rate-limit por IP para endpoints públicos (anti-scraping)."""
    RATE_LIMIT_KEY_PREFIX = "ratelimit:cert"
    RATE_LIMIT_MAX = 30
    RATE_LIMIT_WINDOW = 60

    def dispatch(self, request, *args, **kwargs):
        ip = (
            request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
            or request.META.get("REMOTE_ADDR", "unknown")
        )
        key = f"{self.RATE_LIMIT_KEY_PREFIX}:{ip}"
        count = cache.get(key, 0)
        if count >= self.RATE_LIMIT_MAX:
            logger.warning("Rate-limit cert validation: IP=%s", ip)
            return HttpResponse("Rate-limit excedido", status=429)
        cache.set(key, count + 1, timeout=self.RATE_LIMIT_WINDOW)
        return super().dispatch(request, *args, **kwargs)


# =============================================================================
# TREINAMENTO (CRUD)
# =============================================================================

class TreinamentoFormsetMixin:
    """Fonte única de lógica para form principal + formset de participantes."""
    success_message = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'form_participantes' not in context:
            if self.request.POST:
                context['form_participantes'] = ParticipanteFormSet(
                    self.request.POST, instance=self.object)
            else:
                context['form_participantes'] = ParticipanteFormSet(instance=self.object)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object() if isinstance(self, UpdateView) else None
        form = self.get_form()
        form_participantes = ParticipanteFormSet(request.POST, instance=self.object)

        if form.is_valid() and form_participantes.is_valid():
            return self.form_valid(form, form_participantes)
        return self.form_invalid(form, form_participantes)

    def form_valid(self, form, form_participantes):
        with transaction.atomic():
            form.instance.filial = self.request.user.filial_ativa
            self.object = form.save()
            form_participantes.instance = self.object
            form_participantes.save()

        # Sem super().form_valid(): evita salvar o form uma segunda vez.
        if self.success_message:
            messages.success(self.request, self.success_message)
        return redirect(self.get_success_url())

    def form_invalid(self, form, form_participantes):
        return self.render_to_response(
            self.get_context_data(form=form, form_participantes=form_participantes)
        )


class CriarTreinamentoView(LoginRequiredMixin, PermissionRequiredMixin,
                           TreinamentoFormsetMixin, CreateView):
    model = Treinamento
    form_class = TreinamentoForm
    template_name = 'treinamentos/criar_treinamento.html'
    success_url = reverse_lazy('treinamentos:treinamento_list')
    success_message = "✅ Treinamento cadastrado com sucesso!"
    permission_required = 'treinamentos.add_treinamento'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastrar Novo Treinamento'
        return context


class TreinamentoListView(LoginRequiredMixin, ViewFilialScopedMixin, TecnicoScopeMixin, ListView):
    """Lista treinamentos (exclui tipos Online, gerenciados pelo EAD)."""
    model = Treinamento
    template_name = 'treinamentos/treinamento_list.html'
    context_object_name = 'treinamentos'
    paginate_by = 30
    tecnico_scope_lookup = 'participantes__funcionario'

    def get_queryset(self):
        queryset = (
            super().get_queryset()
            .select_related('tipo_curso')
            .exclude(tipo_curso__modalidade='O')
        )

        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        tipo_curso = self.request.GET.get('tipo_curso')
        if tipo_curso:
            queryset = queryset.filter(tipo_curso_id=tipo_curso)

        busca = self.request.GET.get('q')
        if busca:
            queryset = queryset.filter(
                Q(nome__icontains=busca) |
                Q(local__icontains=busca) |
                Q(palestrante__icontains=busca)
            )
        return queryset.order_by('-data_inicio')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tipos_curso'] = TipoCurso.objects.filter(ativo=True).exclude(modalidade='O')
        context['total_treinamentos'] = Treinamento.objects.exclude(
            tipo_curso__modalidade='O').count()
        return context


class EditarTreinamentoView(LoginRequiredMixin, PermissionRequiredMixin,
                            TreinamentoFormsetMixin, UpdateView):
    model = Treinamento
    form_class = TreinamentoForm
    template_name = 'treinamentos/criar_treinamento.html'
    success_message = "🔄 Treinamento atualizado com sucesso!"
    permission_required = 'treinamentos.change_treinamento'
    tecnico_scope_lookup = 'participantes__funcionario'

    def get_success_url(self):
        return reverse('treinamentos:detalhe_treinamento', kwargs={'pk': self.object.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Treinamento'
        return context


class DetalheTreinamentoView(LoginRequiredMixin, PermissionRequiredMixin,
                             TecnicoScopeMixin, DetailView):
    model = Treinamento
    template_name = 'treinamentos/detalhe_treinamento.html'
    permission_required = 'treinamentos.view_treinamento'
    tecnico_scope_lookup = 'participantes__funcionario'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['participantes'] = self.object.participantes.select_related('funcionario')
        return context


class ExcluirTreinamentoView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Treinamento
    permission_required = 'treinamentos.delete_treinamento'
    success_url = reverse_lazy('treinamentos:treinamento_list')
    tecnico_scope_lookup = 'participantes__funcionario'

    def get(self, request, *args, **kwargs):
        # Exclusão só via POST (modal)
        return HttpResponseRedirect(
            reverse('treinamentos:detalhe_treinamento', kwargs={'pk': self.get_object().pk})
        )

    def form_valid(self, form):
        nome = self.object.nome
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                f'Não é possível excluir "{nome}": há registros vinculados.'
            )
            return redirect('treinamentos:detalhe_treinamento', pk=self.object.pk)
        messages.success(self.request, f'Treinamento "{nome}" excluído com sucesso.')
        return response


# =============================================================================
# TIPO DE CURSO (CRUD)
# =============================================================================

class TipoCursoNomeUnicoMixin:
    """
    Garante nome único por filial ignorando o escopo do FilialManager
    (usa _base_manager), evitando IntegrityError no banco.
    """

    def form_valid(self, form):
        filial = form.instance.filial or self.request.user.filial_ativa
        nome = form.cleaned_data['nome'].strip()

        qs = TipoCurso._base_manager.filter(nome__iexact=nome, filial=filial)
        if form.instance.pk:
            qs = qs.exclude(pk=form.instance.pk)

        if qs.exists():
            form.add_error('nome', 'Já existe um tipo de curso com este nome.')
            return self.form_invalid(form)

        form.instance.nome = nome
        return super().form_valid(form)


class TipoCursoListView(LoginRequiredMixin, PermissionRequiredMixin,
                        ViewFilialScopedMixin, ListView):
    model = TipoCurso
    template_name = 'treinamentos/lista_tipo_curso.html'
    context_object_name = 'cursos'
    paginate_by = 30
    permission_required = 'treinamentos.view_tipocurso'

    def get_queryset(self):
        queryset = super().get_queryset().order_by('nome')

        status = self.request.GET.get('status')
        if status == 'ativo':
            queryset = queryset.filter(ativo=True)
        elif status == 'inativo':
            queryset = queryset.filter(ativo=False)

        busca = self.request.GET.get('busca')
        if busca:
            queryset = queryset.filter(
                Q(nome__icontains=busca) |
                Q(descricao_no_certificado__icontains=busca)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_ativos'] = self.get_queryset().filter(ativo=True).count()
        return context


class CriarTipoCursoView(LoginRequiredMixin, PermissionRequiredMixin,
                         TipoCursoNomeUnicoMixin, SuccessMessageMixin, CreateView):
    model = TipoCurso
    form_class = TipoCursoForm
    template_name = 'treinamentos/criar_tipo_curso.html'
    success_url = reverse_lazy('treinamentos:lista_tipos_curso')
    permission_required = 'treinamentos.add_tipocurso'
    success_message = "✅ Tipo de curso cadastrado com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastrar Tipo de Curso'
        return context

    def form_valid(self, form):
        form.instance.filial = self.request.user.filial_ativa
        return super().form_valid(form)


class EditarTipoCursoView(LoginRequiredMixin, PermissionRequiredMixin,
                          TipoCursoNomeUnicoMixin, SuccessMessageMixin, UpdateView):
    model = TipoCurso
    form_class = TipoCursoForm
    template_name = 'treinamentos/editar_tipo_curso.html'
    success_url = reverse_lazy('treinamentos:lista_tipos_curso')
    permission_required = 'treinamentos.change_tipocurso'
    success_message = "Tipo de curso atualizado com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Tipo de Curso'
        return context


class ExcluirTipoCursoView(LoginRequiredMixin, PermissionRequiredMixin,
                           SuccessMessageMixin, DeleteView):
    model = TipoCurso
    template_name = 'treinamentos/excluir_tipo_curso.html'
    success_url = reverse_lazy('treinamentos:lista_tipos_curso')
    permission_required = 'treinamentos.delete_tipocurso'
    success_message = "Tipo de curso excluído com sucesso!"

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                "Não é possível excluir: há treinamentos ou cursos EAD usando este tipo. "
                "Desative-o em vez de excluir."
            )
            return redirect(self.success_url)


# =============================================================================
# RELATÓRIOS
# =============================================================================

class RelatorioTreinamentosView(LoginRequiredMixin, PermissionRequiredMixin,
                                ViewFilialScopedMixin, TecnicoScopeMixin, ListView):
    model = Treinamento
    template_name = 'treinamentos/relatorio_treinamentos.html'
    context_object_name = 'object_list'
    paginate_by = 30
    permission_required = 'treinamentos.ver_relatorios'
    tecnico_scope_lookup = 'participantes__funcionario'

    def get_queryset(self):
        queryset = super().get_queryset().select_related('tipo_curso', 'responsavel')

        ano = self.request.GET.get('ano')
        if ano:
            queryset = queryset.filter(data_inicio__year=ano)

        tipo_curso_id = self.request.GET.get('tipo_curso')
        if tipo_curso_id:
            queryset = queryset.filter(tipo_curso_id=tipo_curso_id)

        return queryset.order_by('-data_inicio')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['anos'] = Treinamento.objects.dates('data_inicio', 'year', order='DESC')
        context['tipos_curso'] = TipoCurso.objects.filter(ativo=True).order_by('nome')
        context['current_ano'] = self.request.GET.get('ano')
        context['current_tipo_curso'] = self.request.GET.get('tipo_curso')
        return context


class RelatorioTreinamentoWordView(LoginRequiredMixin, PermissionRequiredMixin,
                                   TecnicoScopeMixin, View):
    """Relatório de um treinamento em .docx."""
    permission_required = 'treinamentos.view_treinamento'
    tecnico_scope_lookup = 'participantes__funcionario'

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        try:
            base_qs = Treinamento.objects.select_related(
                'tipo_curso', 'responsavel'
            ).prefetch_related('participantes__funcionario')
            scoped_qs = self.scope_tecnico_queryset(base_qs)
            treinamento = get_object_or_404(scoped_qs, pk=pk)

            caminho_logo = os.path.join(settings.MEDIA_ROOT, 'imagens', 'logocetest.png')
            if not os.path.exists(caminho_logo):
                logger.warning("Logomarca não encontrada em %s; relatório sem logo.", caminho_logo)
                caminho_logo = None

            buffer = treinamento_generators.gerar_relatorio_word(treinamento, caminho_logo)

            response = HttpResponse(
                buffer,
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            nome_arquivo = ''.join(
                c for c in treinamento.nome if c.isalnum() or c in (' ', '_')
            ).rstrip()
            response['Content-Disposition'] = (
                f'attachment; filename="relatorio_{nome_arquivo[:30]}.docx"'
            )
            return response

        except Http404:
            messages.error(request, "Treinamento não encontrado ou sem permissão de acesso.")
            return redirect('treinamentos:treinamento_list')

        except Exception:
            logger.exception("Erro ao gerar relatório Word (treinamento %s)", pk)
            messages.error(request, "Ocorreu um erro inesperado ao gerar o relatório Word.")
            return redirect('treinamentos:detalhe_treinamento', pk=pk)


class RelatorioGeralExcelView(LoginRequiredMixin, PermissionRequiredMixin,
                              ViewFilialScopedMixin, View):
    """Relatório geral de treinamentos em .xlsx."""
    permission_required = 'treinamentos.ver_relatorios'

    def get(self, request, *args, **kwargs):
        list_view = RelatorioTreinamentosView()
        list_view.request = request
        list_view.args = args
        list_view.kwargs = kwargs
        queryset = list_view.get_queryset()

        try:
            buffer = treinamento_generators.gerar_relatorio_excel(queryset)
            response = HttpResponse(
                buffer,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            data_hoje = datetime.now().strftime('%Y-%m-%d')
            response['Content-Disposition'] = (
                f'attachment; filename="relatorio_geral_treinamentos_{data_hoje}.xlsx"'
            )
            return response
        except Exception:
            logger.exception("Erro ao gerar relatório Excel")
            messages.error(request, "Ocorreu um erro ao gerar o relatório Excel.")
            return redirect('treinamentos:relatorio_treinamentos')


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


class DashboardView(LoginRequiredMixin, PermissionRequiredMixin, TecnicoScopeMixin, TemplateView):
    template_name = 'treinamentos/dashboard.html'
    permission_required = 'treinamentos.ver_relatorios'
    tecnico_scope_lookup = 'participantes__funcionario'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        base_queryset = self.scope_tecnico_queryset(Treinamento.objects.all())

        area_map = dict(TipoCurso.AREA_CHOICES)
        status_map = dict(Treinamento.STATUS_CHOICES)
        modalidade_map = dict(TipoCurso.MODALIDADE_CHOICES)

        # --- Presencial ---
        area_data_db = base_queryset.values('tipo_curso__area').annotate(total=Count('id'))
        treinamentos_por_area = [
            {'nome_legivel': area_map.get(i['tipo_curso__area'], i['tipo_curso__area']),
             'total': i['total']}
            for i in area_data_db
        ]

        status_data_db = base_queryset.values('status').annotate(total=Count('id'))
        status_treinamentos = [
            {'nome_legivel': status_map.get(i['status'], i['status']), 'total': i['total']}
            for i in status_data_db
        ]

        modalidade_data_db = base_queryset.values('tipo_curso__modalidade').annotate(total=Count('id'))
        treinamentos_por_modalidade = [
            {'nome_legivel': modalidade_map.get(i['tipo_curso__modalidade'],
                                                i['tipo_curso__modalidade']),
             'total': i['total']}
            for i in modalidade_data_db
        ]

        custo_data_db = base_queryset.values('tipo_curso__area').annotate(
            total=Coalesce(Sum('custo'), 0.0, output_field=FloatField())
        )
        custo_por_area = [
            {'nome_legivel': area_map.get(i['tipo_curso__area'], i['tipo_curso__area']),
             'total': i['total']}
            for i in custo_data_db
        ]

        # --- EAD ---
        ead_total_cursos = CursoEAD.objects.filter(status='publicado').count()
        ead_total_matriculas = MatriculaEAD.objects.count()
        ead_em_andamento = MatriculaEAD.objects.filter(status='em_andamento').count()
        ead_certificados = CertificadoEAD.objects.count()

        ead_status_map = dict(MatriculaEAD._meta.get_field('status').choices)
        ead_status_chart = [
            {
                'status': i['status'],
                'nome_legivel': ead_status_map.get(i['status'], i['status']),
                'total': i['total'],
            }
            for i in MatriculaEAD.objects.values('status')
            .annotate(total=Count('id')).order_by('-total')
        ]
        ead_top_cursos = list(
            CursoEAD.objects.filter(status='publicado')
            .annotate(total=Count('matriculas_ead'))
            .filter(total__gt=0)
            .order_by('-total')
            .values('titulo', 'total')[:10]
        )

        dashboard_data = {
            'area': treinamentos_por_area,
            'status': status_treinamentos,
            'modalidade': treinamentos_por_modalidade,
            'custo': custo_por_area,
            'ead_status': ead_status_chart,
            'ead_top_cursos': ead_top_cursos,
        }

        total_custo = base_queryset.aggregate(
            total=Coalesce(Sum('custo'), 0.0, output_field=FloatField())
        )['total']

        context.update({
            'total_treinamentos': base_queryset.count(),
            'total_participantes': Participante.objects.filter(
                treinamento__in=base_queryset).count(),
            'total_custo': total_custo,
            'em_andamento': base_queryset.filter(status='A').count(),
            'treinamentos_recentes': base_queryset.select_related(
                'tipo_curso').order_by('-data_inicio')[:5],
            'ead_total_cursos': ead_total_cursos,
            'ead_total_matriculas': ead_total_matriculas,
            'ead_em_andamento': ead_em_andamento,
            'ead_certificados': ead_certificados,
            'dashboard_data_json': json.dumps(dashboard_data, cls=DecimalEncoder),
        })
        return context


# =============================================================================
# CERTIFICADO PRESENCIAL / ASSINATURA
# =============================================================================

class VerificarCertificadoView(_RateLimitPublicMixin, View):
    """Validação PÚBLICA de certificado via protocolo (QR Code)."""
    template_name = 'treinamentos/verificar_certificado.html'

    def get(self, request, *args, **kwargs):
        protocolo = self.kwargs.get('protocolo')
        try:
            participante = Participante.objects.select_related(
                'funcionario', 'treinamento__tipo_curso',
            ).get(protocolo_validacao=protocolo)
            context = {
                'valido': True,
                'participante': participante,
                'treinamento': participante.treinamento,
                'data_emissao': participante.data_registro,
            }
        except (Participante.DoesNotExist, ValueError):
            context = {'valido': False, 'protocolo': protocolo}

        return render(request, self.template_name, context)


class PaginaAssinaturaView(LoginRequiredMixin, View):
    """Coleta da assinatura digital (participante ou instrutor)."""
    template_name = 'treinamentos/pagina_assinatura.html'

    def get_assinatura_obj(self, token):
        try:
            return Assinatura.objects.select_related(
                'participante__funcionario',
                'treinamento_responsavel__responsavel',
            ).get(token_acesso=token)
        except Assinatura.DoesNotExist:
            return None

    def get(self, request, *args, **kwargs):
        token = self.kwargs.get('token')
        assinatura_obj = self.get_assinatura_obj(token)

        if not assinatura_obj:
            messages.error(request, "Link de assinatura inválido ou expirado.")
            return redirect('core:index')

        usuario_deve_assinar = None
        if assinatura_obj.participante:
            usuario_deve_assinar = assinatura_obj.participante.funcionario
        elif assinatura_obj.treinamento_responsavel:
            usuario_deve_assinar = assinatura_obj.treinamento_responsavel.responsavel

        if request.user != usuario_deve_assinar:
            messages.warning(
                request,
                "Você está logado com um usuário diferente do esperado para esta assinatura. "
                "Por favor, acesse com o usuário correto."
            )

        if assinatura_obj.esta_assinada:
            messages.info(request, "Este documento já foi assinado.")

        return render(request, self.template_name, {
            'titulo': 'Coleta de Assinatura',
            'assinatura_obj': assinatura_obj,
            'nome_assinante': assinatura_obj.get_signer(),
            'token': token,
        })

    def post(self, request, *args, **kwargs):
        token = self.kwargs.get('token')
        assinatura_obj = self.get_assinatura_obj(token)

        if not assinatura_obj:
            messages.error(request, "Link de assinatura inválido ou expirado.")
            return redirect('core:index')

        if assinatura_obj.esta_assinada:
            messages.error(request, "Este documento já foi assinado.")
            return redirect('treinamentos:pagina_assinatura', token=token)

        assinatura_data = request.POST.get('assinatura_json')
        if not assinatura_data:
            messages.error(request, "Nenhuma assinatura foi fornecida.")
            return render(request, self.template_name, {
                'assinatura_obj': assinatura_obj,
                'nome_assinante': assinatura_obj.get_signer(),
                'token': token,
            })

        assinatura_obj.assinatura_json = assinatura_data
        assinatura_obj.data_assinatura = timezone.now()
        assinatura_obj.save()

        messages.success(request, "✅ Assinatura registrada com sucesso!")
        return redirect('core:index')


class GerarCertificadoPDFView(LoginRequiredMixin, TecnicoScopeMixin, View):
    """Certificado em PDF (frente e verso) para um participante."""
    tecnico_scope_lookup = 'treinamento__participantes__funcionario'

    def get_qrcode_svg(self, participante):
        url_validacao = self.request.build_absolute_uri(
            reverse('treinamentos:verificar_certificado',
                    kwargs={'protocolo': participante.protocolo_validacao})
        )
        img = qrcode.make(url_validacao, image_factory=qrcode.image.svg.SvgPathImage, border=1)
        buffer = io.BytesIO()
        img.save(buffer)
        return buffer.getvalue().decode('utf-8')

    def get_context_data(self, participante):
        treinamento = participante.treinamento
        gabarito = GabaritoCertificado.objects.filter(ativo=True).first()
        if not gabarito:
            raise Exception("Nenhum Gabarito de Certificado ativo foi encontrado.")

        documento = getattr(participante.funcionario, 'cpf',
                            getattr(participante.funcionario, 'rg', 'Não informado'))

        data_inicio = treinamento.data_inicio.strftime('%d/%m/%Y')
        data_fim = (treinamento.data_fim.strftime('%d/%m/%Y')
                    if treinamento.data_fim else data_inicio)

        try:
            carga_horaria_extenso = num2words(treinamento.duracao, lang='pt_BR')
        except Exception:
            carga_horaria_extenso = str(treinamento.duracao)

        tipo = treinamento.tipo_curso
        context_frente = {
            'participante_nome': participante.funcionario.get_full_name(),
            'participante_documento': documento,
            'empresa_nome': gabarito.empresa_nome,
            'nome_curso': tipo.nome,
            'conteudo_programatico': tipo.descricao_no_certificado or "",
            'referencia_normativa': tipo.referencia_normativa or "",
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'carga_horaria': treinamento.duracao,
            'carga_horaria_extenso': carga_horaria_extenso,
            'local': treinamento.local,
        }

        grade_formatada = (tipo.grade_curricular or "").replace('\n', '<br>')
        context_verso = {
            'grade_curricular': mark_safe(grade_formatada),
            'protocolo': str(participante.protocolo_validacao),
            'qr_code_svg': mark_safe(self.get_qrcode_svg(participante)),
        }

        return {
            'gabarito': gabarito,
            'contexto_frente': context_frente,
            'contexto_verso': context_verso,
            'participante': participante,
            'treinamento': treinamento,
            'assinatura_participante': getattr(participante, 'assinatura', None),
            'assinatura_responsavel': getattr(treinamento, 'assinatura_responsavel', None),
            'data_emissao': timezone.now(),
        }

    def get(self, request, *args, **kwargs):
        if not WEASYPRINT_DISPONIVEL:
            messages.error(request, "A biblioteca 'WeasyPrint' não foi encontrada. "
                                    "Geração de PDF está desabilitada.")
            return redirect(request.META.get('HTTP_REFERER', 'treinamentos:treinamento_list'))

        try:
            base_qs = Participante.objects.select_related(
                'funcionario',
                'treinamento__tipo_curso',
                'treinamento__responsavel',
                'assinatura',
                'treinamento__assinatura_responsavel',
            )
            base_qs = self.scope_tecnico_queryset(base_qs)
            participante = get_object_or_404(base_qs, pk=self.kwargs.get('pk'))
        except Http404:
            messages.error(request, "Participante não encontrado ou sem permissão.")
            return redirect('treinamentos:treinamento_list')
        except Exception:
            logger.exception("Erro ao buscar participante para certificado")
            messages.error(request, "Erro ao buscar participante.")
            return redirect('treinamentos:treinamento_list')

        treinamento = participante.treinamento
        detalhe = ('treinamentos:detalhe_treinamento',)

        if treinamento.status != 'F':
            messages.error(request, "Este treinamento ainda não foi finalizado.")
            return redirect(*detalhe, pk=treinamento.pk)

        if not participante.presente:
            messages.error(request, "Este participante não teve a presença confirmada.")
            return redirect(*detalhe, pk=treinamento.pk)

        assinatura_part = getattr(participante, 'assinatura', None)
        if not assinatura_part or not assinatura_part.esta_assinada:
            messages.error(request, "O participante ainda não assinou o certificado.")
            return redirect(*detalhe, pk=treinamento.pk)

        assinatura_resp = getattr(treinamento, 'assinatura_responsavel', None)
        if not assinatura_resp or not assinatura_resp.esta_assinada:
            messages.error(request, "O instrutor responsável ainda não assinou o certificado.")
            return redirect(*detalhe, pk=treinamento.pk)

        try:
            context_data = self.get_context_data(participante)
            html_string = get_template('treinamentos/certificado_template.html').render(context_data)

            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = (
                f'inline; filename="certificado_{participante.funcionario.username}.pdf"'
            )

            css_files = []
            css_path = os.path.join(settings.STATIC_ROOT or '', 'css', 'certificado.css')
            if os.path.exists(css_path):
                css_files.append(CSS(css_path))

            HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(
                response, stylesheets=css_files
            )

            if not participante.certificado_emitido:
                participante.certificado_emitido = True
                participante.save(update_fields=['certificado_emitido'])

            return response

        except Exception as e:
            logger.exception("Erro ao gerar PDF do certificado")
            messages.error(request, f"Ocorreu um erro inesperado ao gerar o PDF: {e}")
            return redirect(*detalhe, pk=treinamento.pk)


# =============================================================================
# EAD — CATÁLOGO
# =============================================================================

class EADCatalogoView(LoginRequiredMixin, ListView):
    model = CursoEAD
    template_name = "treinamentos/ead/catalogo.html"
    context_object_name = "cursos"
    paginate_by = 12

    def get_queryset(self):
        qs = CursoEAD.objects.filter(
            status=CursoEAD.Status.PUBLICADO,
            filial=self.request.user.filial_ativa,
        ).select_related("tipo_curso").annotate(
            total_modulos_count=Count("modulos_ead", distinct=True),
            total_aulas_count=Count("modulos_ead__aulas_ead", distinct=True),
            total_matriculados_count=Count("matriculas_ead", distinct=True),
        )

        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(Q(titulo__icontains=q) | Q(descricao__icontains=q))

        tipo = self.request.GET.get("tipo")
        if tipo:
            qs = qs.filter(tipo_curso_id=tipo)

        nivel = self.request.GET.get("nivel")
        if nivel:
            qs = qs.filter(nivel=nivel)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["tipos_curso"] = TipoCurso.objects.filter(ativo=True).order_by("nome")
        ctx["niveis"] = CursoEAD.Nivel.choices
        ctx["filtro_q"] = self.request.GET.get("q", "")
        ctx["filtro_tipo"] = self.request.GET.get("tipo", "")
        ctx["filtro_nivel"] = self.request.GET.get("nivel", "")

        funcionario = _get_funcionario(self.request.user)
        if funcionario:
            matriculas = MatriculaEAD.objects.filter(
                funcionario=funcionario,
            ).values_list("curso_id", "status", "progresso_percentual")
            ctx["matriculas_map"] = {
                str(m[0]): {"status": m[1], "progresso": m[2]} for m in matriculas
            }
        else:
            ctx["matriculas_map"] = {}
        return ctx


class EADCursoDetailView(LoginRequiredMixin, DetailView):
    model = CursoEAD
    template_name = "treinamentos/ead/curso_detail.html"
    context_object_name = "curso"
    slug_field = "slug"

    def get_queryset(self):
        return CursoEAD.objects.filter(
            status=CursoEAD.Status.PUBLICADO,
            filial=self.request.user.filial_ativa,
        ).select_related("tipo_curso", "criado_por")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        curso = self.object

        ctx["modulos"] = curso.modulos_ead.filter(
            ativo=True
        ).prefetch_related("aulas_ead").order_by("ordem")

        ctx.update({
            "matricula": None,
            "progressos_concluidos": set(),
            "ultima_tentativa": None,
            "tentativas_restantes": 0,
            "nota_ok": False,
            "ch_ok": False,
        })

        funcionario = _get_funcionario(self.request.user)
        if not funcionario:
            return ctx

        matricula = MatriculaEAD.objects.filter(funcionario=funcionario, curso=curso).first()
        ctx["matricula"] = matricula
        if not matricula:
            return ctx

        ctx["progressos_concluidos"] = set(
            ProgressoAulaEAD.objects.filter(
                matricula=matricula, concluida=True,
            ).values_list("aula_id", flat=True)
        )

        ultima = TentativaAvaliacaoEAD.objects.filter(
            matricula=matricula, finalizada_em__isnull=False,
        ).order_by("-numero_tentativa").first()
        ctx["ultima_tentativa"] = ultima
        ctx["tentativas_restantes"] = max(
            0, curso.max_tentativas_avaliacao - matricula.tentativas_avaliacao
        )

        if ultima and ultima.nota is not None:
            ctx["nota_ok"] = ultima.nota >= curso.nota_minima
        ctx["ch_ok"] = matricula.carga_horaria_atingida
        return ctx


class EADMeusCursosView(LoginRequiredMixin, ListView):
    model = MatriculaEAD
    template_name = "treinamentos/ead/meus_cursos.html"
    context_object_name = "matriculas"

    def get_queryset(self):
        funcionario = _get_funcionario(self.request.user)
        if not funcionario:
            return MatriculaEAD.objects.none()
        return MatriculaEAD.objects.filter(
            funcionario=funcionario,
            filial=self.request.user.filial_ativa,
        ).select_related("curso", "curso__tipo_curso").order_by("-data_matricula")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        matriculas = ctx["matriculas"]
        ctx["em_andamento"] = [
            m for m in matriculas if m.status == MatriculaEAD.Status.EM_ANDAMENTO
        ]
        ctx["concluidos"] = [
            m for m in matriculas
            if m.status in (MatriculaEAD.Status.APROVADO, MatriculaEAD.Status.CONCLUIDO)
        ]
        return ctx


class EADMatricularView(LoginRequiredMixin, View):
    def post(self, request, slug):
        curso = get_object_or_404(
            CursoEAD, slug=slug,
            status=CursoEAD.Status.PUBLICADO,
            filial=request.user.filial_ativa,
        )

        funcionario = _get_funcionario(request.user)
        if not funcionario:
            messages.error(request, "Seu usuário não está vinculado a um funcionário.")
            return redirect("treinamentos:ead_curso_detail", slug=slug)

        if MatriculaEAD.objects.filter(funcionario=funcionario, curso=curso).exists():
            messages.warning(request, "Você já está matriculado neste curso.")
            return redirect("treinamentos:ead_curso_detail", slug=slug)

        MatriculaEAD.objects.create(
            funcionario=funcionario,
            curso=curso,
            filial=request.user.filial_ativa,
            matriculado_por=request.user,
            prazo_limite=timezone.now() + timedelta(days=90),
        )

        messages.success(request, f"Matrícula confirmada! Bons estudos no curso: {curso.titulo}")
        return redirect("treinamentos:ead_curso_detail", slug=slug)


# =============================================================================
# EAD — PLAYER
# =============================================================================

class EADAulaPlayerView(LoginRequiredMixin, DetailView):
    model = AulaEAD
    template_name = "treinamentos/ead/aula_player.html"
    context_object_name = "aula"

    def get_queryset(self):
        return AulaEAD.objects.filter(
            ativo=True,
            modulo__curso__filial=self.request.user.filial_ativa,
        ).select_related("modulo", "modulo__curso")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        curso = self.object.modulo.curso

        funcionario = _get_funcionario(request.user)
        self.matricula = (
            MatriculaEAD.objects.filter(funcionario=funcionario, curso=curso).first()
            if funcionario else None
        )
        if not self.matricula:
            messages.warning(request, "Matricule-se no curso para acessar as aulas.")
            return redirect("treinamentos:ead_curso_detail", slug=curso.slug)

        return self.render_to_response(self.get_context_data(object=self.object))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        aula = self.object
        curso = aula.modulo.curso
        matricula = self.matricula

        ctx["matricula"] = matricula
        ctx["progresso"], _ = ProgressoAulaEAD.objects.get_or_create(
            matricula=matricula, aula=aula,
            defaults={"iniciado_em": timezone.now()},
        )

        ctx["modulos"] = curso.modulos_ead.filter(
            ativo=True
        ).prefetch_related("aulas_ead").order_by("ordem")

        todas_aulas = list(
            AulaEAD.objects.filter(modulo__curso=curso, ativo=True)
            .order_by("modulo__ordem", "ordem")
        )
        idx = next((i for i, a in enumerate(todas_aulas) if a.pk == aula.pk), None)
        ctx["aula_anterior"] = todas_aulas[idx - 1] if idx else None
        ctx["aula_proxima"] = (
            todas_aulas[idx + 1] if idx is not None and idx < len(todas_aulas) - 1 else None
        )

        progs = ProgressoAulaEAD.objects.filter(
            matricula=matricula,
        ).values_list("aula_id", "concluida")
        ctx["progressos_map"] = {p[0]: p[1] for p in progs}
        return ctx


@method_decorator(require_POST, name="dispatch")
class EADSalvarProgressoView(LoginRequiredMixin, View):
    """Salva progresso parcial da aula (AJAX)."""

    def post(self, request, pk):
        aula = get_object_or_404(
            AulaEAD, pk=pk, modulo__curso__filial=request.user.filial_ativa,
        )

        funcionario = _get_funcionario(request.user)
        matricula = (
            MatriculaEAD.objects.filter(funcionario=funcionario, curso=aula.modulo.curso).first()
            if funcionario else None
        )
        if not matricula:
            return JsonResponse({"error": "Matrícula não encontrada"}, status=404)

        progresso, _ = ProgressoAulaEAD.objects.get_or_create(
            matricula=matricula, aula=aula,
            defaults={"iniciado_em": timezone.now()},
        )

        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            data = request.POST

        try:
            if "video_posicao_segundos" in data:
                progresso.video_posicao_segundos = int(data["video_posicao_segundos"])
            if "video_duracao_total" in data:
                progresso.video_duracao_total = int(data["video_duracao_total"])
            if "tempo_gasto_segundos" in data:
                progresso.tempo_gasto_segundos = int(data["tempo_gasto_segundos"])
            if "percentual_assistido" in data:
                progresso.percentual_assistido = Decimal(str(data["percentual_assistido"]))
        except (ValueError, TypeError, InvalidOperation):
            return JsonResponse({"error": "Dados inválidos"}, status=400)

        progresso.save()
        return JsonResponse({"ok": True, "percentual": float(progresso.percentual_assistido)})


@method_decorator(require_POST, name="dispatch")
class EADConcluirAulaView(LoginRequiredMixin, View):
    def post(self, request, pk):
        aula = get_object_or_404(
            AulaEAD, pk=pk, modulo__curso__filial=request.user.filial_ativa,
        )

        funcionario = _get_funcionario(request.user)
        matricula = (
            MatriculaEAD.objects.filter(funcionario=funcionario, curso=aula.modulo.curso).first()
            if funcionario else None
        )
        if not matricula:
            return JsonResponse({"error": "Matrícula não encontrada"}, status=404)

        progresso, _ = ProgressoAulaEAD.objects.get_or_create(
            matricula=matricula, aula=aula,
            defaults={"iniciado_em": timezone.now()},
        )
        progresso.marcar_concluida()
        matricula.refresh_from_db()

        return JsonResponse({
            "ok": True,
            "concluida": True,
            "progresso_curso": float(matricula.progresso_percentual),
            "pode_avaliar": matricula.pode_fazer_avaliacao,
        })


# =============================================================================
# EAD — AVALIAÇÃO
# =============================================================================

class EADAvaliacaoView(LoginRequiredMixin, View):
    template_name = "treinamentos/ead/avaliacao.html"

    def get_matricula(self, request, matricula_id):
        funcionario = _get_funcionario(request.user)
        if not funcionario:
            return None
        try:
            return MatriculaEAD.objects.select_related(
                "curso", "curso__avaliacao_ead",
            ).get(pk=matricula_id, funcionario=funcionario)
        except MatriculaEAD.DoesNotExist:
            return None

    def get(self, request, matricula_id):
        matricula = self.get_matricula(request, matricula_id)
        if not matricula:
            messages.error(request, "Matrícula não encontrada.")
            return redirect("treinamentos:ead_meus_cursos")

        if not matricula.pode_fazer_avaliacao:
            messages.warning(
                request,
                "Você ainda não pode fazer a avaliação. "
                f"Complete pelo menos {matricula.curso.percentual_minimo_assistido}% das aulas."
            )
            return redirect("treinamentos:ead_curso_detail", slug=matricula.curso.slug)

        try:
            avaliacao = matricula.curso.avaliacao_ead
        except AvaliacaoEAD.DoesNotExist:
            messages.error(request, "Este curso não possui avaliação cadastrada.")
            return redirect("treinamentos:ead_curso_detail", slug=matricula.curso.slug)

        questoes = list(avaliacao.questoes_ead.filter(
            ativo=True).prefetch_related("alternativas_ead"))
        if avaliacao.embaralhar_questoes:
            random.shuffle(questoes)

        for q in questoes:
            alts = list(q.alternativas_ead.all())
            if avaliacao.embaralhar_alternativas:
                random.shuffle(alts)
            q.alternativas_embaralhadas = alts

        return render(request, self.template_name, {
            "matricula": matricula,
            "avaliacao": avaliacao,
            "questoes": questoes,
            "tentativa_numero": matricula.tentativas_avaliacao + 1,
        })

    def post(self, request, matricula_id):
        matricula = self.get_matricula(request, matricula_id)
        if not matricula or not matricula.pode_fazer_avaliacao:
            messages.error(request, "Não é possível realizar a avaliação.")
            return redirect("treinamentos:ead_meus_cursos")

        avaliacao = matricula.curso.avaliacao_ead

        with transaction.atomic():
            tentativa = TentativaAvaliacaoEAD.objects.create(
                matricula=matricula,
                avaliacao=avaliacao,
                numero_tentativa=matricula.tentativas_avaliacao + 1,
            )

            for questao in avaliacao.questoes_ead.filter(ativo=True):
                alt_id = request.POST.get(f"questao_{questao.pk}")
                alternativa = None
                if alt_id:
                    alternativa = AlternativaEAD.objects.filter(
                        pk=alt_id, questao=questao).first()

                RespostaAlunoEAD.objects.create(
                    tentativa=tentativa,
                    questao=questao,
                    alternativa_escolhida=alternativa,
                )

            tentativa.calcular_nota()

        return redirect("treinamentos:ead_resultado", tentativa_id=tentativa.pk)


class EADResultadoView(LoginRequiredMixin, DetailView):
    model = TentativaAvaliacaoEAD
    template_name = "treinamentos/ead/resultado.html"
    context_object_name = "tentativa"
    pk_url_kwarg = "tentativa_id"

    def get_queryset(self):
        funcionario = _get_funcionario(self.request.user)
        if not funcionario:
            return TentativaAvaliacaoEAD.objects.none()
        return TentativaAvaliacaoEAD.objects.filter(
            matricula__funcionario=funcionario,
        ).select_related("matricula", "matricula__curso", "avaliacao")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tentativa = self.object
        matricula = tentativa.matricula
        curso = matricula.curso

        gabarito = _montar_gabarito(tentativa)
        ctx["gabarito"] = gabarito
        ctx["matricula"] = matricula
        ctx["total_questoes"] = len(gabarito)
        ctx["total_acertos"] = sum(1 for g in gabarito if g["acertou"])

        nota_ok = tentativa.nota is not None and tentativa.nota >= curso.nota_minima
        ch_ok = matricula.carga_horaria_atingida
        ctx["nota_ok"] = nota_ok
        ctx["ch_ok"] = ch_ok
        ctx["aprovado_completo"] = nota_ok and ch_ok
        return ctx


class EADCertificadoView(_RateLimitPublicMixin, DetailView):
    """Verificação pública do certificado EAD por UUID."""
    model = CertificadoEAD
    template_name = "treinamentos/ead/certificado.html"
    context_object_name = "certificado"
    slug_field = "uuid"
    slug_url_kwarg = "uuid"


# =============================================================================
# EAD — GESTÃO (exige permissão)
# =============================================================================

class GestaoAvaliacoesCursoView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = CursoEAD
    template_name = "treinamentos/ead/gestao_avaliacoes.html"
    context_object_name = "curso"
    slug_field = "slug"
    permission_required = 'treinamentos.ver_relatorios'

    def get_queryset(self):
        return CursoEAD.objects.filter(filial=self.request.user.filial_ativa)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        matriculas = MatriculaEAD.objects.filter(
            curso=self.object,
        ).select_related("funcionario").order_by("funcionario__nome")

        dados = []
        for mat in matriculas:
            tentativas = TentativaAvaliacaoEAD.objects.filter(
                matricula=mat, finalizada_em__isnull=False,
            ).order_by("-numero_tentativa")
            dados.append({
                "matricula": mat,
                "tentativas": tentativas,
                "ultima": tentativas.first(),
            })

        ctx["dados_alunos"] = dados
        return ctx


class GestaoTentativaDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = TentativaAvaliacaoEAD
    template_name = "treinamentos/ead/gestao_tentativa.html"
    context_object_name = "tentativa"
    pk_url_kwarg = "tentativa_id"
    permission_required = 'treinamentos.ver_relatorios'

    def get_queryset(self):
        return TentativaAvaliacaoEAD.objects.filter(
            matricula__curso__filial=self.request.user.filial_ativa,
        ).select_related(
            "matricula", "matricula__funcionario", "matricula__curso", "avaliacao",
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        gabarito = _montar_gabarito(self.object)
        ctx["gabarito"] = gabarito
        ctx["matricula"] = self.object.matricula
        ctx["total_questoes"] = len(gabarito)
        ctx["total_acertos"] = sum(1 for g in gabarito if g["acertou"])
        return ctx


class GestaoImprimirProvaView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = TentativaAvaliacaoEAD
    template_name = "treinamentos/ead/imprimir_prova.html"
    context_object_name = "tentativa"
    pk_url_kwarg = "tentativa_id"
    permission_required = 'treinamentos.ver_relatorios'

    def get_queryset(self):
        return TentativaAvaliacaoEAD.objects.filter(
            matricula__curso__filial=self.request.user.filial_ativa,
        ).select_related(
            "matricula", "matricula__funcionario", "matricula__curso", "avaliacao",
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        gabarito = _montar_gabarito(self.object)
        ctx["gabarito"] = gabarito
        ctx["total_questoes"] = len(gabarito)
        ctx["total_acertos"] = sum(1 for g in gabarito if g["acertou"])
        return ctx


class GestaoLiberarTentativaView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Libera uma nova tentativa para o colaborador."""
    permission_required = 'treinamentos.alterar_status'

    def post(self, request, matricula_id):
        try:
            matricula = MatriculaEAD.objects.select_related("curso").get(
                pk=matricula_id, curso__filial=request.user.filial_ativa,
            )
        except MatriculaEAD.DoesNotExist:
            messages.error(request, "Matrícula não encontrada.")
            return redirect("treinamentos:ead_catalogo")

        curso = matricula.curso

        if matricula.status == MatriculaEAD.Status.APROVADO:
            messages.info(request, "Este colaborador já está aprovado.")
        elif matricula.tentativas_avaliacao >= curso.max_tentativas_avaliacao:
            matricula.tentativas_avaliacao = max(0, matricula.tentativas_avaliacao - 1)
            matricula.status = MatriculaEAD.Status.EM_ANDAMENTO
            matricula.save(update_fields=["tentativas_avaliacao", "status"])
            messages.success(request, f"Nova tentativa liberada para {matricula.funcionario}.")
        else:
            restantes = curso.max_tentativas_avaliacao - matricula.tentativas_avaliacao
            messages.info(
                request,
                f"O colaborador ainda tem {restantes} tentativa(s) disponível(is)."
            )

        return redirect("treinamentos:gestao_avaliacoes_curso", slug=curso.slug)


class GestaoGerarCertificadoEADView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Gera o certificado EAD para colaborador aprovado."""
    permission_required = 'treinamentos.gerar_certificados'

    def post(self, request, matricula_id):
        try:
            matricula = MatriculaEAD.objects.select_related(
                "curso", "curso__tipo_curso", "funcionario",
            ).get(pk=matricula_id, curso__filial=request.user.filial_ativa)
        except MatriculaEAD.DoesNotExist:
            messages.error(request, "Matrícula não encontrada.")
            return redirect("treinamentos:ead_catalogo")

        if matricula.status != MatriculaEAD.Status.APROVADO:
            messages.error(request, "O colaborador precisa estar aprovado.")
            return redirect("treinamentos:gestao_avaliacoes_curso", slug=matricula.curso.slug)

        if hasattr(matricula, "certificado_ead"):
            messages.info(request, "Certificado já foi emitido anteriormente.")
            return redirect(matricula.certificado_ead.get_absolute_url())

        funcionario = matricula.funcionario
        curso = matricula.curso

        certificado = CertificadoEAD.objects.create(
            matricula=matricula,
            nome_funcionario=getattr(funcionario, "nome_completo", str(funcionario)),
            cpf_funcionario=getattr(funcionario, "cpf", ""),
            nome_curso=curso.titulo,
            nome_tipo_curso=curso.tipo_curso.nome if curso.tipo_curso else "",
            carga_horaria_exigida=curso.carga_horaria_total,
            carga_horaria_cumprida=matricula.carga_horaria_cumprida_horas,
            nota=matricula.nota_final or Decimal("0.0"),
            nome_instrutor=curso.instrutor_nome,
            filial=curso.filial,
            emitido_por=request.user,
        )

        messages.success(
            request, f"Certificado emitido com sucesso para {certificado.nome_funcionario}."
        )
        return redirect(certificado.get_absolute_url())
