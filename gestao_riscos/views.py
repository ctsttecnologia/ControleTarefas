# gestao_riscos/views.py

import datetime
import logging

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.db.models import Count, ProtectedError, Q, Case, IntegerField, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect

from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView

from core.mixins import FilialCreateMixin
from core.scope import escopo_total
from core.utils import get_filial_ativa
from seguranca_trabalho.models import EntregaEPI

from .forms import CartaoTagForm, IncidenteForm, InspecaoConclusaoForm, InspecaoForm, TipoRiscoForm
from .mixins import GestaoRiscosBaseMixin, GestaoRiscosTecnicoMixin, GestaoRiscosWriteMixin

from django.urls import reverse, reverse_lazy
from .models import (CATEGORIA_RISCO_CHOICES, TIPOS_ZERAM_CONTADOR, GRAVIDADE_CHOICES, SETORES_CHOICES,
                     TIPO_OCORRENCIA_FLAT, STATUS_CHOICES,
                     CartaoTag, Incidente, Inspecao, TipoRisco)

from django.core.cache import cache
from .services import propor_inspecoes



logger = logging.getLogger(__name__)
audit = logging.getLogger('audit.gestao_riscos')  # só IDs — nunca dados pessoais

PERM_SAUDE = 'gestao_riscos.view_dados_saude_incidente'
PERM_ALL_INSPECAO = 'gestao_riscos.view_all_inspecao'
PERM_ALL_CARTAO = 'gestao_riscos.view_all_cartaotag'
MAX_EVENTOS = 1000

# ── Helpers ──────────────────────────────────────────────────────────────────
def _scoped(qs, request, lookup, perm):
    return qs if escopo_total(request.user, perm) else qs.filter(**{lookup: request.user})


def _safe_next(request, fallback):
    url = request.POST.get('next') or request.GET.get('next')
    if url and url_has_allowed_host_and_scheme(
        url, allowed_hosts={request.get_host()}, require_https=request.is_secure(),
    ):
        return redirect(url)
    return redirect(fallback)


class HojeContextMixin:
    """Envia `hoje` ao template para o destaque de cartões vencidos."""

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['hoje'] = timezone.localdate()
        return ctx

class FormRequestKwargsMixin:
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs


# ── Dashboard ────────────────────────────────────────────────────────────────

class GestaoRiscosDashboardView(GestaoRiscosTecnicoMixin, ListView):
    model = Incidente
    template_name = 'gestao_riscos/dashboard.html'
    context_object_name = 'incidentes'
    tecnico_scope_lookup = 'registrado_por'
    permission_view_all = 'gestao_riscos.view_all_incidente'
    CAMPOS_OCULTOS = ('parte_corpo_atingida', 'numero_cat', 'detalhes')  # LGPD/perf

    def get_queryset(self):
        ocultos = list(self.CAMPOS_OCULTOS)
        if not self.request.user.has_perm(PERM_SAUDE):
            ocultos.append('dias_afastamento')
        return (super().get_queryset()
                .select_related('registrado_por')
                .defer(*ocultos)
                .order_by('-data_ocorrencia')[:10])

    def _propor_inspecoes_diario(self, filial):
        """Gera as propostas no máximo 1x por dia e por filial."""
        if not filial or not cache.add(f'propor_insp:{filial.pk}:{timezone.localdate()}', 1, 86400):
            return
        try:
            propor_inspecoes(filial)
        except Exception:
            logger.exception('Falha ao propor inspeções')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        req = self.request

        self._propor_inspecoes_diario(get_filial_ativa(req.user, req))

        base = Inspecao.objects.for_request(req)
        minhas = _scoped(base, req, 'responsavel', PERM_ALL_INSPECAO)

        # Propostas não têm responsável: são visíveis a toda a filial
        ctx['total_propostas'] = base.filter(status='PENDENTE_APROVACAO').count()
        ctx.update(minhas.aggregate(
            total_pendentes=Count('id', filter=Q(status='PENDENTE')),
            total_canceladas=Count('id', filter=Q(status='CANCELADA')),
        ))
        ctx['inspecoes_pendentes'] = (minhas.filter(status='PENDENTE')
                                      .select_related('equipamento', 'responsavel',
                                                      'entrega_epi__equipamento')
                                      .order_by('data_agendada')[:20])
        ctx['inspecoes_propostas'] = (base.filter(status='PENDENTE_APROVACAO')
                                      .select_related('equipamento', 'entrega_epi__equipamento',
                                                      'entrega_epi__ficha__funcionario')
                                      .order_by('data_agendada')[:20])

        # Indicador da filial (não do técnico): ignora quase-acidentes
        ultimo = (Incidente.objects.for_request(req)
                  .filter(tipo_ocorrencia__in=TIPOS_ZERAM_CONTADOR)
                  .order_by('-data_ocorrencia')
                  .values_list('data_ocorrencia', flat=True).first())
        ctx['data_ultimo_acidente'] = ultimo
        ctx['dias_sem_acidentes'] = (
            (timezone.localdate() - timezone.localtime(ultimo).date()).days if ultimo else None
        )
        ctx['titulo_pagina'] = 'Dashboard de Gestão de Riscos'
        ctx['pode_ver_saude'] = req.user.has_perm(PERM_SAUDE)
        return ctx


class ProporInspecoesView(GestaoRiscosBaseMixin, View):
    http_method_names = ['post']
    permission_required = 'gestao_riscos.add_inspecao'

    def post(self, request):
        n = propor_inspecoes(get_filial_ativa(request.user, request))
        messages.success(request, f'{n} inspeção(ões) proposta(s).')
        return redirect('gestao_riscos:lista_riscos')


# ── Incidentes ───────────────────────────────────────────────────────────────
class RegistrarIncidenteView(GestaoRiscosWriteMixin, FormRequestKwargsMixin,
                             FilialCreateMixin, SuccessMessageMixin, CreateView):
    model = Incidente
    form_class = IncidenteForm
    permission_required = 'gestao_riscos.add_incidente'
    template_name = 'gestao_riscos/registrar_incidente.html'
    success_url = reverse_lazy('gestao_riscos:lista_riscos')
    success_message = 'Ocorrência registrada com sucesso!'

    def form_valid(self, form):
        form.instance.registrado_por = self.request.user
        response = super().form_valid(form)
        if self.object and self.object.pk:
            audit.info('incidente_criado id=%s user=%s filial=%s',
                       self.object.pk, self.request.user.pk, self.object.filial_id)
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo_pagina'] = 'Registrar Nova Ocorrência'
        ctx['hoje'] = timezone.localdate()
        return ctx

class ListaIncidenteView(GestaoRiscosTecnicoMixin, ListView):
    model = Incidente
    template_name = 'gestao_riscos/incidente_list.html'
    context_object_name = 'incidentes'
    paginate_by = 20
    tecnico_scope_lookup = 'registrado_por'
    permission_view_all = 'gestao_riscos.view_all_incidente'

    TIPOS = dict(TIPO_OCORRENCIA_FLAT)
    GRAVIDADES = dict(GRAVIDADE_CHOICES)
    SETORES = dict(SETORES_CHOICES)

    @property
    def pode_ver_saude(self):
        return self.request.user.has_perm(PERM_SAUDE)

    def get_queryset(self):
        qs = super().get_queryset().select_related('registrado_por')
        ocultos = ['detalhes', 'parte_corpo_atingida', 'numero_cat']  # LGPD/perf
        if self.pode_ver_saude:
            qs = qs.select_related('funcionario_envolvido')
        else:
            ocultos.append('dias_afastamento')
        qs = qs.defer(*ocultos)

        g = self.request.GET
        if g.get('tipo') in self.TIPOS:
            qs = qs.filter(tipo_ocorrencia=g['tipo'])
        if g.get('gravidade') in self.GRAVIDADES:
            qs = qs.filter(gravidade=g['gravidade'])
        if g.get('setor') in self.SETORES:
            qs = qs.filter(setor=g['setor'])
        if g.get('classificacao') in ('INCIDENTE', 'ACIDENTE'):
            qs = qs.filter(classificacao=g['classificacao'])

        ini, fim = parse_date(g.get('data_ini', '')), parse_date(g.get('data_fim', ''))
        if ini:
            qs = qs.filter(data_ocorrencia__date__gte=ini)
        if fim:
            qs = qs.filter(data_ocorrencia__date__lte=fim)

        search = g.get('search', '').strip()[:100]
        if search:
            qs = qs.filter(Q(descricao__icontains=search) | Q(local_especifico__icontains=search))
        return qs.order_by('-data_ocorrencia')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop('page', None)

        ctx.update(self.object_list.aggregate(
            total=Count('id'),
            total_acidentes=Count('id', filter=Q(classificacao='ACIDENTE')),
            total_incidentes=Count('id', filter=Q(classificacao='INCIDENTE')),
        ))
        ctx.update(
            titulo_pagina='Ocorrências',
            querystring=params.urlencode(),
            pode_ver_saude=self.pode_ver_saude,
            tipos=TIPO_OCORRENCIA_FLAT,
            gravidades=GRAVIDADE_CHOICES,
            setores=SETORES_CHOICES,
            tem_filtro=any(self.request.GET.get(k) for k in
                           ('tipo', 'gravidade', 'setor', 'classificacao',
                            'data_ini', 'data_fim', 'search')),
        )
        return ctx


# ── Inspeções ────────────────────────────────────────────────────────────────
class AgendarInspecaoView(GestaoRiscosWriteMixin, FormRequestKwargsMixin,
                          FilialCreateMixin, SuccessMessageMixin, CreateView):
    model = Inspecao
    form_class = InspecaoForm
    permission_required = 'gestao_riscos.add_inspecao'
    template_name = 'gestao_riscos/inspecao_form.html'
    success_url = reverse_lazy('gestao_riscos:calendario')
    success_message = 'Inspeção agendada com sucesso!'

    def get_initial(self):
        initial = super().get_initial()
        data = parse_date(self.request.GET.get('data', '') or '')
        if data:
            initial['data_agendada'] = data
        initial['responsavel'] = self.request.user
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo_pagina'] = 'Agendar Nova Inspeção'
        return ctx

class ListaInspecoesPropostasView(GestaoRiscosBaseMixin, ListView):
    """Todas as inspeções. Propostas são visíveis a toda a filial; as demais seguem o escopo do técnico."""
    model = Inspecao
    template_name = 'gestao_riscos/inspecao_lista.html'
    context_object_name = 'inspecoes'
    paginate_by = 25
    STATUS_VALIDOS = dict(STATUS_CHOICES)

    def _base_qs(self):
        qs = Inspecao.objects.for_request(self.request)
        if not escopo_total(self.request.user, PERM_ALL_INSPECAO):
            qs = qs.filter(Q(status='PENDENTE_APROVACAO') | Q(responsavel=self.request.user))
        return qs

    def get_queryset(self):
        qs = (self._base_qs()
              .select_related('equipamento', 'responsavel',
                              'entrega_epi__equipamento', 'entrega_epi__ficha__funcionario'))
        status = self.request.GET.get('status', '')
        if status in self.STATUS_VALIDOS:
            qs = qs.filter(status=status)
        prioridade = Case(
            When(status='PENDENTE_APROVACAO', then=0),
            When(status='PENDENTE', then=1),
            When(status='CONCLUIDA', then=2),
            default=3, output_field=IntegerField(),
        )
        return qs.annotate(prioridade=prioridade).order_by('prioridade', 'data_agendada')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop('page', None)
        cont = self._base_qs().aggregate(
            todas=Count('id'),
            propostas=Count('id', filter=Q(status='PENDENTE_APROVACAO')),
            pendentes=Count('id', filter=Q(status='PENDENTE')),
            concluidas=Count('id', filter=Q(status='CONCLUIDA')),
            canceladas=Count('id', filter=Q(status='CANCELADA')),
        )
        ctx.update(
            cont=cont,
            status_atual=self.request.GET.get('status', ''),
            querystring=params.urlencode(),
            titulo_pagina='Inspeções',
            hoje=timezone.localdate(),
        )
        return ctx

class ConfirmarInspecaoView(GestaoRiscosBaseMixin, View):
    http_method_names = ['post']
    permission_required = 'gestao_riscos.change_inspecao'

    def post(self, request, pk):
        bruto = (request.POST.get('data_agendada') or '').strip()
        nova_data = parse_date(bruto) if bruto else None

        if bruto and nova_data is None:
            messages.error(request, 'Data inválida.')
            return _safe_next(request, 'gestao_riscos:inspecao_lista')
        if nova_data and nova_data < timezone.localdate():
            messages.error(request, 'A data da inspeção não pode estar no passado.')
            return _safe_next(request, 'gestao_riscos:inspecao_lista')

        with transaction.atomic():
            inspecao = get_object_or_404(
                Inspecao.objects.for_request(request).select_for_update(),
                pk=pk, status='PENDENTE_APROVACAO',
            )
            inspecao.status = 'PENDENTE'
            inspecao.responsavel = request.user
            campos = ['status', 'responsavel']
            if nova_data:
                inspecao.data_agendada = nova_data
                campos.append('data_agendada')
            inspecao.save(update_fields=campos)

        audit.info('inspecao_confirmada id=%s user=%s data=%s', pk, request.user.pk, inspecao.data_agendada)
        messages.success(
            request,
            f"{inspecao} confirmada para {inspecao.data_agendada:%d/%m/%Y} e atribuída a você.",
        )
        return _safe_next(request, 'gestao_riscos:inspecao_lista')

class InspecaoDetailView(GestaoRiscosTecnicoMixin, DetailView):
    model = Inspecao
    template_name = 'gestao_riscos/inspecao_detail.html'
    context_object_name = 'inspecao'
    tecnico_scope_lookup = 'responsavel'
    permission_view_all = PERM_ALL_INSPECAO

    def get_queryset(self):
        return super().get_queryset().select_related('equipamento', 'entrega_epi', 'responsavel')

class CompletarInspecaoView(GestaoRiscosTecnicoMixin, SuccessMessageMixin, UpdateView):
    model = Inspecao
    form_class = InspecaoConclusaoForm
    permission_required = 'gestao_riscos.change_inspecao'
    template_name = 'gestao_riscos/inspecao_completar_form.html'
    success_url = reverse_lazy('gestao_riscos:calendario')
    success_message = 'Inspeção marcada como Concluída!'
    tecnico_scope_lookup = 'responsavel'
    permission_view_all = PERM_ALL_INSPECAO

    def get_queryset(self):
        return super().get_queryset().filter(status='PENDENTE')

    def form_valid(self, form):
        form.instance.status = 'CONCLUIDA'
        audit.info('inspecao_concluida id=%s user=%s', form.instance.pk, self.request.user.pk)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo_pagina'] = f'Concluir Inspeção: {self.object}'
        return ctx

class _MudarStatusInspecaoView(GestaoRiscosBaseMixin, View):
    http_method_names = ['post']
    permission_required = 'gestao_riscos.change_inspecao'
    origem = ()
    destino = ''
    mensagem = ''
    evento = ''

    def post(self, request, pk):
        qs = Inspecao.objects.for_request(request)
        if not escopo_total(request.user, PERM_ALL_INSPECAO):
            qs = qs.filter(Q(status='PENDENTE_APROVACAO') | Q(responsavel=request.user))
        with transaction.atomic():
            inspecao = get_object_or_404(qs.select_for_update(), pk=pk, status__in=self.origem)
            inspecao.status = self.destino
            inspecao.save(update_fields=['status'])
        audit.info('%s id=%s user=%s', self.evento, pk, request.user.pk)
        messages.success(request, self.mensagem.format(inspecao=inspecao))
        return _safe_next(request, 'gestao_riscos:inspecao_lista')


class CancelarInspecaoView(_MudarStatusInspecaoView):
    origem = ('PENDENTE_APROVACAO', 'PENDENTE')
    destino = 'CANCELADA'
    mensagem = '{inspecao} cancelada.'
    evento = 'inspecao_cancelada'


class ReabrirInspecaoView(_MudarStatusInspecaoView):
    origem = ('CANCELADA',)
    destino = 'PENDENTE_APROVACAO'
    mensagem = '{inspecao} reaberta e devolvida para aprovação.'
    evento = 'inspecao_reaberta'


# ── Calendário ────────────────────────────────────────────────────────
class CalendarioView(GestaoRiscosBaseMixin, TemplateView):
    template_name = 'gestao_riscos/calendario.html'
    extra_context = {'titulo_pagina': 'Calendário de Inspeções'}


class InspecaoEventsApiView(GestaoRiscosBaseMixin, View):
    """JSON p/ FullCalendar. Respeita ?start=&end= enviados pelo próprio FullCalendar."""
    http_method_names = ['get']
    CORES_POR_STATUS = {'CONCLUIDA': '#28a745', 'PENDENTE_APROVACAO': '#ffc107', 'PENDENTE': '#007bff', 'CANCELADA': "#ff0000"}

    @staticmethod
    def _data(valor):
        return parse_date((valor or '')[:10])

    def get(self, request):
        qs = _scoped(Inspecao.objects.for_request(request), request, 'responsavel', PERM_ALL_INSPECAO)

        hoje = timezone.localdate()
        inicio = self._data(request.GET.get('start')) or hoje - datetime.timedelta(days=45)
        fim = self._data(request.GET.get('end')) or hoje + datetime.timedelta(days=45)

        rows = (qs.filter(status__in=self.CORES_POR_STATUS.keys(),
                          data_agendada__range=(inicio, fim))
                .values('id', 'status', 'data_agendada', 'equipamento__nome',
                        'responsavel__first_name', 'responsavel__username')[:MAX_EVENTOS])

        eventos = []
        for r in rows:
            resp = r['responsavel__first_name'] or r['responsavel__username']
            eventos.append({
                'id': r['id'],
                'title': f"{r['equipamento__nome'] or 'Inspeção'}{f' ({resp})' if resp else ''}",
                'start': r['data_agendada'].isoformat(),
                'url': reverse('gestao_riscos:inspecao_detalhe', kwargs={'pk': r['id']}),
                'color': self.CORES_POR_STATUS.get(r['status'], '#6c757d'),
                'allDay': True,
            })
        # reverse_lazy → str
        for e in eventos:
            e['url'] = str(e['url'])
        return JsonResponse(eventos, safe=False)


class EntregasPorEquipamentoView(GestaoRiscosBaseMixin, View):
    """Retorna entregas não devolvidas. Exige permissão explícita (expõe nome de colaborador)."""
    http_method_names = ['get']
    permission_required = 'seguranca_trabalho.view_entregaepi'

    def get(self, request):
        filial = get_filial_ativa(request.user, request)
        try:
            equipamento_id = int(request.GET.get('equipamento_id', ''))
        except (TypeError, ValueError):
            return JsonResponse({'entregas': []})
        if not filial:
            return JsonResponse({'entregas': []})

        rows = (EntregaEPI.objects
                .filter(filial=filial, equipamento_id=equipamento_id, data_devolucao__isnull=True)
                .values('pk', 'data_entrega', 'ficha__funcionario__nome_completo')[:200])

        data = [{
            'id': r['pk'],
            'texto': (f"{r['ficha__funcionario__nome_completo'] or 'Sem ficha'} - "
                      f"Entregue em {r['data_entrega']:%d/%m/%Y}" if r['data_entrega'] else f"Entrega #{r['pk']}"),
        } for r in rows]
        return JsonResponse({'entregas': data})


# ── Cartão de Bloqueio (TAG) ─────────────────────────────────────────────────
class CartaoTagScopeMixin(GestaoRiscosTecnicoMixin):
    model = CartaoTag
    tecnico_scope_lookup = 'funcionario__usuario'
    permission_view_all = PERM_ALL_CARTAO

    def get_queryset(self):
        return super().get_queryset().select_related('funcionario', 'cargo')

class CartaoTagListView(CartaoTagScopeMixin, HojeContextMixin, ListView):
    template_name = 'gestao_riscos/cartao_tag_list.html'
    context_object_name = 'cartoes'
    paginate_by = 10

    def get_queryset(self):
        return super().get_queryset().order_by('-ativo', 'funcionario__nome_completo')



class CartaoTagDetailView(CartaoTagScopeMixin, HojeContextMixin, DetailView):
    template_name = 'gestao_riscos/cartao_tag_detail.html'
    context_object_name = 'cartao'

    def get_queryset(self):
        return super().get_queryset().select_related('funcionario')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        validade = self.object.data_validade
        ctx['vencido'] = bool(validade and validade < ctx['hoje'])
        return ctx


class CartaoTagCreateView(GestaoRiscosWriteMixin, FormRequestKwargsMixin,
                          FilialCreateMixin, SuccessMessageMixin, CreateView):
    model = CartaoTag
    form_class = CartaoTagForm
    permission_required = 'gestao_riscos.add_cartaotag'
    template_name = 'gestao_riscos/cartao_tag_form.html'
    success_message = 'Cartão de Bloqueio criado com sucesso!'

    def get_success_url(self):
        return reverse('gestao_riscos:cartao_tag_detail', args=[self.object.pk])


class CartaoTagUpdateView(CartaoTagScopeMixin, FormRequestKwargsMixin,
                          SuccessMessageMixin, UpdateView):
    form_class = CartaoTagForm
    permission_required = 'gestao_riscos.change_cartaotag'
    template_name = 'gestao_riscos/cartao_tag_form.html'
    success_message = 'Cartão de Bloqueio atualizado com sucesso!'

    def get_queryset(self):
        return super().get_queryset().select_related('funcionario')

    def get_success_url(self):
        return reverse('gestao_riscos:cartao_tag_detail', args=[self.object.pk])


class CartaoTagDeleteView(CartaoTagScopeMixin, SuccessMessageMixin, DeleteView):
    permission_required = 'gestao_riscos.delete_cartaotag'
    template_name = 'gestao_riscos/cartao_tag_confirm_delete.html'
    success_url = reverse_lazy('gestao_riscos:cartao_tag_list')
    success_message = 'Cartão de Bloqueio excluído com sucesso!'

    def get_queryset(self):
        return super().get_queryset().select_related('funcionario')

    def form_valid(self, form):
        audit.info('cartaotag_excluido id=%s user=%s', self.object.pk, self.request.user.pk)
        return super().form_valid(form)


# ── Tipo de Risco ────────────────────────────────────────────────────────────
class TipoRiscoScopeMixin:
    model = TipoRisco

    def get_queryset(self):
        return TipoRisco.objects.for_request(self.request)


class TipoRiscoListView(GestaoRiscosBaseMixin, TipoRiscoScopeMixin, ListView):
    template_name = 'gestao_riscos/tipo_risco_list.html'   
    context_object_name = 'tipos_risco'
    paginate_by = 20
    CATEGORIAS_VALIDAS = dict(CATEGORIA_RISCO_CHOICES)

    def get_queryset(self):
        qs = super().get_queryset()
        g = self.request.GET
        if g.get('categoria') in self.CATEGORIAS_VALIDAS:
            qs = qs.filter(categoria=g['categoria'])
        if g.get('ativo') in ('true', 'false'):
            qs = qs.filter(ativo=g['ativo'] == 'true')
        search = g.get('search', '').strip()[:100]
        if search:
            qs = qs.filter(Q(nome__icontains=search) | Q(nr_referencia__icontains=search)
                           | Q(descricao__icontains=search))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = self.request.GET.copy(); qs.pop('page', None)

        por_cat = (TipoRisco.objects.for_request(self.request)
                   .values('categoria')
                   .annotate(total=Count('id'), ativos=Count('id', filter=Q(ativo=True))))
        contagem = {r['categoria']: r for r in por_cat}  # 1 query p/ tudo
        ctx['titulo_pagina'] = 'Tipos de Riscos'
        ctx['querystring'] = qs.urlencode()
        ctx['total_tipos'] = sum(r['total'] for r in contagem.values())
        ctx['total_ativos'] = sum(r['ativos'] for r in contagem.values())
        ctx['categorias_info'] = [{
            'key': k, 'label': lbl,
            'total': contagem.get(k, {}).get('total', 0),
            'cor': TipoRisco.CORES_CATEGORIA.get(k, TipoRisco.COR_PADRAO),
            'texto_escuro': k == 'ergonomico',
        } for k, lbl in CATEGORIA_RISCO_CHOICES]
        ctx['categorias'] = CATEGORIA_RISCO_CHOICES
        return ctx


class TipoRiscoFormContextMixin:
    titulo = btn_texto = ''

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(titulo=self.titulo, btn_texto=self.btn_texto,
                   cores_categorias=TipoRisco.CORES_CATEGORIA)
        return ctx

    def get_success_message(self, cleaned_data):
        return self.success_message % {'nome': self.object.nome}


class TipoRiscoCreateView(GestaoRiscosWriteMixin, FormRequestKwargsMixin, TipoRiscoFormContextMixin,
                          FilialCreateMixin, SuccessMessageMixin, CreateView):
    model = TipoRisco
    form_class = TipoRiscoForm
    permission_required = 'gestao_riscos.add_tiporisco'
    template_name = 'gestao_riscos/tipo_risco_form.html'  
    success_url = reverse_lazy('gestao_riscos:tipo_risco_list')
    success_message = 'Tipo de Risco "%(nome)s" cadastrado com sucesso!'
    titulo, btn_texto = 'Novo Tipo de Risco', 'Cadastrar'


class TipoRiscoUpdateView(GestaoRiscosBaseMixin, TipoRiscoScopeMixin, FormRequestKwargsMixin,
                          TipoRiscoFormContextMixin, SuccessMessageMixin, UpdateView):
    form_class = TipoRiscoForm
    permission_required = 'gestao_riscos.change_tiporisco'
    template_name = 'gestao_riscos/tipo_risco_form.html'  
    success_url = reverse_lazy('gestao_riscos:tipo_risco_list')
    success_message = 'Tipo de Risco "%(nome)s" atualizado com sucesso!'
    titulo, btn_texto = 'Editar Tipo de Risco', 'Salvar Alterações'


class TipoRiscoDeleteView(GestaoRiscosBaseMixin, TipoRiscoScopeMixin, DeleteView):
    permission_required = 'gestao_riscos.delete_tiporisco'
    template_name = 'gestao_riscos/tipo_risco_confirm_delete.html' 
    success_url = reverse_lazy('gestao_riscos:tipo_risco_list')

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, 'Este tipo está em uso em riscos do PGR. Inative-o em vez de excluir.')
            return redirect('gestao_riscos:tipo_risco_list')
        messages.success(self.request, 'Tipo de Risco excluído com sucesso!')
        return response


class TipoRiscoToggleAtivoView(GestaoRiscosBaseMixin, View):
    http_method_names = ['post']
    permission_required = 'gestao_riscos.change_tiporisco'

    def post(self, request, pk):
        tipo = get_object_or_404(TipoRisco.objects.for_request(request), pk=pk)
        tipo.ativo = not tipo.ativo
        tipo.save(update_fields=['ativo'])
        return JsonResponse({
            'success': True,
            'ativo': tipo.ativo,
            'message': f'"{tipo.nome}" {"ativado" if tipo.ativo else "inativado"} com sucesso!',
        })


class TipoRiscoPopularView(GestaoRiscosBaseMixin, View):
    http_method_names = ['post']
    permission_required = 'gestao_riscos.add_tiporisco'

    RISCOS_PADRAO = {
        'fisico': ['Ruído', 'Vibrações', 'Radiação Ionizante', 'Radiação Não Ionizante', 'Frio',
                   'Calor', 'Pressões Anormais', 'Umidade', 'Temperaturas Extremas'],
        'quimico': ['Poeiras', 'Fumos Metálicos', 'Névoas', 'Neblinas', 'Gases', 'Vapores',
                    'Substâncias, Compostos Químicos em Geral'],
        'biologico': ['Vírus', 'Bactérias', 'Protozoários', 'Fungos', 'Parasitas', 'Bacilos',
                      'Insetos, Cobras, Aranhas, etc.'],
        'ergonomico': ['Esforço Físico Intenso', 'Levantamento e Transporte Manual de Peso',
                       'Exigência de Postura Inadequada', 'Controle Rígido de Produtividade',
                       'Imposição de Ritmos Excessivos', 'Trabalho em Turno e Noturno',
                       'Jornada de Trabalho Prolongada', 'Monotonia e Repetitividade',
                       'Outras Situações Causadoras de Stress Físico e/ou Psíquico'],
        'acidente': [('Arranjo Físico Inadequado', 'NR-12'),
                     ('Máquinas e Equipamentos sem Proteção', 'NR-12'),
                     ('Ferramentas Inadequadas ou Defeituosas', 'NR-12'),
                     ('Eletricidade', 'NR-10'),
                     ('Probabilidade de Incêndio ou Explosão', 'NR-23'),
                     ('Armazenamento Inadequado', 'NR-11'),
                     ('Animais Peçonhentos', ''),
                     ('Iluminação Inadequada', 'NR-17'),
                     ('Outras Situações de Risco que Poderão Contribuir para Ocorrência de Acidentes', '')],
    }
    NR_PADRAO = {'fisico': 'NR-15', 'quimico': 'NR-15', 'biologico': 'NR-15', 'ergonomico': 'NR-17'}

    def post(self, request):
        filial = get_filial_ativa(request.user, request)
        if not filial:
            return JsonResponse({'success': False, 'error': 'Nenhuma filial ativa selecionada.'}, status=400)

        existentes = set(TipoRisco.objects.filter(filial=filial).values_list('categoria', 'nome'))
        novos = []
        for cat, agentes in self.RISCOS_PADRAO.items():
            for item in agentes:
                nome, nr = item if isinstance(item, tuple) else (item, self.NR_PADRAO.get(cat, ''))
                if (cat, nome) not in existentes:
                    novos.append(TipoRisco(categoria=cat, nome=nome, nr_referencia=nr, filial=filial,
                                           codigo_cor=TipoRisco.CORES_CATEGORIA[cat], ativo=True))

        criados = TipoRisco.objects.bulk_create(novos, ignore_conflicts=True)  # 2 queries no total
        total = sum(len(v) for v in self.RISCOS_PADRAO.values())
        return JsonResponse({
            'success': True,
            'criados': len(criados),
            'existentes': total - len(criados),
            'message': f'{len(criados)} tipo(s) de risco criado(s). {total - len(criados)} já existiam.',
        })


