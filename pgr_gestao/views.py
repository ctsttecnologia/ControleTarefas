"""
Views do módulo PGR — Parte 1 (imports, helpers, dashboard, Empresa).

Escopo de filial e de técnico vem de pgr_gestao.selectors
(documentos_visiveis / riscos_visiveis / planos_visiveis).
"""
import json
from django.views import View
import openpyxl
from io import BytesIO
from datetime import date, datetime, timedelta
from pgr_gestao.services import prazo_para
from .conformidade import verificar
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count, Q, Sum, ProtectedError, F
from django.db.models.functions import TruncMonth
from django.forms import inlineformset_factory
from django.http import FileResponse, Http404, JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView,
)

from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from dal import autocomplete

from cliente.models import Cliente
from core.decorators import funcionario_required
from core.mixins import FilialCreateMixin
from core.utils import get_filial_ativa, usuario_ve_todas_filiais
from pgr_gestao.audit import audit
from pgr_gestao.selectors import (
    documentos_visiveis,
    riscos_visiveis,
    planos_visiveis,
    ordenar_por,
    ORDEM_CLASSIFICACAO,
)
from collections import Counter
from .mixins import (
    PGRBaseMixin,
    PGRSoftDeleteMixin,
    PGRTecnicoBaseMixin,
    PGRRequestFormKwargsMixin,
)
from .models import (
    PGRDocumento, PGRRevisao,
    GESGrupoExposicao, RiscoIdentificado, AvaliacaoQuantitativa,
    PlanoAcaoPGR, 
    CronogramaAcaoPGR,
    RiscoEPIRecomendado, RiscoTreinamentoNecessario,
    Empresa, LocalPrestacaoServico, ProfissionalResponsavel,
    AmbienteTrabalho, AnexoPGR, TipoRisco,
    STATUS_CHOICES, STATUS_PGR_CHOICES,
    CLASSIFICACAO_RISCO_CHOICES, TIPO_AVALIACAO_CHOICES,
    CLASSIFICACOES_CRITICAS, STATUS_RISCO_PENDENTE, ORDEM_CLASSIFICACAO
)
from .forms import (
    AcompanhamentoPlanoAcaoForm, AnexoPlanoAcaoForm, AvaliacaoQuantitativaForm, CronogramaAcaoPGRForm, EmpresaForm,
    LocalPrestacaoServicoForm, PGRDocumentoForm, PGRRevisaoForm,
    GESGrupoExposicaoForm, ProfissionalResponsavelForm,
    RiscoIdentificadoForm, PlanoAcaoPGRForm,
    ResponsavelFormSet, AnexoPGRForm, AnexoPGRMultipleForm, validar_arquivo,
)
from .utils.cont_seguranca import validar_acesso_documento
import logging

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import (
    Count, Max, ProtectedError, Q, RestrictedError, Sum,
)
from django.template.loader import render_to_string
from django.utils.dateparse import parse_date
from django.utils.functional import cached_property
from django.utils.text import slugify

from pgr_gestao.selectors import (
    ORDEM_CLASSIFICACAO, ORDEM_PRIORIDADE,
    documentos_visiveis, ordenar_por, planos_visiveis, riscos_visiveis
)



logger = logging.getLogger(__name__)


XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
CRITICOS = ['critico', 'muito_grave']
PENDENTES = ['pendente', 'em_andamento']
MAX_ANEXO_BYTES = 50 * 1024 * 1024
PLANO_PENDENTES = ['pendente', 'em_andamento']
PLANO_LOOKUP_TECNICO = 'risco_identificado__pgr_documento__criado_por'

STATUS_PLANO_ABERTO = ('pendente', 'em_andamento', 'atrasado')  # ⚠ confira STATUS do model
STATUS_PLANO_CONCLUIDO = 'concluido'

PLANO_FILIAL_FIELD = 'risco_identificado__pgr_documento__filial'
PLANO_TECNICO_LOOKUP = 'risco_identificado__pgr_documento__criado_por'
CRONOGRAMA_FILIAL_FIELD = 'pgr_documento__filial'
CRONOGRAMA_TECNICO_LOOKUP = 'pgr_documento__criado_por'

PRAZO_DIAS = {
    # classificacao_risco
    'critico': 15,
    'muito_grave': 30,
    'moderado': 90,
    'marginal': 180,
    'negligenciavel': 365,
    # prioridade_acao (fallback)
    'critica': 15,
    'alta': 30,
    'media': 90,
    'baixa': 180,
}
MESES_ABREV = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun',
               'jul', 'ago', 'set', 'out', 'nov', 'dez']
CATEGORIA_LABELS = {
    'fisico': 'Físico', 'quimico': 'Químico', 'biologico': 'Biológico',
    'ergonomico': 'Ergonômico', 'acidente': 'Acidente', 'mecanico': 'Mecânico',
}
ORDEM_CLASSIF = ['critico', 'muito_grave', 'moderado', 'marginal', 'negligenciavel']



# =============================================================================
# HELPERS INTERNOS
# =============================================================================

def _get_filial_info(request):
    """Nome da filial ativa e flag de acesso global, para o contexto."""
    filial = get_filial_ativa(request.user, request)
    return (filial.nome if filial else None), usuario_ve_todas_filiais(request.user)


def _pct(parte, total):
    """Percentual com 1 casa decimal; 0 se total for 0."""
    return round((parte / total) * 100, 1) if total else 0


# =============================================================================
# AUTOCOMPLETE
# =============================================================================

class ClienteAutocomplete(autocomplete.Select2QuerySetView):
    """Autocomplete de clientes — exige autenticação e respeita a filial."""

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Cliente.objects.none()

        qs = Cliente.objects.for_request(self.request)
        if self.q:
            qs = qs.filter(
                Q(razao_social__icontains=self.q) | Q(nome__icontains=self.q)
            )
        return qs.order_by('razao_social')


# =============================================================================
# DASHBOARD GERENCIAL
# =============================================================================

@funcionario_required
@permission_required('pgr_gestao.view_pgrdocumento', raise_exception=True)
def dashboard_gerencial_view(request):
    """Dashboard gerencial: KPIs, tendências de 12 meses e SLA de planos."""
    hoje = timezone.localdate()

    def _mes_label(d):
        """'out/26' sempre em português, independente do locale do servidor."""
        return f"{MESES_ABREV[d.month - 1]}/{d.strftime('%y')}"

    def _serie(dados, rotulos, ordem=None):
        """dict {chave: total} -> {'keys','labels','data'} serializável."""
        chaves = [k for k in (ordem or list(dados)) if k in dados]
        return {
            'keys': chaves,
            'labels': [rotulos.get(k, k) for k in chaves],
            'data': [dados[k] for k in chaves],
        }

    # ---------------------------------------------------------------------
    # 1. Querysets base (filial + escopo de técnico via selectors)
    # ---------------------------------------------------------------------
    documentos_qs = documentos_visiveis(request)
    riscos_qs = riscos_visiveis(request)
    planos_qs = planos_visiveis(request)
    ges_qs = GESGrupoExposicao.objects.for_request(request).filter(
        pgr_documento__in=documentos_qs
    )
    revisoes_qs = PGRRevisao.objects.for_request(request).filter(
        pgr_documento__in=documentos_qs
    )

    # ---------------------------------------------------------------------
    # 2. Documentos
    # ---------------------------------------------------------------------
    status_docs_data = {
        i['status']: i['total']
        for i in documentos_qs.values('status').annotate(total=Count('id'))
    }
    total_documentos = sum(status_docs_data.values())
    documentos_vigentes = status_docs_data.get('vigente', 0)
    documentos_vencidos = status_docs_data.get('vencido', 0)
    documentos_em_revisao = status_docs_data.get('em_revisao', 0)
    taxa_conformidade_docs = _pct(documentos_vigentes, total_documentos)

    def _vencendo(ate, depois_de=None):
        qs = documentos_qs.filter(
            data_vencimento__lte=hoje + timedelta(days=ate)
        )
        if depois_de is None:
            return qs.filter(data_vencimento__gte=hoje).count()
        return qs.filter(
            data_vencimento__gt=hoje + timedelta(days=depois_de)
        ).count()

    docs_vencendo_30 = _vencendo(30)
    docs_vencendo_60 = _vencendo(60, 30)
    docs_vencendo_90 = _vencendo(90, 60)

    documentos_a_vencer = documentos_qs.filter(
        data_vencimento__lte=hoje + timedelta(days=60),
        data_vencimento__gte=hoje,
    ).select_related('empresa').order_by('data_vencimento')[:10]

    # ---------------------------------------------------------------------
    # 3. Riscos
    # ---------------------------------------------------------------------
    labels_class = dict(CLASSIFICACAO_RISCO_CHOICES)
    class_data = {
        i['classificacao_risco']: i['total']
        for i in riscos_qs.values('classificacao_risco')
        .annotate(total=Count('id')).order_by('classificacao_risco')
    }
    total_riscos = sum(class_data.values())

    riscos_por_classificacao = [
        {
            'classificacao_risco': k,
            'label': labels_class.get(k, k),
            'total': v,
        }
        for k, v in class_data.items()
    ]

    riscos_criticos_count = class_data.get('critico', 0)
    riscos_muito_graves_count = class_data.get('muito_grave', 0)
    riscos_moderados_count = class_data.get('moderado', 0)
    riscos_marginais_count = class_data.get('marginal', 0)
    riscos_negligenciaveis_count = class_data.get('negligenciavel', 0)

    # Índice de severidade ponderado (0-100)
    pesos = {'critico': 10, 'muito_grave': 7, 'moderado': 4,
             'marginal': 2, 'negligenciavel': 1}
    severidade_total = sum(pesos.get(k, 0) * v for k, v in class_data.items())
    indice_severidade = _pct(severidade_total, total_riscos * 10)

    riscos_por_status = list(
        riscos_qs.values('status_controle').annotate(total=Count('id'))
    )
    status_riscos_data = {
        i['status_controle']: i['total'] for i in riscos_por_status
    }
    riscos_controlados = status_riscos_data.get('controlado', 0)
    riscos_em_controle = status_riscos_data.get('em_controle', 0)
    riscos_identificados = status_riscos_data.get('identificado', 0)
    taxa_controle_riscos = _pct(riscos_controlados, total_riscos)

    riscos_criticos_pendentes = ordenar_por(
        riscos_qs.filter(
            classificacao_risco__in=['critico', 'muito_grave'],
        ).exclude(
            status_controle__in=['controlado', 'eliminado'],
        ).select_related('tipo_risco', 'ges', 'pgr_documento'),
        'classificacao_risco', ORDEM_CLASSIFICACAO,
    )[:10]

    top_tipos_risco = [
        {
            'nome': i['tipo_risco__nome'],
            'categoria': CATEGORIA_LABELS.get(i['tipo_risco__categoria'], i['tipo_risco__categoria']),
            'total': i['total'],
        }
        for i in riscos_qs.values('tipo_risco__nome', 'tipo_risco__categoria')
        .annotate(total=Count('id')).order_by('-total')[:5]
    ]
    top_ges_criticos = [
        {
            'nome': i['ges__nome'],
            'empresa': i['ges__pgr_documento__empresa__razao_social'],
            'total': i['total'],
        }
        for i in riscos_qs.filter(classificacao_risco__in=['critico', 'muito_grave'])
        .values('ges__nome', 'ges__pgr_documento__empresa__razao_social')
        .annotate(total=Count('id')).order_by('-total')[:5]
    ]


    # ---------------------------------------------------------------------
    # 4. Planos de ação
    # ---------------------------------------------------------------------
    status_planos_data = {
        i['status']: i['total']
        for i in planos_qs.values('status').annotate(total=Count('id'))
    }
    total_planos = sum(status_planos_data.values())
    planos_pendentes = status_planos_data.get('pendente', 0)
    planos_em_andamento = status_planos_data.get('em_andamento', 0)
    planos_concluidos = status_planos_data.get('concluido', 0)

    planos_atrasados = planos_qs.filter(
        status__in=['pendente', 'em_andamento'],
        data_prevista__lt=hoje,
    ).count()
    status_planos_data['atrasado'] = planos_atrasados

    taxa_conclusao_planos = _pct(planos_concluidos, total_planos)
    taxa_atraso_planos = _pct(planos_atrasados, total_planos)

    # SLA: tempo médio (dias) entre criação e conclusão. Calculado em Python
    # para não depender de aritmética de datas do banco.
    duracoes = [
        (conclusao - timezone.localtime(criado).date()).days
        for conclusao, criado in planos_qs.filter(
            status='concluido',
            data_conclusao__isnull=False,
            criado_em__isnull=False,
        ).values_list('data_conclusao', 'criado_em')
    ]
    tempo_medio_dias = round(sum(duracoes) / len(duracoes)) if duracoes else 0

    # ---------------------------------------------------------------------
    # 5. Tendências (12 meses)
    # ---------------------------------------------------------------------
    doze_meses_atras = hoje - timedelta(days=365)

    riscos_mes = riscos_qs.filter(
        data_identificacao__gte=doze_meses_atras
    ).annotate(mes=TruncMonth('data_identificacao')).values('mes').annotate(
        total=Count('id'),
        criticos=Count('id', filter=Q(
            classificacao_risco__in=['critico', 'muito_grave']
        )),
    ).order_by('mes')
    riscos_mes = [i for i in riscos_mes if i['mes']]

    planos_mes = planos_qs.filter(
        criado_em__date__gte=doze_meses_atras
    ).annotate(mes=TruncMonth('criado_em')).values('mes').annotate(
        criados=Count('id'),
        concluidos=Count('id', filter=Q(status='concluido')),
    ).order_by('mes')
    planos_mes = [i for i in planos_mes if i['mes']]

    # ---------------------------------------------------------------------
    # 6. Complementos e saúde geral
    # ---------------------------------------------------------------------
    total_ges = ges_qs.filter(ativo=True).count()
    total_revisoes = revisoes_qs.count()
    ultimas_revisoes = revisoes_qs.select_related(
        'pgr_documento', 'pgr_documento__empresa'
    ).order_by('-data_realizacao')[:5]
    ultimos_planos = planos_qs.select_related(
        'risco_identificado', 'risco_identificado__pgr_documento'
    ).order_by('-criado_em')[:5]

    # 40% conformidade docs + 30% controle de riscos + 30% conclusão de planos
    saude_geral = round(
        taxa_conformidade_docs * 0.4
        + taxa_controle_riscos * 0.3
        + taxa_conclusao_planos * 0.3,
        1,
    )
    if saude_geral >= 80:
        saude_status, saude_cor, saude_icone = 'excelente', 'success', 'bi-emoji-smile'
    elif saude_geral >= 60:
        saude_status, saude_cor, saude_icone = 'boa', 'info', 'bi-emoji-neutral'
    elif saude_geral >= 40:
        saude_status, saude_cor, saude_icone = 'regular', 'warning', 'bi-emoji-expressionless'
    else:
        saude_status, saude_cor, saude_icone = 'crítica', 'danger', 'bi-emoji-frown'

    filial_info, acesso_global = _get_filial_info(request)

    charts = {
        'docs': _serie(
            status_docs_data, dict(STATUS_PGR_CHOICES),
            ['vigente', 'em_revisao', 'vencido', 'elaboracao', 'cancelado'],
        ),
        'riscos': _serie(class_data, labels_class, ORDEM_CLASSIF),
        'planos': _serie(
            status_planos_data,
            {'pendente': 'Pendentes', 'em_andamento': 'Em andamento',
            'concluido': 'Concluídos', 'atrasado': 'Atrasados (prazo vencido)'},
            ['pendente', 'em_andamento', 'concluido', 'atrasado'],
        ),
        'riscos_mes': {
            'labels': [_mes_label(i['mes']) for i in riscos_mes],
            'total': [i['total'] for i in riscos_mes],
            'criticos': [i['criticos'] for i in riscos_mes],
        },
        'planos_mes': {
            'labels': [_mes_label(i['mes']) for i in planos_mes],
            'criados': [i['criados'] for i in planos_mes],
            'concluidos': [i['concluidos'] for i in planos_mes],
        },
    }

    # ---------------------------------------------------------------------
    # 7. Contexto
    # ---------------------------------------------------------------------
    context = {
        # Documentos
        'total_documentos': total_documentos,
        'documentos_vigentes': documentos_vigentes,
        'documentos_vencidos': documentos_vencidos,
        'documentos_em_revisao': documentos_em_revisao,
        'status_docs_data': status_docs_data,
        'taxa_conformidade_docs': taxa_conformidade_docs,
        'docs_vencendo_30': docs_vencendo_30,
        'docs_vencendo_60': docs_vencendo_60,
        'docs_vencendo_90': docs_vencendo_90,
        'documentos_a_vencer': documentos_a_vencer,
        'documentos_proximo_vencimento': documentos_a_vencer,

        # Riscos
        'total_riscos': total_riscos,
        'riscos_por_classificacao': riscos_por_classificacao,
        'riscos_criticos_count': riscos_criticos_count,
        'riscos_muito_graves_count': riscos_muito_graves_count,
        'riscos_moderados_count': riscos_moderados_count,
        'riscos_marginais_count': riscos_marginais_count,
        'riscos_negligenciaveis_count': riscos_negligenciaveis_count,
        'indice_severidade': indice_severidade,
        'riscos_por_status': riscos_por_status,
        'riscos_controlados': riscos_controlados,
        'riscos_em_controle': riscos_em_controle,
        'riscos_identificados': riscos_identificados,
        'taxa_controle_riscos': taxa_controle_riscos,
        'riscos_criticos': riscos_criticos_pendentes,
        'riscos_criticos_pendentes': riscos_criticos_pendentes,
        'top_tipos_risco': top_tipos_risco,
        'top_ges_criticos': top_ges_criticos,

        # Planos
        'total_planos': total_planos,
        'planos_pendentes': planos_pendentes,
        'planos_em_andamento': planos_em_andamento,
        'planos_concluidos': planos_concluidos,
        'planos_atrasados': planos_atrasados,
        'status_planos_data': status_planos_data,
        'taxa_conclusao_planos': taxa_conclusao_planos,
        'taxa_atraso_planos': taxa_atraso_planos,
        'tempo_medio_dias': tempo_medio_dias,

        # Tendências
        'riscos_por_mes_labels': [i['mes'].strftime('%b/%y') for i in riscos_mes],
        'riscos_por_mes_total': [i['total'] for i in riscos_mes],
        'riscos_por_mes_criticos': [i['criticos'] for i in riscos_mes],
        'planos_evolucao_labels': [i['mes'].strftime('%b/%y') for i in planos_mes],
        'planos_evolucao_criados': [i['criados'] for i in planos_mes],
        'planos_evolucao_concluidos': [i['concluidos'] for i in planos_mes],

        # Complementos
        'total_ges': total_ges,
        'total_revisoes': total_revisoes,
        'ultimas_revisoes': ultimas_revisoes,
        'ultimos_planos': ultimos_planos,

        # Saúde geral
        'saude_geral': saude_geral,
        'saude_status': saude_status,
        'saude_cor': saude_cor,
        'saude_icone': saude_icone,

        # Contexto
        'filial_info': filial_info,
        'acesso_global': acesso_global,

        'charts': charts,
    }
    return render(request, 'pgr_gestao/dashboard_gerencial.html', context)


# =============================================================================
# EMPRESAS
# =============================================================================

class EmpresaListView(PGRBaseMixin, ListView):
    model = Empresa
    template_name = 'pgr_gestao/empresa_list.html'
    context_object_name = 'empresas'
    paginate_by = 20
    permission_required = 'pgr_gestao.view_empresa'

    def get_queryset(self):
        self.base_qs = super().get_queryset()
        queryset = self.base_qs.select_related('cliente', 'filial')

        tipo = self.request.GET.get('tipo')
        grau_risco = self.request.GET.get('grau_risco')
        ativo = self.request.GET.get('ativo')
        search = self.request.GET.get('search')

        if tipo:
            queryset = queryset.filter(tipo_empresa=tipo)
        if grau_risco:
            queryset = queryset.filter(grau_risco=grau_risco)
        if ativo in ('true', 'false'):
            queryset = queryset.filter(ativo=(ativo == 'true'))
        if search:
            queryset = queryset.filter(
                Q(cliente__razao_social__icontains=search) |
                Q(cliente__nome__icontains=search) |
                Q(cnpj__icontains=search) |
                Q(descricao_cnae__icontains=search)
            )
        return queryset.order_by('cliente__razao_social')

    def get(self, request, *args, **kwargs):
        if request.GET.get('export') == 'excel':
            return self.exportar_excel()
        return super().get(request, *args, **kwargs)

    def exportar_excel(self):
        headers = ['Razão Social', 'CNPJ', 'Tipo', 'CNAE', 'Grau de Risco',
                   'Empregados', 'Cidade', 'UF', 'Ativa']
        linhas = (
            [e.cliente.razao_social, e.cnpj, e.get_tipo_empresa_display(),
             e.cnae_especifico or '', e.grau_risco, e.numero_empregados,
             e.cidade or '', e.estado or '', 'Sim' if e.ativo else 'Não']
            for e in self.get_queryset()
        )
        audit(self.request, 'exportar_empresas')
        return _xlsx_response(
            'Empresas', headers, linhas,
            f"empresas_{timezone.localdate():%Y%m%d}.xlsx",
            {'A': 40, 'B': 22, 'D': 18, 'G': 22},
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        docs = documentos_visiveis(self.request).order_by()

        resumo = self.base_qs.aggregate(
            total=Count('id'), ativas=Count('id', filter=Q(ativo=True)),
        )
        context['total_empresas'] = resumo['total']
        context['empresas_ativas'] = resumo['ativas']
        context['total_pgrs'] = docs.filter(
            empresa_id__in=self.base_qs.values('cliente_id')
        ).count()

        # PGRDocumento aponta para Cliente: conta por cliente_id, sem N+1
        empresas = list(context['empresas'])
        contagem = dict(
            docs.filter(empresa_id__in=[e.cliente_id for e in empresas])
            .values_list('empresa_id').annotate(n=Count('id'))
        )
        for e in empresas:
            e.total_pgrs = contagem.get(e.cliente_id, 0)
        context['empresas'] = empresas
        return context

class EmpresaDetailView(PGRBaseMixin, DetailView):
    model = Empresa
    template_name = 'pgr_gestao/empresa_detail.html'
    context_object_name = 'empresa'
    permission_required = 'pgr_gestao.view_empresa'

    def get_queryset(self):
        return super().get_queryset().select_related('cliente', 'filial')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        empresa = self.object

        documentos = list(
            documentos_visiveis(self.request)
            .filter(empresa_id=empresa.cliente_id)
            .select_related('local_prestacao')
            .order_by('-data_elaboracao')
        )
        por_local = Counter(d.local_prestacao_id for d in documentos)

        locais = list(
            LocalPrestacaoServico.objects.for_request(self.request)
            .filter(empresa_id=empresa.cliente_id, ativo=True)
        )
        for l in locais:
            l.total_pgrs = por_local.get(l.pk, 0)

        riscos = riscos_visiveis(self.request).filter(
            pgr_documento__empresa_id=empresa.cliente_id
        ).aggregate(
            total=Count('id'),
            criticos=Count('id', filter=Q(classificacao_risco__in=CLASSIFICACOES_CRITICAS)),
        )

        context.update({
            'documentos_pgr': documentos,
            'locais_prestacao': locais,
            'pgrs_vigentes': sum(d.status == 'vigente' for d in documentos),
            'pgrs_vencidos': sum(d.status == 'vencido' for d in documentos),
            'total_riscos': riscos['total'],
            'riscos_criticos': riscos['criticos'],
        })
        return context

class EmpresaCreateView(PGRBaseMixin, PGRRequestFormKwargsMixin, FilialCreateMixin, CreateView):
    model = Empresa
    form_class = EmpresaForm
    template_name = 'pgr_gestao/empresa_form.html'
    permission_required = 'pgr_gestao.add_empresa'
    success_url = reverse_lazy('pgr_gestao:empresa_list')

    def form_valid(self, form):
        response = super().form_valid(form)  # FilialCreateMixin define a filial e salva
        if _is_ajax(self.request):
            return JsonResponse({
                'success': True,
                'id': self.object.pk,
                'razao_social': str(self.object),
            })
        return response

    def form_invalid(self, form):
        if _is_ajax(self.request):
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
        return super().form_invalid(form)


class EmpresaUpdateView(PGRBaseMixin, PGRRequestFormKwargsMixin, UpdateView):
    model = Empresa
    form_class = EmpresaForm
    template_name = 'pgr_gestao/empresa_form.html'
    permission_required = 'pgr_gestao.change_empresa'

    def get_success_url(self):
        return reverse_lazy('pgr_gestao:empresa_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, 'Empresa atualizada com sucesso!')
        return super().form_valid(form)


class EmpresaDeleteView(PGRBaseMixin, DeleteView):
    model = Empresa
    template_name = 'pgr_gestao/empresa_confirm_delete.html'
    permission_required = 'pgr_gestao.delete_empresa'
    success_url = reverse_lazy('pgr_gestao:empresa_list')

    def form_valid(self, form):
        # No Django 4+, DeleteView.post() chama form_valid(); delete() não é
        # mais executado, então a mensagem precisa ficar aqui.
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                'Esta empresa possui locais, documentos ou outros registros '
                'vinculados. Inative-a em vez de excluir.',
            )
            return redirect('pgr_gestao:empresa_detail', pk=self.object.pk)
        messages.success(self.request, 'Empresa excluída com sucesso!')
        return response

# =============================================================================
# PARTE 2A — Documentos, Revisões, GES, Riscos, Avaliações
# -----------------------------------------------------------------------------
# Imports a acrescentar no topo (se ainda não existirem da Parte 1):
#   from django.core.exceptions import PermissionDenied
#   from django.db import transaction
#   from django.db.models import Count, Q, Sum, ProtectedError
#   from django.utils.functional import cached_property
#   from .selectors import documentos_visiveis, ordenar_por, ORDEM_PRIORIDADE
#
# Pré-requisitos: FilialCreateMixin na versão da seção 3.5 da auditoria e
# filial_field correto nos models filhos (tabela 2.1).
# =============================================================================


def _ges_visiveis(request):
    return GESGrupoExposicao.objects.for_request(request).filter(
        pgr_documento__in=documentos_visiveis(request)
    )


# =============================================================================
# DOCUMENTOS PGR
# =============================================================================

class PGRDocumentoListView(PGRTecnicoBaseMixin, ListView):
    model = PGRDocumento
    template_name = 'pgr_gestao/documento_list.html'
    context_object_name = 'documentos'
    paginate_by = 20
    permission_required = 'pgr_gestao.view_pgrdocumento'
    tecnico_scope_lookup = 'criado_por'

    def get_queryset(self):
        # Base sem filtros de tela: os cards mostram o total do escopo do usuário.
        self.base_qs = super().get_queryset()
        queryset = self.base_qs.select_related(
            'empresa', 'local_prestacao'
        ).prefetch_related('responsaveis')

        status = self.request.GET.get('status')
        empresa_id = self.request.GET.get('empresa')
        search = self.request.GET.get('search')

        if status:
            queryset = queryset.filter(status=status)
        if empresa_id:
            queryset = queryset.filter(empresa_id=empresa_id)
        if search:
            queryset = queryset.filter(
                Q(codigo_documento__icontains=search) |
                Q(empresa__razao_social__icontains=search)
            )
        return queryset.order_by('-data_elaboracao')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # PGRDocumento.empresa aponta para Cliente (não para pgr_gestao.Empresa):
        # o filtro por id só funciona se o select listar Clientes.
        context['empresas'] = Cliente.objects.for_request(self.request).filter(
            pk__in=self.base_qs.order_by().values('empresa_id')
        ).order_by('razao_social')
        context['status_choices'] = STATUS_PGR_CHOICES

        resumo = self.base_qs.order_by().aggregate(
            total=Count('id'),
            vigentes=Count('id', filter=Q(status='vigente')),
            vencidos=Count('id', filter=Q(status='vencido')),
            em_revisao=Count('id', filter=Q(status='em_revisao')),
        )
        context['total_documentos'] = resumo['total']
        context['docs_vigentes'] = resumo['vigentes']
        context['docs_vencidos'] = resumo['vencidos']
        context['docs_em_revisao'] = resumo['em_revisao']

        params = self.request.GET.copy()
        params.pop('page', None)
        context['get_params'] = params.urlencode()
        return context


class PGRDocumentoDetailView(PGRTecnicoBaseMixin, DetailView):
    model = PGRDocumento
    template_name = 'pgr_gestao/documento_detail.html'
    context_object_name = 'documento'
    permission_required = 'pgr_gestao.view_pgrdocumento'
    tecnico_scope_lookup = 'criado_por'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        documento = self.object

        context.setdefault(
            'responsaveis_formset',
            ResponsavelFormSet(instance=documento, prefix='responsaveis', request=self.request),
        )

        context['revisoes'] = documento.revisoes.order_by('-numero_revisao')
        context['grupos_exposicao'] = documento.grupos_exposicao.filter(
            ativo=True
        ).select_related('cargo', 'funcao')

        riscos = RiscoIdentificado.objects.filter(pgr_documento=documento)
        resumo = riscos.aggregate(
            total=Count('id'),
            criticos=Count('id', filter=Q(classificacao_risco__in=CLASSIFICACOES_CRITICAS)),
            controlados=Count('id', filter=Q(status_controle='controlado')),
        )
        context['total_riscos'] = resumo['total']
        context['riscos_criticos'] = resumo['criticos']
        context['riscos_controlados'] = resumo['controlados']
        rotulos = dict(CLASSIFICACAO_RISCO_CHOICES)
        context['riscos_stats'] = [
            {
                'classificacao_risco': i['classificacao_risco'],
                'label': rotulos.get(i['classificacao_risco'], i['classificacao_risco']),
                'total': i['total'],
            }
            for i in riscos.values('classificacao_risco').annotate(
                total=Count('id')
            ).order_by('classificacao_risco')
        ]
        context['riscos'] = ordenar_por(
            riscos.select_related('tipo_risco', 'ges'),
            'prioridade_acao', ORDEM_PRIORIDADE, '-data_identificacao',
        )

        context['cronograma'] = documento.cronograma_acoes.order_by('numero_item')
        context['planos_acao'] = ordenar_por(
            PlanoAcaoPGR.objects.filter(
                risco_identificado__pgr_documento=documento
            ).select_related('risco_identificado'),
            'prioridade', ORDEM_PRIORIDADE, 'data_prevista',
        )
        context['anexos_pgr'] = documento.anexos_pgr.order_by('ordem', 'numero_romano')

        r = PlanoAcaoPGR.objects.filter(
            risco_identificado__pgr_documento=documento
        ).aggregate(
            pendentes=Count('id', filter=Q(status='pendente')),
            andamento=Count('id', filter=Q(status='em_andamento')),
            concluidos=Count('id', filter=Q(status='concluido')),
        )
        context['planos_pendentes'] = r['pendentes']
        context['planos_em_andamento'] = r['andamento']
        context['planos_concluidos'] = r['concluidos']
        return context

    def post(self, request, *args, **kwargs):
        # A rota é de visualização; salvar responsáveis exige permissão de edição.
        if not request.user.has_perm('pgr_gestao.change_pgrdocumento'):
            raise PermissionDenied
        self.object = self.get_object()
        formset = ResponsavelFormSet(
                request.POST, instance=self.object, prefix='responsaveis', request=request
        )
        if formset.is_valid():
            formset.save()
            messages.success(request, 'Responsáveis atualizados com sucesso!')
            return redirect('pgr_gestao:documento_detail', pk=self.object.pk)
        return self.render_to_response(
            self.get_context_data(responsaveis_formset=formset)
        )

    


class PGRDocumentoCreateView(PGRBaseMixin, PGRRequestFormKwargsMixin, FilialCreateMixin, CreateView):
    model = PGRDocumento
    form_class = PGRDocumentoForm
    template_name = 'pgr_gestao/documento_form.html'
    permission_required = 'pgr_gestao.add_pgrdocumento'
    success_url = reverse_lazy('pgr_gestao:documento_list')

    def get_initial(self):
        initial = super().get_initial()
        cliente_id = self.request.GET.get('empresa')
        if cliente_id and cliente_id.isdigit() and Cliente.objects.for_request(
            self.request
        ).filter(pk=cliente_id).exists():
            initial['empresa'] = int(cliente_id)
        return initial

    def form_valid(self, form):
        # FilialCreateMixin define a filial (get_filial_ativa) e trata IntegrityError.
        form.instance.criado_por = self.request.user
        return super().form_valid(form)


class PGRDocumentoUpdateView(PGRBaseMixin, PGRRequestFormKwargsMixin, UpdateView):
    model = PGRDocumento
    form_class = PGRDocumentoForm
    template_name = 'pgr_gestao/documento_form.html'
    permission_required = 'pgr_gestao.change_pgrdocumento'

    def get_success_url(self):
        return reverse('pgr_gestao:documento_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, 'Documento PGR atualizado com sucesso!')
        return super().form_valid(form)


class PGRDocumentoDeleteView(PGRSoftDeleteMixin, PGRTecnicoBaseMixin, DeleteView):
    model = PGRDocumento
    permission_required = 'pgr_gestao.delete_pgrdocumento'
    tecnico_scope_lookup = 'criado_por'
    template_name = 'pgr_gestao/documento_confirm_delete.html'
    success_url = reverse_lazy('pgr_gestao:documento_list')


# =============================================================================
# REVISÕES
# =============================================================================

class PGRRevisaoCreateView(PGRBaseMixin, CreateView):
    model = PGRRevisao
    form_class = PGRRevisaoForm
    template_name = 'pgr_gestao/revisao_form.html'
    permission_required = 'pgr_gestao.add_pgrrevisao'

    @cached_property
    def pgr(self):
        pgr_id = self.kwargs.get('pgr_id')
        if not pgr_id:
            return None
        return get_object_or_404(documentos_visiveis(self.request), pk=pgr_id)

    def get_initial(self):
        initial = super().get_initial()
        if self.pgr:
            initial['pgr_documento'] = self.pgr
            ultima = self.pgr.revisoes.order_by('-numero_revisao').values_list(
                'numero_revisao', flat=True
            ).first()
            initial['numero_revisao'] = 0 if ultima is None else ultima + 1
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.pgr:
            context['pgr_documento'] = self.pgr
        return context

    def form_valid(self, form):
        if self.pgr and not form.instance.pgr_documento_id:
            form.instance.pgr_documento = self.pgr
        pgr = form.instance.pgr_documento

        # Nunca confie no pgr_documento vindo do POST.
        if not documentos_visiveis(self.request).filter(pk=pgr.pk).exists():
            raise PermissionDenied

        form.instance.criado_por = self.request.user
        form.instance.filial_id = pgr.filial_id

        with transaction.atomic():
            response = super().form_valid(form)
            pgr.data_ultima_revisao = form.instance.data_realizacao
            pgr.versao_atual = form.instance.numero_revisao + 1
            pgr.save(update_fields=['data_ultima_revisao', 'versao_atual', 'atualizado_em'])

        messages.success(self.request, 'Revisão registrada com sucesso!')
        return response

    def get_success_url(self):
        return reverse('pgr_gestao:documento_detail', kwargs={'pk': self.object.pgr_documento_id})


class PGRRevisaoDetailView(PGRBaseMixin, DetailView):
    model = PGRRevisao
    template_name = 'pgr_gestao/revisao_detail.html'
    context_object_name = 'revisao'
    permission_required = 'pgr_gestao.view_pgrrevisao'


# =============================================================================
# GES - Grupos de Exposição Similar
# =============================================================================

class GESListView(PGRTecnicoBaseMixin, ListView):
    model = GESGrupoExposicao
    template_name = 'pgr_gestao/ges_list.html'
    context_object_name = 'grupos_exposicao'
    paginate_by = 20
    permission_required = 'pgr_gestao.view_gesgrupoexposicao'
    tecnico_scope_lookup = 'pgr_documento__criado_por'

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'pgr_documento', 'ambiente_trabalho', 'cargo', 'funcao'
        ).annotate(num_riscos=Count('riscos', filter=Q(riscos__excluido_em__isnull=False), distinct=True))

        pgr_id = self.request.GET.get('pgr')
        ambiente_id = self.request.GET.get('ambiente')
        ativo = self.request.GET.get('ativo')
        search = self.request.GET.get('search')

        if pgr_id:
            queryset = queryset.filter(pgr_documento_id=pgr_id)
        if ambiente_id:
            queryset = queryset.filter(ambiente_trabalho_id=ambiente_id)
        if ativo:
            queryset = queryset.filter(ativo=ativo == 'true')
        if search:
            queryset = queryset.filter(
                Q(codigo__icontains=search) |
                Q(nome__icontains=search) |
                Q(descricao_atividades__icontains=search)
            )
        return queryset.order_by('codigo')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['documentos_pgr'] = documentos_visiveis(self.request).filter(
            status='vigente'
        ).select_related('empresa')
        context['ambientes'] = AmbienteTrabalho.objects.for_request(self.request)

        grupos = self.object_list
        resumo = grupos.aggregate(
            total=Count('id'),
            ativos=Count('id', filter=Q(ativo=True)),
            trabalhadores=Sum('numero_trabalhadores'),
        )
        context['total_ges'] = resumo['total']
        context['ges_ativos'] = resumo['ativos']
        context['total_trabalhadores'] = resumo['trabalhadores'] or 0
        context['total_riscos'] = RiscoIdentificado.objects.for_request(
            self.request
        ).filter(ges__in=grupos.order_by().values('pk')).count()
        context['filtrando'] = any(
            self.request.GET.get(k) for k in ('pgr', 'ambiente', 'ativo', 'search')
        )

        return context


class GESDetailView(PGRTecnicoBaseMixin, DetailView):
    model = GESGrupoExposicao
    template_name = 'pgr_gestao/ges_detail.html'
    context_object_name = 'ges'
    permission_required = 'pgr_gestao.view_gesgrupoexposicao'
    tecnico_scope_lookup = 'pgr_documento__criado_por'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ges = self.object
        riscos_qs = ges.riscos.all()

        context['riscos'] = ordenar_por(
            riscos_qs.select_related('tipo_risco'),
            'classificacao_risco', ORDEM_CLASSIFICACAO, 'codigo_risco',
        )

        resumo = riscos_qs.order_by().aggregate(
            total=Count('id'),
            criticos=Count('id', filter=Q(classificacao_risco__in=CLASSIFICACOES_CRITICAS)),
            controlados=Count('id', filter=Q(status_controle='controlado')),
            pendentes=Count('id', filter=Q(status_controle__in=STATUS_RISCO_PENDENTE)),
        )
        context['total_riscos'] = resumo['total']
        context['riscos_criticos'] = resumo['criticos']
        context['riscos_controlados'] = resumo['controlados']
        context['riscos_pendentes'] = resumo['pendentes']

        rotulos = dict(CLASSIFICACAO_RISCO_CHOICES)
        por_classe = riscos_qs.order_by().values('classificacao_risco').annotate(total=Count('id'))
        context['riscos_stats'] = [
            {'classificacao_risco': i['classificacao_risco'],
             'label': rotulos.get(i['classificacao_risco'], i['classificacao_risco']),
             'total': i['total']}
            for i in sorted(por_classe,
                            key=lambda i: -ORDEM_CLASSIFICACAO.get(i['classificacao_risco'], 0))
        ]

        def sem_duplicados(qs, *campos):
            vistos, resultado = set(), []
            for obj in qs:
                chave = tuple(getattr(obj, c) for c in campos)
                if chave not in vistos:
                    vistos.add(chave)
                    resultado.append(obj)
            return resultado

        context['epis_recomendados'] = sem_duplicados(
            RiscoEPIRecomendado.objects.filter(risco_identificado__ges=ges)
            .select_related('equipamento').order_by('equipamento__nome'),
            'equipamento_id', 'ca_numero',
        )
        context['treinamentos_necessarios'] = sem_duplicados(
            RiscoTreinamentoNecessario.objects.filter(risco_identificado__ges=ges)
            .select_related('tipo_curso').order_by('tipo_curso__nome'),
            'tipo_curso_id',
        )
        return context

class GESCreateView(PGRBaseMixin, PGRRequestFormKwargsMixin, FilialCreateMixin, CreateView):
    model = GESGrupoExposicao
    form_class = GESGrupoExposicaoForm
    template_name = 'pgr_gestao/ges_form.html'
    permission_required = 'pgr_gestao.add_gesgrupoexposicao'
    success_url = reverse_lazy('pgr_gestao:ges_list')

    def form_valid(self, form):
        form.instance.criado_por = self.request.user
        return super().form_valid(form)


class GESUpdateView(PGRBaseMixin, PGRRequestFormKwargsMixin, UpdateView):
    model = GESGrupoExposicao
    form_class = GESGrupoExposicaoForm
    template_name = 'pgr_gestao/ges_form.html'
    permission_required = 'pgr_gestao.change_gesgrupoexposicao'

    def get_success_url(self):
        return reverse('pgr_gestao:ges_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, 'GES atualizado com sucesso!')
        return super().form_valid(form)


class GESDeleteView(PGRSoftDeleteMixin, PGRTecnicoBaseMixin, DeleteView):
    model = GESGrupoExposicao
    template_name = 'pgr_gestao/ges_confirm_delete.html'
    permission_required = 'pgr_gestao.delete_gesgrupoexposicao'
    tecnico_scope_lookup = 'pgr_documento__criado_por'
    success_url = reverse_lazy('pgr_gestao:ges_list')


@funcionario_required
@require_POST
def ges_toggle_ativo(request, pk):
    """Ativa/inativa um GES via AJAX."""
    if not request.user.has_perm('pgr_gestao.change_gesgrupoexposicao'):
        return JsonResponse({
            'success': False,
            'error': 'Você não tem permissão para alterar este GES.',
        }, status=403)

    ges = _ges_visiveis(request).filter(pk=pk).first()
    if ges is None:
        return JsonResponse({'success': False, 'error': 'GES não encontrado.'}, status=404)

    ges.ativo = not ges.ativo
    ges.save(update_fields=['ativo', 'atualizado_em'])
    return JsonResponse({
        'success': True,
        'ativo': ges.ativo,
        'message': f'GES "{ges.nome}" {"ativado" if ges.ativo else "inativado"} com sucesso!',
    })


# =============================================================================
# RISCOS IDENTIFICADOS
# =============================================================================

class RiscoIdentificadoListView(PGRTecnicoBaseMixin, ListView):
    model = RiscoIdentificado
    template_name = 'pgr_gestao/risco_list.html'
    context_object_name = 'riscos'
    paginate_by = 20
    permission_required = 'pgr_gestao.view_riscoidentificado'
    tecnico_scope_lookup = 'pgr_documento__criado_por'

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'pgr_documento', 'ges', 'tipo_risco', 'ambiente_trabalho', 'cargo'
        ).prefetch_related('avaliacoes_quantitativas', 'planos_acao')

        pgr_id = self.request.GET.get('pgr')
        classificacao = self.request.GET.get('classificacao')
        status = self.request.GET.get('status')
        prioridade = self.request.GET.get('prioridade')
        tipo_risco = self.request.GET.get('tipo_risco')
        search = self.request.GET.get('search')

        if pgr_id:
            queryset = queryset.filter(pgr_documento_id=pgr_id)
        if classificacao:
            queryset = queryset.filter(classificacao_risco=classificacao)
        if status:
            queryset = queryset.filter(status_controle=status)
        if prioridade:
            queryset = queryset.filter(prioridade_acao=prioridade)
        if tipo_risco:
            queryset = queryset.filter(tipo_risco_id=tipo_risco)
        if search:
            queryset = queryset.filter(
                Q(codigo_risco__icontains=search) |
                Q(agente__icontains=search) |
                Q(fonte_geradora__icontains=search)
            )
        return ordenar_por(queryset, 'prioridade_acao', ORDEM_PRIORIDADE, '-data_identificacao')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['documentos_pgr'] = documentos_visiveis(self.request).filter(status='vigente')
        context['tipos_risco'] = TipoRisco.objects.for_request(self.request).filter(ativo=True)

        resumo = self.object_list.aggregate(
            total=Count('id'),
            criticos=Count('id', filter=Q(classificacao_risco__in=CLASSIFICACOES_CRITICAS)),
            controlados=Count('id', filter=Q(status_controle='controlado')),
        )
        context['total_riscos'] = resumo['total']
        context['riscos_criticos'] = resumo['criticos']
        context['riscos_controlados'] = resumo['controlados']
        return context


class RiscoIdentificadoDetailView(PGRTecnicoBaseMixin, DetailView):
    model = RiscoIdentificado
    template_name = 'pgr_gestao/risco_detail.html'
    context_object_name = 'risco'
    permission_required = 'pgr_gestao.view_riscoidentificado'
    tecnico_scope_lookup = 'pgr_documento__criado_por'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        risco = self.object

        context['tipos_risco'] = TipoRisco.objects.for_request(self.request).filter(ativo=True)
        context['avaliacoes'] = risco.avaliacoes_quantitativas.order_by('-data_avaliacao')
        context['medidas_controle'] = risco.medidas_controle.select_related(
            'medida_controle'
        ).order_by('medida_controle__prioridade')
        context['planos_acao'] = ordenar_por(
            risco.planos_acao.all(), 'prioridade', ORDEM_PRIORIDADE, 'data_prevista'
        )
        context['epis_recomendados'] = risco.epis_recomendados.select_related('equipamento')
        context['treinamentos_necessarios'] = risco.treinamentos_necessarios.select_related('tipo_curso')
        return context


class RiscoIdentificadoCreateView(PGRBaseMixin, PGRRequestFormKwargsMixin, FilialCreateMixin, CreateView):
    """
    A classificação do risco é calculada no pre_save do model (fonte única).
    O _calcular_classificacao_risco da view foi removido: usava limites
    inventados e divergia da regra do model.
    """
    model = RiscoIdentificado
    form_class = RiscoIdentificadoForm
    template_name = 'pgr_gestao/risco_form.html'
    permission_required = 'pgr_gestao.add_riscoidentificado'

    def get_initial(self):
        initial = super().get_initial()
        ges_id = self.request.GET.get('ges')
        if ges_id:
            ges = get_object_or_404(
                _ges_visiveis(self.request).select_related('pgr_documento'), pk=ges_id
            )
            initial.update({
                'ges': ges,
                'pgr_documento': ges.pgr_documento,
                'ambiente_trabalho': ges.ambiente_trabalho,
                'cargo': ges.cargo,
            })
        initial['data_identificacao'] = timezone.localdate()
        return initial

    def form_valid(self, form):
        form.instance.criado_por = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('pgr_gestao:risco_detail', kwargs={'pk': self.object.pk})


class RiscoIdentificadoUpdateView(PGRBaseMixin, PGRRequestFormKwargsMixin, UpdateView):
    model = RiscoIdentificado
    form_class = RiscoIdentificadoForm
    template_name = 'pgr_gestao/risco_form.html'
    permission_required = 'pgr_gestao.change_riscoidentificado'

    def get_success_url(self):
        return reverse('pgr_gestao:risco_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, 'Risco atualizado com sucesso!')
        return super().form_valid(form)


class RiscoIdentificadoDeleteView(PGRSoftDeleteMixin, PGRTecnicoBaseMixin, DeleteView):

    model = RiscoIdentificado
    template_name = 'pgr_gestao/risco_confirm_delete.html'
    permission_required = 'pgr_gestao.delete_riscoidentificado'
    success_url = reverse_lazy('pgr_gestao:risco_list')
    tecnico_scope_lookup = 'pgr_documento__criado_por'




# =============================================================================
# AVALIAÇÕES QUANTITATIVAS
# =============================================================================

AVALIACAO_FILIAL_FIELD = 'risco_identificado__pgr_documento__filial'


class AvaliacaoQuantitativaListView(PGRTecnicoBaseMixin, ListView):
    model = AvaliacaoQuantitativa
    template_name = 'pgr_gestao/avaliacao_list.html'
    context_object_name = 'avaliacoes'
    paginate_by = 20
    permission_required = 'pgr_gestao.view_avaliacaoquantitativa'
    tecnico_scope_lookup = 'risco_identificado__pgr_documento__criado_por'
    filial_field = AVALIACAO_FILIAL_FIELD

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'risco_identificado', 'risco_identificado__pgr_documento',
            'risco_identificado__ges'
        )

        tipo = self.request.GET.get('tipo')
        conforme = self.request.GET.get('conforme')
        risco_id = self.request.GET.get('risco')
        search_query = self.request.GET.get('search')

        if tipo:
            queryset = queryset.filter(tipo_avaliacao=tipo)
        if conforme in ('true', 'false'):
            queryset = queryset.filter(conforme=(conforme == 'true'))
        if risco_id:
            queryset = queryset.filter(risco_identificado_id=risco_id)
        if search_query:
            queryset = queryset.filter(
                Q(equipamento_utilizado__icontains=search_query) |
                Q(risco_identificado__agente__icontains=search_query)
            )
        from django.utils.dateparse import parse_date
        for chave, lookup in (('data_inicio', 'data_avaliacao__gte'),
                              ('data_fim', 'data_avaliacao__lte')):
            try:
                valor = parse_date(self.request.GET.get(chave) or '')
            except ValueError:
                valor = None
            if valor:
                queryset = queryset.filter(**{lookup: valor})
        return queryset.order_by('-data_avaliacao')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tipos_avaliacao'] = TIPO_AVALIACAO_CHOICES
        resumo = self.object_list.order_by().aggregate(
            total=Count('id'),
            conformes=Count('id', filter=Q(conforme=True)),
            nao_conformes=Count('id', filter=Q(conforme=False)),
            riscos=Count('risco_identificado', distinct=True),
        )
        context['total_avaliacoes'] = resumo['total']
        context['total_conformes'] = resumo['conformes']
        context['total_nao_conformes'] = resumo['nao_conformes']
        context['total_riscos_avaliados'] = resumo['riscos']
        context['riscos_para_filtro'] = RiscoIdentificado.objects.for_request(
            self.request
        ).filter(
            pgr_documento__in=documentos_visiveis(self.request)
        ).order_by('agente')

        params = self.request.GET.copy()
        params.pop('page', None)  # evita "page=2&page=3" na paginação
        context['get_params'] = params.urlencode()
        return context


class AvaliacaoQuantitativaDetailView(PGRTecnicoBaseMixin, DetailView):
    model = AvaliacaoQuantitativa
    template_name = 'pgr_gestao/avaliacao_detail.html'
    context_object_name = 'avaliacao'
    permission_required = 'pgr_gestao.view_avaliacaoquantitativa'
    tecnico_scope_lookup = 'risco_identificado__pgr_documento__criado_por'
    filial_field = AVALIACAO_FILIAL_FIELD


class AvaliacaoQuantitativaCreateView(PGRBaseMixin, PGRRequestFormKwargsMixin, FilialCreateMixin, CreateView):
    model = AvaliacaoQuantitativa
    form_class = AvaliacaoQuantitativaForm
    template_name = 'pgr_gestao/avaliacao_form.html'
    permission_required = 'pgr_gestao.add_avaliacaoquantitativa'

    @cached_property
    def risco(self):
        risco_pk = self.kwargs.get('risco_pk') or self.request.GET.get('risco')
        if not risco_pk:
            return None
        return get_object_or_404(
            RiscoIdentificado.objects.for_request(self.request).filter(
                pgr_documento__in=documentos_visiveis(self.request)
            ).select_related('tipo_risco', 'ges'),
            pk=risco_pk,
        )

    def get_initial(self):
        initial = super().get_initial()
        if self.risco:
            initial['risco_identificado'] = self.risco
        initial['data_avaliacao'] = timezone.localdate()
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.risco:
            context['risco'] = self.risco
        return context

    def form_valid(self, form):
        form.instance.criado_por = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('pgr_gestao:risco_detail', kwargs={'pk': self.object.risco_identificado_id})


class AvaliacaoQuantitativaUpdateView(PGRTecnicoBaseMixin, PGRRequestFormKwargsMixin, UpdateView):
    model = AvaliacaoQuantitativa
    form_class = AvaliacaoQuantitativaForm
    template_name = 'pgr_gestao/avaliacao_form.html'
    permission_required = 'pgr_gestao.change_avaliacaoquantitativa'
    tecnico_scope_lookup = 'risco_identificado__pgr_documento__criado_por'
    filial_field = AVALIACAO_FILIAL_FIELD

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['risco'] = self.object.risco_identificado
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Avaliação quantitativa atualizada com sucesso!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('pgr_gestao:risco_detail', kwargs={'pk': self.object.risco_identificado_id})


class AvaliacaoQuantitativaDeleteView(PGRTecnicoBaseMixin, DeleteView):
    model = AvaliacaoQuantitativa
    template_name = 'pgr_gestao/confirm_delete.html'
    permission_required = 'pgr_gestao.delete_avaliacaoquantitativa'
    tecnico_scope_lookup = 'risco_identificado__pgr_documento__criado_por'
    filial_field = AVALIACAO_FILIAL_FIELD  # sem isso o mixin filtra por 'filial' e dá FieldError

    def get_success_url(self):
        return reverse('pgr_gestao:risco_detail', kwargs={'pk': self.object.risco_identificado_id})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Avaliação quantitativa excluída com sucesso.')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object_name'] = 'Avaliação Quantitativa'
        context['object_info'] = f"'{self.object.get_tipo_avaliacao_display()}' de {self.object.data_avaliacao}"
        return context

# =============================================================================
# PLANOS DE AÇÃO
# =============================================================================

class PlanoAcaoPGRListView(PGRTecnicoBaseMixin, ListView):
    model = PlanoAcaoPGR
    template_name = 'pgr_gestao/plano_acao_list.html'
    context_object_name = 'planos'
    paginate_by = 20
    permission_required = 'pgr_gestao.view_planoacaopgr'
    tecnico_scope_lookup = PLANO_LOOKUP_TECNICO

    def get_queryset(self):
        qs = super().get_queryset().select_related(
            'risco_identificado', 'risco_identificado__pgr_documento',
            'risco_identificado__tipo_risco',
        )
        g = self.request.GET
        for campo in ('status', 'prioridade', 'tipo_acao'):
            if g.get(campo):
                qs = qs.filter(**{campo: g[campo]})
        if g.get('atrasado') == 'true':
            qs = qs.filter(status__in=PLANO_PENDENTES,
                           data_prevista__lt=timezone.localdate())
        if g.get('pgr'):
            qs = qs.filter(risco_identificado__pgr_documento_id=g['pgr'])
        if g.get('search'):
            s = g['search']
            qs = qs.filter(
                Q(descricao_acao__icontains=s) | Q(responsavel__icontains=s) |
                Q(risco_identificado__agente__icontains=s)
            )
        return ordenar_por(qs, 'prioridade', ORDEM_PRIORIDADE, 'data_prevista')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoje = timezone.localdate()
        r = self.object_list.aggregate(
            total=Count('id'),
            pendentes=Count('id', filter=Q(status='pendente')),
            andamento=Count('id', filter=Q(status='em_andamento')),
            concluidos=Count('id', filter=Q(status='concluido')),
            atrasados=Count('id', filter=Q(status__in=PLANO_PENDENTES,
                                           data_prevista__lt=hoje)),
        )
        context.update({
            'total_planos': r['total'],
            'planos_pendentes': r['pendentes'],
            'planos_em_andamento': r['andamento'],
            'planos_concluidos': r['concluidos'],
            'planos_atrasados': r['atrasados'],
            'documentos_pgr': documentos_visiveis(self.request).filter(status='vigente'),
        })
        return context


class PlanoAcaoPGRDetailView(PGRTecnicoBaseMixin, DetailView):
    model = PlanoAcaoPGR
    template_name = 'pgr_gestao/plano_acao_detail.html'
    context_object_name = 'plano'
    permission_required = 'pgr_gestao.view_planoacaopgr'
    tecnico_scope_lookup = PLANO_LOOKUP_TECNICO

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        plano = self.object
        context['risco'] = plano.risco_identificado
        context['esta_atrasado'] = plano.esta_atrasado
        context['acompanhamentos'] = plano.acompanhamentos.order_by('-data_acompanhamento', '-criado_em')
        context['anexos'] = plano.anexos.all()
        if plano.data_prevista:
            dias = (timezone.localdate() - plano.data_prevista).days
            if dias > 0:
                context['dias_atraso'] = dias
            else:
                context['dias_restantes'] = -dias
        return context


class PlanoAcaoPGRCreateView(PGRBaseMixin, PGRRequestFormKwargsMixin,
                             FilialCreateMixin, CreateView):
    model = PlanoAcaoPGR
    form_class = PlanoAcaoPGRForm
    template_name = 'pgr_gestao/plano_acao_form.html'
    permission_required = 'pgr_gestao.add_planoacaopgr'

    def get_initial(self):
        initial = super().get_initial()
        risco_id = self.request.GET.get('risco')
        if risco_id and risco_id.isdigit():
            risco = get_object_or_404(riscos_visiveis(self.request), pk=risco_id)
            initial.update({
                'risco_identificado': risco,
                'prioridade': risco.prioridade_acao,
                'data_prevista': prazo_para(risco.classificacao_risco),
            })
        return initial

    def form_valid(self, form):
        form.instance.criado_por = self.request.user
        response = super().form_valid(form)
        audit(self.request, 'create_plano', self.object)
        return response

    def get_success_url(self):
        if self.request.POST.get('action') == 'save_and_new':
            return reverse('pgr_gestao:plano_acao_create')
        return reverse('pgr_gestao:plano_acao_detail', kwargs={'pk': self.object.pk})


class PlanoAcaoPGRUpdateView(PGRTecnicoBaseMixin, PGRRequestFormKwargsMixin, UpdateView):
    model = PlanoAcaoPGR
    form_class = PlanoAcaoPGRForm
    template_name = 'pgr_gestao/plano_acao_form.html'
    permission_required = 'pgr_gestao.change_planoacaopgr'
    tecnico_scope_lookup = PLANO_LOOKUP_TECNICO

    def form_valid(self, form):
        response = super().form_valid(form)
        audit(self.request, 'update_plano', self.object)
        messages.success(self.request, 'Plano de ação atualizado com sucesso!')
        return response

    def get_success_url(self):
        return reverse('pgr_gestao:plano_acao_detail', kwargs={'pk': self.object.pk})


@funcionario_required
@permission_required('pgr_gestao.change_planoacaopgr', raise_exception=True)
def concluir_plano_acao(request, pk):
    """Marca um plano de ação como concluído."""
    plano = get_object_or_404(planos_visiveis(request), pk=pk)

    if request.method == 'POST':
        plano.status = 'concluido'
        plano.data_conclusao = timezone.localdate()
        # Confirme que 'evidencia_conclusao' é campo real do model; senão o valor é ignorado.
        plano.evidencia_conclusao = request.POST.get('evidencia_conclusao', '')
        plano.save()
        audit(request, 'concluir_plano', plano)
        messages.success(request, 'Plano de ação concluído com sucesso!')
        return redirect('pgr_gestao:plano_acao_detail', pk=pk)

    return render(request, 'pgr_gestao/plano_acao_concluir.html', {'plano': plano})


@funcionario_required
@permission_required('pgr_gestao.change_planoacaopgr', raise_exception=True)
@require_POST
def adicionar_anexo_plano(request, pk):
    plano = get_object_or_404(planos_visiveis(request), pk=pk)
    form = AnexoPlanoAcaoForm(request.POST, request.FILES, request=request)
    if form.is_valid():
        anexo = form.save(commit=False)
        anexo.plano_acao, anexo.criado_por = plano, request.user
        anexo.save()
        audit(request, 'upload_anexo', anexo)
        messages.success(request, 'Anexo adicionado com sucesso!')
    else:
        messages.error(request, '; '.join(e for errs in form.errors.values() for e in errs))
    return redirect('pgr_gestao:plano_acao_detail', pk=pk)


@funcionario_required
@permission_required('pgr_gestao.view_riscoidentificado', raise_exception=True)
def risco_info_ajax(request, pk):
    """Dados do risco para o formulário do plano (com prioridade e prazo sugeridos)."""
    r = get_object_or_404(riscos_visiveis(request), pk=pk)
    return JsonResponse({
        'agente': r.agente,
        'classificacao': r.classificacao_risco,
        'classificacao_display': r.get_classificacao_risco_display(),
        'fonte_geradora': r.fonte_geradora or '',
        'prioridade_sugerida': r.prioridade_acao,
        'data_sugerida': prazo_para(r.classificacao_risco).isoformat(),
    })


# =============================================================================
# CRONOGRAMA DE AÇÕES
# =============================================================================

class CronogramaAcaoListView(PGRTecnicoBaseMixin, ListView):
    model = CronogramaAcaoPGR
    template_name = 'pgr_gestao/cronograma_list.html'
    context_object_name = 'acoes'
    paginate_by = 20
    permission_required = 'pgr_gestao.view_cronogramaacaopgr'
    tecnico_scope_lookup = 'pgr_documento__criado_por'
    filial_field = 'pgr_documento__filial'

    def get_queryset(self):
        qs = super().get_queryset().select_related('pgr_documento').order_by('-data_proxima_avaliacao')

        pgr = self.request.GET.get('pgr') or self.request.GET.get('pgr_documento')
        status = self.request.GET.get('status')
        search = self.request.GET.get('search') or self.request.GET.get('responsavel')

        if pgr:
            qs = qs.filter(pgr_documento_id=pgr)
        if status:
            qs = qs.filter(status=status)
        if search:
            qs = qs.filter(
                Q(acao_necessaria__icontains=search) |
                Q(responsavel__icontains=search)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = STATUS_CHOICES
        context['documentos_pgr'] = documentos_visiveis(self.request)

        resumo = self.object_list.order_by().aggregate(
            total=Count('id'),
            pendentes=Count('id', filter=Q(status='pendente')),
            em_andamento=Count('id', filter=Q(status='em_andamento')),
            concluidas=Count('id', filter=Q(status='concluido')),
            atrasadas=Count('id', filter=Q(
                status__in=STATUS_PLANO_ABERTO,
                data_proxima_avaliacao__lt=timezone.localdate(),
            )),
        )
        context['total_acoes'] = resumo['total']
        context['acoes_pendentes'] = resumo['pendentes']
        context['acoes_em_andamento'] = resumo['em_andamento']
        context['acoes_concluidas'] = resumo['concluidas']
        context['acoes_atrasadas'] = resumo['atrasadas']
        return context


class CronogramaAcaoDetailView(PGRBaseMixin, DetailView):
    model = CronogramaAcaoPGR
    template_name = 'pgr_gestao/cronograma_detail.html'
    context_object_name = 'acao'
    permission_required = 'pgr_gestao.view_cronogramaacaopgr'

    def get_queryset(self):
        return super().get_queryset().select_related('pgr_documento')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = STATUS_CHOICES
        return context


class CronogramaAcaoCreateView(PGRBaseMixin, PGRRequestFormKwargsMixin, SuccessMessageMixin,
                               FilialCreateMixin, CreateView):
    model = CronogramaAcaoPGR
    form_class = CronogramaAcaoPGRForm
    template_name = 'pgr_gestao/cronograma_form.html'
    success_message = 'Ação do cronograma criada com sucesso!'
    permission_required = 'pgr_gestao.add_cronogramaacaopgr'

    @cached_property
    def pgr(self):
        pgr_pk = self.kwargs.get('pgr_pk')
        if not pgr_pk:
            return None
        return get_object_or_404(documentos_visiveis(self.request), pk=pgr_pk)

    def get_initial(self):
        initial = super().get_initial()
        if self.pgr:
            initial['pgr_documento'] = self.pgr
            ultimo = self.pgr.cronograma_acoes.aggregate(m=Max('numero_item'))['m']
            initial['numero_item'] = (ultimo or 0) + 1
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Nova Ação no Cronograma'
        context['botao'] = 'Cadastrar'
        if self.pgr:
            context['documento_pgr'] = self.pgr
        return context

    def form_valid(self, form):
        pgr = form.cleaned_data['pgr_documento']
        if not documentos_visiveis(self.request).filter(pk=pgr.pk).exists():
            raise PermissionDenied
        return super().form_valid(form)

    def get_success_url(self):
        if self.kwargs.get('pgr_pk'):
            return reverse('pgr_gestao:documento_detail', kwargs={'pk': self.kwargs['pgr_pk']})
        return reverse('pgr_gestao:cronograma_list')


class CronogramaAcaoUpdateView(PGRBaseMixin, SuccessMessageMixin, UpdateView):
    model = CronogramaAcaoPGR
    form_class = CronogramaAcaoPGRForm
    template_name = 'pgr_gestao/cronograma_form.html'
    success_message = 'Ação do cronograma atualizada com sucesso!'
    permission_required = 'pgr_gestao.change_cronogramaacaopgr'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f'Editar Ação #{self.object.numero_item:02d}'
        context['botao'] = 'Salvar Alterações'
        context['editando'] = True
        return context

    def get_success_url(self):
        if self.kwargs.get('pgr_pk'):
            return reverse('pgr_gestao:documento_detail', kwargs={'pk': self.kwargs['pgr_pk']})
        return reverse('pgr_gestao:cronograma_detail', kwargs={'pk': self.object.pk})


class CronogramaAcaoDeleteView(PGRBaseMixin, DeleteView):
    model = CronogramaAcaoPGR
    template_name = 'pgr_gestao/cronograma_confirm_delete.html'
    permission_required = 'pgr_gestao.delete_cronogramaacaopgr'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Excluir Ação'
        context['mensagem'] = f"Confirma exclusão da ação '{self.object.acao_necessaria}'?"
        context['pgr_documento'] = self.object.pgr_documento
        return context

    def get_success_url(self):
        if self.kwargs.get('pgr_pk'):
            return reverse('pgr_gestao:documento_detail', kwargs={'pk': self.kwargs['pgr_pk']})
        return reverse('pgr_gestao:cronograma_list')

    def form_valid(self, form):
        # Django >= 4: delete() não é mais chamado pelo DeleteView.
        response = super().form_valid(form)
        messages.success(self.request, 'Ação do cronograma excluída com sucesso!')
        return response


@funcionario_required
@permission_required('pgr_gestao.change_cronogramaacaopgr', raise_exception=True)
@require_POST
def atualizar_status_acao(request, pk):
    """Atualiza o status de uma ação do cronograma."""
    acao = get_object_or_404(
        CronogramaAcaoPGR.objects.for_request(request).filter(
            pgr_documento__in=documentos_visiveis(request)
        ),
        pk=pk,
    )
    novo_status = request.POST.get('status')

    if novo_status in dict(STATUS_CHOICES):
        acao.status = novo_status
        if novo_status == 'concluido' and not acao.data_realizacao:
            acao.data_realizacao = timezone.localdate()
        acao.save()
        messages.success(request, f'Status atualizado para "{acao.get_status_display()}".')
    else:
        messages.error(request, 'Status inválido!')

    return redirect('pgr_gestao:cronograma_detail', pk=pk)


# =============================================================================
# PROFISSIONAIS RESPONSÁVEIS
# =============================================================================

class ProfissionalResponsavelListView(PGRBaseMixin, ListView):
    model = ProfissionalResponsavel
    template_name = 'pgr_gestao/profissional_list.html'
    context_object_name = 'profissionais'
    paginate_by = 20
    permission_required = 'pgr_gestao.view_profissionalresponsavel'

    def get_queryset(self):
        queryset = super().get_queryset()

        ativo = self.request.GET.get('ativo')
        funcao = self.request.GET.get('funcao')
        search = self.request.GET.get('search')

        if ativo:
            queryset = queryset.filter(ativo=ativo == 'true')
        if funcao:
            queryset = queryset.filter(funcao__icontains=funcao)
        if search:
            queryset = queryset.filter(
                Q(nome_completo__icontains=search) |
                Q(registro_classe__icontains=search) |
                Q(email__icontains=search)
            )
        return queryset.order_by('nome_completo')


class ProfissionalResponsavelCreateView(PGRBaseMixin, PGRRequestFormKwargsMixin, FilialCreateMixin, CreateView):
    model = ProfissionalResponsavel
    form_class = ProfissionalResponsavelForm
    template_name = 'pgr_gestao/profissional_form.html'
    permission_required = 'pgr_gestao.add_profissionalresponsavel'
    success_url = reverse_lazy('pgr_gestao:profissional_list')


class ProfissionalResponsavelUpdateView(PGRBaseMixin, PGRRequestFormKwargsMixin, UpdateView):
    model = ProfissionalResponsavel
    form_class = ProfissionalResponsavelForm
    template_name = 'pgr_gestao/profissional_form.html'
    permission_required = 'pgr_gestao.change_profissionalresponsavel'
    success_url = reverse_lazy('pgr_gestao:profissional_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Editar Profissional: {self.object.nome_completo}'
        return context


class ProfissionalResponsavelDeleteView(PGRBaseMixin, DeleteView):
    model = ProfissionalResponsavel
    template_name = 'pgr_gestao/profissional_confirm_delete.html'
    permission_required = 'pgr_gestao.delete_profissionalresponsavel'
    success_url = reverse_lazy('pgr_gestao:profissional_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Confirmar Exclusão: {self.object.nome_completo}'
        context['cancel_url'] = reverse_lazy('pgr_gestao:profissional_list')
        return context

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except (ProtectedError, RestrictedError):
            messages.error(
                self.request,
                'Profissional vinculado a documentos PGR. Inative-o em vez de excluir.',
            )
            return redirect('pgr_gestao:profissional_list')
        messages.success(self.request, 'Profissional excluído com sucesso.')
        return response


# =============================================================================
# LOCAL DE PRESTAÇÃO DE SERVIÇOS
# =============================================================================

class LocalPrestacaoCreateView(PGRBaseMixin, PGRRequestFormKwargsMixin, FilialCreateMixin, CreateView):
    model = LocalPrestacaoServico
    form_class = LocalPrestacaoServicoForm
    template_name = 'pgr_gestao/local_prestacao_form.html'
    permission_required = 'pgr_gestao.add_localprestacaoservico'

    def form_valid(self, form):
        # FilialCreateMixin já seta a filial, então só usamos o save padrão.
        messages.success(self.request, 'Local de Prestação cadastrado com sucesso!')
        response = super().form_valid(form)

        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'id': self.object.id,
                'razao_social': self.object.razao_social,
            })
        return response

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
        return super().form_invalid(form)

    def get_initial(self):
        initial = super().get_initial()
        empresa_id = self.request.GET.get('empresa')
        if empresa_id:
            initial['empresa'] = get_object_or_404(
                Empresa.objects.for_request(self.request), pk=empresa_id
            )
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Novo Local de Prestação'
        return context

    def get_success_url(self):
        return reverse_lazy('pgr_gestao:empresa_detail', kwargs={'pk': self.object.empresa.pk})


class LocalPrestacaoUpdateView(PGRBaseMixin, UpdateView):
    model = LocalPrestacaoServico
    form_class = LocalPrestacaoServicoForm
    template_name = 'pgr_gestao/local_prestacao_form.html'
    permission_required = 'pgr_gestao.change_localprestacaoservico'

    def get_success_url(self):
        return reverse_lazy('pgr_gestao:empresa_detail', kwargs={'pk': self.object.empresa.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Local de Prestação'
        return context


# =============================================================================
# HELPERS (2C)
# =============================================================================

def _is_ajax(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


def _riscos_visiveis(request):
    """Riscos da filial, restritos aos documentos que o usuário pode ver."""
    return RiscoIdentificado.objects.for_request(request).filter(
        pgr_documento__in=documentos_visiveis(request)
    )


def _data_get(request, chave):
    """Lê data ISO do GET; ignora valor inválido em vez de gerar erro 500."""
    try:
        return parse_date(request.GET.get(chave) or '')
    except ValueError:
        return None


def _chart(qs, campo, labels):
    dados = qs.values(campo).annotate(total=Count('id')).order_by(campo)
    return {
        'labels': [labels.get(i[campo], i[campo] or 'N/A') for i in dados],
        'valores': [i['total'] for i in dados],
    }

def _xlsx_response(titulo, headers, linhas, filename, larguras=None):
    """Gera o .xlsx padrão (cabeçalho azul, bordas) e devolve o HttpResponse."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = titulo

    lado = Side(style='thin')
    borda = Border(left=lado, right=lado, top=lado, bottom=lado)
    fill = PatternFill(start_color='003366', end_color='003366', fill_type='solid')
    fonte = Font(bold=True, color='FFFFFF')
    centro = Alignment(horizontal='center', vertical='center', wrap_text=True)
    esquerda = Alignment(horizontal='left', vertical='center', wrap_text=True)

    for col, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=col, value=h)
        c.fill, c.font, c.alignment, c.border = fill, fonte, centro, borda

    for row, valores in enumerate(linhas, 2):
        for col, v in enumerate(valores, 1):
            c = ws.cell(row=row, column=col, value=v)
            if isinstance(v, str) and v.startswith('='):
                c.data_type = 's'  # impede interpretação como fórmula
            if isinstance(v, (date, datetime)):
                c.number_format = 'DD/MM/YYYY'
            c.border, c.alignment = borda, esquerda

    for letra, largura in (larguras or {}).items():
        ws.column_dimensions[letra].width = largura

    buffer = BytesIO()
    wb.save(buffer)
    response = HttpResponse(buffer.getvalue(), content_type=XLSX_MIME)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# =============================================================================
# RELATÓRIOS E ESTATÍSTICAS
# =============================================================================

@funcionario_required
@permission_required('pgr_gestao.view_pgrdocumento', raise_exception=True)
def relatorios_pgr(request):
    """Página principal de relatórios — escopo de filial e técnico via selectors."""
    user = request.user
    documentos_pgr = documentos_visiveis(request).select_related('empresa')
    riscos_qs = _riscos_visiveis(request)
    planos_qs = planos_visiveis(request)

    pgr_id = request.GET.get('pgr')
    if pgr_id and pgr_id.isdigit() and documentos_pgr.filter(pk=pgr_id).exists():
        riscos_qs = riscos_qs.filter(pgr_documento_id=pgr_id)
        planos_qs = planos_qs.filter(risco_identificado__pgr_documento_id=pgr_id)

    data_inicio = _data_get(request, 'data_inicio')
    data_fim = _data_get(request, 'data_fim')
    if data_inicio:
        riscos_qs = riscos_qs.filter(criado_em__date__gte=data_inicio)
        planos_qs = planos_qs.filter(criado_em__date__gte=data_inicio)
    if data_fim:
        riscos_qs = riscos_qs.filter(criado_em__date__lte=data_fim)
        planos_qs = planos_qs.filter(criado_em__date__lte=data_fim)

    # Rótulos vindos dos choices reais dos models (evita divergência de valores)
    classificacao_labels = dict(CLASSIFICACAO_RISCO_CHOICES)
    status_risco_labels = dict(RiscoIdentificado._meta.get_field('status_controle').flatchoices)
    status_plano_labels = dict(PlanoAcaoPGR._meta.get_field('status').flatchoices)
    categoria_labels = {
        'fisico': 'Físico', 'quimico': 'Químico', 'biologico': 'Biológico',
        'ergonomico': 'Ergonômico', 'acidente': 'Acidente', 
    }

    top_riscos = ordenar_por(
        riscos_qs.select_related('tipo_risco', 'ges'),
        'classificacao_risco', ORDEM_CLASSIFICACAO, '-gravidade_g',
    )[:10]

    filial_info, acesso_global = _get_filial_info(request)

    context = {
        'total_riscos': riscos_qs.count(),
        'riscos_criticos': riscos_qs.filter(classificacao_risco__in=CRITICOS).count(),
        'riscos_controlados': riscos_qs.filter(status_controle='controlado').count(),
        'planos_pendentes': planos_qs.filter(status__in=PENDENTES).count(),
        'riscos_por_classificacao': json.dumps(_chart(riscos_qs, 'classificacao_risco', classificacao_labels)),
        'riscos_por_categoria': json.dumps(_chart(riscos_qs, 'tipo_risco__categoria', categoria_labels)),
        'riscos_por_status_controle': json.dumps(_chart(riscos_qs, 'status_controle', status_risco_labels)),
        'planos_por_status': json.dumps(_chart(planos_qs, 'status', status_plano_labels)),
        'top_riscos': top_riscos,
        'documentos_pgr': documentos_pgr,
        'pode_exportar_pdf': user.has_perm('pgr_gestao.view_pgrdocumento'),
        'pode_exportar_excel': user.has_perm('pgr_gestao.view_riscoidentificado'),
        'pode_ver_estatistico': user.has_perm('pgr_gestao.view_pgrdocumento'),
        'filial_info': filial_info,
        'acesso_global': acesso_global,
    }
    return render(request, 'pgr_gestao/relatorios.html', context)


@funcionario_required
@permission_required('pgr_gestao.view_riscoidentificado', raise_exception=True)
def relatorio_riscos_por_classificacao(request):
    riscos_qs = _riscos_visiveis(request)

    riscos_stats = riscos_qs.values(
        'classificacao_risco', 'status_controle'
    ).annotate(total=Count('id')).order_by('classificacao_risco', 'status_controle')

    dados_grafico = {}
    for stat in riscos_stats:
        dados_grafico.setdefault(stat['classificacao_risco'], {})[stat['status_controle']] = stat['total']

    riscos_por_tipo = riscos_qs.values(
        'tipo_risco__nome', 'tipo_risco__categoria'
    ).annotate(total=Count('id')).order_by('-total')[:10]

    return render(request, 'pgr_gestao/relatorio_riscos_classificacao.html', {
        'dados_grafico': dados_grafico,
        'riscos_stats': riscos_stats,
        'riscos_por_tipo': riscos_por_tipo,
    })


@funcionario_required
@permission_required('pgr_gestao.view_planoacaopgr', raise_exception=True)
def relatorio_planos_acao(request):
    planos_qs = planos_visiveis(request)
    hoje = timezone.localdate()

    planos_por_status = planos_qs.values('status').annotate(
        total=Count('id'), custo_total=Sum('custo_estimado')
    )
    # Prioridade é texto: ordena em Python pelo peso (crítica > alta > média > baixa)
    planos_por_prioridade = sorted(
        planos_qs.values('prioridade').annotate(total=Count('id')),
        key=lambda i: -ORDEM_PRIORIDADE.get(i['prioridade'], 0),
    )
    planos_atrasados = planos_qs.filter(
        status__in=PENDENTES, data_prevista__lt=hoje
    ).select_related('risco_identificado').order_by('data_prevista')[:20]

    total_planos = planos_qs.count()
    planos_concluidos = planos_qs.filter(status='concluido').count()
    taxa_conclusao = (planos_concluidos / total_planos * 100) if total_planos else 0

    return render(request, 'pgr_gestao/relatorio_planos_acao.html', {
        'planos_por_status': planos_por_status,
        'planos_por_prioridade': planos_por_prioridade,
        'planos_atrasados': planos_atrasados,
        'taxa_conclusao': taxa_conclusao,
        'total_planos': total_planos,
        'planos_concluidos': planos_concluidos,
    })


# =============================================================================
# CONFORMIDADE
# =============================================================================

class PGRConformidadeView(PGRTecnicoBaseMixin, DetailView):
    model = PGRDocumento
    template_name = 'pgr_gestao/verificar_conformidade.html'  # use o nome do seu arquivo
    context_object_name = 'documento'
    permission_required = 'pgr_gestao.view_pgrdocumento'
    tecnico_scope_lookup = 'criado_por'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(verificar(self.object, self.request.user))
        return context


# =============================================================================
# AJAX / API ENDPOINTS
# =============================================================================

@funcionario_required
@permission_required('pgr_gestao.view_localprestacaoservico', raise_exception=True)
def get_locais_prestacao_ajax(request, empresa_id):
    locais = LocalPrestacaoServico.objects.for_request(request).filter(
        empresa_id=empresa_id, ativo=True
    ).values('id', 'razao_social')
    return JsonResponse(list(locais), safe=False)


@funcionario_required
@permission_required('pgr_gestao.view_gesgrupoexposicao', raise_exception=True)
def get_ges_ajax(request, pgr_id):
    ges = GESGrupoExposicao.objects.for_request(request).filter(
        pgr_documento_id=pgr_id,
        pgr_documento__in=documentos_visiveis(request),
        ativo=True,
    ).values('id', 'codigo', 'nome')
    return JsonResponse(list(ges), safe=False)


@funcionario_required
@permission_required('pgr_gestao.view_pgrdocumento', raise_exception=True)
def dashboard_stats_ajax(request):
    docs_qs = documentos_visiveis(request)
    riscos_qs = _riscos_visiveis(request)
    planos_qs = planos_visiveis(request)

    return JsonResponse({
        'total_documentos': docs_qs.count(),
        'documentos_vigentes': docs_qs.filter(status='vigente').count(),
        'total_riscos': riscos_qs.count(),
        'riscos_criticos': riscos_qs.filter(classificacao_risco__in=CRITICOS).count(),
        'planos_pendentes': planos_qs.filter(status='pendente').count(),
        'planos_atrasados': planos_qs.filter(
            status__in=PENDENTES, data_prevista__lt=timezone.localdate()
        ).count(),
    })


# =============================================================================
# EXPORTAÇÕES
# =============================================================================

@funcionario_required
@permission_required('pgr_gestao.view_pgrdocumento', raise_exception=True)
def gerar_relatorio_completo_pdf(request, pk):
    documento = get_object_or_404(documentos_visiveis(request), pk=pk)

    from .utils.pdf_generator import gerar_pdf_pgr

    try:
        pdf_buffer = gerar_pdf_pgr(documento)
    except Exception:
        logger.exception('Erro ao gerar PDF do PGR %s', pk)
        messages.error(request, 'Não foi possível gerar o PDF. Tente novamente ou contate o suporte.')
        return redirect('pgr_gestao:documento_detail', pk=pk)

    nome = f"PGR_{slugify(documento.codigo_documento)}_{slugify(documento.empresa.razao_social)}.pdf"
    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{nome}"'
    return response


@funcionario_required
@permission_required('pgr_gestao.view_riscoidentificado', raise_exception=True)
def exportar_inventario_riscos_excel(request, pk):
    documento = get_object_or_404(documentos_visiveis(request), pk=pk)

    riscos = RiscoIdentificado.objects.filter(
        pgr_documento=documento
    ).select_related('ges', 'tipo_risco').order_by('ges__codigo', 'codigo_risco')

    headers = [
        'GES', 'Código Risco', 'Tipo', 'Agente', 'Fonte Geradora',
        'Perfil Exposição', 'Gravidade', 'Exposição', 'Severidade',
        'Probabilidade', 'Classificação', 'Status', 'Prioridade',
        'Medidas Controle', 'Data Identificação',
    ]
    linhas = (
        [
            r.ges.nome if r.ges else 'N/A',
            r.codigo_risco or 'N/A',
            r.tipo_risco.nome,
            r.agente,
            r.fonte_geradora or '',
            r.get_perfil_exposicao_display(),
            r.gravidade_g,
            r.exposicao_e,
            r.severidade_s,
            r.probabilidade_p,
            r.get_classificacao_risco_display(),
            r.get_status_controle_display(),
            r.get_prioridade_acao_display(),
            r.medidas_controle_existentes or '',
            r.data_identificacao,
        ]
        for r in riscos
    )
    return _xlsx_response(
        'Inventário de Riscos', headers, linhas,
        f'Inventario_Riscos_{slugify(documento.codigo_documento)}.xlsx',
        {'A': 20, 'D': 25, 'E': 30, 'N': 40, 'O': 18},
    )


@funcionario_required
@permission_required('pgr_gestao.view_planoacaopgr', raise_exception=True)
def exportar_planos_acao_excel(request):
    qs = planos_visiveis(request).select_related('risco_identificado').order_by('-data_prevista')

    for campo in ('status', 'prioridade', 'tipo_acao'):
        valor = request.GET.get(campo)
        if valor:
            qs = qs.filter(**{campo: valor})
    if request.GET.get('atrasado') == 'true':
        qs = qs.filter(status__in=PENDENTES, data_prevista__lt=timezone.localdate())
    busca = request.GET.get('search')
    if busca:
        qs = qs.filter(Q(descricao_acao__icontains=busca) | Q(responsavel__icontains=busca))

    headers = [
        'ID', 'Descrição da Ação', 'Risco Associado', 'Tipo de Ação', 'Prioridade',
        'Status', 'Responsável', 'Data Prevista', 'Data de Conclusão',
        'Custo Estimado (R$)', 'Custo Real (R$)', 'Evidência',
    ]
    linhas = (
        [
            p.pk,
            p.descricao_acao,
            p.risco_identificado.agente if p.risco_identificado else 'N/A',
            p.get_tipo_acao_display(),
            p.get_prioridade_display(),
            p.get_status_display(),
            p.responsavel,
            p.data_prevista,
            p.data_conclusao,
            p.custo_estimado,
            p.custo_real,
            'Sim' if p.evidencia else 'Não',  # não expõe URL do arquivo na planilha
        ]
        for p in qs
    )
    return _xlsx_response(
        'Planos de Ação', headers, linhas,
        f"planos_de_acao_{timezone.localdate():%Y%m%d}.xlsx",
        {'B': 50, 'C': 30, 'G': 20, 'H': 15, 'I': 18},
    )


@funcionario_required
@permission_required('pgr_gestao.view_cronogramaacaopgr', raise_exception=True)
def exportar_cronograma_acoes(request, pk):
    documento = get_object_or_404(documentos_visiveis(request), pk=pk)
    acoes = documento.cronograma_acoes.all().order_by('numero_item')

    headers = [
        'Item', 'Ação Necessária', 'Público Alvo', 'Periodicidade',
        'Responsável', 'Status', 'Próxima Avaliação',
    ]
    linhas = (
        [
            a.numero_item, a.acao_necessaria, a.publico_alvo,
            a.get_periodicidade_display(), a.responsavel,
            a.get_status_display(), a.data_proxima_avaliacao or 'N/A',
        ]
        for a in acoes
    )
    return _xlsx_response(
        'Cronograma de Ações', headers, linhas,
        f'Cronograma_PGR_{slugify(documento.codigo_documento)}.xlsx',
        {'B': 50, 'C': 25, 'G': 20},
    )


# =============================================================================
# ANEXOS DO PGR
# =============================================================================

class AnexoPGRListView(PGRBaseMixin, ListView):
    model = AnexoPGR
    template_name = 'pgr_gestao/anexos/anexo_list.html'
    context_object_name = 'anexos'
    permission_required = 'pgr_gestao.view_anexopgr'

    def get_queryset(self):
        self.pgr_documento = get_object_or_404(
            documentos_visiveis(self.request), pk=self.kwargs['pgr_id']
        )
        return AnexoPGR.objects.filter(
            pgr_documento=self.pgr_documento
        ).order_by('ordem', 'numero_romano')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['documento'] = self.pgr_documento
        context['form_upload'] = AnexoPGRForm()
        context['form_multiple'] = AnexoPGRMultipleForm()
        return context


def _anexo_visivel(request, pk):
    return get_object_or_404(
        AnexoPGR.objects.filter(pgr_documento__in=documentos_visiveis(request)), pk=pk
    )


@funcionario_required
@permission_required('pgr_gestao.add_anexopgr', raise_exception=True)
@require_POST
def anexo_pgr_upload(request, pgr_id):
    """Upload de um ou vários anexos."""
    pgr_documento = get_object_or_404(documentos_visiveis(request), pk=pgr_id)
    ajax = _is_ajax(request)
    arquivos = request.FILES.getlist('arquivo')

    if len(arquivos) <= 1:
        form = AnexoPGRForm(request.POST, request.FILES)
        if not form.is_valid():
            if ajax:
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
            messages.error(request, 'Erro ao enviar anexo. Verifique os campos.')
            return redirect('pgr_gestao:anexo_list', pgr_id=pgr_id)

        anexo = form.save(commit=False)
        anexo.pgr_documento = pgr_documento
        anexo.criado_por = request.user
        anexo.save()
        audit(request, 'upload_anexo', anexo)
        messages.success(request, f'Anexo "{anexo.titulo_completo}" enviado com sucesso!')

        if ajax:
            return JsonResponse({'success': True, 'anexo': {
                'id': anexo.pk,
                'titulo': anexo.titulo_completo,
                'extensao': anexo.extensao,
                'tamanho': anexo.tamanho_formatado,
                'icone': anexo.icone_tipo,
            }})
        return redirect('pgr_gestao:anexo_list', pgr_id=pgr_id)

    tipo_anexo = request.POST.get('tipo_anexo', 'outro')
    titulo_base = request.POST.get('titulo', '')
    incluir_pdf = request.POST.get('incluir_no_pdf') == 'on'
    criados = 0

    for arq in arquivos:
        if arq.size > MAX_ANEXO_BYTES:
            messages.warning(request, f'Arquivo "{arq.name}" ignorado (maior que 50MB).')
            continue
        titulo = titulo_base or dict(AnexoPGR.TIPO_ANEXO_CHOICES).get(tipo_anexo, arq.name)
        anexo = AnexoPGR(
            pgr_documento=pgr_documento,
            tipo_anexo=tipo_anexo,
            titulo=titulo,
            arquivo=arq,
            nome_arquivo_original=arq.name,
            incluir_no_pdf=incluir_pdf,
            criado_por=request.user,
        )
        try:
            anexo.save()
        except ValidationError as e:
            messages.warning(request, f'Arquivo "{arq.name}" rejeitado: {"; ".join(e.messages)}')
            continue
        audit(request, 'upload_anexo', anexo)
        criados += 1

    if criados:
        messages.success(request, f'{criados} anexo(s) enviado(s) com sucesso!')
    if ajax:
        return JsonResponse({'success': True, 'criados': criados})
    return redirect('pgr_gestao:anexo_list', pgr_id=pgr_id)


@funcionario_required
@permission_required('pgr_gestao.delete_anexopgr', raise_exception=True)
@require_POST
def anexo_pgr_delete(request, pk):
    anexo = _anexo_visivel(request, pk)
    pgr_id = anexo.pgr_documento_id
    titulo = anexo.titulo_completo

    # O arquivo físico é removido pelo delete()/signal do model, depois do commit.
    anexo.delete()
    audit(request, 'excluir_anexo', anexo)
    messages.success(request, f'Anexo "{titulo}" excluído com sucesso!')

    if _is_ajax(request):
        return JsonResponse({'success': True})
    return redirect('pgr_gestao:anexo_list', pgr_id=pgr_id)

def romano():
    raise NotImplementedError


@funcionario_required
@permission_required('pgr_gestao.change_anexopgr', raise_exception=True)
@require_POST
def anexo_pgr_reordenar(request, pgr_id):
    """Reordena anexos (drag-and-drop) e renumera os algarismos romanos."""
    get_object_or_404(documentos_visiveis(request), pk=pgr_id)

    try:
        ids = [int(i) for i in json.loads(request.body).get('ordem', [])]
    except (ValueError, TypeError, AttributeError):
        return JsonResponse({'success': False, 'error': 'Dados inválidos.'}, status=400)

    anexos_doc = AnexoPGR.objects.filter(pgr_documento_id=pgr_id)
    for a in anexos_doc:
        anexos_doc.filter(pk=a.pk).update(numero_romano=f'~{a.pk}')
    for idx, a in enumerate(anexos_doc.order_by('ordem', 'pk'), 1):
        anexos_doc.filter(pk=a.pk).update(numero_romano=romano(idx))

    return JsonResponse({'success': True})


@funcionario_required
@permission_required('pgr_gestao.change_anexopgr', raise_exception=True)
def anexo_pgr_editar(request, pk):
    """Edita título/tipo de um anexo (HTML do formulário via AJAX)."""
    anexo = _anexo_visivel(request, pk)
    ajax = _is_ajax(request)
    lista_url = redirect('pgr_gestao:anexo_list', pgr_id=anexo.pgr_documento_id)

    if request.method == 'POST':
        form = AnexoPGRForm(
            request.POST, request.FILES, instance=anexo, request=request
        )
        if form.is_valid():
            anexo = form.save()
            audit(request, 'editar_anexo', anexo)
            messages.success(request, f'Anexo "{anexo.titulo_completo}" atualizado!')
            if ajax:
                return JsonResponse({'success': True, 'titulo': anexo.titulo_completo})
            return lista_url

        if ajax:
            erros = {campo: [str(e) for e in msgs] for campo, msgs in form.errors.items()}
            return JsonResponse({'success': False, 'errors': erros}, status=400)

        erros = '; '.join(str(e) for msgs in form.errors.values() for e in msgs)
        messages.error(request, f'Erro ao atualizar o anexo: {erros}')
        return lista_url

    if ajax:
        from django.template.loader import render_to_string
        html = render_to_string(
            'pgr_gestao/anexos/_anexo_edit_form.html',
            {'form': AnexoPGRForm(instance=anexo, request=request), 'anexo': anexo},
            request=request,
        )
        return JsonResponse({'success': True, 'html': html})

    return lista_url


class AnexoPGRDownloadView(PGRBaseMixin, View):
    """Download de anexo do PGR (verifica permissão)."""
    permission_required = 'pgr_gestao.view_anexopgr'

    def get(self, request, pk):
        anexo = _anexo_visivel(request, pk)
        if not anexo.arquivo:
            raise Http404("Arquivo não encontrado.")
        response = FileResponse(anexo.arquivo.open('rb'), as_attachment=True)
        response['Content-Disposition'] = f'attachment; filename="{anexo.nome_arquivo_original}"'
        return response

class AcompanhamentoPlanoAcaoView(PGRBaseMixin, DetailView):
    model = PlanoAcaoPGR
    template_name = 'pgr_gestao/acompanhamento_plano_acao.html'
    context_object_name = 'plano_acao'
    permission_required = 'pgr_gestao.view_planoacaopgr'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['historico'] = self.object.historico_acoes.order_by('-criado_em')
        context['titulo_pagina'] = f'Acompanhamento da Ação #{self.object.pk}'
        return context

    def post(self, request, *args, **kwargs):
        plano_acao = self.get_object()
        form = AcompanhamentoPlanoAcaoForm(request.POST, request.FILES, request=request)
        if form.is_valid():
            acomp = form.save(commit=False)
            acomp.plano_acao = plano_acao
            acomp.registrado_por = request.user
            acomp.save()