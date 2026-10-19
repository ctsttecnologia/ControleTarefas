# ltcat/views.py
import base64
from datetime import date
import json
from pydoc import doc

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.db import models
from django.db.models import Count, Q, Max, Sum, Prefetch
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView,
)
from django.utils import timezone, formats
from tornado.web import url
from cliente.models import Cliente
from core.decorators import funcionario_required
from core.mixins import FilialCreateMixin, ViewFilialScopedMixin
from core.models import TokenAssinaturaRemota
from departamento_pessoal.models import Cargo, Funcionario
from seguranca_trabalho.models import Funcao

from .mixins import (
    FilialFormKwargsMixin,
    LTCATAccessMixin,
    LTCATBaseMixin,
    LTCATChildMixin,
    LTCATDeleteContextMixin
)
from .forms import (
    AnexoLTCATForm, AvaliacaoPericulosidadeForm, ConclusaoFuncaoForm, EmpresaLTCATForm,
    FuncaoAnalisadaForm, LocalPrestacaoServicoForm, LTCATForm, ReconhecimentoRiscoForm,
    RecomendacaoTecnicaForm, RevisaoLTCATForm,
)
from .models import (
    STATUS_LTCAT_CHOICES,
    TIPO_RESPONSABILIDADE_LTCAT_CHOICES, TIPO_RISCO_CHOICES, CODIGO_GFIP_CHOICES,
    AnexoLTCAT, AvaliacaoPericulosidade, ConclusaoFuncao, DocumentoLocalPrestacao,
    EmpresaLTCAT, FuncaoAnalisada, LocalPrestacaoServicoLTCAT, LTCATDocumento,
    LTCATDocumentoResponsavel, ProfissionalResponsavelLTCAT, ReconhecimentoRisco,
    RecomendacaoTecnica, RevisaoLTCAT,
)

from functools import wraps
import logging
from django.core.exceptions import PermissionDenied, ValidationError
from core.utils import get_filial_ativa, usuario_ve_todas_filiais
from .forms import MedidaControleForm
from .models import MedidaControle
from django.contrib.auth.mixins import PermissionRequiredMixin
from datetime import date, timedelta
from django.contrib.auth.mixins import LoginRequiredMixin

from django.db.models.functions import TruncMonth
from django.views.generic import TemplateView



STATUS_CORES = {
    'rascunho': '#6c757d', 'em_elaboracao': '#ffc107', 'em_revisao': '#fd7e14',
    'aprovado': '#17a2b8', 'vigente': '#28a745', 'vencido': '#dc3545', 'cancelado': '#495057',
}
RISCO_CORES = {
    'fisico': '#28a745', 'quimico': '#dc3545', 'biologico': '#6f42c1',
    'ergonomico': '#fd7e14', 'acidente': '#007bff',
}
MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']


audit = logging.getLogger('ltcat.audit')

MAX_ASSINATURA_BYTES = 2 * 1024 * 1024


def ajax_perm(perm):
    """Exige permissão Django em FBV AJAX (padrão AppPermissionMixin)."""
    def deco(fn):
        @wraps(fn)
        def wrapper(request, *a, **kw):
            if not request.user.has_perm(perm):
                return JsonResponse({'error': 'Sem permissão.'}, status=403)
            return fn(request, *a, **kw)
        return funcionario_required(wrapper)
    return deco

def _filial_qs(request, qs, lookup='filial'):
    """Escopo por filial usando a fonte única do projeto."""
    if usuario_ve_todas_filiais(request.user):
        return qs
    filial = get_filial_ativa(request.user, request)
    return qs.filter(**{lookup: filial}) if filial else qs.none()

def _get_ltcat_or_404(request, pk):
    return get_object_or_404(_filial_qs(request, LTCATDocumento.objects.filter(ativo=True)), pk=pk)

# =============================================================================
# == DASHBOARD
# =============================================================================

class DashboardView(LTCATBaseMixin, ViewFilialScopedMixin, ListView):

    model = LTCATDocumento                              # ← resolve o ImproperlyConfigured
    template_name = 'ltcat/dashboard.html'
    context_object_name = 'laudos'

    def get_queryset(self):
        # super() passa pelo mixin de filial (core/mixins.py)
        return super().get_queryset().filter(ativo=True)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        hoje = date.today()
        docs = self.object_list                         # já filtrado por filial + ativo

        vencido_q = Q(status='vencido') | Q(status__in=['vigente', 'aprovado'], data_vencimento__lt=hoje)
        andamento_q = Q(status__in=['rascunho', 'em_elaboracao', 'em_revisao'])
        k = docs.aggregate(
            total=Count('pk'),
            vigentes=Count('pk', filter=Q(status='vigente') & ~Q(data_vencimento__lt=hoje)),
            andamento=Count('pk', filter=andamento_q),
            vencidos=Count('pk', filter=vencido_q),
            a_vencer=Count('pk', filter=Q(status__in=['vigente', 'aprovado'],
                                          data_vencimento__range=(hoje, hoje + timedelta(days=90)))),
            sem_resp=Count('pk', filter=~Q(responsavel_info__profissional__tipo_habilitacao__in=['eng_seg', 'med_trab']),
                           distinct=True),
        )
        # sem_resp acima conta com join; cálculo exato:
        k['sem_resp'] = docs.exclude(
            responsavel_info__profissional__tipo_habilitacao__in=['eng_seg', 'med_trab']).count()

        # ── Exposição ──
        funcoes = FuncaoAnalisada.objects.filter(ltcat_documento__in=docs, ativo=True)
        f = funcoes.aggregate(n=Count('pk'), trab=Sum('numero_trabalhadores'))
        riscos = ReconhecimentoRisco.objects.filter(funcao__in=funcoes)
        r = riscos.aggregate(
            n=Count('pk'),
            quanti=Count('pk', filter=Q(tipo_avaliacao='quantitativo')),
            hab_perm=Count('pk', filter=Q(habitual_permanente=True)),
            sem_calib=Count('pk', filter=Q(tipo_avaliacao='quantitativo') & (Q(equipamento='') | Q(data_calibracao__isnull=True))),
            sem_esocial=Count('pk', filter=Q(codigo_esocial='', tipo_risco__in=['fisico', 'quimico', 'biologico'])),
        )
        riscos_tipo = dict(riscos.values_list('tipo_risco').annotate(n=Count('pk')))

        # ── Conclusões ──
        conc = ConclusaoFuncao.objects.filter(ltcat_documento__in=docs)
        c = conc.aggregate(
            insalubre=Count('pk', filter=Q(faz_jus_insalubridade=True)),
            periculoso=Count('pk', filter=Q(faz_jus_periculosidade=True)),
            aposentadoria=Count('pk', filter=Q(faz_jus_aposentadoria_especial=True)),
            sem_exposicao=Count('pk', filter=Q(tipo_conclusao='sem_exposicao')),
        )
        gfip_labels = dict(CODIGO_GFIP_CHOICES)
        gfip = [{'label': gfip_labels.get(cod, cod), 'n': n}
                for cod, n in conc.values_list('codigo_gfip').annotate(n=Count('pk')).order_by('codigo_gfip')]

        # ── Recomendações ──
        rec = RecomendacaoTecnica.objects.filter(ltcat_documento__in=docs).aggregate(
            total=Count('pk'),
            implementadas=Count('pk', filter=Q(implementada=True)),
            pendentes=Count('pk', filter=Q(implementada=False)),
            atrasadas=Count('pk', filter=Q(implementada=False, prazo_implementacao__lt=hoje)),
            alta=Count('pk', filter=Q(implementada=False, prioridade='alta')),
        )
        rec['pct'] = round(rec['implementadas'] * 100 / rec['total']) if rec['total'] else 0

        # ── Medidas de controle ──
        m = MedidaControle.objects.filter(risco__in=riscos).aggregate(
            epi_sem_ca=Count('pk', filter=Q(tipo='epi', numero_ca='')),
            ineficazes=Count('pk', filter=Q(eficaz=False)),
            sem_nr06=Count('pk', filter=Q(tipo='epi', atende_nr06=False)),
        )
        funcoes_sem_conclusao = funcoes.filter(conclusoes__isnull=True).count()
        laudos_sem_periculosidade = docs.filter(andamento_q | Q(status='vigente'),
                                                avaliacoes_periculosidade__isnull=True).count()

        # ── Séries ──
        status_cnt = dict(docs.values_list('status').annotate(n=Count('pk')))
        inicio = (hoje.replace(day=1) - timedelta(days=335)).replace(day=1)
        por_mes = {row['m'].strftime('%Y-%m'): row['n'] for row in
                   docs.filter(data_elaboracao__gte=inicio)
                   .annotate(m=TruncMonth('data_elaboracao')).values('m').annotate(n=Count('pk'))}
        meses, y, mo = [], inicio.year, inicio.month
        for _ in range(12):
            meses.append((f"{y}-{mo:02d}", f"{MESES[mo-1]}/{str(y)[2:]}"))
            mo, y = (1, y + 1) if mo == 12 else (mo + 1, y)

        # ── Alertas ──
        alertas = []
        if k['vencidos']:
            alertas.append(f"{k['vencidos']} laudo(s) vencido(s) — revise para manter o PPP válido.")
        if k['sem_resp']:
            alertas.append(f"{k['sem_resp']} laudo(s) sem Eng. de Segurança ou Médico do Trabalho (IN 128/2022).")
        if r['sem_calib']:
            alertas.append(f"{r['sem_calib']} avaliação(ões) quantitativa(s) sem equipamento/calibração.")
        if m['epi_sem_ca']:
            alertas.append(f"{m['epi_sem_ca']} EPI(s) sem nº de CA (NR-06).")

        ctx.update({
            'kpis': [
                {'label': 'Total', 'valor': k['total'], 'icone': 'fa-file-medical', 'cor': ''},
                {'label': 'Vigentes', 'valor': k['vigentes'], 'icone': 'fa-check-circle', 'cor': 'success'},
                {'label': 'Em andamento', 'valor': k['andamento'], 'icone': 'fa-pen', 'cor': 'info'},
                {'label': 'A vencer', 'valor': k['a_vencer'], 'icone': 'fa-hourglass-half', 'cor': 'warning', 'sub': 'próx. 90 dias'},
                {'label': 'Vencidos', 'valor': k['vencidos'], 'icone': 'fa-times-circle', 'cor': 'danger'},
                {'label': 'Sem resp. habilitado', 'valor': k['sem_resp'], 'icone': 'fa-user-slash', 'cor': 'danger'},
            ],
            'kpis_exposicao': [
                {'label': 'Funções/GHE', 'valor': f['n']},
                {'label': 'Trabalhadores', 'valor': f['trab'] or 0},
                {'label': 'Riscos reconhecidos', 'valor': r['n']},
                {'label': 'Avaliações quantitativas', 'valor': r['quanti']},
                {'label': 'Exposição habitual/permanente', 'valor': r['hab_perm']},
                {'label': 'Apos. especial', 'valor': c['aposentadoria']},
            ],
            'conformidade': [
                {'label': 'Funções sem conclusão', 'n': funcoes_sem_conclusao},
                {'label': 'Laudos ativos sem avaliação NR-16', 'n': laudos_sem_periculosidade},
                {'label': 'Quantitativas sem equipamento/calibração', 'n': r['sem_calib']},
                {'label': 'Agentes previdenciários sem código eSocial', 'n': r['sem_esocial']},
                {'label': 'EPIs sem CA', 'n': m['epi_sem_ca']},
                {'label': 'EPIs sem requisitos NR-06', 'n': m['sem_nr06']},
                {'label': 'Medidas sem eficácia comprovada', 'n': m['ineficazes']},
            ],
            'conclusoes': c, 'gfip': gfip, 'recomendacoes': rec, 'alertas': alertas,
            'recentes': docs.select_related('empresa', 'filial').prefetch_related(
                Prefetch('responsavel_info', queryset=LTCATDocumentoResponsavel.objects
                         .select_related('profissional').order_by('tipo_responsabilidade'))
            ).order_by('-atualizado_em')[:8],
            'proximos_vencimentos': docs.filter(
                status__in=['vigente', 'aprovado'],
                data_vencimento__range=(hoje, hoje + timedelta(days=90)),
            ).select_related('empresa').order_by('data_vencimento')[:6],
            'top_empresas': docs.values('empresa__razao_social').annotate(n=Count('pk')).order_by('-n')[:5],
            'charts': {
                'status': {
                    'labels': [lbl for cod, lbl in STATUS_LTCAT_CHOICES if status_cnt.get(cod)],
                    'values': [status_cnt[cod] for cod, _ in STATUS_LTCAT_CHOICES if status_cnt.get(cod)],
                    'colors': [STATUS_CORES[cod] for cod, _ in STATUS_LTCAT_CHOICES if status_cnt.get(cod)],
                },
                'mensal': {'labels': [l for _, l in meses], 'values': [por_mes.get(key, 0) for key, _ in meses]},
                'riscos': {
                    'labels': [lbl for _, lbl in TIPO_RISCO_CHOICES],
                    'values': [riscos_tipo.get(cod, 0) for cod, _ in TIPO_RISCO_CHOICES],
                    'colors': [RISCO_CORES[cod] for cod, _ in TIPO_RISCO_CHOICES],
                },
            },
        })
        return ctx

# =============================================================================
# == EMPRESA LTCAT (Contratada) - CRUD
# =============================================================================

class EmpresaLTCATListView(LTCATBaseMixin, ViewFilialScopedMixin, ListView):

    model = EmpresaLTCAT
    template_name = 'ltcat/empresa_ltcat_list.html'
    context_object_name = 'empresas'
    paginate_by = 20
    permission_required = 'ltcat.view_empresaltcat'

    def get_queryset(self):
        qs = (super().get_queryset()
            .select_related('cliente')
            .annotate(total_laudos=Count('documentos_ltcat_contratada')))
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(cliente__razao_social__icontains=q)
                | Q(cnpj__icontains=q)
                | Q(cidade__icontains=q)
            )
        return qs.order_by('cliente__razao_social')


    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['busca'] = self.request.GET.get('q', '').strip()
        return ctx


class EmpresaLTCATCreateView(LTCATBaseMixin, FilialFormKwargsMixin, FilialCreateMixin, CreateView):
    model = EmpresaLTCAT
    form_class = EmpresaLTCATForm
    template_name = "ltcat/empresa_ltcat_form.html"
    permission_required = "ltcat.add_empresaltcat"

    def form_valid(self, form):
        form.instance.criado_por = self.request.user
        messages.success(self.request, "Empresa contratada cadastrada com sucesso!")
        return super().form_valid(form)

    def get_success_url(self):
        next_url = self.request.GET.get("next")
        if next_url:
            return next_url
        return reverse("ltcat:empresa_ltcat_list")


class EmpresaLTCATUpdateView(LTCATBaseMixin, FilialFormKwargsMixin, ViewFilialScopedMixin, UpdateView):
    model = EmpresaLTCAT
    form_class = EmpresaLTCATForm
    template_name = "ltcat/empresa_ltcat_form.html"
    permission_required = "ltcat.change_empresaltcat"

    def form_valid(self, form):
        messages.success(self.request, "Empresa contratada atualizada com sucesso!")
        return super().form_valid(form)

    def get_success_url(self):
        next_url = self.request.GET.get("next")
        if next_url:
            return next_url
        return reverse("ltcat:empresa_ltcat_list")


class Empresa(LTCATBaseMixin, LTCATAccessMixin, ViewFilialScopedMixin, DeleteView):
    model = EmpresaLTCAT
    template_name = "ltcat/confirma_delete.html"
    permission_required = "ltcat.delete_empresaltcat"
    success_url = reverse_lazy("ltcat:empresa_ltcat_list")

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Empresa contratada excluida com sucesso!")
        return super().delete(request, *args, **kwargs)

    def form_valid(self, form):
        self.object.delete()  # soft delete (model)
        audit.info('ltcat_cancelado doc=%s user=%s', self.object.pk, self.request.user.pk)
        messages.success(self.request, 'LTCAT cancelado (mantido para guarda legal).')
        return redirect(self.success_url)

class LTCATDeleteView(LTCATBaseMixin, LTCATAccessMixin, ViewFilialScopedMixin,
                      LTCATDeleteContextMixin, DeleteView):
    model = LTCATDocumento
    template_name = "ltcat/confirma_delete.html"
    success_url = reverse_lazy("ltcat:ltcat_list")
    permission_required = "ltcat.delete_ltcatdocumento"
    cancel_url_name = "ltcat:ltcat_list"
    voltar_label = "Laudos"
    soft_delete = True
    confirma_label = "Cancelar LTCAT"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not self.check_ltcat_access(obj):
            raise Http404("LTCAT não encontrado.")
        return obj

    def form_valid(self, form):
        self.object.delete()  # soft delete
        audit.info("ltcat_cancelado doc=%s user=%s", self.object.pk, self.request.user.pk)
        messages.success(self.request, "LTCAT cancelado (mantido para guarda legal).")
        return redirect(self.success_url)

# Exclusão: bloqueia no servidor também
class EmpresaLTCATDeleteView(PermissionRequiredMixin, DeleteView):
    permission_required = 'ltcat.delete_empresaltcat'
    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx['laudos_vinculados'] = self.object.documentos_ltcat_contratada.count()
        return ctx
    
    def form_valid(self, form):
        if self.object.documentos_ltcat_contratada.exists():
            messages.error(self.request, 'A empresa está vinculada a laudos e não pode ser excluída.')
            return redirect('ltcat:empresa_ltcat_list')
        return super().form_valid(form)

# models.py — garante a mesma regra no banco
contratada = models.ForeignKey(EmpresaLTCAT, on_delete=models.PROTECT, null=True, blank=True, related_name='ltcats')


# =============================================================================
# == LTCAT DOCUMENTO - CRUD
# =============================================================================

class LTCATListView(LTCATBaseMixin, ViewFilialScopedMixin, ListView):
    model = LTCATDocumento
    template_name = "ltcat/ltcat_list.html"
    context_object_name = "ltcats"
    paginate_by = 15
    permission_required = "ltcat.view_ltcatdocumento"

    def get_queryset(self):
        qs = (
            super().get_queryset()
            .select_related("empresa", "filial")
            .annotate(
                total_funcoes=Count("funcoes"),
                total_riscos=Count("funcoes__riscos"),
            )
        )

        status = self.request.GET.get("status")
        busca = self.request.GET.get("q")
        if status:
            qs = qs.filter(status=status)
        if busca:
            qs = qs.filter(
                Q(empresa__razao_social__icontains=busca)
                | Q(titulo__icontains=busca)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = STATUS_LTCAT_CHOICES
        ctx["status_atual"] = self.request.GET.get("status", "")
        ctx["busca"] = self.request.GET.get("q", "")
        return ctx


class LTCATCreateView(LTCATBaseMixin, FilialFormKwargsMixin, FilialCreateMixin, CreateView):
    model = LTCATDocumento
    form_class = LTCATForm
    template_name = "ltcat/ltcat_form.html"
    permission_required = "ltcat.add_ltcatdocumento"

    def form_valid(self, form):
        form.instance.criado_por = self.request.user
        messages.success(self.request, "LTCAT criado com sucesso!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.object.pk})


class LTCATUpdateView(LTCATBaseMixin, FilialFormKwargsMixin, LTCATAccessMixin, ViewFilialScopedMixin, UpdateView):
    model = LTCATDocumento
    form_class = LTCATForm
    template_name = "ltcat/ltcat_form.html"
    permission_required = "ltcat.change_ltcatdocumento"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not self.check_ltcat_access(obj):
            raise Http404("LTCAT nao encontrado.")
        return obj

    def form_valid(self, form):
        if form.cleaned_data['status'] in ('aprovado', 'vigente'):
            pend = form.instance.pendencias_legais
            if pend:
                form.add_error('status', 'Pendências: ' + '; '.join(pend))
                return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.object.pk})


class LTCATDetailView(LTCATBaseMixin, LTCATAccessMixin, ViewFilialScopedMixin, DetailView):
    model = LTCATDocumento
    template_name = "ltcat/ltcat_detail.html"
    context_object_name = "ltcat"
    permission_required = "ltcat.view_ltcatdocumento"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not self.check_ltcat_access(obj):
            raise Http404("LTCAT nao encontrado.")
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ltcat_doc = self.object
        ctx["revisoes"] = ltcat_doc.revisoes.all()
        ctx["funcoes"] = ltcat_doc.funcoes.prefetch_related("riscos").all()
        ctx["periculosidades"] = ltcat_doc.avaliacoes_periculosidade.all()
        ctx["conclusoes"] = ltcat_doc.conclusoes.select_related("funcao").all()
        ctx["recomendacoes"] = ltcat_doc.recomendacoes.all()
        ctx["anexos"] = ltcat_doc.anexos.all()
        ctx['locais'] = LocalPrestacaoServicoLTCAT.objects.filter(
            empresa=ltcat_doc.empresa, filial=ltcat_doc.filial)

        # Responsaveis vinculados
        ctx["responsaveis_doc"] = LTCATDocumentoResponsavel.objects.filter(
            ltcat_documento=ltcat_doc
        ).select_related("profissional", "profissional__funcionario")

        ctx['funcionarios_disponiveis'] = (Funcionario.objects
            .filter(filial=ltcat_doc.filial, status='ativo')
            .only('id', 'nome_completo', 'cargo__nome')       # minimização LGPD
            .select_related('cargo').order_by('nome_completo'))
        ctx['pendencias'] = ltcat_doc.pendencias_legais

        ctx["tipos_responsabilidade"] = TIPO_RESPONSABILIDADE_LTCAT_CHOICES
        return ctx


class LTCATDeleteView(LTCATBaseMixin, LTCATAccessMixin, ViewFilialScopedMixin, DeleteView):
    model = LTCATDocumento
    template_name = "ltcat/confirma_delete.html"
    success_url = reverse_lazy("ltcat:ltcat_list")
    permission_required = "ltcat.delete_ltcatdocumento"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not self.check_ltcat_access(obj):
            raise Http404("LTCAT não encontrado.")
        return obj

    def form_valid(self, form):
        self.object.delete()  # soft delete (model)
        audit.info('ltcat_cancelado doc=%s user=%s', self.object.pk, self.request.user.pk)
        messages.success(self.request, 'LTCAT cancelado (mantido para guarda legal).')
        return redirect(self.success_url)


# =============================================================================
# == LOCAIS DE PRESTACAO DE SERVICO - CRUD
# =============================================================================

class LocalPrestacaoListView(LTCATBaseMixin, ViewFilialScopedMixin, ListView):
    model = LocalPrestacaoServicoLTCAT
    template_name = "ltcat/local_list.html"
    context_object_name = "locais"
    paginate_by = 20
    permission_required = "ltcat.view_localprestacaoservicoltcat"

    def get_queryset(self):
        qs = super().get_queryset().select_related("empresa", "logradouro", "filial")
        busca = self.request.GET.get("q")
        empresa_id = self.request.GET.get("empresa")
        if busca:
            qs = qs.filter(
                Q(nome_local__icontains=busca)
                | Q(empresa__razao_social__icontains=busca)
                | Q(cidade__icontains=busca)
            )
        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["busca"] = self.request.GET.get("q", "")
        return ctx


class LocalPrestacaoCreateView(LTCATBaseMixin, FilialFormKwargsMixin, FilialCreateMixin, CreateView):
    model = LocalPrestacaoServicoLTCAT
    form_class = LocalPrestacaoServicoForm
    template_name = "ltcat/local_form.html"
    permission_required = "ltcat.add_localprestacaoservicoltcat"
    success_url = reverse_lazy("ltcat:local_list")

    def form_valid(self, form):
        form.instance.criado_por = self.request.user
        messages.success(self.request, "Local de prestacao cadastrado com sucesso!")
        return super().form_valid(form)


class LocalPrestacaoUpdateView(LTCATBaseMixin, FilialFormKwargsMixin, ViewFilialScopedMixin, UpdateView):
    model = LocalPrestacaoServicoLTCAT
    form_class = LocalPrestacaoServicoForm
    template_name = "ltcat/local_form.html"
    permission_required = "ltcat.change_localprestacaoservicoltcat"
    success_url = reverse_lazy("ltcat:local_list")

    def form_valid(self, form):
        messages.success(self.request, "Local de prestacao atualizado!")
        return super().form_valid(form)


class LocalPrestacaoDeleteView(LTCATBaseMixin, ViewFilialScopedMixin,
                               LTCATDeleteContextMixin, DeleteView):
    model = LocalPrestacaoServicoLTCAT
    template_name = "ltcat/confirma_delete.html"
    permission_required = "ltcat.delete_localprestacaoservicoltcat"
    success_url = reverse_lazy("ltcat:local_list")
    cancel_url_name = "ltcat:local_list"
    voltar_label = "Locais"

    def form_valid(self, form):
        messages.success(self.request, "Local excluído com sucesso!")
        return super().form_valid(form)

# =============================================================================
# == REVISOES (filho de LTCAT)
# =============================================================================

class RevisaoCreateView(LTCATChildMixin, CreateView):  # mantenha seus mixins
    model = RevisaoLTCAT
    form_class = RevisaoLTCATForm
    template_name = "ltcat/revisao_form.html"
    permission_required = "ltcat.add_revisaoltcat"

    def get_proxima_revisao(self):
        if not hasattr(self, "_proxima"):
            ultimo = (RevisaoLTCAT.objects
                      .filter(ltcat_documento=self.get_ltcat())
                      .aggregate(m=Max("numero_revisao"))["m"])
            self._proxima = 0 if ultimo is None else int(ultimo) + 1
        return self._proxima

    def get_initial(self):
        initial = super().get_initial()
        u = self.request.user
        initial.update({
            "numero_revisao": self.get_proxima_revisao(),
            "data_realizada": date.today(),
            "realizada_por": u.get_full_name() or u.get_username(),
        })
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["proxima_revisao"] = self.get_proxima_revisao()
        return ctx

    def form_valid(self, form):
        ltcat = self.get_ltcat()
        form.instance.ltcat_documento = ltcat
        numero = form.cleaned_data.get("numero_revisao")
        if RevisaoLTCAT.objects.filter(ltcat_documento=ltcat, numero_revisao=numero).exists():
            form.add_error("numero_revisao", f"Já existe a revisão nº {numero} para este laudo.")
            return self.form_invalid(form)
        try:
            with transaction.atomic():
                response = super().form_valid(form)
        except IntegrityError:
            form.add_error("numero_revisao", "Número de revisão já utilizado.")
            return self.form_invalid(form)
        messages.success(self.request, "Revisão cadastrada com sucesso!")
        return response

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.get_ltcat().pk})

class RevisaoUpdateView(LTCATChildMixin, UpdateView):
    model = RevisaoLTCAT
    form_class = RevisaoLTCATForm
    template_name = "ltcat/revisao_form.html"
    permission_required = "ltcat.change_revisaoltcat"

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


class RevisaoDeleteView(LTCATChildMixin, DeleteView):
    model = RevisaoLTCAT
    template_name = "ltcat/confirma_delete.html"
    permission_required = "ltcat.delete_revisaoltcat"

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


# =============================================================================
# == FUNCOES ANALISADAS (filho de LTCAT)
# =============================================================================

class FuncaoCreateView(LTCATChildMixin, CreateView):
    model = FuncaoAnalisada
    form_class = FuncaoAnalisadaForm
    template_name = "ltcat/funcao_form.html"
    permission_required = "ltcat.add_funcaoanalisada"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["ltcat"] = self.get_ltcat()
        return kwargs

    def form_valid(self, form):
        form.instance.ltcat_documento = self.get_ltcat()
        messages.success(self.request, "Funcao adicionada com sucesso!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


class FuncaoUpdateView(LTCATChildMixin, UpdateView):
    model = FuncaoAnalisada
    form_class = FuncaoAnalisadaForm
    template_name = "ltcat/funcao_form.html"
    permission_required = "ltcat.change_funcaoanalisada"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["ltcat"] = self.get_ltcat()
        return kwargs

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


class FuncaoDeleteView(LTCATChildMixin, DeleteView):
    model = FuncaoAnalisada
    template_name = "ltcat/confirma_delete.html"
    permission_required = "ltcat.delete_funcaoanalisada"

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


# =============================================================================
# == RECONHECIMENTO DE RISCOS (filho de LTCAT)
# =============================================================================
class RiscoScopeMixin:
    def get_queryset(self):
        return ReconhecimentoRisco.objects.filter(funcao__ltcat_documento=self.get_ltcat())
class RiscoCreateView(LTCATChildMixin, CreateView):
    """Cria um risco vinculado a um LTCAT (e opcionalmente a uma funcao)."""
    model = ReconhecimentoRisco
    form_class = ReconhecimentoRiscoForm
    template_name = "ltcat/risco_form.html"
    permission_required = "ltcat.add_reconhecimentorisco"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["ltcat"] = self.get_ltcat()
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        funcao_pk = self.request.GET.get("funcao") or self.kwargs.get("funcao_pk")
        ctx['funcao'] = FuncaoAnalisada.objects.filter(
            pk=funcao_pk, ltcat_documento=self.get_ltcat()).first() if funcao_pk else None
        return ctx

    def get_initial(self):
        initial = super().get_initial()
        funcao_pk = self.request.GET.get("funcao") or self.kwargs.get("funcao_pk")
        if funcao_pk:
            initial["funcao"] = funcao_pk
        return initial

    def form_valid(self, form):
        if form.cleaned_data['funcao'].ltcat_documento_id != self.get_ltcat().pk:
            raise PermissionDenied
        messages.success(self.request, 'Risco cadastrado com sucesso!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


class RiscoUpdateView(RiscoScopeMixin, LTCATChildMixin, UpdateView):
    model = ReconhecimentoRisco
    form_class = ReconhecimentoRiscoForm
    template_name = "ltcat/risco_form.html"
    permission_required = "ltcat.change_reconhecimentorisco"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["ltcat"] = self.get_ltcat()
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Risco atualizado com sucesso!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})

class RiscoDeleteView(RiscoScopeMixin, LTCATChildMixin, DeleteView):
    model = ReconhecimentoRisco
    template_name = "ltcat/confirma_delete.html"
    permission_required = "ltcat.delete_reconhecimentorisco"

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


# =============================================================================
# == AVALIACAO DE PERICULOSIDADE (filho de LTCAT)
# =============================================================================

class PericulosidadeCreateView(LTCATChildMixin, CreateView):
    model = AvaliacaoPericulosidade
    form_class = AvaliacaoPericulosidadeForm
    template_name = "ltcat/periculosidade_form.html"
    permission_required = "ltcat.add_avaliacaopericulosidade"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["ltcat"] = self.get_ltcat()
        return kwargs

    def form_valid(self, form):
        form.instance.ltcat_documento = self.get_ltcat()
        messages.success(self.request, "Avaliacao de periculosidade adicionada!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


class PericulosidadeUpdateView(LTCATChildMixin, UpdateView):
    model = AvaliacaoPericulosidade
    form_class = AvaliacaoPericulosidadeForm
    template_name = "ltcat/periculosidade_form.html"
    permission_required = "ltcat.change_avaliacaopericulosidade"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["ltcat"] = self.get_ltcat()
        return kwargs

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


# =============================================================================
# == CONCLUSOES (filho de LTCAT)
# =============================================================================

class ConclusaoCreateView(LTCATChildMixin, CreateView):
    model = ConclusaoFuncao
    form_class = ConclusaoFuncaoForm
    template_name = "ltcat/conclusao_form.html"
    permission_required = "ltcat.add_conclusaofuncao"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["ltcat"] = self.get_ltcat()
        return kwargs

    def form_valid(self, form):
        form.instance.ltcat_documento = self.get_ltcat()
        messages.success(self.request, "Conclusao adicionada com sucesso!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


class ConclusaoUpdateView(LTCATChildMixin, UpdateView):
    model = ConclusaoFuncao
    form_class = ConclusaoFuncaoForm
    template_name = "ltcat/conclusao_form.html"
    permission_required = "ltcat.change_conclusaofuncao"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["ltcat"] = self.get_ltcat()
        return kwargs

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


# =============================================================================
# == RECOMENDACOES (filho de LTCAT)
# =============================================================================

class RecomendacaoCreateView(LTCATChildMixin, CreateView):
    model = RecomendacaoTecnica
    form_class = RecomendacaoTecnicaForm
    template_name = "ltcat/recomendacao_form.html"
    permission_required = "ltcat.add_recomendacaotecnica"

    def form_valid(self, form):
        form.instance.ltcat_documento = self.get_ltcat()
        messages.success(self.request, "Recomendacao adicionada com sucesso!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


class RecomendacaoUpdateView(LTCATChildMixin, UpdateView):
    model = RecomendacaoTecnica
    form_class = RecomendacaoTecnicaForm
    template_name = "ltcat/recomendacao_form.html"
    permission_required = "ltcat.change_recomendacaotecnica"

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


class RecomendacaoDeleteView(LTCATChildMixin, DeleteView):
    model = RecomendacaoTecnica
    template_name = "ltcat/confirma_delete.html"
    permission_required = "ltcat.delete_recomendacaotecnica"

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


# =============================================================================
# == ANEXOS (filho de LTCAT)
# =============================================================================

class AnexoCreateView(LTCATChildMixin, CreateView):
    model = AnexoLTCAT
    form_class = AnexoLTCATForm
    template_name = "ltcat/anexo_form.html"
    permission_required = "ltcat.add_anexoltcat"

    def form_valid(self, form):
        form.instance.ltcat_documento = self.get_ltcat()
        messages.success(self.request, "Anexo adicionado com sucesso!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


class AnexoDeleteView(LTCATChildMixin, DeleteView):
    model = AnexoLTCAT
    template_name = "ltcat/confirma_delete.html"
    permission_required = "ltcat.delete_anexoltcat"

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


# =============================================================================
# == HELPERS PRIVADOS (uso interno das FBVs AJAX)
# =============================================================================

def _user_pode_acessar_ltcat(user, ltcat_doc, session_filial_id):
    """Replica logica do LTCATAccessMixin para FBVs."""
    if user.is_superuser or user.is_staff:
        return True
    return bool(session_filial_id) and ltcat_doc.filial_id == int(session_filial_id)


# =============================================================================
# == AJAX - LOCAIS DE PRESTACAO
# =============================================================================

@funcionario_required
def ajax_locais_por_empresa(request):
    """Retorna locais de prestacao filtrados por empresa (Cliente)."""
    empresa_id = request.GET.get("empresa_id")
    if not empresa_id:
        return JsonResponse([], safe=False)

    qs = LocalPrestacaoServicoLTCAT.objects.filter(empresa_id=empresa_id)

    user = request.user
    filial_id = request.session.get("active_filial_id")
    if not (user.is_superuser or user.is_staff) and filial_id:
        qs = qs.filter(filial_id=filial_id)

    locais = [{"id": str(loc.pk), "nome": str(loc)} for loc in qs]
    return JsonResponse(locais, safe=False)


@funcionario_required
def ajax_buscar_logradouros(request):
    """Autocomplete de logradouros com busca por texto."""
    from logradouro.models import Logradouro

    termo = request.GET.get("q", "").strip()
    if len(termo) < 2:
        return JsonResponse([], safe=False)

    filial_id = request.session.get("active_filial_id")
    qs = Logradouro.objects.all()

    user = request.user
    if not (user.is_superuser or user.is_staff) and filial_id:
        qs = qs.filter(filial_id=filial_id)
    elif filial_id:
        qs = qs.filter(filial_id=filial_id)

    qs = qs.filter(
        Q(endereco__icontains=termo)
        | Q(bairro__icontains=termo)
        | Q(cidade__icontains=termo)
        | Q(cep__icontains=termo.replace("-", ""))
    )[:20]

    resultados = [
        {
            "id": log.pk,
            "text": log.get_endereco_completo(),
            "endereco": log.endereco,
            "numero": log.numero,
            "bairro": log.bairro,
            "cidade": log.cidade,
            "estado": log.estado,
            "cep": log.cep_formatado,
        }
        for log in qs
    ]
    return JsonResponse(resultados, safe=False)


@ajax_perm('ltcat.add_localprestacaoservicoltcat')
@require_POST
def ajax_local_create_bulk(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)
    empresa = get_object_or_404(_filial_qs(request, Cliente.objects.all()), pk=data.get('empresa_id'))
    locais = data.get('locais') or []
    if not 0 < len(locais) <= 50:
        return JsonResponse({'error': 'Envie de 1 a 50 locais.'}, status=400)

    erros, objs = [], []
    for i, item in enumerate(locais, 1):
        form = LocalPrestacaoServicoForm(item | {'empresa': empresa.pk}, filial=empresa.filial)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.filial = empresa.filial
            objs.append(obj)
        else:
            erros += [f'Unidade {i}: {e}' for e in form.errors.as_text().splitlines() if e.strip()]
    if erros:
        return JsonResponse({'errors': erros}, status=400)
    with transaction.atomic():
        for o in objs:
            o.save()
    messages.success(request, f'{len(objs)} local(is) cadastrado(s) com sucesso!')
    return JsonResponse({'success': True, 'total': len(objs), 'redirect': reverse('ltcat:local_list')})
  
# =============================================================================
# == AJAX - DADOS DE CLIENTE
# =============================================================================

@ajax_perm('ltcat.add_empresaltcat')
def ajax_dados_cliente(request):
    cliente = get_object_or_404(_filial_qs(request, Cliente.objects.all()),
                                pk=request.GET.get('cliente_id'))

    log = getattr(cliente, "logradouro", None)
    dados = {
        "razao_social": cliente.razao_social or "",
        "cnpj": getattr(cliente, "cnpj", "") or "",
        "telefone": getattr(cliente, "telefone", "") or "",
        "email": getattr(cliente, "email", "") or "",
        "endereco": "",
        "numero": "",
        "complemento": "",
        "bairro": "",
        "cidade": "",
        "estado": "",
        "cep": "",
    }

    if log:
        dados.update({
            "endereco": getattr(log, "endereco", "") or "",
            "numero": getattr(log, "numero", "") or "",
            "complemento": getattr(log, "complemento", "") or "",
            "bairro": getattr(log, "bairro", "") or "",
            "cidade": getattr(log, "cidade", "") or "",
            "estado": getattr(log, "estado", "") or "",
            "cep": getattr(log, "cep", "") or "",
        })

    return JsonResponse(dados)


# =============================================================================
# == AJAX - VINCULOS LOCAIS x DOCUMENTO LTCAT
# =============================================================================

@funcionario_required
@require_POST
def ajax_vincular_locais_documento(request, ltcat_pk):
    """Vincula locais de prestacao ao documento LTCAT."""
    ltcat_doc = get_object_or_404(LTCATDocumento, pk=ltcat_pk)
    filial_id = request.session.get("active_filial_id")

    if not _user_pode_acessar_ltcat(request.user, ltcat_doc, filial_id):
        return JsonResponse({"error": "Sem permissao."}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON invalido."}, status=400)

    local_ids = data.get("local_ids", [])
    if not local_ids:
        return JsonResponse({"error": "Nenhum local informado."}, status=400)

    locais = LocalPrestacaoServicoLTCAT.objects.filter(
        pk__in=local_ids, empresa=ltcat_doc.empresa,
    )

    ja_vinculados = set(
        DocumentoLocalPrestacao.objects.filter(
            ltcat_documento=ltcat_doc, local_prestacao_id__in=local_ids,
        ).values_list("local_prestacao_id", flat=True)
    )

    tem_principal = DocumentoLocalPrestacao.objects.filter(
        ltcat_documento=ltcat_doc, principal=True,
    ).exists()

    novos = []
    for idx, local in enumerate(locais):
        if local.pk not in ja_vinculados:
            novos.append(DocumentoLocalPrestacao(
                ltcat_documento=ltcat_doc,
                local_prestacao=local,
                principal=(not tem_principal and idx == 0 and not novos),
                ordem=DocumentoLocalPrestacao.objects.filter(
                    ltcat_documento=ltcat_doc
                ).count() + len(novos),
            ))

    if novos:
        DocumentoLocalPrestacao.objects.bulk_create(novos)

    total = len(novos)
    return JsonResponse({
        "success": True,
        "vinculados": total,
        "message": f"{total} local(is) vinculado(s) ao documento.",
    })

@funcionario_required
@require_POST
def ajax_desvincular_local_documento(request, ltcat_pk, pk):
    """Remove o vínculo de um local com o documento LTCAT."""
    ltcat_doc = get_object_or_404(LTCATDocumento, pk=ltcat_pk)
    filial_id = request.session.get("active_filial_id")

    if not _user_pode_acessar_ltcat(request.user, ltcat_doc, filial_id):
        return JsonResponse({"success": False, "error": "Sem permissão."}, status=403)

    vinculo = (DocumentoLocalPrestacao.objects
               .select_related('local_prestacao')
               .filter(pk=pk, ltcat_documento=ltcat_doc)
               .first())
    if not vinculo:
        return JsonResponse({"success": False,
                             "error": "Local não vinculado a este laudo."}, status=404)

    nome = vinculo.local_prestacao.nome_local
    vinculo.delete()

    return JsonResponse({
        "success": True,
        "message": f"Local '{nome}' desvinculado do documento.",
    })

@funcionario_required
@require_POST
def ajax_toggle_principal_local(request, ltcat_pk, pk):
    """Marca/desmarca um local como principal no documento."""
    ltcat_doc = get_object_or_404(LTCATDocumento, pk=ltcat_pk)
    filial_id = request.session.get("active_filial_id")

    if not _user_pode_acessar_ltcat(request.user, ltcat_doc, filial_id):
        return JsonResponse({"error": "Sem permissao."}, status=403)

    vinculo = get_object_or_404(
        DocumentoLocalPrestacao, pk=pk, ltcat_documento=ltcat_doc,
    )
    vinculo.principal = not vinculo.principal
    vinculo.save()

    return JsonResponse({
        "success": True,
        "principal": vinculo.principal,
        "message": (
            f"Local '{vinculo.local_prestacao.nome_local}' "
            f"{'marcado como' if vinculo.principal else 'desmarcado de'} principal."
        ),
    })


# =============================================================================
# == AJAX - INFO CARGO/FUNCAO
# =============================================================================

@ajax_perm('ltcat.view_funcaoanalisada')
def ajax_cargo_info(request):
    cargo = get_object_or_404(_filial_qs(request, Cargo.objects.filter(ativo=True)),
                              pk=request.GET.get('cargo_id'))
    return JsonResponse({'nome': cargo.nome, 'cbo': cargo.cbo or '',
                         'descricao': cargo.descricao or ''})


@ajax_perm('ltcat.view_funcaoanalisada')
def ajax_funcao_st_info(request):
    """Retorna nome e descricao de uma Funcao (Seguranca do Trabalho)."""
    funcao = get_object_or_404(_filial_qs(request, Funcao.objects.filter(ativo=True)),
                                  pk=request.GET.get('funcao_id'))
                                             
    return JsonResponse({"nome": funcao.nome, "registro": funcao.registro or "",
                "descricao": funcao.descricao or "",})

# =============================================================================
# == AJAX - RESPONSAVEIS DO DOCUMENTO LTCAT
# =============================================================================

@require_POST
@ajax_perm('ltcat.change_ltcatdocumento')
def ajax_vincular_responsavel(request, ltcat_pk):
    ltcat_doc = _get_ltcat_or_404(request, ltcat_pk)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido."}, status=400)

    funcionario_id = data.get("funcionario_id")
    tipo = data.get("tipo_responsabilidade", "elaborador")
    funcao_prof = data.get("funcao_profissional", "").strip()
    registro = data.get("registro_classe", "").strip()
    orgao = data.get("orgao_classe", "").strip()

    if not funcionario_id:
        return JsonResponse({"error": "Funcionário não informado."}, status=400)
    if not funcao_prof:
        return JsonResponse({"error": "Função profissional é obrigatória."}, status=400)
    if not registro:
        return JsonResponse({"error": "Registro de classe é obrigatório."}, status=400)

    funcionario = get_object_or_404(
        Funcionario.objects.filter(filial=ltcat_doc.filial, status='ativo'), pk=funcionario_id)

    profissional = ProfissionalResponsavelLTCAT.objects.filter(
        funcionario=funcionario, filial=ltcat_doc.filial,
    ).first()

    if not profissional:
        profissional = ProfissionalResponsavelLTCAT.objects.create(
            funcionario=funcionario,
            filial=ltcat_doc.filial,
            nome_completo=funcionario.nome_completo,
            funcao=funcao_prof,
            registro_classe=registro,
            orgao_classe=orgao or None,
            email=getattr(funcionario, "email_pessoal", None) or None,
            telefone=getattr(funcionario, "telefone", None) or None,
        )
    else:
        atualizar = False
        if funcao_prof and profissional.funcao != funcao_prof:
            profissional.funcao = funcao_prof
            atualizar = True
        if registro and profissional.registro_classe != registro:
            profissional.registro_classe = registro
            atualizar = True
        if orgao and profissional.orgao_classe != orgao:
            profissional.orgao_classe = orgao
            atualizar = True
        if atualizar:
            profissional.save()

    vinculo, created = LTCATDocumentoResponsavel.objects.get_or_create(
        ltcat_documento=ltcat_doc,
        profissional=profissional,
        defaults={"tipo_responsabilidade": tipo},
    )

    if not created:
        return JsonResponse({
            "error": f"{profissional.nome_completo} ja esta vinculado a este documento."
        }, status=400)

    return JsonResponse({
        "success": True,
        "vinculo_id": vinculo.pk,
        "profissional_id": profissional.pk,
        "nome": profissional.nome_completo,
        "funcao": profissional.funcao,
        "registro": profissional.registro_classe,
        "tipo": vinculo.get_tipo_responsabilidade_display(),
        "message": f"{profissional.nome_completo} vinculado com sucesso.",
    })


@funcionario_required
@require_POST
def ajax_desvincular_responsavel(request, ltcat_pk, pk):
    """Desvincula um profissional do documento LTCAT."""
    ltcat_doc = get_object_or_404(LTCATDocumento, pk=ltcat_pk)
    filial_id = request.session.get("active_filial_id")

    if not _user_pode_acessar_ltcat(request.user, ltcat_doc, filial_id):
        return JsonResponse({"error": "Sem permissao."}, status=403)

    vinculo = get_object_or_404(
        LTCATDocumentoResponsavel, pk=pk, ltcat_documento=ltcat_doc
    )
    nome = vinculo.profissional.nome_completo
    vinculo.delete()

    return JsonResponse({
        "success": True,
        "message": f"{nome} desvinculado com sucesso.",
    })


@ajax_perm('ltcat.change_profissionalresponsavelltcat')
@require_POST
def ajax_salvar_assinatura(request, pk):
    profissional = get_object_or_404(
        _filial_qs(request, ProfissionalResponsavelLTCAT.objects.all()), pk=pk)
    if len(request.body) > MAX_ASSINATURA_BYTES * 1.4:
        return JsonResponse({'error': 'Arquivo muito grande.'}, status=413)
    try:
        data = json.loads(request.body)
        _, imgstr = data['assinatura'].split(';base64,', 1)
        raw = base64.b64decode(imgstr, validate=True)
    except (ValueError, KeyError, json.JSONDecodeError):
        return JsonResponse({'error': 'Dados de assinatura inválidos.'}, status=400)
    if len(raw) > MAX_ASSINATURA_BYTES:
        return JsonResponse({'error': 'Arquivo muito grande.'}, status=413)

    arquivo = ContentFile(raw, name=f'assinatura_{profissional.pk}.png')  # nome sem PII
    if profissional.assinatura_imagem:
        profissional.assinatura_imagem.delete(save=False)
    profissional.assinatura_imagem = arquivo
    profissional.save(update_fields=["assinatura_imagem"])
    audit.info('assinatura_salva prof=%s user=%s', profissional.pk, request.user.pk)
    return JsonResponse({"success": True, "message": "Assinatura salva com sucesso."})

@funcionario_required
@require_POST
def ajax_limpar_assinatura(request, pk):
    """Remove a assinatura digital de um profissional."""
    profissional = get_object_or_404(ProfissionalResponsavelLTCAT, pk=pk)
    filial_id = request.session.get("active_filial_id")

    user = request.user
    if not (user.is_superuser or user.is_staff):
        if not filial_id or profissional.filial_id != int(filial_id):
            return JsonResponse({"error": "Sem permissao."}, status=403)

    if profissional.assinatura_imagem:
        try:
            profissional.assinatura_imagem.delete(save=False)
        except Exception:
            pass
        profissional.assinatura_imagem = None
        profissional.save(update_fields=["assinatura_imagem"])

    return JsonResponse({
        "success": True,
        "message": "Assinatura removida com sucesso.",
    })


@funcionario_required
def ajax_buscar_profissional_por_funcionario(request):
    """
    Retorna dados do ProfissionalResponsavelLTCAT vinculado a um funcionario,
    se existir. Usado para pre-preencher o modal.
    """
    funcionario_id = request.GET.get("funcionario_id")
    if not funcionario_id:
        return JsonResponse({"found": False})

    filial_id = request.session.get("active_filial_id")
    profissional = ProfissionalResponsavelLTCAT.objects.filter(
        funcionario_id=funcionario_id, filial_id=filial_id,
    ).first()

    if profissional:
        return JsonResponse({
            "found": True,
            "funcao_profissional": profissional.funcao,
            "registro_classe": profissional.registro_classe,
            "orgao_classe": profissional.orgao_classe or "",
        })

    return JsonResponse({"found": False})


# =============================================================================
# == GERACAO DE PDF
# =============================================================================

@ajax_perm('ltcat.view_ltcatdocumento')
def gerar_pdf_ltcat(request, pk):
    from .relatorio_pdf import LTCATRelatorio
    doc = _get_ltcat_or_404(request, pk)
    pdf = LTCATRelatorio(doc).gerar()
    audit.info('pdf_gerado doc=%s user=%s ip=%s', doc.pk, request.user.pk,
               request.META.get('REMOTE_ADDR'))
    resp = HttpResponse(pdf, content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="LTCAT_{doc.codigo_documento}.pdf"'
    resp['Cache-Control'] = 'no-store'
    return resp

# ═════════════════════════════════════════════════════════════════════
# Medidas
# ═════════════════════════════════════════════════════════════════════
class MedidaScopeMixin:
    """Escopo: só medidas de riscos do LTCAT da URL (evita IDOR)."""
    model = MedidaControle

    def get_queryset(self):
        return MedidaControle.objects.filter(
            risco__funcao__ltcat_documento=self.get_ltcat()
        ).select_related('risco', 'risco__funcao')

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


class MedidaCreateView(MedidaScopeMixin, LTCATChildMixin, CreateView):
    form_class = MedidaControleForm
    template_name = "ltcat/medida_form.html"
    permission_required = "ltcat.add_medidacontrole"

    def get_risco(self):
        if not hasattr(self, '_risco'):
            self._risco = get_object_or_404(
                ReconhecimentoRisco,
                pk=self.kwargs["risco_pk"],
                funcao__ltcat_documento=self.get_ltcat(),
            )
        return self._risco

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["risco"] = self.get_risco()
        return ctx

    def form_valid(self, form):
        form.instance.risco = self.get_risco()
        messages.success(self.request, "Medida de controle cadastrada com sucesso!")
        return super().form_valid(form)


class MedidaUpdateView(MedidaScopeMixin, LTCATChildMixin, UpdateView):
    form_class = MedidaControleForm
    template_name = "ltcat/medida_form.html"
    permission_required = "ltcat.change_medidacontrole"

    def form_valid(self, form):
        messages.success(self.request, "Medida de controle atualizada!")
        return super().form_valid(form)


class MedidaDeleteView(MedidaScopeMixin, LTCATChildMixin, DeleteView):
    template_name = "ltcat/confirma_delete.html"
    permission_required = "ltcat.delete_medidacontrole"

    def form_valid(self, form):          # Django ≥ 4 (delete() não é chamado)
        messages.success(self.request, "Medida de controle excluída!")
        return super().form_valid(form)


# Necessária se a rota "anexo_download" já está no urls.py
@ajax_perm('ltcat.view_anexoltcat')
def anexo_download(request, ltcat_pk, pk):
    from django.conf import settings
    from django.http import FileResponse
    doc = _get_ltcat_or_404(request, ltcat_pk)
    anexo = get_object_or_404(AnexoLTCAT, pk=pk, ltcat_documento=doc)
    audit.info('anexo_download anexo=%s user=%s', anexo.pk, request.user.pk)
    ext = (anexo.extensao or 'bin').lower()
    nome = f"anexo_{anexo.pk}.{ext}"
    if settings.DEBUG:
        return FileResponse(anexo.arquivo.open('rb'), as_attachment=True, filename=nome)
    resp = HttpResponse()
    resp['X-Accel-Redirect'] = f'/protected/{anexo.arquivo.name}'
    resp['Content-Type'] = anexo.mime_type or 'application/octet-stream'
    resp['Content-Disposition'] = f'attachment; filename="{nome}"'
    return resp


@funcionario_required
@require_POST
def ajax_gerar_link_assinatura(request, ltcat_pk, prof_pk):
    ltcat_doc = get_object_or_404(LTCATDocumento, pk=ltcat_pk)
    filial_id = request.session.get("active_filial_id")

    if not _user_pode_acessar_ltcat(request.user, ltcat_doc, filial_id):
        return JsonResponse({"success": False, "error": "Sem permissão."}, status=403)

    prof = (ProfissionalResponsavelLTCAT.objects
            .filter(pk=prof_pk, ltcatdocumento=ltcat_doc)
            .first())
    if not prof:
        return JsonResponse({"success": False,
                             "error": "Profissional não vinculado a este laudo."}, status=404)

    if prof.data_assinatura:
        return JsonResponse({"success": False,
                             "error": "Profissional já assinou."}, status=400)

    ct = ContentType.objects.get_for_model(prof)
    TokenAssinaturaRemota.objects.filter(          # invalida os links anteriores
        content_type=ct, object_id=prof.pk, usado_em__isnull=True,
    ).update(usado_em=timezone.now())

    token = prof.gerar_token_assinatura(usuario=request.user, horas_validade=72)
    url = prof.get_link_assinatura(token, request=request)
    expira_em = token.expira_em
    audit.info('link_assinatura doc=%s prof=%s user=%s', ltcat_doc.pk, prof.pk, request.user.pk)
    return JsonResponse({
        "success": True,
        "url": url,
        "expira_em": expira_em.strftime("%d/%m/%Y %H:%M"),
    })


@ajax_perm('ltcat.change_profissionalresponsavelltcat')
@require_POST
def ajax_salvar_assinatura(request, pk):
    prof = get_object_or_404(_filial_qs(request, ProfissionalResponsavelLTCAT.objects.all()), pk=pk)
    if len(request.body) > MAX_ASSINATURA_BYTES * 1.4:
        return JsonResponse({'error': 'Arquivo muito grande.'}, status=413)
    try:
        data = json.loads(request.body)
        if prof.data_assinatura:           # assinatura presencial substitui a anterior
            prof.limpar_assinatura()
        prof.salvar_assinatura(assinatura_base64=data.get('assinatura'),
                               ip=request.META.get('REMOTE_ADDR'))
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)
    except ValidationError as e:
        return JsonResponse({'error': ' '.join(e.messages)}, status=400)
    audit.info('assinatura_salva prof=%s user=%s', prof.pk, request.user.pk)
    return JsonResponse({'success': True})


@ajax_perm('ltcat.change_profissionalresponsavelltcat')
@require_POST
def ajax_limpar_assinatura(request, pk):
    prof = get_object_or_404(_filial_qs(request, ProfissionalResponsavelLTCAT.objects.all()), pk=pk)
    prof.limpar_assinatura()
    audit.info('assinatura_removida prof=%s user=%s', prof.pk, request.user.pk)
    return JsonResponse({'success': True})




