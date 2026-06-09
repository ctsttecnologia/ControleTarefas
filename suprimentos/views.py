
# suprimentos/views.py
"""
Views do app Suprimentos — implementam o fluxo completo:
PEDIDO → APROVAR → SOLICITAÇÃO/COTAÇÃO (NxN) → APROVAR COTAÇÃO →
MONTAR PEDIDO DE COMPRA → ACOMPANHAR ENTREGA → FINALIZAR
"""

from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Sum, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView, DetailView, ListView, UpdateView, DeleteView, View, TemplateView,
)
from .forms import (
    CotacaoCabecalhoForm, CotacaoItemValorFormSet, PedidoForm, ItemPedidoFormSet,  AprovarPedidoForm,
    EntregaPedidoCompraForm, ParceiroForm, MaterialForm
   
)
from .models import (
    CategoriaMaterial, HistoricoSolicitacao, Parceiro, Material, Contrato,
    Pedido, HistoricoPedido, SolicitacaoCompra, ItemSolicitacao, Cotacao,
    PedidoCompra, ItemPedidoCompra, EntregaAnexo,
)
from collections import defaultdict
from django.db import IntegrityError
import logging


logger = logging.getLogger(__name__)


# Constantes de módulo (não recriam a cada request)
CAMPOS_VERBA = {
    CategoriaMaterial.EPI:        ("verba_epi", "saldo_epi"),
    CategoriaMaterial.CONSUMO:    ("verba_consumo", "saldo_consumo"),
    CategoriaMaterial.FERRAMENTA: ("verba_ferramenta", "saldo_ferramenta"),
}
SALDO_POR_CLASSIF = {cat: campos[1] for cat, campos in CAMPOS_VERBA.items()}

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def _obter_verba_do_mes(sol):
    """
    Resolve a verba do mês de referência da solicitação (defensivo).
    Retorna (verba_ou_None, erro_ou_None).
    """
    ref = sol.data_necessaria or timezone.now().date()
    try:
        verba = sol.contrato.verba_do_mes(ref.year, ref.month)
    except Exception:
        logger.exception("Falha ao obter verba do mês (contrato=%s)", sol.contrato_id)
        return None, "Não foi possível consultar a verba do contrato."
    return verba, None


def _registrar_historico(func, **kwargs):
    """Wrapper seguro para registro de histórico — nunca quebra o fluxo."""
    try:
        func(**kwargs)
    except Exception:
        logger.exception("Falha ao registrar histórico (%s)", func.__qualname__)

# ═════════════════════════════════════════════════════════════
# DASHBOARD
# ═════════════════════════════════════════════════════════════
class SuprimentosDashboard(LoginRequiredMixin, TemplateView):
    template_name = "suprimentos/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["pedidos_pendentes"] = Pedido.objects.filter(
            status=Pedido.StatusChoices.PENDENTE
        ).count()
        ctx["solicitacoes_cotacao"] = SolicitacaoCompra.objects.filter(
            status=SolicitacaoCompra.StatusChoices.FAZER_COTACAO
        ).count()
        ctx["solicitacoes_aprovacao"] = SolicitacaoCompra.objects.filter(
            status=SolicitacaoCompra.StatusChoices.EM_APROVACAO
        ).count()
        ctx["pcs_pendentes_entrega"] = PedidoCompra.objects.filter(
            status__in=[
                PedidoCompra.StatusPC.ENVIADO_FORNECEDOR,
                PedidoCompra.StatusPC.EMITIDO,
                PedidoCompra.StatusPC.ENTREGA_PARCIAL,   # ← novo
            ]
        ).count()
        ctx["ultimos_pedidos"] = Pedido.objects.select_related("contrato").order_by("-data_pedido")[:10]

        return ctx


# ═════════════════════════════════════════════════════════════
# 1. PEDIDO — CRUD + Submissão
# ═════════════════════════════════════════════════════════════
class PedidoListView(LoginRequiredMixin, ListView):
    model = Pedido
    template_name = "suprimentos/pedido_list.html"
    context_object_name = "pedidos"
    paginate_by = 20

    def get_queryset(self):
        qs = Pedido.objects.select_related("contrato", "solicitante")
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs.visiveis_para(self.request.user) if hasattr(qs, "visiveis_para") else qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = Pedido.StatusChoices.choices
        return ctx


class PedidoDetailView(LoginRequiredMixin, DetailView):
    model = Pedido
    template_name = "suprimentos/pedido_detail.html"
    context_object_name = "pedido"
    

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["itens"] = self.object.itens.select_related("material")
        ctx["anexos"] = self.object.anexos.all()
        ctx["historico"] = self.object.historico.all()
        ok, erros = self.object.verificar_verba()
        ctx["verba_ok"], ctx["verba_erros"] = ok, erros
        return ctx


class PedidoCreateView(LoginRequiredMixin, CreateView):
    model = Pedido
    form_class = PedidoForm
    template_name = "suprimentos/pedido_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx["formset"] = ItemPedidoFormSet(self.request.POST)
        else:
            ctx["formset"] = ItemPedidoFormSet()
        return ctx

    @transaction.atomic
    def form_valid(self, form):
        ctx = self.get_context_data()
        formset = ctx["formset"]
        form.instance.solicitante = self.request.user
        if not form.instance.filial_id:
            form.instance.filial = getattr(self.request.user, "filial", None)
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            HistoricoPedido.registrar(
                pedido=self.object,
                descricao="Pedido criado (rascunho).",
                responsavel=self.request.user,
                status_novo=self.object.status,
            )
            messages.success(self.request, f"Pedido {self.object.numero} criado.")
            return redirect(self.object.get_absolute_url())
        return self.render_to_response(self.get_context_data(form=form))


class PedidoUpdateView(LoginRequiredMixin, UpdateView):
    model = Pedido
    form_class = PedidoForm
    template_name = "suprimentos/pedido_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx["formset"] = ItemPedidoFormSet(self.request.POST, instance=self.object)
        else:
            ctx["formset"] = ItemPedidoFormSet(instance=self.object)
        return ctx

    @transaction.atomic
    def form_valid(self, form):
        ctx = self.get_context_data()
        formset = ctx["formset"]
        if formset.is_valid():
            self.object = form.save()
            formset.save()
            HistoricoPedido.registrar(
                pedido=self.object,
                descricao="Pedido editado.",
                responsavel=self.request.user,
            )
            messages.success(self.request, "Pedido atualizado.")
            return redirect(self.object.get_absolute_url())
        return self.render_to_response(self.get_context_data(form=form))


@login_required
def pedido_submeter(request, pk):
    """RASCUNHO/REVISAO → PENDENTE (envia para aprovação)."""
    pedido = get_object_or_404(Pedido, pk=pk)
    if pedido.status not in (Pedido.StatusChoices.RASCUNHO, Pedido.StatusChoices.REVISAO):
        messages.error(request, "Pedido não pode ser submetido neste status.")
        return redirect(pedido.get_absolute_url())
    if not pedido.itens.exists():
        messages.error(request, "Adicione ao menos um item antes de submeter.")
        return redirect(pedido.get_absolute_url())
    anterior = pedido.status
    pedido.status = Pedido.StatusChoices.PENDENTE
    pedido.save(update_fields=["status", "atualizado_em"])
    HistoricoPedido.registrar(
        pedido=pedido, descricao="Pedido submetido para aprovação.",
        responsavel=request.user,
        status_anterior=anterior, status_novo=pedido.status,
    )
    messages.success(request, "Pedido enviado para aprovação.")
    return redirect(pedido.get_absolute_url())


# ═════════════════════════════════════════════════════════════
# 2. APROVAR PEDIDO (Gerente)
# ═════════════════════════════════════════════════════════════
@login_required
@permission_required("suprimentos.pode_aprovar_pedido", raise_exception=True)
def pedido_aprovar(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    if pedido.status != Pedido.StatusChoices.PENDENTE:
        messages.error(request, "Apenas pedidos PENDENTES podem ser avaliados.")
        return redirect(pedido.get_absolute_url())

    if request.method == "POST":
        form = AprovarPedidoForm(request.POST)
        if form.is_valid():
            decisao = form.cleaned_data["decisao"]
            motivo = form.cleaned_data["motivo"]
            anterior = pedido.status
            pedido.aprovador = request.user

            if decisao == "APROVAR":
                pedido.status = Pedido.StatusChoices.APROVADO
                pedido.data_aprovacao = timezone.now()
                pedido.save()
                HistoricoPedido.registrar(
                    pedido=pedido, descricao="Pedido aprovado.",
                    responsavel=request.user,
                    status_anterior=anterior, status_novo=pedido.status,
                )
                # Gera solicitação de compra automaticamente
                try:
                    sol = pedido.gerar_solicitacao_compra(request.user)
                    messages.success(
                        request,
                        f"Pedido aprovado. Solicitação {sol.numero} gerada.",
                    )
                    return redirect(sol.get_absolute_url())
                except ValidationError as e:
                    messages.warning(request, f"Pedido aprovado, mas: {e.messages}")

            elif decisao == "REVISAR":
                pedido.status = Pedido.StatusChoices.REVISAO
                pedido.motivo_revisao = motivo
                pedido.save()
                HistoricoPedido.registrar(
                    pedido=pedido, descricao=f"Devolvido para revisão: {motivo}",
                    responsavel=request.user,
                    status_anterior=anterior, status_novo=pedido.status,
                )
                messages.info(request, "Pedido devolvido para revisão.")

            else:  # REPROVAR
                pedido.status = Pedido.StatusChoices.REPROVADO
                pedido.motivo_reprovacao = motivo
                pedido.save()
                HistoricoPedido.registrar(
                    pedido=pedido, descricao=f"Reprovado: {motivo}",
                    responsavel=request.user,
                    status_anterior=anterior, status_novo=pedido.status,
                )
                messages.warning(request, "Pedido reprovado.")
            return redirect(pedido.get_absolute_url())
    else:
        form = AprovarPedidoForm()

    return render(request, "suprimentos/pedido_aprovar.html", {
        "pedido": pedido, "form": form,
        "itens": pedido.itens.select_related("material"),
    })


# ═════════════════════════════════════════════════════════════
# 3. SOLICITAÇÃO — Listagem / Detalhe / Cotação (NxN)
# ═════════════════════════════════════════════════════════════
class SolicitacaoListView(LoginRequiredMixin, ListView):
    model = SolicitacaoCompra
    template_name = "suprimentos/solicitacao_list.html"
    context_object_name = "solicitacoes"
    paginate_by = 20

    def get_queryset(self):
        qs = SolicitacaoCompra.objects.select_related("contrato", "solicitante", "comprador")
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = SolicitacaoCompra.StatusChoices.choices
        return ctx


class SolicitacaoDetailView(LoginRequiredMixin, DetailView):
    model = SolicitacaoCompra
    template_name = "suprimentos/solicitacao_detail.html"
    context_object_name = "solicitacao"
    

    # ──────────────────────────────────────────────────────────────
    # Ordem oficial do fluxo da solicitação (CANCELADO fica fora)
    # ──────────────────────────────────────────────────────────────
    @property
    def fluxo(self):
        S = SolicitacaoCompra.StatusChoices
        return [
            S.FAZER_COTACAO,
            S.COTACAO_ENVIADA,
            S.EM_APROVACAO,
            S.APROVADO,
            S.ENVIAR_PEDIDO,
            S.PEDIDO_GERADO,
            S.EM_ENTREGA,
            S.FINALIZADO,
        ]

    # ──────────────────────────────────────────────────────────────
    def get_queryset(self):
        """Otimiza o carregamento do objeto principal e relações diretas."""
        return (
            super()
            .get_queryset()
            .select_related(
                "pedido",
                "pedido__contrato",
                "solicitante",
                "comprador",
                "aprovador_cotacao",
            )
        )

    # ──────────────────────────────────────────────────────────────
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        sol = self.object
        user = self.request.user
        S = SolicitacaoCompra.StatusChoices
        status = sol.status
        anexos_qs = sol.anexos.select_related("enviado_por")


        # Esconde confidenciais de quem não tem permissão
        if not user.has_perm("suprimentos.view_anexosolicitacao_confidencial"):
            anexos_qs = anexos_qs.filter(confidencial=False)

        ctx.update({
            "anexos": anexos_qs,
            
        })
    

        # ───────── Posição atual no fluxo ─────────
        fluxo = self.fluxo
        try:
            pos = fluxo.index(status)
        except ValueError:          # CANCELADO ou status fora do fluxo
            pos = -1

        def passou(etapa) -> bool:
            """True se o fluxo já atingiu (ou ultrapassou) a etapa informada."""
            return pos >= fluxo.index(etapa)

        # ───────── Querysets / dados base ─────────
        itens = (
            sol.itens
            .select_related("material")
            .prefetch_related("cotacoes__fornecedor")
        )
        pedidos_compra = sol.pedidos_compra.select_related("fornecedor")
        tem_cotacoes = itens.filter(cotacoes__isnull=False).exists()

        # ───────── Permissões ─────────
        pode_cotar_perm   = user.has_perm("suprimentos.pode_cotar")
        pode_aprovar_perm = user.has_perm("suprimentos.pode_aprovar_cotacao")

        # ───────── Estados pontuais ─────────
        em_cotacao   = status in (S.FAZER_COTACAO, S.COTACAO_ENVIADA)
        em_aprovacao = status == S.EM_APROVACAO
        pronto_pc    = status in (S.APROVADO, S.ENVIAR_PEDIDO)  # pode montar PC

        # ───────── Monta contexto ─────────
        ctx.update(
            {
                # Dados
                "itens": itens,
                "anexos": sol.anexos.all(),
                "pedidos_compra": pedidos_compra,
                "historico": sol.historico.all(),
                "comparativo": self._montar_comparativo(itens),
                "tem_cotacoes": tem_cotacoes,
                "todos_cotados": sol.todos_itens_cotados,

                # Stepper — "done" = já passou da etapa; "active" = está nela
                "step_cotacao_done":   passou(S.EM_APROVACAO),
                "step_cotacao_active": em_cotacao,
                "step_aprov_done":     passou(S.APROVADO),
                "step_aprov_active":   em_aprovacao,
                "step_pc_done":        passou(S.PEDIDO_GERADO),
                "step_pc_active":      pronto_pc,

                # Navegação lateral
                "nav_cotacao":   status != S.FAZER_COTACAO,
                "nav_aprovacao": passou(S.EM_APROVACAO),
                "pc_gerado":     passou(S.PEDIDO_GERADO),

                # Botões de ação (estado + permissão)
                "pode_cotar": em_cotacao and pode_cotar_perm,
                "pode_enviar_aprovacao": (
                    status == S.COTACAO_ENVIADA
                    and tem_cotacoes
                    and pode_cotar_perm
                ),
                "pode_aprovar_cotacao": em_aprovacao and pode_aprovar_perm,
                "pode_montar_pc": pronto_pc and pode_aprovar_perm,
            }
        )
        return ctx

    # ──────────────────────────────────────────────────────────────
    @staticmethod
    def _montar_comparativo(itens):
        """Total que cada fornecedor representaria se fornecesse tudo o que cotou."""
        agregado = defaultdict(lambda: {"total": Decimal("0.00"), "qtd_itens": 0})

        for item in itens:
            for cotacao in item.cotacoes.all():
                nome = cotacao.fornecedor.nome_fantasia
                agregado[nome]["total"] += cotacao.valor_total
                agregado[nome]["qtd_itens"] += 1

        return sorted(
            ({"fornecedor": nome, **dados} for nome, dados in agregado.items()),
            key=lambda x: x["total"],
        )
    

@login_required
@permission_required("suprimentos.pode_cotar", raise_exception=True)
def cotacao_adicionar(request, solicitacao_pk):
    """
    Lança a cotação de UM fornecedor para os itens da solicitação.
    Gera 1 Cotacao por ItemSolicitacao que tiver valor preenchido.
    """
    solicitacao = get_object_or_404(SolicitacaoCompra, pk=solicitacao_pk)
    itens = list(
        solicitacao.itens.select_related("material")
        .exclude(status=ItemSolicitacao.StatusItem.CANCELADO)
    )

    # initial do formset: uma linha por item da solicitação
    initial_itens = [{"item_id": item.pk} for item in itens]

    if request.method == "POST":
        cab_form = CotacaoCabecalhoForm(request.POST, request.FILES)
        formset = CotacaoItemValorFormSet(request.POST, initial=initial_itens)

        if cab_form.is_valid() and formset.is_valid():
            fornecedor = cab_form.cleaned_data["fornecedor"]

            # Coleta apenas os itens com valor > 0 preenchido
            linhas_validas = [
                f.cleaned_data for f in formset
                if f.cleaned_data.get("valor_unitario")
            ]

            if not linhas_validas:
                messages.error(request, "Informe ao menos um valor por item.")
            else:
                # Mapa rápido id -> ItemSolicitacao
                mapa_itens = {item.pk: item for item in itens}
                try:
                    with transaction.atomic():
                        criadas = 0
                        for linha in linhas_validas:
                            item = mapa_itens.get(linha["item_id"])
                            if not item:
                                continue

                            # Verifica duplicidade ANTES (respeita o UniqueConstraint)
                            ja_existe = Cotacao.objects.filter(
                                item_solicitacao=item,
                                fornecedor=fornecedor,
                            ).exists()
                            if ja_existe:
                                raise IntegrityError(
                                    f"item:{item.material.descricao}"
                                )

                            Cotacao.objects.create(
                                item_solicitacao=item,
                                fornecedor=fornecedor,
                                valor_unitario=linha["valor_unitario"],
                                prazo_entrega_dias=cab_form.cleaned_data.get("prazo_entrega_dias"),
                                condicoes_pagamento=cab_form.cleaned_data.get("condicoes_pagamento", ""),
                                validade_cotacao=cab_form.cleaned_data.get("validade_cotacao"),
                                observacoes=cab_form.cleaned_data.get("observacoes", ""),
                                anexo_cotacao=cab_form.cleaned_data.get("anexo_cotacao"),
                                criado_por=request.user,
                            )
                            # Atualiza status do item
                            if item.status == ItemSolicitacao.StatusItem.PENDENTE_COTACAO:
                                item.status = ItemSolicitacao.StatusItem.COTADO
                                item.save(update_fields=["status"])
                            criadas += 1

                        # Atualiza status da solicitação se já está cotando
                        if solicitacao.status == SolicitacaoCompra.StatusChoices.FAZER_COTACAO:
                            solicitacao.status = SolicitacaoCompra.StatusChoices.COTACAO_ENVIADA
                            solicitacao.save(update_fields=["status", "atualizado_em"])

                    messages.success(
                        request,
                        f"Cotação de {fornecedor.nome_fantasia} lançada para {criadas} item(ns)!"
                    )
                    return redirect("suprimentos:solicitacao_detalhe", pk=solicitacao.pk)

                except IntegrityError as e:
                    messages.error(
                        request,
                        f"O fornecedor '{fornecedor.nome_fantasia}' já cotou um ou mais "
                        f"destes itens. Edite a cotação existente, se necessário."
                    )
    else:
        cab_form = CotacaoCabecalhoForm()
        formset = CotacaoItemValorFormSet(initial=initial_itens)

    # Junta cada subform com seu item para o template (mesma ordem!)
    linhas = list(zip(formset.forms, itens))

    return render(request, "suprimentos/cotacao_form.html", {
        "cab_form": cab_form,
        "formset": formset,
        "linhas": linhas,
        "solicitacao": solicitacao,
    })


@login_required
def cotacao_excluir(request, pk):
    cot = get_object_or_404(Cotacao, pk=pk)
    sol_pk = cot.item_solicitacao.solicitacao.pk
    cot.delete()
    messages.info(request, "Cotação removida.")
    return redirect("suprimentos:solicitacao_detalhe", pk=sol_pk)


@login_required
@permission_required("suprimentos.pode_cotar", raise_exception=True)
def solicitacao_enviar_aprovacao(request, pk):
    """FAZER_COTACAO → EM_APROVACAO (todos os itens cotados)."""
    sol = get_object_or_404(SolicitacaoCompra, pk=pk)
    if not sol.todos_itens_cotados:
        messages.error(request, "Todos os itens precisam de ao menos 1 cotação.")
        return redirect(sol.get_absolute_url())
    sol.comprador = request.user
    sol.data_cotacao = timezone.now().date()
    sol.status = SolicitacaoCompra.StatusChoices.EM_APROVACAO
    sol.save()
    messages.success(request, "Cotações enviadas para aprovação.")
    return redirect(sol.get_absolute_url())


# ─────────────────────────────────────────────────────────────
# HELPERS — cotacao_aprovar
# ─────────────────────────────────────────────────────────────
def _coletar_escolhas(request, itens):
    """
    Lê as escolhas do POST e soma por classificação.
    Retorna: (escolhas, total_por_classif, erro_str_ou_None)
    """
    escolhas = []  # [(item, cotacao_ou_None)]
    total_por_classif = defaultdict(lambda: Decimal("0.00"))

    for item in itens:
        cotacao_id = request.POST.get(f"cotacao_{item.pk}", "").strip()

        if cotacao_id:
            # valida que o ID é numérico antes de consultar
            if not cotacao_id.isdigit():
                return [], total_por_classif, (
                    f"Cotação inválida para o item “{item.material.descricao}”."
                )
            cotacao = item.cotacoes.filter(pk=cotacao_id).first()
            if not cotacao:
                return [], total_por_classif, (
                    f"Cotação inválida para o item “{item.material.descricao}”."
                )
            escolhas.append((item, cotacao))
            total_por_classif[item.material.classificacao] += cotacao.valor_total
        else:
            escolhas.append((item, None))  # "Nenhum" → não comprar

    return escolhas, total_por_classif, None


def _checar_estouros(total_por_classif, verba, labels):
    """Retorna lista de mensagens de estouro por classificação."""
    estouros = []
    for classif, total in total_por_classif.items():
        campo_saldo = SALDO_POR_CLASSIF.get(classif)
        if not campo_saldo:
            continue
        saldo = getattr(verba, campo_saldo, None) or Decimal("0.00")
        if total > saldo:
            label = labels.get(classif, classif)
            estouros.append(
                f"{label}: escolhido R$ {total:.2f} > saldo R$ {saldo:.2f}"
            )
    return estouros


def _devolver_para_revisao(request, sol, msg_estouro, S):
    """Devolve o pedido vinculado para REVISÃO de forma atômica."""
    with transaction.atomic():
        pedido = getattr(sol, "pedido", None)
        if pedido is not None:
            status_anterior = pedido.status
            pedido.status = Pedido.StatusChoices.REVISAO
            pedido.motivo_revisao = msg_estouro
            pedido.save(update_fields=[
                "status", "motivo_revisao", "atualizado_em",
            ])
            _registrar_historico(
                HistoricoPedido.registrar,
                pedido=pedido,
                descricao=f"Devolvido para revisão (verba): {msg_estouro}",
                responsavel=request.user,
                status_anterior=status_anterior,
                status_novo=Pedido.StatusChoices.REVISAO,
            )

        _registrar_historico(
            HistoricoSolicitacao.registrar,
            solicitacao=sol,
            descricao=f"Cotação não aprovada — {msg_estouro}",
            responsavel=request.user,
            status_anterior=sol.status,
            status_novo=sol.status,
        )


def _montar_comparativo(itens):
    """Agrega cotações por fornecedor para o comparativo (GET)."""
    agg = {}
    for item in itens:
        for cot in item.cotacoes.all():
            f = cot.fornecedor
            entry = agg.setdefault(f.id, {
                "fornecedor": f,
                "total": Decimal("0.00"),
                "qtd_itens": 0,
                "prazos": [],
                "pagamentos": set(),
            })
            entry["total"] += cot.valor_total
            entry["qtd_itens"] += 1
            if cot.prazo_entrega_dias is not None:
                entry["prazos"].append(cot.prazo_entrega_dias)
            if cot.condicoes_pagamento:
                entry["pagamentos"].add(cot.condicoes_pagamento.strip())

    comparativo = []
    for entry in agg.values():
        prazos = entry.pop("prazos")
        pagamentos = entry.pop("pagamentos")
        entry["prazo"] = max(prazos) if prazos else None
        entry["pagamentos_lista"] = " | ".join(sorted(pagamentos)) if pagamentos else ""
        if len(pagamentos) == 1:
            entry["pagamento"] = next(iter(pagamentos))
        elif len(pagamentos) > 1:
            entry["pagamento"] = "Variadas"
        else:
            entry["pagamento"] = None
        comparativo.append(entry)

    comparativo.sort(key=lambda d: d["total"])
    return comparativo


def _montar_painel_verba(sol, labels):
    """Monta o painel de verba e o dict de saldos para o JS (GET)."""
    verba, _ = _obter_verba_do_mes(sol)

    painel_verba = []
    saldos_json = {}
    for classif, (campo_verba, campo_saldo) in CAMPOS_VERBA.items():
        v_verba = (getattr(verba, campo_verba, None) or Decimal("0.00")) if verba else Decimal("0.00")
        v_saldo = (getattr(verba, campo_saldo, None) or Decimal("0.00")) if verba else Decimal("0.00")
        painel_verba.append({
            "classif": classif,
            "label": labels.get(classif, classif),
            "verba": v_verba,
            "saldo": v_saldo,
            "estimado": Decimal("0.00"),
        })
        saldos_json[classif] = float(v_saldo)

    return painel_verba, saldos_json


# ─────────────────────────────────────────────────────────────
# 4. APROVAR COTAÇÃO (escolha por item) + CHECAGEM DE VERBA
# ─────────────────────────────────────────────────────────────
@login_required
@permission_required("suprimentos.pode_aprovar_cotacao", raise_exception=True)
def cotacao_aprovar(request, pk):
    """
    Gerente escolhe a cotação vencedora de cada item.

    Reforço de servidor:
        - Só processa se a solicitação estiver EM_APROVACAO (idempotência).
        - select_for_update() evita aprovação concorrente (duplo clique / abas).
        - Toda gravação é atômica; verba insuficiente devolve para REVISÃO.

    Regra de verba (por classificação EPI/CONSUMO/FERRAMENTA):
        - Verba suficiente   → APROVA a solicitação.
        - Verba insuficiente → devolve o Pedido para REVISÃO.
    """
    sol = get_object_or_404(
        SolicitacaoCompra.objects.select_related("contrato"),
        pk=pk,
    )

    S = SolicitacaoCompra.StatusChoices

    # ═════════════════════════════════════════════════════════
    # 🔒 GUARDA DE STATUS (server-side, antes de qualquer coisa)
    # ═════════════════════════════════════════════════════════
    if sol.status != S.EM_APROVACAO:
        messages.warning(
            request,
            f"Esta solicitação não está disponível para aprovação "
            f"(status atual: {sol.get_status_display()}).",
        )
        return redirect(sol.get_absolute_url())

    itens = (
        sol.itens
        .select_related("material")
        .prefetch_related("cotacoes__fornecedor")
    )
    labels = dict(CategoriaMaterial.choices)

    # ═════════════════════════════════════════════════════════
    # POST — coleta escolhas → valida verba → grava (atômico)
    # ═════════════════════════════════════════════════════════
    if request.method == "POST":
        escolhas, total_por_classif, erro_post = _coletar_escolhas(request, itens)
        if erro_post:
            messages.error(request, erro_post)
            return redirect(request.path)

        # Exige ao menos uma cotação escolhida
        if not any(cot for _, cot in escolhas):
            messages.warning(request, "Escolha ao menos uma cotação para aprovar.")
            return redirect(request.path)

        # ── Verba do mês (defensivo) ─────────────────────────
        verba, erro = _obter_verba_do_mes(sol)
        if erro:
            messages.error(request, erro)
            return redirect(request.path)
        if verba is None:
            messages.error(
                request,
                "Verba do contrato não cadastrada para o período da solicitação.",
            )
            return redirect(request.path)

        # ── Checagem de saldo por classificação ──────────────
        estouros = _checar_estouros(total_por_classif, verba, labels)

        # ── VERBA INSUFICIENTE → devolve para REVISÃO ────────
        if estouros:
            msg_estouro = "Verba insuficiente — " + " | ".join(estouros)
            _devolver_para_revisao(request, sol, msg_estouro, S)
            messages.error(
                request,
                f"❌ {msg_estouro}. Pedido devolvido para revisão do solicitante.",
            )
            return redirect(sol.get_absolute_url())

        # ── VERBA OK → grava tudo de forma atômica e APROVA ──
        try:
            with transaction.atomic():
                # 🔒 Lock + revalidação do status sob trava (anti-concorrência)
                sol_locked = (
                    SolicitacaoCompra.objects
                    .select_for_update()
                    .get(pk=sol.pk)
                )
                if sol_locked.status != S.EM_APROVACAO:
                    messages.warning(
                        request,
                        "Esta solicitação já foi processada por outro usuário.",
                    )
                    return redirect(sol_locked.get_absolute_url())

                for item, cot in escolhas:
                    if cot:
                        item.cotacao_escolhida = cot
                        item.status = ItemSolicitacao.StatusItem.APROVADO
                    else:
                        item.cotacao_escolhida = None
                        item.status = ItemSolicitacao.StatusItem.REPROVADO  # "não comprar"
                    item.save(update_fields=[
                        "cotacao_escolhida", "status", "atualizado_em",
                    ])

                sol_locked.status = S.APROVADO
                sol_locked.aprovador_cotacao = request.user
                sol_locked.data_validacao_cotacao = timezone.now().date()
                sol_locked.save(update_fields=[
                    "status", "aprovador_cotacao",
                    "data_validacao_cotacao", "atualizado_em",
                ])

                _registrar_historico(
                    HistoricoSolicitacao.registrar,
                    solicitacao=sol_locked,
                    descricao="Cotações aprovadas dentro da verba.",
                    responsavel=request.user,
                    status_anterior=S.EM_APROVACAO,
                    status_novo=S.APROVADO,
                )
        except SolicitacaoCompra.DoesNotExist:
            messages.error(request, "Solicitação não encontrada.")
            return redirect("suprimentos:lista_solicitacoes")

        messages.success(
            request,
            "✅ Cotações aprovadas dentro da verba. Monte os Pedidos de Compra.",
        )
        return redirect("suprimentos:montar_pedido_compra", pk=sol.pk)

    # ═════════════════════════════════════════════════════════
    # GET — comparativo por fornecedor + painel de verba + saldos
    # ═════════════════════════════════════════════════════════
    comparativo = _montar_comparativo(itens)
    painel_verba, saldos_json = _montar_painel_verba(sol, labels)

    return render(request, "suprimentos/cotacao_aprovar.html", {
        "solicitacao": sol,
        "itens": itens,
        "comparativo": comparativo,
        "painel_verba": painel_verba,
        "saldos_json": saldos_json,
    })


# ═════════════════════════════════════════════════════════════
# 5. MONTAR PEDIDO DE COMPRA (NxN — agrupa por fornecedor)
# ═════════════════════════════════════════════════════════════
@login_required
@permission_required("suprimentos.pode_montar_pc", raise_exception=True)
@transaction.atomic
def montar_pedido_compra(request, pk):
    """Agrupa itens aprovados por fornecedor e gera 1 PedidoCompra por fornecedor."""
    sol = get_object_or_404(SolicitacaoCompra, pk=pk)

    # Alias local para legibilidade
    PC_GERADO = SolicitacaoCompra.StatusChoices.PEDIDO_GERADO

    if request.method == "POST":
        sol = SolicitacaoCompra.objects.select_for_update().get(pk=sol.pk)

        # ── 1) Idempotência ──────────────────────────────────────
        if sol.status == PC_GERADO:
            messages.info(request, "Os Pedidos de Compra já foram gerados.")
            return redirect(sol.get_absolute_url())

        status_anterior = sol.status


        # 🔁 Reavalia DENTRO do lock (consistência garantida)
        itens_aprovados = sol.itens.filter(
            status=ItemSolicitacao.StatusItem.APROVADO,
            cotacao_escolhida__isnull=False,
        ).select_related("cotacao_escolhida__fornecedor", "material")

        if not itens_aprovados.exists():
            messages.error(request, "Nenhum item aprovado com cotação escolhida.")
            return redirect(sol.get_absolute_url())

        # ✅ Respeita os fornecedores marcados nos checkboxes
        fornecedores_sel = set(request.POST.getlist("fornecedores"))
        observacoes = request.POST.get("observacoes", "").strip()

        # Agrupa por fornecedor (apenas os selecionados)
        grupos = {}
        for item in itens_aprovados:
            forn = item.cotacao_escolhida.fornecedor
            if fornecedores_sel and str(forn.pk) not in fornecedores_sel:
                continue
            grupos.setdefault(forn.pk, {"fornecedor": forn, "itens": []})
            grupos[forn.pk]["itens"].append(item)

        if not grupos:
            messages.error(request, "Selecione ao menos um fornecedor para gerar o PC.")
            return redirect(request.path)

        pcs_criados = []
        for dados in grupos.values():
            pc = PedidoCompra.objects.create(
                solicitacao=sol,
                fornecedor=dados["fornecedor"],
                filial=sol.filial,
                status=PedidoCompra.StatusPC.EMITIDO,
                data_emissao=timezone.now().date(),
                criado_por=request.user,
                observacoes=observacoes,
            )
            for item in dados["itens"]:
                cot = item.cotacao_escolhida
                ItemPedidoCompra.objects.create(
                    pedido_compra=pc,
                    cotacao=cot,
                    item_solicitacao=item,
                    material=item.material,
                    quantidade=item.quantidade,
                    valor_unitario=cot.valor_unitario,
                )
            pc.recalcular_total()
            pcs_criados.append(pc)

        # ── Atualiza status da solicitação ───────────────────────
        sol.status = PC_GERADO  # ← era SOLICITACAO_GERADA
        sol.data_criacao_pedido = timezone.now().date()
        sol.save(update_fields=["status", "data_criacao_pedido", "atualizado_em"])

         # ── Histórico ────────────────────────────────────────────
        try:
            HistoricoSolicitacao.registrar(
                solicitacao=sol,
                descricao=(
                    f"{len(pcs_criados)} Pedido(s) de Compra emitido(s): "
                    + ", ".join(pc.numero for pc in pcs_criados)
                ),
                responsavel=request.user,
                status_anterior=status_anterior,
                status_novo=PC_GERADO,  # ← era SOLICITACAO_GERADA
            )
        except Exception:
            pass

        messages.success(request, f"{len(pcs_criados)} Pedido(s) de Compra emitido(s).")

        if len(pcs_criados) == 1:
            return redirect(pcs_criados[0].get_absolute_url())
        return redirect(sol.get_absolute_url())

    # ── Preview (GET) ─────────────────────────────────────────
    itens_aprovados = sol.itens.filter(
        status=ItemSolicitacao.StatusItem.APROVADO,
        cotacao_escolhida__isnull=False,
    ).select_related("cotacao_escolhida__fornecedor", "material")

    if not itens_aprovados.exists():
        messages.error(request, "Nenhum item aprovado com cotação escolhida.")
        return redirect(sol.get_absolute_url())

    # Agrupa por fornecedor + consolida prazo/pagamento divergentes
    #   prazo:     maior (pior caso de entrega)
    #   pagamento: condição única, "Variadas" ou None
    grupos = {}
    for item in itens_aprovados:
        cot = item.cotacao_escolhida
        forn = cot.fornecedor

        g = grupos.setdefault(forn.pk, {
            "fornecedor": forn,
            "itens": [],
            "total": Decimal("0.00"),
            "prazos": [],
            "pagamentos": set(),
        })

        item.valor_cotado = cot.valor_unitario
        item.total_cotado = cot.valor_total
        g["itens"].append(item)
        g["total"] += cot.valor_total

        if cot.prazo_entrega_dias is not None:
            g["prazos"].append(cot.prazo_entrega_dias)
        if cot.condicoes_pagamento:
            g["pagamentos"].add(cot.condicoes_pagamento.strip())

    # Pós-processa: consolida prazo e pagamento por fornecedor
    grupos_fornecedor = []
    for g in grupos.values():
        prazos = g.pop("prazos")
        pagamentos = g.pop("pagamentos")

        # Prazo → maior (pior caso); None se não houver
        g["prazo"] = max(prazos) if prazos else None

        # Pagamento → único, "Variadas" ou None
        if len(pagamentos) == 1:
            g["pagamento"] = next(iter(pagamentos))
        elif len(pagamentos) > 1:
            g["pagamento"] = "Variadas"
        else:
            g["pagamento"] = None

        # Para tooltip quando houver divergência
        g["pagamentos_lista"] = " | ".join(sorted(pagamentos)) if pagamentos else ""

        grupos_fornecedor.append(g)

    grupos_fornecedor = sorted(grupos_fornecedor, key=lambda d: d["total"])

    return render(request, "suprimentos/montar_pc.html", {
        "solicitacao": sol,
        "grupos_fornecedor": grupos_fornecedor,
        "itens": list(itens_aprovados),
        "verba_disponivel": sol.valor_estimado,
    })

# ═════════════════════════════════════════════════════════════
# 6. PEDIDO DE COMPRA — Detalhe / Acompanhar Entrega / Finalizar
# ═════════════════════════════════════════════════════════════
class PedidoCompraDetailView(LoginRequiredMixin, DetailView):
    model = PedidoCompra
    template_name = "suprimentos/pedido_compra_detail.html"
    context_object_name = "pc"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["itens"] = self.object.itens.select_related("material")
        ctx["anexos_entrega"] = self.object.anexos_entrega.all()  # ← novo
        return ctx

@login_required
@permission_required("suprimentos.pode_receber_pc", raise_exception=True)
@transaction.atomic
def pc_finalizar(request, pk):
    """RECEBIDO — completa o saldo restante e, se todos da SOL, conclui."""
    pc = get_object_or_404(PedidoCompra, pk=pk)
    pc.status = PedidoCompra.StatusPC.RECEBIDO
    pc.recebido_por = request.user
    if not pc.data_entrega_efetiva:
        pc.data_entrega_efetiva = timezone.now().date()
    pc.save()

    # Completa apenas o que faltar (não sobrescreve entregas parciais)
    itens = list(pc.itens.all())
    for item in itens:
        if (item.quantidade_recebida or 0) < item.quantidade:
            item.quantidade_recebida = item.quantidade
    if itens:
        ItemPedidoCompra.objects.bulk_update(itens, ["quantidade_recebida"])

    sol = pc.solicitacao
    todos = sol.pedidos_compra.exclude(status=PedidoCompra.StatusPC.CANCELADO)
    if all(p.status == PedidoCompra.StatusPC.RECEBIDO for p in todos):
        sol.status = SolicitacaoCompra.StatusChoices.CONCLUIDO
        sol.data_entrega_efetiva = timezone.now().date()
        sol.save()
        messages.success(request, "PC recebido. Solicitação CONCLUÍDA!")
    else:
        messages.success(request, "Pedido de Compra recebido.")
    return redirect(pc.get_absolute_url())

@login_required
@permission_required("suprimentos.pode_visualizar_pc", raise_exception=True)
def pc_enviar_fornecedor(request, pk):
    pc = get_object_or_404(PedidoCompra, pk=pk)
    pc.status = PedidoCompra.StatusPC.ENVIADO_FORNECEDOR
    pc.data_envio = timezone.now().date()
    pc.save()
    messages.success(request, "Pedido enviado ao fornecedor.")
    return redirect(pc.get_absolute_url())


def _render_entrega(request, pc, itens, form):
    """
    Renderiza a tela de recebimento/entrega de um Pedido de Compra.

    Helper compartilhado entre o fluxo GET e os retornos de erro
    do POST (ex.: rollback por quantidade inválida).
    """
    contexto = {
        "pc": pc,
        "pedido": pc,          # alias defensivo p/ templates antigos
        "itens": itens,
        "form": form,
        "titulo": f"Recebimento — {pc.numero}",
    }
    return render(request, "suprimentos/pc_entrega.html", contexto)


@login_required
@permission_required("suprimentos.pode_receber_pedido_compra", raise_exception=True)
@transaction.atomic
def pc_acompanhar_entrega(request, pk):
    """
    Registra recebimento de um Pedido de Compra.

    Reforço de servidor:
        - Bloqueia GET/POST se o PC estiver ENTREGUE / RECEBIDO / CANCELADO.
        - select_for_update() evita recebimento concorrente.
    """
    pc = get_object_or_404(
        PedidoCompra.objects.prefetch_related("itens__material"), pk=pk
    )

    S = PedidoCompra.StatusPC

    # Status que impedem novo recebimento
    STATUS_FINALIZADOS = (S.ENTREGUE, S.RECEBIDO, S.CANCELADO)

    # ═════════════════════════════════════════════════════════
    # 🔒 GUARDA DE STATUS
    # ═════════════════════════════════════════════════════════
    if pc.status in STATUS_FINALIZADOS:
        messages.warning(
            request,
            f"Este pedido não está disponível para entrega "
            f"(status atual: {pc.get_status_display()}).",
        )
        return redirect("suprimentos:pc_detalhe", pk=pc.pk)

    itens = list(pc.itens.select_related("material"))

    if request.method == "POST":
        form = EntregaPedidoCompraForm(request.POST, request.FILES, instance=pc)

        if form.is_valid():
            # 🔒 Lock + revalidação sob trava
            pc_locked = (
                PedidoCompra.objects
                .select_for_update()
                .get(pk=pc.pk)
            )
            if pc_locked.status in STATUS_FINALIZADOS:
                messages.warning(
                    request,
                    "Este pedido já foi finalizado por outro usuário.",
                )
                return redirect("suprimentos:pc_detalhe", pk=pc.pk)

            pc = form.save()

            # 1) Processa recebimento item a item
            houve_recebimento = False
            for item in itens:
                raw = request.POST.get(f"recebido_{item.pk}", "").strip()
                if not raw:
                    continue
                try:
                    qtd = Decimal(raw.replace(",", "."))
                except (InvalidOperation, AttributeError):
                    messages.warning(
                        request,
                        f"Valor inválido para o item {item.material.descricao}.",
                    )
                    continue

                if qtd <= 0:
                    continue
                if qtd > item.saldo:
                    messages.error(
                        request,
                        f"Quantidade recebida ({qtd}) maior que o saldo "
                        f"({item.saldo}) para {item.material.descricao}.",
                    )
                    transaction.set_rollback(True)
                    return redirect(
                        "suprimentos:pc_acompanhar_entrega", pk=pc.pk
                    )  # ✅ redireciona, sai do atomic

                item.quantidade_recebida = (item.quantidade_recebida or Decimal("0")) + qtd
                item.save(update_fields=["quantidade_recebida"])
                houve_recebimento = True

            # 2) Salva anexos
            for arquivo in form.cleaned_data.get("anexos", []):
                EntregaAnexo.objects.create(
                    pedido_compra=pc,
                    arquivo=arquivo,
                    nota_fiscal=pc.numero_nota_fiscal or "",
                    enviado_por=request.user,
                )

            # 3) Registra quem recebeu + atualiza status
            if houve_recebimento and not pc.recebido_por:
                pc.recebido_por = request.user
                pc.save(update_fields=["recebido_por", "atualizado_em"])

            pc.atualizar_status_entrega()

            if houve_recebimento:
                messages.success(request, "Recebimento registrado com sucesso!")
            else:
                messages.info(request, "Dados de entrega atualizados.")
            return redirect("suprimentos:pc_detalhe", pk=pc.pk)
    else:
        form = EntregaPedidoCompraForm(instance=pc)

    return _render_entrega(request, pc, itens, form)


@login_required
@permission_required("suprimentos.pode_visualizar_pedido_compra", raise_exception=True)
def pc_detalhe(request, pk):
    """Detalhe do Pedido de Compra com todas as entregas/anexos e progresso."""
    pc = get_object_or_404(
        PedidoCompra.objects.select_related("fornecedor", "filial"),
        pk=pk,
    )
    itens = list(pc.itens.select_related("material"))

    # Anexos de entrega (ordenados do mais recente p/ o mais antigo)
    anexos = (
        pc.anexos_entrega
        .select_related("enviado_por")
        .order_by("-created_at")  # ajuste se o campo de data tiver outro nome
    )

    # Totais agregados
    total_pedido = sum((i.quantidade or Decimal("0") for i in itens), Decimal("0"))
    total_recebido = sum((i.quantidade_recebida or Decimal("0") for i in itens), Decimal("0"))
    total_saldo = total_pedido - total_recebido

    progresso_pct = Decimal("0")
    if total_pedido > 0:
        progresso_pct = (total_recebido / total_pedido * 100).quantize(Decimal("0.1"))

    valor_total = sum(
        ((i.quantidade or Decimal("0")) * (i.valor_unitario or Decimal("0")) for i in itens),
        Decimal("0"),
    )

    # Agrupa anexos por nota fiscal (cada "recebimento" = uma NF)
    entregas = {}
    for anexo in anexos:
        chave = anexo.nota_fiscal or "Sem NF"
        entregas.setdefault(chave, []).append(anexo)

    context = {
        "pc": pc,
        "itens": itens,
        "anexos": anexos,
        "entregas": entregas,
        "total_pedido": total_pedido,
        "total_recebido": total_recebido,
        "total_saldo": total_saldo,
        "progresso_pct": progresso_pct,
        "valor_total": valor_total,
    }
    return render(request, "suprimentos/pc_detalhe.html", context)


# ═════════════════════════════════════════════════════════════
# CADASTROS AUXILIARES (Parceiro / Material / Contrato)
# ═════════════════════════════════════════════════════════════
class ParceiroListView(LoginRequiredMixin, ListView):
    model = Parceiro
    template_name = "suprimentos/parceiro_list.html"
    context_object_name = "parceiros"
    paginate_by = 25


class ParceiroCreateView(LoginRequiredMixin, CreateView):
    model = Parceiro
    form_class = ParceiroForm
    template_name = "suprimentos/parceiro_form.html"
    success_url = reverse_lazy("suprimentos:parceiro_list")


class MaterialListView(LoginRequiredMixin, ListView):
    model = Material
    template_name = "suprimentos/material_list.html"
    context_object_name = "materiais"
    paginate_by = 30

    def get_queryset(self):
        qs = Material.objects.all()
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(Q(descricao__icontains=q) | Q(codigo__icontains=q))
        return qs


class MaterialCreateView(LoginRequiredMixin, CreateView):
    model = Material
    form_class = MaterialForm
    template_name = "suprimentos/material_form.html"
    success_url = reverse_lazy("suprimentos:material_list")


class ContratoListView(LoginRequiredMixin, ListView):
    model = Contrato
    template_name = "suprimentos/contrato_list.html"
    context_object_name = "contratos"
    paginate_by = 25


# ═════════════════════════════════════════════════════════════
# 7. PEDIDO DE COMPRA — Impressão (A4 / PDF)
# ═════════════════════════════════════════════════════════════
class PedidoCompraImprimirView(LoginRequiredMixin, DetailView):
    model = PedidoCompra
    template_name = "suprimentos/pc_imprimir.html"
    context_object_name = "pc"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["itens"] = self.object.itens.select_related("material", "cotacao")
        ctx["valor_total"] = self.object.valor_total  # ← campo real do model
        ctx["emitido_em"] = timezone.now()
        return ctx
