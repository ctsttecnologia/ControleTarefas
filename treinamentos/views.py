
# treinamentos/views.py

import io
import json
import logging
import os
import random
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

import qrcode
import qrcode.image.svg
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.db import transaction
from django.db.models import Count, ProtectedError, Q, Sum, DecimalField, Value
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
from django.contrib.staticfiles import finders
from core.mixins import TecnicoScopeMixin, ViewFilialScopedMixin

from . import treinamento_generators
from .forms import ParticipanteFormSet, TipoCursoForm, TreinamentoForm
from .models import (
    AlternativaEAD, AulaEAD, AvaliacaoEAD, Assinatura, CertificadoEAD,
    CursoEAD, GabaritoCertificado, MatriculaEAD, Participante,
    ProgressoAulaEAD, RespostaAlunoEAD, TentativaAvaliacaoEAD, TipoCurso,
    Treinamento,
)
from .mixins import FiltrosPaginacaoMixin, PaginacaoQSMixin, TreinamentoScopedMixin, FilialScopedMixin, RateLimitPublicMixin, filial_do_request
from .privacy import mascarar_cpf, mascarar_nome
from django.utils.html import escape
from core.utils import usuario_ve_todas_filiais
from pathlib import Path
from django.contrib.staticfiles import finders
import base64
import binascii
import uuid
from django.utils.formats import number_format
from django.db.models import Prefetch
from django.contrib.staticfiles import finders
from weasyprint import HTML, CSS

ZERO = Value(Decimal('0'), output_field=DecimalField(max_digits=14, decimal_places=2))
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
    """Form principal + formset de participantes."""
    success_message = ""
    formset_prefix = 'participantes'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def _formset(self, data=None):
        return ParticipanteFormSet(data, instance=self.object or Treinamento(),
                                   prefix=self.formset_prefix, request=self.request)

    def get_context_data(self, **kwargs):
        kwargs.setdefault('participantes_formset', self._formset())
        return super().get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object() if isinstance(self, UpdateView) else None
        form = self.get_form()
        formset = self._formset(request.POST)
        if form.is_valid() and formset.is_valid():
            return self.form_valid(form, formset)
        return self.form_invalid(form, formset)

    def form_valid(self, form, formset):
        with transaction.atomic():
            if not form.instance.pk:
                form.instance.filial = filial_do_request(self.request)
            self.object = form.save()
            formset.instance = self.object
            formset.save()
        if self.success_message:
            messages.success(self.request, self.success_message)
        return redirect(self.get_success_url())

    def form_invalid(self, form, formset):
        return self.render_to_response(
            self.get_context_data(form=form, participantes_formset=formset))


class CriarTreinamentoView(LoginRequiredMixin, PermissionRequiredMixin,
                           TreinamentoFormsetMixin, CreateView):
    model = Treinamento
    form_class = TreinamentoForm
    template_name = 'treinamentos/treinamento_form.html'
    success_url = reverse_lazy('treinamentos:treinamento_list')
    success_message = "Treinamento cadastrado com sucesso!"
    permission_required = 'treinamentos.add_treinamento'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastrar Novo Treinamento'
        return context


class TreinamentoListView(TreinamentoScopedMixin, PaginacaoQSMixin, ListView):
    permission_required = 'treinamentos.view_treinamento'
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
        ctx = super().get_context_data(**kwargs)
        ctx['tipos_curso'] = TipoCurso.objects.for_request(self.request).filter(ativo=True).exclude(modalidade='O')
        ctx['total_treinamentos'] = ctx['paginator'].count if ctx.get('paginator') else 0
        ctx['status_choices'] = Treinamento._meta.get_field('status').choices

        return ctx


class EditarTreinamentoView(TreinamentoScopedMixin, TreinamentoFormsetMixin, UpdateView):
    model = Treinamento
    form_class = TreinamentoForm
    template_name = 'treinamentos/treinamento_form.html'
    success_message = "Treinamento atualizado com sucesso!"
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


class DetalheTreinamentoView(TreinamentoScopedMixin, DetailView):
    model = Treinamento
    template_name = 'treinamentos/detalhe_treinamento.html'
    permission_required = 'treinamentos.view_treinamento'
    tecnico_scope_lookup = 'participantes__funcionario'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        participantes = (self.object.participantes
                         .select_related('funcionario__funcionario')
                         .order_by('funcionario__funcionario__nome_completo'))

        context['participantes'] = participantes
        context['presentes'] = sum(1 for p in participantes if p.presente)

        return context


class ExcluirTreinamentoView(TreinamentoScopedMixin, DeleteView):
    http_method_names = ['post']
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
        try:
            return super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, 'Não é possível excluir: há registros vinculados a este treinamento.')

            return redirect(self.success_url)


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


class TipoCursoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = TipoCurso
    template_name = "treinamentos/lista_tipo_curso.html"
    context_object_name = "cursos"
    permission_required = "treinamentos.view_tipocurso"
    paginate_by = 20

    def get_queryset(self):
        qs = TipoCurso.objects.for_request(self.request).order_by("nome")
        termo = self.request.GET.get("q", "").strip()
        if termo:
            qs = qs.filter(
                Q(nome__icontains=termo)
                | Q(conteudo_programatico__icontains=termo)
                | Q(descricao_no_certificado__icontains=termo)
                | Q(referencia_normativa__icontains=termo)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "").strip()
        ctx["total_registros"] = ctx["paginator"].count if ctx.get("paginator") else len(ctx["cursos"])
        return ctx

class CriarTipoCursoView(LoginRequiredMixin, PermissionRequiredMixin,
                         TipoCursoNomeUnicoMixin, SuccessMessageMixin, CreateView):
    model = TipoCurso
    form_class = TipoCursoForm
    template_name = 'treinamentos/tipo_curso_form.html'
    success_url = reverse_lazy('treinamentos:lista_tipo_curso')
    permission_required = 'treinamentos.add_tipocurso'
    success_message = "Tipo de curso cadastrado com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastrar Tipo de Curso'
        return context

    def form_valid(self, form):
        form.instance.filial = filial_do_request(self.request)
        return super().form_valid(form)


class EditarTipoCursoView(FilialScopedMixin, TipoCursoNomeUnicoMixin, SuccessMessageMixin, UpdateView):
    model = TipoCurso
    form_class = TipoCursoForm
    template_name = 'treinamentos/tipo_curso_form.html'
    success_url = reverse_lazy('treinamentos:lista_tipo_curso')
    permission_required = 'treinamentos.change_tipocurso'
    success_message = "Tipo de curso atualizado com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Tipo de Curso'
        return context


class ExcluirTipoCursoView(FilialScopedMixin, SuccessMessageMixin, DeleteView):
    model = TipoCurso
    template_name = 'treinamentos/excluir_tipo_curso.html'
    success_url = reverse_lazy('treinamentos:lista_tipo_curso')
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

class RelatorioTreinamentosView(FiltrosPaginacaoMixin, LoginRequiredMixin, ListView):
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


class RelatorioTreinamentoWordView(TreinamentoScopedMixin, View):
    """Relatório de um treinamento em .docx."""
    permission_required = 'treinamentos.view_treinamento'
    tecnico_scope_lookup = 'participantes__funcionario'

    def get(self, request, *args, **kwargs):
        pk = kwargs['pk']
        qs = Treinamento.objects.for_request(request).select_related('tipo_curso', 'responsavel') \
            .prefetch_related('participantes__funcionario')
        treinamento = get_object_or_404(self.scope_tecnico_queryset(qs), pk=pk)
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

class DashboardView(LoginRequiredMixin, TecnicoScopeMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'treinamentos/dashboard.html'
    permission_required = 'treinamentos.ver_relatorios'
    tecnico_scope_lookup = 'participantes__funcionario'

    # ── Escopo ──────────────────────────────────────────────────────────────
    def _por_filial(self, qs, campo='filial'):
        if usuario_ve_todas_filiais(self.request.user):
            return qs
        return qs.filter(**{campo: filial_do_request(self.request)})

    def _treinamentos(self):
        # O JOIN do escopo técnico duplica linhas; o subselect por pk elimina isso
        escopo = self.scope_tecnico_queryset(self._por_filial(Treinamento.objects.all()))
        return Treinamento.objects.filter(pk__in=escopo.values('pk'))

    # ── Helpers ─────────────────────────────────────────────────────────────
    @staticmethod
    def _serie(qs, campo, rotulos, com_status=False):
        """Agrupa por `campo` e devolve [{label, total[, status]}] ordenado."""
        itens = []
        for i in qs.values(campo).annotate(total=Count('pk')).order_by('-total'):
            item = {'label': rotulos.get(i[campo], i[campo] or '—'), 'total': i['total']}
            if com_status:
                item['status'] = i[campo]
            itens.append(item)
        return itens

    # ── Contexto ────────────────────────────────────────────────────────────
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tr = self._treinamentos()
        cursos = self._por_filial(CursoEAD.objects.all())
        mat = self._por_filial(MatriculaEAD.objects.all())
        certs = self._por_filial(CertificadoEAD.objects.all())

        areas = dict(TipoCurso.AREA_CHOICES)
        publicado = CursoEAD.Status.PUBLICADO

        # Presencial: KPIs em uma única query
        kpi = tr.aggregate(
            total=Count('pk'),
            andamento=Count('pk', filter=Q(status='A')),
            custo=Coalesce(Sum('custo'), ZERO),
        )
        custo_area = (tr.values('tipo_curso__area')
                        .annotate(total=Coalesce(Sum('custo'), ZERO))
                        .order_by('-total'))

        # EAD: KPIs em uma única query
        kpi_ead = mat.aggregate(
            total=Count('pk'),
            andamento=Count('pk', filter=Q(status=MatriculaEAD.Status.EM_ANDAMENTO)),
        )
        top_cursos = list(
            cursos.filter(status=publicado)
            .annotate(total=Count('matriculas_ead', filter=Q(matriculas_ead__in=mat)))
            .filter(total__gt=0).order_by('-total')
            .values('titulo', 'total')[:10]
        )

        ctx.update({
            'total_treinamentos': kpi['total'],
            'em_andamento': kpi['andamento'],
            'total_custo': kpi['custo'],
            'total_custo_fmt': number_format(kpi['custo'], 2, force_grouping=True),
            'total_participantes': Participante.objects.filter(treinamento__in=tr).count(),
            'treinamentos_recentes': tr.select_related('tipo_curso').order_by('-data_inicio')[:5],

            'ead_total_cursos': cursos.filter(status=publicado).count(),
            'ead_total_matriculas': kpi_ead['total'],
            'ead_em_andamento': kpi_ead['andamento'],
            'ead_certificados': certs.count(),

            # Dict puro → {{ dashboard_data|json_script:"dash-data" }}
            'dashboard_data': {
                'area': self._serie(tr, 'tipo_curso__area', areas),
                'status': self._serie(tr, 'status', dict(Treinamento.STATUS_CHOICES), com_status=True),
                'modalidade': self._serie(tr, 'tipo_curso__modalidade', dict(TipoCurso.MODALIDADE_CHOICES)),
                'custo': [{'label': areas.get(i['tipo_curso__area'], '—'), 'total': float(i['total'])}
                          for i in custo_area],
                'ead_status': self._serie(mat, 'status', dict(MatriculaEAD.Status.choices), com_status=True),
                'ead_top_cursos': top_cursos,
            },
        })
        return ctx

# =============================================================================
# CERTIFICADO PRESENCIAL / ASSINATURA
# =============================================================================

def _noindex(response):
    response['X-Robots-Tag'] = 'noindex, nofollow'
    response['Cache-Control'] = 'no-store'
    return response


class VerificarCertificadoView(_RateLimitPublicMixin, View):
    """Validação PÚBLICA de certificado via protocolo (QR Code). Não expõe CPF."""
    http_method_names = ['get']
    template_name = 'treinamentos/verificar_certificado.html'

    def get(self, request, protocolo):
        ctx = {'valido': False, 'protocolo': str(protocolo)[:64]}
        try:
            uuid_protocolo = uuid.UUID(str(protocolo))
        except ValueError:
            return _noindex(render(request, self.template_name, ctx))

        p = (Participante.objects
             .select_related('funcionario', 'treinamento__tipo_curso')
             .filter(protocolo_validacao=uuid_protocolo, certificado_emitido=True)
             .first())

        if p:
            t = p.treinamento
            ctx.update({
                'valido': True,
                'protocolo': str(p.protocolo_validacao),
                'nome': mascarar_nome(p.funcionario.get_full_name()),
                'curso': t.tipo_curso.nome,
                'carga_horaria': t.duracao,
                'data_conclusao': t.data_fim or t.data_inicio,
            })
        return _noindex(render(request, self.template_name, ctx))


class PaginaAssinaturaView(LoginRequiredMixin, View):
    """Coleta da assinatura digital (participante ou instrutor)."""
    http_method_names = ['get', 'post']
    template_name = 'treinamentos/pagina_assinatura.html'
    PREFIXO_PNG = 'data:image/png;base64,'
    MAX_BYTES = 500_000

    def _buscar(self, request, token, lock=False):
        qs = Assinatura.objects.select_related(
            'participante__funcionario', 'treinamento_responsavel__responsavel')
        if lock:
            qs = qs.select_for_update(of=('self',))
        obj = qs.filter(token_acesso=token).first()

        if not obj or obj.expirado:
            messages.error(request, 'Link de assinatura inválido ou expirado.')
            return None, redirect('core:index')
        if request.user != obj.usuario_esperado():
            logger.warning('Assinatura negada: user=%s token=%s...', request.user.pk, token[:6])
            messages.error(request, 'Este link de assinatura pertence a outra pessoa.')
            return None, redirect('core:index')
        return obj, None

    def _contexto(self, obj, token):
        return {
            'titulo': 'Coleta de Assinatura',
            'assinatura_obj': obj,
            'nome_assinante': obj.get_signer(),
            'token': token,
        }

    @classmethod
    def _png_valido(cls, dados):
        if not dados.startswith(cls.PREFIXO_PNG) or len(dados) > cls.MAX_BYTES:
            return False
        try:
            raw = base64.b64decode(dados[len(cls.PREFIXO_PNG):], validate=True)
        except (binascii.Error, ValueError):
            return False
        return raw.startswith(b'\x89PNG\r\n\x1a\n')

    def get(self, request, token):
        obj, erro = self._buscar(request, token)
        if erro:
            return erro
        return render(request, self.template_name, self._contexto(obj, token))

    def post(self, request, token):
        dados = request.POST.get('assinatura_json', '')
        if not request.POST.get('aceite_termo') or not self._png_valido(dados):
            messages.error(request, 'Desenhe a assinatura e aceite o termo para continuar.')
            return redirect('treinamentos:pagina_assinatura', token=token)

        with transaction.atomic():
            obj, erro = self._buscar(request, token, lock=True)
            if erro:
                return erro
            if obj.esta_assinada:
                messages.info(request, 'Este documento já foi assinado.')
                return redirect('treinamentos:pagina_assinatura', token=token)

            obj.assinatura_json = dados
            obj.data_assinatura = timezone.now()
            obj.assinado_por = request.user
            obj.ip_assinatura = request.META.get('REMOTE_ADDR')  # atrás de proxy: use o IP real
            obj.user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]
            obj.save(update_fields=['assinatura_json', 'data_assinatura', 'assinado_por',
                                    'ip_assinatura', 'user_agent'])

        messages.success(request, '✅ Assinatura registrada com sucesso!')
        # Volta para a mesma página, que agora exibe o estado "assinado"
        return redirect('treinamentos:pagina_assinatura', token=token)

def linebreaksbr():
    raise NotImplementedError


class GerarCertificadoPDFView(LoginRequiredMixin, View):
    """Certificado em PDF (frente e verso). Acesso: o próprio participante ou um gestor."""
    http_method_names = ['get']
    template_name = 'treinamentos/certificado_template.html'
    css_static = 'css/treinamentos/certificado_pdf.css'
       
    

    def get_participante(self, request, pk):
        tipo = p.treinamento.tipo_curso
        p = get_object_or_404(Participante, pk=pk) 

        qs = Participante.objects.select_related(
            'funcionario', 'treinamento__tipo_curso', 'treinamento__responsavel',
            'assinatura', 'treinamento__assinatura_responsavel',
        )
        if not usuario_ve_todas_filiais(request.user):
            qs = qs.filter(treinamento__filial=filial_do_request(request))
        participante = get_object_or_404(qs, pk=pk)

        eh_dono = participante.funcionario_id == request.user.pk
        eh_gestor = request.user.has_perm('treinamentos.gerar_certificados')
        if not (eh_dono or eh_gestor):
            logger.warning('Certificado negado: user=%s participante=%s', request.user.pk, pk)
            raise PermissionDenied

        tipo = participante.treinamento.tipo_curso
        if not tipo or not tipo.certificado:
            raise Http404("Este treinamento não emite certificado.")
        
        return participante

    @staticmethod
    def validar(participante):
        t = participante.treinamento
        if t.status != 'F':
            return 'Este treinamento ainda não foi finalizado.'
        if not t.tipo_curso.certificado:
            return 'Este tipo de curso não emite certificado.'
        if not participante.presente:
            return 'Este participante não teve a presença confirmada.'
        a_part = getattr(participante, 'assinatura', None)
        if not a_part or not a_part.esta_assinada:
            return 'O participante ainda não assinou o certificado.'
        a_resp = getattr(t, 'assinatura_responsavel', None)
        if not a_resp or not a_resp.esta_assinada:
            return 'O instrutor responsável ainda não assinou o certificado.'
        if not GabaritoCertificado.objects.filter(ativo=True).exists():
            return 'Nenhum gabarito de certificado ativo. Contate o administrador.'
        return None

    def get_qrcode_svg(self, participante):
        url = self.request.build_absolute_uri(reverse(
            'treinamentos:verificar_certificado',
            kwargs={'protocolo': participante.protocolo_validacao},
        ))
        img = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, border=1)
        buffer = io.BytesIO()
        img.save(buffer)
        return buffer.getvalue().decode('utf-8')

    @staticmethod
    def get_documento(user):
        """CPF fica no Funcionario vinculado, não no User."""
        func = _get_funcionario(user)
        return getattr(func, 'cpf', '') or getattr(user, 'cpf', '') or 'Não informado'

    def get_context_data(self, participante):
        treinamento = participante.treinamento
        tipo = treinamento.tipo_curso
        gabarito = GabaritoCertificado.objects.filter(ativo=True).first()

        fmt = lambda d: timezone.localtime(d).strftime('%d/%m/%Y') if d else ''
        data_inicio = fmt(treinamento.data_inicio)
        data_fim = fmt(treinamento.data_fim) or data_inicio

        try:
            ch_extenso = num2words(treinamento.duracao, lang='pt_BR')
        except Exception:
            ch_extenso = str(treinamento.duracao)

        # Valores crus: o escape é feito em renderizar_texto(), que retorna mark_safe
        contexto_frente = {
            'participante_nome': participante.funcionario.get_full_name(),
            'participante_documento': self.get_documento(participante.funcionario),
            'empresa_nome': gabarito.empresa_nome,
            'nome_curso': tipo.nome,
            'conteudo_programatico': tipo.descricao_no_certificado or '',
            'referencia_normativa': tipo.referencia_normativa or '',
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'carga_horaria': treinamento.duracao,
            'carga_horaria_extenso': ch_extenso,
            'local': treinamento.local or '',
        }
        contexto_verso = {
            'grade_curricular': linebreaksbr(escape(tipo.grade_curricular or '')),
            'protocolo': str(participante.protocolo_validacao),
            'qr_code_svg': mark_safe(self.get_qrcode_svg(participante)),  # gerado pelo sistema
        }
        return {
            'gabarito': gabarito,
            'texto_frente': gabarito.renderizar_texto(contexto_frente),
            'texto_verso': gabarito.renderizar_verso(contexto_verso),
            'contexto_verso': contexto_verso,
            'participante': participante,
            'treinamento': treinamento,
            'assinatura_participante': participante.assinatura,
            'assinatura_responsavel': treinamento.assinatura_responsavel,
            'data_emissao': timezone.localtime(),
            'fundo_uri': Path(gabarito.imagem_fundo.path).as_uri() if gabarito.imagem_fundo else None,
        }

    def get(self, request, pk):
        participante = self.get_participante(request, pk)
        voltar = redirect('treinamentos:detalhe_treinamento', pk=participante.treinamento_id)
        
        if not WEASYPRINT_DISPONIVEL:
            messages.error(request, 'Geração de PDF indisponível no momento.')
            return voltar
        if erro := self.validar(participante):
            messages.error(request, erro)
            return voltar

        try:
            html = get_template(self.template_name).render(
                self.get_context_data(participante), request)
            css_path = finders.find(self.css_static)
            if not css_path:
                logger.warning('CSS do certificado não encontrado: %s', self.css_static)
            pdf = HTML(string=html, base_url=request.build_absolute_uri('/')).write_pdf(
                stylesheets=[CSS(filename=css_path)] if css_path else None)
        except Exception:
            logger.exception('Erro ao gerar PDF do certificado (participante %s)', pk)
            messages.error(request, 'Erro ao gerar o PDF. A equipe técnica foi notificada.')
            return voltar

        Participante.objects.filter(pk=participante.pk, certificado_emitido=False) \
            .update(certificado_emitido=True)

        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'inline; filename="certificado_{str(participante.protocolo_validacao)[:8]}.pdf"')
        response['Cache-Control'] = 'private, no-store'
        response['X-Content-Type-Options'] = 'nosniff'
                
        return response


# =============================================================================
# EAD — CATÁLOGO
# =============================================================================

class EADCatalogoView(LoginRequiredMixin, PaginacaoQSMixin, ListView):
    model = CursoEAD
    template_name = "treinamentos/ead/catalogo.html"
    context_object_name = "cursos"
    paginate_by = 12

    def get_queryset(self):
        qs = CursoEAD.objects.filter(
            status=CursoEAD.Status.PUBLICADO,
            filial=self.request.user.filial_ativa,
        ).select_related("tipo_curso").annotate(
            total_modulos_count=Count('modulos_ead', filter=Q(modulos_ead__ativo=True), distinct=True),
            total_aulas_count=Count('modulos_ead__aulas_ead', filter=Q(modulos_ead__aulas_ead__ativo=True), distinct=True),
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
        ctx.update({
            "tipos_curso": TipoCurso.objects.for_request(self.request).filter(ativo=True).order_by("nome"),
            "niveis": CursoEAD.Nivel.choices,
            "filtro_q": self.request.GET.get("q", ""),
            "filtro_tipo": self.request.GET.get("tipo", ""),
            "filtro_nivel": self.request.GET.get("nivel", ""),
        })

        cursos = list(ctx["cursos"])  # carrega a página uma vez só
        func = _get_funcionario(self.request.user)
        progresso = dict(
            MatriculaEAD.objects
            .filter(funcionario=func, curso_id__in=[c.pk for c in cursos])
            .values_list("curso_id", "progresso_percentual")
        ) if func else {}

        for c in cursos:
            c.progresso_usuario = progresso.get(c.pk)
        ctx["cursos"] = ctx["object_list"] = cursos
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

        ctx["modulos"] = (
            curso.modulos_ead.filter(ativo=True)
            .prefetch_related(
                Prefetch("aulas_ead", queryset=AulaEAD.objects.order_by("ordem"))
            )
            .order_by("ordem")
        )

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

        matricula = (
            MatriculaEAD.objects.filter(funcionario=funcionario, curso=curso)
            .select_related("certificado_ead")
            .first()
        )
        ctx["matricula"] = matricula
        if not matricula:
            return ctx

        ctx["progressos_concluidos"] = set(
            ProgressoAulaEAD.objects.filter(
                matricula=matricula, concluida=True,
            ).values_list("aula_id", flat=True)
        )

        ultima = (
            TentativaAvaliacaoEAD.objects.filter(
                matricula=matricula, finalizada_em__isnull=False,
            )
            .order_by("-numero_tentativa")
            .first()
        )
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
        ).select_related("curso__tipo_curso", "certificado_ead").order_by("-data_matricula")

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
    http_method_names = ['post']
    PRAZO_DIAS = 90

    def post(self, request, slug):
        curso = get_object_or_404(
            CursoEAD.objects.for_request(request),
            slug=slug, status=CursoEAD.Status.PUBLICADO,
        )
        funcionario = _get_funcionario(request.user)
        if not funcionario:
            messages.error(request, 'Seu usuário não está vinculado a um funcionário.')
            return redirect('treinamentos:ead_curso_detail', slug=slug)

        _, criada = MatriculaEAD.objects.get_or_create(
            funcionario=funcionario, curso=curso,
            defaults={
                'filial': curso.filial,
                'matriculado_por': request.user,
                'prazo_limite': timezone.now() + timedelta(days=self.PRAZO_DIAS),
            },
        )
        if criada:
            messages.success(request, f'Matrícula confirmada! Bons estudos em: {curso.titulo}')
        else:
            messages.info(request, 'Você já está matriculado neste curso.')
        return redirect('treinamentos:ead_curso_detail', slug=slug)



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
            modulo__ativo=True,                                # ← segurança
            modulo__curso__status=CursoEAD.Status.PUBLICADO,   # ← segurança
            modulo__curso__filial=self.request.user.filial_ativa,
        ).select_related("modulo", "modulo__curso")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        curso = self.object.modulo.curso

        funcionario = _get_funcionario(request.user)
        self.matricula = (
            MatriculaEAD.objects
            .filter(funcionario=funcionario, curso=curso)
            .exclude(status__in=[                              # ← segurança
                MatriculaEAD.Status.CANCELADO,
                MatriculaEAD.Status.EXPIRADO,
            ])
            .first()
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

        aulas_ativas = AulaEAD.objects.filter(ativo=True).order_by("ordem")
        ctx["modulos"] = (
            curso.modulos_ead.filter(ativo=True)
            .prefetch_related(Prefetch("aulas_ead", queryset=aulas_ativas))  # ← ajuste 1
            .order_by("ordem")
        )

        todas_aulas = list(
            AulaEAD.objects
            .filter(modulo__curso=curso, modulo__ativo=True, ativo=True)     # ← ajuste 2
            .order_by("modulo__ordem", "ordem")
            .only("pk", "titulo", "modulo_id")
        )
        idx = next((i for i, a in enumerate(todas_aulas) if a.pk == aula.pk), None)
        ctx["aula_anterior"] = todas_aulas[idx - 1] if idx else None
        ctx["aula_proxima"] = (
            todas_aulas[idx + 1] if idx is not None and idx < len(todas_aulas) - 1 else None
        )

        ctx["progressos_map"] = dict(
            ProgressoAulaEAD.objects.filter(matricula=matricula)
            .values_list("aula_id", "concluida")
        )
        return ctx


        
@method_decorator(require_POST, name="dispatch")
class EADSalvarProgressoView(LoginRequiredMixin, View):
    """Salva progresso parcial (AJAX). O servidor limita o tempo enviado pelo cliente."""
    http_method_names = ['post']
    MAX_INCREMENTO = 60          # JS envia a cada 30s → 2x de margem
    PCT_CONCLUSAO = Decimal('90')

    def post(self, request, pk):
        funcionario = _get_funcionario(request.user)
        if not funcionario:
            return JsonResponse({'error': 'Usuário sem funcionário vinculado'}, status=403)

        aula = get_object_or_404(
            AulaEAD.objects.select_related('modulo__curso'),
            pk=pk, ativo=True, modulo__ativo=True,
        )
        matricula = MatriculaEAD.objects.filter(
            funcionario=funcionario, curso=aula.modulo.curso,
        ).exclude(status__in=[MatriculaEAD.Status.CANCELADO, MatriculaEAD.Status.EXPIRADO]).first()
        if not matricula:
            return JsonResponse({'error': 'Matrícula não encontrada'}, status=404)

        try:
            data = json.loads(request.body or '{}')
            delta = max(0, min(int(data.get('tempo_delta_segundos', 0)), self.MAX_INCREMENTO))
            pct = max(Decimal('0'), min(Decimal(str(data.get('percentual_assistido', 0))), Decimal('100')))
            pos = max(0, int(data.get('video_posicao_segundos', 0)))
            dur = max(0, int(data.get('video_duracao_total', 0)))
        except (ValueError, TypeError, InvalidOperation, json.JSONDecodeError):
            return JsonResponse({'error': 'Dados inválidos'}, status=400)

        with transaction.atomic():
            progresso, _ = ProgressoAulaEAD.objects.select_for_update().get_or_create(
                matricula=matricula, aula=aula, defaults={'iniciado_em': timezone.now()},
            )
            teto = aula.duracao_estimada_min * 60 * 2
            progresso.tempo_gasto_segundos = min(progresso.tempo_gasto_segundos + delta, teto)
            progresso.percentual_assistido = max(progresso.percentual_assistido, pct)
            progresso.video_posicao_segundos = pos
            if dur:
                progresso.video_duracao_total = dur
            progresso.save()

            if not progresso.concluida and progresso.percentual_assistido >= self.PCT_CONCLUSAO:
                progresso.marcar_concluida()      # já chama recalcular_progresso()
            else:
                matricula.recalcular_progresso()

        matricula.refresh_from_db()
        return JsonResponse({
            'ok': True,
            'percentual': float(progresso.percentual_assistido),
            'concluida': progresso.concluida,
            'progresso_curso': float(matricula.progresso_percentual),
            'pode_avaliar': matricula.pode_fazer_avaliacao,
            'aulas_concluidas_ids': list(ProgressoAulaEAD.objects.filter(
                matricula=matricula, concluida=True).values_list('aula_id', flat=True)),

        })

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
    template_name = 'treinamentos/ead/avaliacao.html'
    TOLERANCIA_SEG = 60

    def _sessao_key(self, matricula):
        return f'aval_inicio_{matricula.pk}'

    def _get_matricula(self, request, matricula_id, lock=False):
        funcionario = _get_funcionario(request.user)
        if not funcionario:
            return None
        qs = MatriculaEAD.objects.select_related('curso')
        if lock:
            qs = qs.select_for_update()
        return qs.filter(pk=matricula_id, funcionario=funcionario).first()

    @staticmethod
    def _get_avaliacao(matricula):
        try:
            av = matricula.curso.avaliacao_ead
            return av if av.ativo else None
        except AvaliacaoEAD.DoesNotExist:
            return None

    def get(self, request, matricula_id):
        matricula = self._get_matricula(request, matricula_id)
        if not matricula:
            messages.error(request, 'Matrícula não encontrada.')
            return redirect('treinamentos:ead_meus_cursos')

        if not matricula.pode_fazer_avaliacao:
            messages.warning(
                request,
                f'Complete pelo menos {matricula.curso.percentual_minimo_assistido}% '
                'das aulas e verifique suas tentativas restantes.')
            return redirect('treinamentos:ead_curso_detail', slug=matricula.curso.slug)

        avaliacao = self._get_avaliacao(matricula)
        if not avaliacao:
            messages.error(request, 'Este curso não possui avaliação ativa.')
            return redirect('treinamentos:ead_curso_detail', slug=matricula.curso.slug)

        questoes = list(avaliacao.questoes_ead.filter(ativo=True)
                        .prefetch_related('alternativas_ead').order_by('ordem'))
        if avaliacao.embaralhar_questoes:
            random.shuffle(questoes)
        for q in questoes:
            alts = list(q.alternativas_ead.all())
            if avaliacao.embaralhar_alternativas:
                random.shuffle(alts)
            q.alternativas_embaralhadas = alts

        # Marca o início só uma vez (recarregar a página não zera o relógio)
        key = self._sessao_key(matricula)
        inicio = request.session.setdefault(key, timezone.now().timestamp())
        restante = max(0, int(avaliacao.tempo_limite_min * 60 - (timezone.now().timestamp() - inicio)))

        return render(request, self.template_name, {
            'matricula': matricula,
            'avaliacao': avaliacao,
            'questoes': questoes,
            'tentativa_numero': matricula.tentativas_avaliacao + 1,
            'tempo_restante_seg': restante,
        })

    def post(self, request, matricula_id):
        with transaction.atomic():
            matricula = self._get_matricula(request, matricula_id, lock=True)
            if not matricula or not matricula.pode_fazer_avaliacao:
                messages.error(request, 'Não é possível realizar a avaliação.')
                return redirect('treinamentos:ead_meus_cursos')

            avaliacao = self._get_avaliacao(matricula)
            if not avaliacao:
                messages.error(request, 'Avaliação indisponível.')
                return redirect('treinamentos:ead_curso_detail', slug=matricula.curso.slug)

            inicio = request.session.pop(self._sessao_key(matricula), None)
            if inicio is None:
                messages.error(request, 'Sessão da avaliação inválida. Inicie novamente.')
                return redirect('treinamentos:ead_avaliacao', matricula_id=matricula.pk)

            tempo_esgotado = bool(avaliacao.tempo_limite_min) and (
                timezone.now().timestamp() - inicio > avaliacao.tempo_limite_min * 60 + self.TOLERANCIA_SEG)


            tentativa = TentativaAvaliacaoEAD.objects.create(
                matricula=matricula, avaliacao=avaliacao,
                numero_tentativa=matricula.tentativas_avaliacao + 1,
            )

            questoes = list(avaliacao.questoes_ead.filter(ativo=True).prefetch_related('alternativas_ead'))
            respostas = []
            for q in questoes:
                alt_id = None if tempo_esgotado else request.POST.get(f'questao_{q.pk}')
                alternativa = next((a for a in q.alternativas_ead.all() if str(a.pk) == alt_id), None)
                respostas.append(RespostaAlunoEAD(
                    tentativa=tentativa, questao=q, alternativa_escolhida=alternativa))
            RespostaAlunoEAD.objects.bulk_create(respostas)

            tentativa.calcular_nota()

        if tempo_esgotado:
            messages.warning(request, 'Tempo esgotado: as respostas enviadas fora do prazo foram desconsideradas.')
        return redirect('treinamentos:ead_resultado', tentativa_id=tentativa.pk)

class EADResultadoView(LoginRequiredMixin, DetailView):
    template_name = 'treinamentos/ead/resultado.html'
    context_object_name = 'tentativa'
    pk_url_kwarg = 'tentativa_id'

    def get_queryset(self):
        qs = (TentativaAvaliacaoEAD.objects
              .filter(finalizada_em__isnull=False)
              .select_related('matricula__curso__tipo_curso', 'matricula__certificado_ead'))
        func = _get_funcionario(self.request.user)
        if not func:
            raise Http404
        return qs.filter(matricula__funcionario=func)  # aluno só vê a própria tentativa

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        t = self.object
        m = t.matricula
        curso = m.curso
        nota_ok = t.nota is not None and t.nota >= curso.nota_minima
        ch_ok = m.carga_horaria_atingida
        restantes = max(0, curso.max_tentativas_avaliacao - m.tentativas_avaliacao)
        mostrar_gabarito = nota_ok or restantes == 0

        # 2. Gabarito (2 queries, sem N+1)
        respostas = (RespostaAlunoEAD.objects
                     .filter(tentativa=t)
                     .select_related('questao', 'alternativa_escolhida')
                     .prefetch_related(Prefetch(
                         'questao__alternativas_ead',
                         queryset=AlternativaEAD.objects.order_by('ordem'),
                     ))
                     .order_by('questao__ordem'))
        gabarito = [{
            'questao': r.questao,
            'alternativas': r.questao.alternativas_ead.all(),
            'escolhida': r.alternativa_escolhida,
            'acertou': r.esta_correta,
        } for r in respostas]

        ctx.update({
            'matricula': m,
            'nota_ok': nota_ok,
            'ch_ok': ch_ok,
            'aprovado_completo': nota_ok and ch_ok,
            'tentativas_restantes': restantes,
            'mostrar_gabarito': mostrar_gabarito,  # evita cola na próxima tentativa
            'gabarito': gabarito,
            'total_questoes': len(gabarito),
            'total_acertos': sum(g['acertou'] for g in gabarito),
        })
        return ctx


class EADCertificadoView(RateLimitPublicMixin, DetailView):
    model = CertificadoEAD
    template_name = 'treinamentos/ead/certificado.html'
    context_object_name = 'certificado'
    slug_field = slug_url_kwarg = 'uuid'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        c = self.object
        dono = getattr(self.request.user, 'funcionario', None) == c.matricula.funcionario
        gestor = self.request.user.has_perm('treinamentos.gerar_certificados')
        ctx['nome_exibicao'] = c.nome_funcionario if (dono or gestor) else mascarar_nome(c.nome_funcionario)
        ctx['cpf_exibicao'] = mascarar_cpf(c.cpf_funcionario)
        return ctx


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
