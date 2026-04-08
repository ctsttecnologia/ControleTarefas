
# suprimentos/views.py

import json
import logging
import uuid
from datetime import date
from decimal import Decimal
from io import BytesIO
from django.db.models import Q
from functools import reduce
import operator
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction, IntegrityError
from django.db.models import Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import (
    ListView, CreateView, UpdateView, DetailView,
    DeleteView, FormView, TemplateView,
)

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from weasyprint import HTML

from core.mixins import (
    ViewFilialScopedMixin, FilialCreateMixin, SSTPermissionMixin,
    AppPermissionMixin,
)
from usuario.models import Filial
from logradouro.models import Logradouro
from seguranca_trabalho.models import Equipamento
from ferramentas.models import Ferramenta as FerramentaModel

from .models import (
    Parceiro, Material, Contrato, VerbaContrato,
    Pedido, ItemPedido, CategoriaMaterial, TipoMaterial,
    AnexoPedido, HistoricoPedido,
    SolicitacaoCompra, AnexoSolicitacao, HistoricoSolicitacao,
    TipoObra, TipoNotaFiscal,
)
from .forms import (
    ParceiroForm, UploadFileForm,
    MaterialForm, ContratoForm, VerbaContratoForm,
    PedidoForm, ItemPedidoForm,
    ReprovarPedidoForm, ConfirmarRecebimentoForm,
    DevolverPedidoForm, RevisaoPedidoForm, AnexoPedidoForm,
    CotacaoForm, ValidarCotacaoForm,
    CriarPedidoSiengeForm, AprovarPedidoSiengeForm,
    EnviarPedidoFornecedorForm, RegistrarEntregaForm,
    EncerrarSolicitacaoForm, CancelarSolicitacaoForm,
    AnexoSolicitacaoForm, ObservacaoSolicitacaoForm, 
)
from .relatorios import gerar_relatorio_completo
from notifications.services import (
    notificar_pedido_pendente,
    notificar_pedido_revisao,
    notificar_pedido_aprovado,
    notificar_pedido_reprovado,
    notificar_pedido_entregue,
    notificar_pedido_recebido,
    notificar_pedido_verba_excedida,
    notificar_solicitacao_criada,
    notificar_cotacao_enviada,
    notificar_cotacao_validada,
    notificar_pedido_sienge_criado,
    notificar_pedido_sienge_aprovado,
    notificar_pedido_enviado_fornecedor,
    notificar_entrega_registrada,
    notificar_solicitacao_concluida,
    notificar_solicitacao_cancelada,
)
# views.py — dashboard_suprimentos()

from django.contrib.auth import get_user_model
from cliente.models import Cliente

User = get_user_model()

logger = logging.getLogger(__name__)

_APP = 'suprimentos'


# ════════════════════════════════════════════
#   HELPER — Queryset de Pedido filtrado
# ════════════════════════════════════════════

def _pedido_qs_for_user(user):
    """Retorna queryset de Pedido já filtrado por filial ativa."""
    qs = Pedido.objects.select_related('contrato', 'solicitante', 'aprovador')
    filial_ativa = getattr(user, 'filial_ativa', None)
    if filial_ativa:
        qs = qs.filter(contrato__filial=filial_ativa)
    return qs


def _get_pedido_seguro(user, pk):
    """Busca pedido garantindo escopo de filial."""
    return get_object_or_404(_pedido_qs_for_user(user), pk=pk)

def _registrar_hist_pedido(pedido, descricao, user, status_ant='', status_novo=''):
    HistoricoPedido.registrar(
        pedido=pedido,
        descricao=descricao,
        responsavel=user,
        status_anterior=status_ant,
        status_novo=status_novo,
    )


# ════════════════════════════════════════════
#   PARCEIRO — Importação em massa
# ════════════════════════════════════════════

class ImportacaoParceiroError(Exception):
    def __init__(self, message, column_name=None):
        self.message = message
        self.column_name = column_name
        super().__init__(self.message)

    def __str__(self):
        if self.column_name:
            return f"Coluna '{self.column_name}': {self.message}"
        return self.message


@login_required
def parceiro_download_template(request):
    columns = [
        'Nome da Filial*', 'Nome Fantasia*', 'Razão Social', 'CNPJ',
        'Inscrição Estadual', 'Pessoa de Contato', 'Telefone', 'Celular',
        'E-mail', 'Site', 'É Fabricante? (SIM/NAO)*', 'É Fornecedor? (SIM/NAO)*',
        'CEP do Endereço', 'Observações',
    ]
    df_modelo = pd.DataFrame(columns=columns)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_modelo.to_excel(writer, index=False, sheet_name='Parceiros')
        workbook = writer.book
        worksheet = writer.sheets['Parceiros']
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4F81BD", fill_type="solid")
        for i, col_title in enumerate(columns, 1):
            cell = worksheet.cell(row=1, column=i)
            cell.font = header_font
            cell.fill = header_fill
            worksheet.column_dimensions[cell.column_letter].width = len(col_title) + 5
        dv = DataValidation(type="list", formula1='"SIM,NAO"', allow_blank=True)
        worksheet.add_data_validation(dv)
        dv.add('K2:L1048576')
        filiais = Filial.objects.all().values_list('nome',)
        df_filiais = pd.DataFrame(filiais, columns=['Nomes de Filiais Válidas'])
        df_filiais.to_excel(writer, index=False, sheet_name='Filiais para Consulta')
        worksheet.freeze_panes = 'A2'
    output.seek(0)
    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="modelo_importacao_parceiros.xlsx"'
    return response


class ParceiroBulkUploadView(LoginRequiredMixin, AppPermissionMixin, SSTPermissionMixin, View):
    app_label_required = _APP
    permission_required = 'suprimentos.add_parceiro'
    template_name = 'suprimentos/upload_parceiros.html'
    form_class = UploadFileForm

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        if 'parceiros_upload_erros' in request.session:
            del request.session['parceiros_upload_erros']
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})
        try:
            df = self._ler_e_validar_planilha(request.FILES['file'])
            with transaction.atomic():
                sucessos_count, linhas_com_erro = self._processar_dataframe(df)
                if linhas_com_erro:
                    raise IntegrityError()
            messages.success(
                request,
                f"Importação concluída! {sucessos_count} parceiros criados/atualizados.",
            )
            return redirect(reverse('suprimentos:parceiro_upload_massa'))
        except (ValueError, IntegrityError, ImportacaoParceiroError) as e:
            msg = str(e) if str(e) else "Importação cancelada devido a erros."
            if 'linhas_com_erro' in locals() and linhas_com_erro:
                request.session['parceiros_upload_erros'] = linhas_com_erro
                msg = f"Importação falhou com {len(linhas_com_erro)} erros. Nenhum parceiro salvo."
            messages.error(request, msg)
            context = {
                'form': form,
                'errors': [e['Erro'] for e in locals().get('linhas_com_erro', [])],
                'error_report_available': 'linhas_com_erro' in locals() and bool(linhas_com_erro),
            }
            return render(request, self.template_name, context)

    def _ler_e_validar_planilha(self, arquivo):
        if not arquivo.name.endswith('.xlsx'):
            raise ValueError('O arquivo deve ser .xlsx')
        df = pd.read_excel(arquivo, dtype=str).fillna('')
        colunas_esperadas = ['Nome da Filial*', 'Nome Fantasia*', 'Razão Social']
        if not all(col in df.columns for col in colunas_esperadas):
            faltantes = set(colunas_esperadas) - set(df.columns)
            raise ValueError(f"Colunas obrigatórias não encontradas: {', '.join(faltantes)}")
        return df

    def _processar_dataframe(self, df):
        linhas_com_erro, sucessos_count = [], 0
        for index, row in df.iterrows():
            try:
                self._processar_linha(row)
                sucessos_count += 1
            except ImportacaoParceiroError as e:
                linha_erro = row.to_dict()
                linha_erro['Erro'] = f"Linha {index + 2}, {e}"
                linhas_com_erro.append(linha_erro)
        return sucessos_count, linhas_com_erro

    def _processar_linha(self, row):
        nome_filial_raw = row.get('Nome da Filial*', '').strip()
        if not nome_filial_raw:
            raise ImportacaoParceiroError("Campo obrigatório.", column_name='Nome da Filial*')

        filial_encontrada = None
        for filial_db in Filial.objects.all():
            if filial_db.nome.lower() == nome_filial_raw.lower():
                filial_encontrada = filial_db
                break
        if not filial_encontrada:
            raise ImportacaoParceiroError(
                f"Filial '{nome_filial_raw}' não encontrada.",
                column_name='Nome da Filial*',
            )
        filial = filial_encontrada

        razao_social = row.get('Razão Social', '').strip()
        if not razao_social:
            raise ImportacaoParceiroError("Campo obrigatório.", column_name='Razão Social')
        nome_fantasia = row.get('Nome Fantasia*', '').strip()
        if not nome_fantasia:
            raise ImportacaoParceiroError("Campo obrigatório.", column_name='Nome Fantasia*')

        endereco = None
        cep = row.get('CEP do Endereço', '').strip()
        if cep:
            endereco = Logradouro.objects.filter(cep=cep).first()
            if not endereco:
                raise ImportacaoParceiroError(f"CEP '{cep}' não encontrado.", column_name='CEP do Endereço')

        eh_fabricante = str(row.get('É Fabricante? (SIM/NAO)*', '')).strip().upper() in ['SIM', 'S', 'YES', 'Y', '1']
        eh_fornecedor = str(row.get('É Fornecedor? (SIM/NAO)*', '')).strip().upper() in ['SIM', 'S', 'YES', 'Y', '1']
        cnpj = row.get('CNPJ', '').strip() or None

        try:
            identificador = {'cnpj': cnpj} if cnpj else {'razao_social': razao_social, 'filial': filial}
            Parceiro.objects.update_or_create(
                **identificador,
                defaults={
                    'filial': filial,
                    'nome_fantasia': nome_fantasia,
                    'razao_social': razao_social,
                    'inscricao_estadual': row.get('Inscrição Estadual', '').strip(),
                    'contato': row.get('Pessoa de Contato', '').strip(),
                    'telefone': row.get('Telefone', '').strip(),
                    'celular': row.get('Celular', '').strip(),
                    'email': row.get('E-mail', '').strip(),
                    'site': row.get('Site', '').strip(),
                    'endereco': endereco,
                    'observacoes': row.get('Observações', '').strip(),
                    'eh_fabricante': eh_fabricante,
                    'eh_fornecedor': eh_fornecedor,
                    'ativo': True,
                }
            )
        except Exception as e:
            raise ImportacaoParceiroError(f"Erro ao salvar: {str(e)}")


@login_required
def parceiro_download_erros(request):
    linhas_com_erro = request.session.pop('parceiros_upload_erros', [])
    if not linhas_com_erro:
        messages.warning(request, "Não há relatório de erros.")
        return redirect(reverse('suprimentos:parceiro_upload_massa'))
    df_erros = pd.DataFrame(linhas_com_erro)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_erros.to_excel(writer, index=False, sheet_name='Parceiros_Com_Erros')
    output.seek(0)
    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="relatorio_erros_parceiros.xlsx"'
    return response


# ════════════════════════════════════════════
#   PARCEIRO — CRUD
# ════════════════════════════════════════════

class ParceiroListView(LoginRequiredMixin, AppPermissionMixin, SSTPermissionMixin, ViewFilialScopedMixin, ListView):
    app_label_required = _APP
    model = Parceiro
    template_name = 'suprimentos/parceiro_list.html'
    context_object_name = 'parceiros'
    paginate_by = 20
    permission_required = 'suprimentos.view_parceiro'

    def get_queryset(self):
        qs = super().get_queryset().order_by('nome_fantasia')
        query = self.request.GET.get('q')
        if query:
            qs = qs.filter(
                Q(nome_fantasia__icontains=query) |
                Q(razao_social__icontains=query) |
                Q(cnpj__icontains=query)
            ).distinct()
        return qs


class ParceiroDetailView(LoginRequiredMixin, AppPermissionMixin, SSTPermissionMixin, ViewFilialScopedMixin, DetailView):
    app_label_required = _APP
    model = Parceiro
    template_name = 'suprimentos/parceiro_detail.html'
    context_object_name = 'parceiro'
    permission_required = 'suprimentos.view_parceiro'


class ParceiroCreateView(LoginRequiredMixin, AppPermissionMixin, SSTPermissionMixin, FilialCreateMixin, CreateView):
    app_label_required = _APP
    model = Parceiro
    form_class = ParceiroForm
    template_name = 'suprimentos/parceiro_form.html'
    success_url = reverse_lazy('suprimentos:parceiro_list')
    permission_required = 'suprimentos.add_parceiro'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo_pagina'] = 'Cadastrar Novo Fornecedor'
        return ctx


class ParceiroUpdateView(LoginRequiredMixin, AppPermissionMixin, SSTPermissionMixin, ViewFilialScopedMixin, UpdateView):
    app_label_required = _APP
    model = Parceiro
    form_class = ParceiroForm
    template_name = 'suprimentos/parceiro_form.html'
    success_url = reverse_lazy('suprimentos:parceiro_list')
    permission_required = 'suprimentos.change_parceiro'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo_pagina'] = 'Editar Fornecedor'
        return ctx


class ParceiroDeleteView(LoginRequiredMixin, AppPermissionMixin, SSTPermissionMixin, ViewFilialScopedMixin, DeleteView):
    app_label_required = _APP
    model = Parceiro
    template_name = 'suprimentos/parceiro_confirm_delete.html'
    success_url = reverse_lazy('suprimentos:parceiro_list')
    context_object_name = 'object'
    permission_required = 'suprimentos.delete_parceiro'


# ════════════════════════════════════════════
#   DASHBOARD SUPRIMENTOS
# ════════════════════════════════════════════

class DashboardSuprimentosView(LoginRequiredMixin, AppPermissionMixin, TemplateView):
    app_label_required = _APP
    template_name = 'suprimentos/dashboard.html'

    @staticmethod
    def _dec(val):
        return val or Decimal('0')

    @staticmethod
    def _pct(parte, total):
        if not total or total == 0:
            return 0
        return min(int((parte / total) * 100), 100)

    def _contrato_ids(self, user, cliente_id=None):
        qs = Contrato.objects.filter(ativo=True)

        # Filtra por filial (superusuário vê todos)
        if not user.is_superuser:
            filial_ativa = getattr(user, 'filial_ativa', None)
            if filial_ativa:
                qs = qs.filter(filial=filial_ativa)

        # usar 'cliente' (FK direta) ou 'cliente__id' (traversal)
        if cliente_id:
            qs = qs.filter(cliente=cliente_id)   # ← era cliente_id=, agora cliente=

        contrato_ids = list(qs.values_list('id', flat=True))
        return qs, contrato_ids

    def _verbas_mes(self, contrato_ids, ano, mes):
        agg = VerbaContrato.objects.filter(
            contrato_id__in=contrato_ids, ano=ano, mes=mes,
        ).aggregate(
            epi=Coalesce(Sum('verba_epi'), Decimal('0')),
            consumo=Coalesce(Sum('verba_consumo'), Decimal('0')),
            ferramenta=Coalesce(Sum('verba_ferramenta'), Decimal('0')),
        )
        agg['total'] = agg['epi'] + agg['consumo'] + agg['ferramenta']
        return agg

    def _compras_mes(self, contrato_ids, ano, mes, status_list, funcionario_id=None):
        base = ItemPedido.objects.filter(
            pedido__contrato_id__in=contrato_ids,
            pedido__status__in=status_list,
            pedido__data_pedido__year=ano,
            pedido__data_pedido__month=mes,
        )

        # ── NOVO: filtro por funcionário ──
        if funcionario_id:
            base = base.filter(pedido__solicitante_id=funcionario_id)

        compras = base.values('material__classificacao').annotate(
            total=Coalesce(Sum('valor_total'), Decimal('0')),
        )
        por_class = {r['material__classificacao']: r['total'] for r in compras}
        epi        = self._dec(por_class.get('EPI'))
        consumo    = self._dec(por_class.get('CONSUMO'))
        ferramenta = self._dec(por_class.get('FERRAMENTA'))

        trib = base.filter(
            material__grupo_tributario__isnull=False
        ).aggregate(
            valor_produtos=Coalesce(Sum('valor_total'),    Decimal('0')),
            custo_real    =Coalesce(Sum('custo_real'),     Decimal('0')),
            total_creditos=Coalesce(Sum('total_creditos'), Decimal('0')),
            total_impostos=Coalesce(Sum('total_impostos'), Decimal('0')),
        )

        return {
            'epi': epi, 'consumo': consumo, 'ferramenta': ferramenta,
            'total': epi + consumo + ferramenta,
            'trib': trib,
        }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        hoje    = timezone.now()
        ano     = int(self.request.GET.get('ano', hoje.year))
        mes     = int(self.request.GET.get('mes', hoje.month))
        user    = self.request.user
        STATUS_COMPRA = ['APROVADO', 'ENTREGUE', 'RECEBIDO']

        # ══════════════════════════════════════════
        # FILTROS — funcionário e cliente
        # ══════════════════════════════════════════
        funcionario_id = self.request.GET.get('funcionario', '').strip()
        cliente_id     = self.request.GET.get('cliente', '').strip()

        # ── Filial ativa do usuário ──
        filial_ativa = getattr(user, 'filial_ativa', None)

        # ══════════════════════════════════════════
        # LISTAS DOS SELECTS — filtradas por filial
        # ══════════════════════════════════════════

        # Funcionários: superusuário vê todos, demais só da filial ativa
        funcionarios_qs = User.objects.filter(is_active=True)
        if not user.is_superuser and filial_ativa:
            funcionarios_qs = funcionarios_qs.filter(filial_ativa=filial_ativa)
        ctx['funcionarios_filter'] = funcionarios_qs.order_by('first_name', 'last_name')

        # Clientes: superusuário vê todos, demais só da filial ativa
        clientes_qs = Cliente.objects.filter(estatus=True)
        if not user.is_superuser and filial_ativa:
            clientes_qs = clientes_qs.filter(filial=filial_ativa)
        ctx['clientes_filter'] = clientes_qs.order_by('nome')

        ctx['funcionario_selecionado'] = funcionario_id
        ctx['cliente_selecionado']     = cliente_id

        # ══════════════════════════════════════════
        # CONTRATOS — filtrados por filial e cliente
        # ══════════════════════════════════════════
        contratos_qs, contrato_ids = self._contrato_ids(
            user, cliente_id=cliente_id or None
        )

        # ══════════════════════════════════════════
        # GUARD — sem dados, retorna contexto mínimo
        # ══════════════════════════════════════════
        ctx['sem_dados'] = len(contrato_ids) == 0
        if ctx['sem_dados']:
            # Preenche zeros para não quebrar o template
            zero = Decimal('0')
            for key in [
                'total_verba_epi', 'total_verba_consumo', 'total_verba_ferramenta', 'total_verba',
                'total_compra_epi', 'total_compra_consumo', 'total_compra_ferramenta', 'total_compra',
                'saldo_epi', 'saldo_consumo', 'saldo_ferramenta', 'saldo_geral',
                'pct_epi', 'pct_consumo', 'pct_ferramenta', 'pct_geral',
                'pct_custo_real', 'pct_creditos',
            ]:
                ctx[key] = zero
            ctx['custos_tributarios'] = {
                'valor_produtos': zero, 'custo_real': zero,
                'total_creditos': zero, 'total_impostos': zero,
            }
            ctx['pedidos_pendentes']     = []
            ctx['grafico_meses']         = json.dumps([])
            ctx['saldo_anual']           = []
            ctx['contratos']             = contratos_qs
            ctx['materiais_total']       = 0
            ctx['materiais_sem_grupo']   = 0
            ctx['sol_fazer_cotacao']     = 0
            ctx['sol_validar_cotacao']   = 0
            ctx['sol_criar_pedido']      = 0
            ctx['sol_aprovar_pedido']    = 0
            ctx['sol_enviar_pedido']     = 0
            ctx['sol_entrega_pendente']  = 0
            ctx['sol_concluidas_mes']    = 0
            ctx['solicitacoes_urgentes'] = []
            ctx['is_comprador']          = _user_is_comprador(user)
            ctx['ano']                   = ano
            ctx['mes']                   = mes
            ctx['anos_disponiveis']      = range(2024, hoje.year + 2)
            ctx['meses'] = [
                (1,'Janeiro'),(2,'Fevereiro'),(3,'Março'),
                (4,'Abril'),(5,'Maio'),(6,'Junho'),
                (7,'Julho'),(8,'Agosto'),(9,'Setembro'),
                (10,'Outubro'),(11,'Novembro'),(12,'Dezembro'),
            ]
            return ctx  # ← sai cedo, sem queries desnecessárias

        # ══════════════════════════════════════════
        # DADOS NORMAIS (tem contratos)
        # ══════════════════════════════════════════

        # ── Verbas do mês ──
        verbas = self._verbas_mes(contrato_ids, ano, mes)
        ctx['total_verba_epi']        = verbas['epi']
        ctx['total_verba_consumo']    = verbas['consumo']
        ctx['total_verba_ferramenta'] = verbas['ferramenta']
        ctx['total_verba']            = verbas['total']

        # ── Compras do mês ──
        compras = self._compras_mes(
            contrato_ids, ano, mes, STATUS_COMPRA,
            funcionario_id=funcionario_id or None,
        )
        ctx['total_compra_epi']        = compras['epi']
        ctx['total_compra_consumo']    = compras['consumo']
        ctx['total_compra_ferramenta'] = compras['ferramenta']
        ctx['total_compra']            = compras['total']

        # ── Saldos ──
        ctx['saldo_epi']        = verbas['epi']        - compras['epi']
        ctx['saldo_consumo']    = verbas['consumo']    - compras['consumo']
        ctx['saldo_ferramenta'] = verbas['ferramenta'] - compras['ferramenta']
        ctx['saldo_geral']      = verbas['total']      - compras['total']

        # ── Percentuais ──
        ctx['pct_epi']        = self._pct(compras['epi'],        verbas['epi'])
        ctx['pct_consumo']    = self._pct(compras['consumo'],    verbas['consumo'])
        ctx['pct_ferramenta'] = self._pct(compras['ferramenta'], verbas['ferramenta'])
        ctx['pct_geral']      = self._pct(compras['total'],      verbas['total'])

        # ── Tributação ──
        ctx['custos_tributarios'] = compras['trib']

        mat_qs = Material.objects.filter(ativo=True)
        ctx['materiais_total']     = mat_qs.count()
        ctx['materiais_sem_grupo'] = mat_qs.filter(grupo_tributario__isnull=True).count()

        trib = compras['trib']
        ctx['pct_custo_real'] = self._pct(trib['custo_real'],     trib['valor_produtos']) if trib['valor_produtos'] > 0 else 0
        ctx['pct_creditos']   = self._pct(trib['total_creditos'], trib['valor_produtos']) if trib['valor_produtos'] > 0 else 0

        # ── Gráfico últimos 6 meses ──
        periodos = []
        for i in range(5, -1, -1):
            m_ = hoje.month - i
            a_ = hoje.year
            while m_ <= 0:
                m_ += 12
                a_ -= 1
            periodos.append((a_, m_))

        periodo_q = reduce(operator.or_, [Q(ano=a_, mes=m_) for a_, m_ in periodos])

        verbas_bulk = VerbaContrato.objects.filter(
            contrato_id__in=contrato_ids,
        ).filter(
            periodo_q,
        ).values('ano', 'mes').annotate(
            epi       =Coalesce(Sum('verba_epi'),        Decimal('0')),
            consumo   =Coalesce(Sum('verba_consumo'),    Decimal('0')),
            ferramenta=Coalesce(Sum('verba_ferramenta'), Decimal('0')),
        )
        verbas_map = {(v['ano'], v['mes']): v for v in verbas_bulk}

        compras_periodo_q = reduce(
            operator.or_,
            [Q(pedido__data_pedido__year=a_, pedido__data_pedido__month=m_) for a_, m_ in periodos]
        )

        compras_bulk_qs = ItemPedido.objects.filter(
            pedido__contrato_id__in=contrato_ids,
            pedido__status__in=STATUS_COMPRA,
        ).filter(
            compras_periodo_q,
        )
        if funcionario_id:
            compras_bulk_qs = compras_bulk_qs.filter(pedido__solicitante_id=funcionario_id)

        compras_bulk = compras_bulk_qs.values(
            'pedido__data_pedido__year',
            'pedido__data_pedido__month',
            'material__classificacao',
        ).annotate(total=Coalesce(Sum('valor_total'), Decimal('0')))

        compras_trib_bulk_qs = compras_bulk_qs.filter(
            material__grupo_tributario__isnull=False,
        ).values(
            'pedido__data_pedido__year',
            'pedido__data_pedido__month',
        ).annotate(
            custo_real=Coalesce(Sum('custo_real'),     Decimal('0')),
            creditos  =Coalesce(Sum('total_creditos'), Decimal('0')),
        )
        trib_map = {
            (t['pedido__data_pedido__year'], t['pedido__data_pedido__month']): t
            for t in compras_trib_bulk_qs
        }

        compras_map = {}
        for c in compras_bulk:
            key = (c['pedido__data_pedido__year'], c['pedido__data_pedido__month'])
            compras_map.setdefault(key, {})[c['material__classificacao']] = float(c['total'])

        grafico_meses = []
        for a_, m_ in periodos:
            v = verbas_map.get((a_, m_), {})
            c = compras_map.get((a_, m_), {})
            t = trib_map.get((a_, m_), {})
            v_epi = float(v.get('epi', 0))
            v_con = float(v.get('consumo', 0))
            v_fer = float(v.get('ferramenta', 0))
            c_epi = c.get('EPI', 0)
            c_con = c.get('CONSUMO', 0)
            c_fer = c.get('FERRAMENTA', 0)
            grafico_meses.append({
                'label'           : f"{m_:02d}/{a_}",
                'verba_total'     : v_epi + v_con + v_fer,
                'compra_total'    : c_epi + c_con + c_fer,
                'custo_real'      : float(t.get('custo_real', 0)),
                'creditos'        : float(t.get('creditos', 0)),
                'verba_epi'       : v_epi, 'verba_consumo': v_con, 'verba_ferramenta': v_fer,
                'compra_epi'      : c_epi, 'compra_consumo': c_con, 'compra_ferramenta': c_fer,
            })
        ctx['grafico_meses'] = json.dumps(grafico_meses)

        # ── Pedidos pendentes ──
        pedidos_qs = Pedido.objects.filter(
            status=Pedido.StatusChoices.PENDENTE,
            contrato_id__in=contrato_ids,
        ).select_related('contrato', 'solicitante').annotate(
            valor_total_pedido=Coalesce(Sum('itens__valor_total'), Decimal('0')),
        )
        if funcionario_id:
            pedidos_qs = pedidos_qs.filter(solicitante_id=funcionario_id)
        ctx['pedidos_pendentes'] = pedidos_qs[:10]

        # ── Pipeline — Solicitações ──
        sol_qs = SolicitacaoCompra.objects.filter(contrato_id__in=contrato_ids)
        if funcionario_id:
            sol_qs = sol_qs.filter(solicitante_id=funcionario_id)

        ctx['sol_fazer_cotacao']    = sol_qs.filter(status='FAZER_COTACAO').count()
        ctx['sol_validar_cotacao']  = sol_qs.filter(status='COTACAO_ENVIADA').count()
        ctx['sol_criar_pedido']     = sol_qs.filter(status='CRIAR_PEDIDO_CT').count()
        ctx['sol_aprovar_pedido']   = sol_qs.filter(status='EM_APROVACAO').count()
        ctx['sol_enviar_pedido']    = sol_qs.filter(status='ENVIAR_PEDIDO').count()
        ctx['sol_entrega_pendente'] = sol_qs.filter(status='ENTREGA_PENDENTE').count()
        ctx['sol_concluidas_mes']   = sol_qs.filter(
            status='CONCLUIDO',
            atualizado_em__year=ano,
            atualizado_em__month=mes,
        ).count()
        ctx['solicitacoes_urgentes'] = sol_qs.exclude(
            status__in=['CONCLUIDO', 'CANCELADO']
        ).order_by('criado_em')[:10]

        ctx['is_comprador'] = _user_is_comprador(user)
        ctx['contratos']    = contratos_qs

        ctx['ano']              = ano
        ctx['mes']              = mes
        ctx['anos_disponiveis'] = range(2024, hoje.year + 2)
        ctx['meses'] = [
            (1,'Janeiro'),(2,'Fevereiro'),(3,'Março'),
            (4,'Abril'),(5,'Maio'),(6,'Junho'),
            (7,'Julho'),(8,'Agosto'),(9,'Setembro'),
            (10,'Outubro'),(11,'Novembro'),(12,'Dezembro'),
        ]

        return ctx


# ════════════════════════════════════════════
#   MATERIAL — CRUD
# ════════════════════════════════════════════

class MaterialListView(LoginRequiredMixin, AppPermissionMixin, ListView):
    """Materiais são globais (catálogo compartilhado entre filiais)."""
    app_label_required = _APP
    model = Material
    template_name = 'suprimentos/material_list.html'
    context_object_name = 'materiais'
    paginate_by = 30

    def get_queryset(self):
        qs = Material.objects.select_related(
            'ncm', 'grupo_tributario'
        ).all()

        q = self.request.GET.get('q', '')
        classificacao = self.request.GET.get('classificacao', '')
        tipo = self.request.GET.get('tipo', '')
        sem_grupo = self.request.GET.get('sem_grupo', '')

        if q:
            qs = qs.filter(
                Q(descricao__icontains=q) | Q(marca__icontains=q) | Q(codigo__icontains=q)
            )
        if classificacao:
            qs = qs.filter(classificacao=classificacao)
        if tipo:
            qs = qs.filter(tipo=tipo)
        if sem_grupo == '1':
            qs = qs.filter(grupo_tributario__isnull=True, ativo=True)
        elif sem_grupo == '0':
            qs = qs.filter(grupo_tributario__isnull=False, ativo=True)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo_pagina'] = 'Catálogo de Materiais'
        ctx['classificacoes'] = CategoriaMaterial.choices
        ctx['tipos'] = TipoMaterial.choices
        ctx['filtro_q'] = self.request.GET.get('q', '')
        ctx['filtro_classificacao'] = self.request.GET.get('classificacao', '')
        ctx['filtro_tipo'] = self.request.GET.get('tipo', '')
        ctx['filtro_sem_grupo'] = self.request.GET.get('sem_grupo', '')

        qs = Material.objects.filter(ativo=True)
        ctx['total_materiais'] = qs.count()
        ctx['com_grupo_tributario'] = qs.filter(grupo_tributario__isnull=False).count()
        ctx['sem_grupo_tributario'] = qs.filter(grupo_tributario__isnull=True).count()
        ctx['com_ncm'] = qs.filter(ncm__isnull=False).count()
        return ctx


class MaterialCreateView(LoginRequiredMixin, AppPermissionMixin, CreateView):
    app_label_required = _APP
    model = Material
    form_class = MaterialForm
    template_name = 'suprimentos/material_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo_pagina'] = 'Novo Material'
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        material = self.object
        filial_ativa = getattr(self.request.user, 'filial_ativa', None)
        msgs = []

        if form.cleaned_data.get('criar_equipamento_epi'):
            equipamento = Equipamento.objects.create(
                nome=material.descricao,
                modelo=form.cleaned_data.get('epi_modelo', '') or '',
                fabricante=form.cleaned_data['epi_fabricante'],
                certificado_aprovacao=form.cleaned_data.get('epi_ca', ''),
                vida_util_dias=form.cleaned_data['epi_vida_util_dias'],
                filial=filial_ativa,
            )
            material.equipamento_epi = equipamento
            material.save(update_fields=['equipamento_epi'])
            msgs.append(f'Equipamento EPI (CA: {equipamento.certificado_aprovacao}) criado no SST')

        if form.cleaned_data.get('criar_ferramenta'):
            codigo = form.cleaned_data.get('ferr_codigo', '').strip()
            if not codigo:
                codigo = f"FERR-{uuid.uuid4().hex[:8].upper()}"
            ferramenta = FerramentaModel.objects.create(
                nome=material.descricao,
                codigo_identificacao=codigo,
                patrimonio=form.cleaned_data.get('ferr_patrimonio', '') or None,
                fabricante_marca=material.marca or None,
                localizacao_padrao=form.cleaned_data['ferr_localizacao'],
                data_aquisicao=form.cleaned_data['ferr_data_aquisicao'],
                quantidade=form.cleaned_data.get('ferr_quantidade') or 0,
                fornecedor=form.cleaned_data.get('ferr_fornecedor'),
                filial=filial_ativa,
                status=FerramentaModel.Status.DISPONIVEL,
            )
            material.ferramenta_ref = ferramenta
            material.save(update_fields=['ferramenta_ref'])
            msgs.append(f'Ferramenta "{ferramenta.nome}" ({codigo}) criada no módulo de Ferramentas')

        if msgs:
            detalhes = ' | '.join(msgs)
            messages.success(self.request, f'Material "{material.descricao}" criado! ✅ {detalhes}')
        else:
            messages.success(self.request, f'Material "{material.descricao}" criado!')
        return response

    def get_success_url(self):
        return reverse('suprimentos:material_lista')


class MaterialUpdateView(LoginRequiredMixin, AppPermissionMixin, UpdateView):
    app_label_required = _APP
    model = Material
    form_class = MaterialForm
    template_name = 'suprimentos/material_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo_pagina'] = f'Editar: {self.object.descricao}'
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        material = self.object
        filial_ativa = getattr(self.request.user, 'filial_ativa', None)
        msgs = []

        if form.cleaned_data.get('criar_equipamento_epi') and not material.equipamento_epi:
            equipamento = Equipamento.objects.create(
                nome=material.descricao,
                modelo=form.cleaned_data.get('epi_modelo', '') or '',
                fabricante=form.cleaned_data['epi_fabricante'],
                certificado_aprovacao=form.cleaned_data.get('epi_ca', ''),
                vida_util_dias=form.cleaned_data['epi_vida_util_dias'],
                filial=filial_ativa,
            )
            material.equipamento_epi = equipamento
            material.save(update_fields=['equipamento_epi'])
            msgs.append(f'Equipamento EPI (CA: {equipamento.certificado_aprovacao}) criado no SST')

        if form.cleaned_data.get('criar_ferramenta') and not material.ferramenta_ref:
            codigo = form.cleaned_data.get('ferr_codigo', '').strip()
            if not codigo:
                codigo = f"FERR-{uuid.uuid4().hex[:8].upper()}"
            ferramenta = FerramentaModel.objects.create(
                nome=material.descricao,
                codigo_identificacao=codigo,
                patrimonio=form.cleaned_data.get('ferr_patrimonio', '') or None,
                fabricante_marca=material.marca or None,
                localizacao_padrao=form.cleaned_data['ferr_localizacao'],
                data_aquisicao=form.cleaned_data['ferr_data_aquisicao'],
                quantidade=form.cleaned_data.get('ferr_quantidade') or 0,
                fornecedor=form.cleaned_data.get('ferr_fornecedor'),
                filial=filial_ativa,
                status=FerramentaModel.Status.DISPONIVEL,
            )
            material.ferramenta_ref = ferramenta
            material.save(update_fields=['ferramenta_ref'])
            msgs.append(f'Ferramenta "{ferramenta.nome}" ({codigo}) criada no módulo de Ferramentas')

        if msgs:
            detalhes = ' | '.join(msgs)
            messages.success(self.request, f'Material atualizado! ✅ {detalhes}')
        else:
            messages.success(self.request, 'Material atualizado!')
        return response

    def get_success_url(self):
        return reverse('suprimentos:material_lista')


# ════════════════════════════════════════════
#   CONTRATO — CRUD + Verbas
# ════════════════════════════════════════════

class ContratoListView(LoginRequiredMixin, AppPermissionMixin, ViewFilialScopedMixin, ListView):
    app_label_required = _APP
    model = Contrato
    template_name = 'suprimentos/contrato_list.html'
    context_object_name = 'contratos'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().filter(ativo=True)
        q = self.request.GET.get('q', '')
        if q:
            qs = qs.filter(Q(cm__icontains=q) | Q(cliente__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo_pagina'] = 'Contratos'
        return ctx


class ContratoCreateView(LoginRequiredMixin, AppPermissionMixin, FilialCreateMixin, CreateView):
    app_label_required = _APP
    model = Contrato
    form_class = ContratoForm
    template_name = 'suprimentos/contrato_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo_pagina'] = 'Novo Contrato'
        return ctx


class ContratoUpdateView(LoginRequiredMixin, AppPermissionMixin, ViewFilialScopedMixin, UpdateView):
    app_label_required = _APP
    model = Contrato
    form_class = ContratoForm
    template_name = 'suprimentos/contrato_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo_pagina'] = f'Editar CM {self.object.cm}'
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Contrato atualizado!')
        return super().form_valid(form)


class ContratoDetailView(LoginRequiredMixin, AppPermissionMixin, ViewFilialScopedMixin, DetailView):
    app_label_required = _APP
    model = Contrato
    template_name = 'suprimentos/contrato_detail.html'
    context_object_name = 'contrato'

    def get_object(self, queryset=None):
        try:
            return super().get_object(queryset)
        except self.model.DoesNotExist:
            if Contrato.objects.filter(pk=self.kwargs['pk']).exists():
                messages.warning(
                    self.request,
                    'Este contrato pertence a outra filial. '
                    'Selecione a filial correta no menu superior.'
                )
            else:
                messages.error(self.request, 'Contrato não encontrado.')
            raise

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        hoje = timezone.now()
        ano = int(self.request.GET.get('ano', hoje.year))
        mes = int(self.request.GET.get('mes', hoje.month))

        verba = self.object.verba_do_mes(ano, mes)
        ctx['verba'] = verba
        ctx['ano'] = ano
        ctx['mes'] = mes

        ctx['historico'] = VerbaContrato.objects.filter(
            contrato=self.object
        ).order_by('-ano', '-mes')[:12]

        ctx['pedidos'] = Pedido.objects.filter(
            contrato=self.object
        ).select_related('solicitante').order_by('-data_pedido')[:20]

        ctx['verba_form'] = VerbaContratoForm(initial={
            'ano': ano, 'mes': mes,
            'verba_epi': verba.verba_epi,
            'verba_consumo': verba.verba_consumo,
            'verba_ferramenta': verba.verba_ferramenta,
        })

        ctx['meses'] = [
            (1, 'Jan'), (2, 'Fev'), (3, 'Mar'), (4, 'Abr'),
            (5, 'Mai'), (6, 'Jun'), (7, 'Jul'), (8, 'Ago'),
            (9, 'Set'), (10, 'Out'), (11, 'Nov'), (12, 'Dez'),
        ]
        ctx['anos_disponiveis'] = range(2024, hoje.year + 2)
        ctx['is_gerente'] = self.request.user.is_gerente or self.request.user.is_superuser

        return ctx

    def post(self, request, *args, **kwargs):
        """Salvar/atualizar verba mensal — só Gerente."""
        self.object = self.get_object()
        user = request.user

        if not (user.is_gerente or user.is_superuser):
            messages.error(request, 'Apenas Gerentes podem alterar verbas.')
            return redirect(self.object.get_absolute_url())

        form = VerbaContratoForm(request.POST)
        if form.is_valid():
            ano = form.cleaned_data['ano']
            mes = form.cleaned_data['mes']
            verba, _ = VerbaContrato.objects.get_or_create(
                contrato=self.object, ano=ano, mes=mes,
            )
            verba.verba_epi = form.cleaned_data['verba_epi']
            verba.verba_consumo = form.cleaned_data['verba_consumo']
            verba.verba_ferramenta = form.cleaned_data['verba_ferramenta']
            verba.save()
            messages.success(request, f'Verba de {mes:02d}/{ano} atualizada!')
        else:
            messages.error(request, 'Erro ao salvar verba.')
        return redirect(
            f"{self.object.get_absolute_url()}?ano={form.cleaned_data.get('ano', '')}&mes={form.cleaned_data.get('mes', '')}"
        )



# ════════════════════════════════════════════
#   PEDIDO — Workflow (REFATORADO)
# ════════════════════════════════════════════

class PedidoCreateView(LoginRequiredMixin, AppPermissionMixin, CreateView):
    app_label_required = _APP
    model = Pedido
    form_class = PedidoForm
    template_name = 'suprimentos/pedido_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo_pagina'] = 'Novo Pedido de Material'
        ctx['anexo_form'] = AnexoPedidoForm()
        return ctx

    def form_valid(self, form):
        user = self.request.user
        form.instance.solicitante = user
        form.instance.filial = getattr(user, 'filial_ativa', None)
        response = super().form_valid(form)
        pedido = self.object

        # Upload de anexos
        arquivos = self.request.FILES.getlist('anexos')
        for arq in arquivos:
            AnexoPedido.objects.create(
                pedido=pedido, arquivo=arq, enviado_por=user,
            )

        _registrar_hist_pedido(
            pedido,
            f"Pedido criado por {user.get_full_name() or user.username}.",
            user, status_novo='RASCUNHO',
        )
        messages.success(self.request, f'Pedido {pedido.numero} criado! Adicione os itens.')
        return response


class PedidoDetailView(LoginRequiredMixin, AppPermissionMixin, DetailView):
    app_label_required = _APP
    model = Pedido
    template_name = 'suprimentos/pedido_detail.html'
    context_object_name = 'pedido'

    def get_queryset(self):
        return _pedido_qs_for_user(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        pedido = self.object
        user = self.request.user

        ctx['itens'] = pedido.itens.select_related('material').all()
        ctx['totais'] = pedido.totais_por_classificacao()
        ctx['item_form'] = ItemPedidoForm()
        ctx['reprovar_form'] = ReprovarPedidoForm()
        ctx['receber_form'] = ConfirmarRecebimentoForm()
        ctx['devolver_form'] = DevolverPedidoForm()
        ctx['anexo_form'] = AnexoPedidoForm()
        ctx['anexos'] = pedido.anexos.all()
        ctx['historico'] = pedido.historico.all()

        verba = pedido.contrato.verba_do_mes(
            pedido.data_pedido.year, pedido.data_pedido.month,
        )
        ctx['verba'] = verba

        is_gerente = user.is_gerente or user.is_superuser

        ctx['pode_editar'] = (
            pedido.status in [Pedido.StatusChoices.RASCUNHO, Pedido.StatusChoices.REVISAO]
            and (user == pedido.solicitante or is_gerente)
        )
        ctx['pode_enviar'] = (
            pedido.status in [Pedido.StatusChoices.RASCUNHO, Pedido.StatusChoices.REVISAO]
            and (user == pedido.solicitante or is_gerente)
        )
        ctx['pode_aprovar'] = (
            pedido.status == Pedido.StatusChoices.PENDENTE
            and is_gerente
        )
        ctx['pode_devolver'] = (
            pedido.status == Pedido.StatusChoices.PENDENTE
            and is_gerente
        )
        ctx['pode_revisar'] = (
            pedido.status == Pedido.StatusChoices.REVISAO
            and user == pedido.solicitante
        )
        ctx['pode_entregar'] = (
            pedido.status == Pedido.StatusChoices.APROVADO
            and is_gerente
        )
        ctx['pode_receber'] = (
            pedido.status == Pedido.StatusChoices.ENTREGUE
        )
        ctx['pode_cancelar'] = (
            pedido.status in [
                Pedido.StatusChoices.RASCUNHO,
                Pedido.StatusChoices.PENDENTE,
                Pedido.StatusChoices.REVISAO,
            ]
            and (user == pedido.solicitante or is_gerente)
        )

        # Form de revisão se estiver nesse status
        if pedido.status == Pedido.StatusChoices.REVISAO and user == pedido.solicitante:
            ctx['revisao_form'] = RevisaoPedidoForm(instance=pedido)

        # Link para solicitação gerada
        if pedido.solicitacao_gerada:
            ctx['solicitacao'] = pedido.solicitacao_gerada

        return ctx

# ════════════════════════════════════════════
#   PEDIDO — ListView (MANTIDA)
# ════════════════════════════════════════════

class PedidoListView(LoginRequiredMixin, AppPermissionMixin, ListView):
    app_label_required = _APP
    model = Pedido
    template_name = 'suprimentos/pedido_list.html'
    context_object_name = 'pedidos'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        qs = _pedido_qs_for_user(user)

        # Técnicos só veem seus pedidos
        if not (user.is_gerente or user.is_coordenador or user.is_administrador):
            qs = qs.filter(solicitante=user)

        status = self.request.GET.get('status', '')
        q = self.request.GET.get('q', '')
        if status:
            qs = qs.filter(status=status)
        if q:
            qs = qs.filter(
                Q(numero__icontains=q) | Q(contrato__cliente__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo_pagina'] = 'Pedidos de Material'
        ctx['status_choices'] = Pedido.StatusChoices.choices
        ctx['filtro_status'] = self.request.GET.get('status', '')
        ctx['filtro_q'] = self.request.GET.get('q', '')
        return ctx


# ════════════════════════════════════════════
#   PEDIDO — Views que já existiam (MANTIDAS)
# ════════════════════════════════════════════

class ItemPedidoCreateView(LoginRequiredMixin, AppPermissionMixin, View):
    """Adiciona item ao pedido (POST)."""
    app_label_required = _APP

    def post(self, request, pk):
        pedido = _get_pedido_seguro(request.user, pk)

        if pedido.status not in [Pedido.StatusChoices.RASCUNHO, Pedido.StatusChoices.REVISAO]:
            messages.error(request, 'Só é possível alterar pedidos em rascunho ou revisão.')
            return redirect(pedido.get_absolute_url())

        form = ItemPedidoForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.pedido = pedido
            item.save()
            messages.success(request, f'Item "{item.material}" adicionado!')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')

        return redirect(pedido.get_absolute_url())


class ItemPedidoDeleteView(LoginRequiredMixin, AppPermissionMixin, View):
    """Remove item do pedido."""
    app_label_required = _APP

    def post(self, request, pk, item_pk):
        pedido = _get_pedido_seguro(request.user, pk)
        item = get_object_or_404(ItemPedido, pk=item_pk, pedido=pedido)

        if pedido.status not in [Pedido.StatusChoices.RASCUNHO, Pedido.StatusChoices.REVISAO]:
            messages.error(request, 'Só é possível alterar pedidos em rascunho ou revisão.')
            return redirect(pedido.get_absolute_url())

        nome = str(item.material)
        item.delete()
        messages.success(request, f'Item "{nome}" removido.')
        return redirect(pedido.get_absolute_url())


class PedidoReprovarView(LoginRequiredMixin, AppPermissionMixin, View):
    """PENDENTE → REPROVADO (só Gerente)."""
    app_label_required = _APP

    def post(self, request, pk):
        pedido = _get_pedido_seguro(request.user, pk)
        user = request.user
        if not (user.is_gerente or user.is_superuser):
            messages.error(request, 'Apenas Gerentes podem reprovar pedidos.')
            return redirect(pedido.get_absolute_url())
        if pedido.status != Pedido.StatusChoices.PENDENTE:
            messages.error(request, 'Pedido não está pendente.')
            return redirect(pedido.get_absolute_url())

        form = ReprovarPedidoForm(request.POST)
        if form.is_valid():
            status_ant = pedido.status
            pedido.status = Pedido.StatusChoices.REPROVADO
            pedido.aprovador = user
            pedido.motivo_reprovacao = form.cleaned_data['motivo']
            pedido.data_aprovacao = timezone.now()
            pedido.save(update_fields=['status', 'aprovador', 'motivo_reprovacao', 'data_aprovacao'])

            _registrar_hist_pedido(
                pedido,
                f"Reprovado por {user.get_full_name() or user.username}. "
                f"Motivo: {pedido.motivo_reprovacao}",
                user, status_ant, 'REPROVADO',
            )
            notificar_pedido_reprovado(pedido)
            messages.info(request, f'Pedido {pedido.numero} reprovado.')
        else:
            messages.error(request, 'Informe o motivo da reprovação.')
        return redirect(pedido.get_absolute_url())


class PedidoEntregarView(LoginRequiredMixin, AppPermissionMixin, View):
    """APROVADO → ENTREGUE (só Gerente)."""
    app_label_required = _APP

    def post(self, request, pk):
        pedido = _get_pedido_seguro(request.user, pk)
        user = request.user
        if not (user.is_gerente or user.is_superuser):
            messages.error(request, 'Apenas Gerentes podem marcar entrega.')
            return redirect(pedido.get_absolute_url())
        if pedido.status != Pedido.StatusChoices.APROVADO:
            messages.error(request, 'Pedido não está aprovado.')
            return redirect(pedido.get_absolute_url())

        status_ant = pedido.status
        pedido.status = Pedido.StatusChoices.ENTREGUE
        pedido.data_entrega = timezone.now().date()
        pedido.save(update_fields=['status', 'data_entrega'])

        _registrar_hist_pedido(
            pedido,
            f"Marcado como entregue por {user.get_full_name() or user.username}.",
            user, status_ant, 'ENTREGUE',
        )
        notificar_pedido_entregue(pedido)
        messages.success(request, f'Pedido {pedido.numero} marcado como entregue! 📦')
        return redirect(pedido.get_absolute_url())


class PedidoReceberView(LoginRequiredMixin, AppPermissionMixin, View):
    """ENTREGUE → RECEBIDO."""
    app_label_required = _APP

    def post(self, request, pk):
        pedido = _get_pedido_seguro(request.user, pk)
        if pedido.status != Pedido.StatusChoices.ENTREGUE:
            messages.error(request, 'Pedido não está marcado como entregue.')
            return redirect(pedido.get_absolute_url())

        form = ConfirmarRecebimentoForm(request.POST)
        if form.is_valid():
            obs = form.cleaned_data.get('observacao_recebimento', '')
            if obs:
                pedido.observacao = f"{pedido.observacao}\n[Recebimento] {obs}".strip()

            status_ant = pedido.status
            pedido.recebedor = request.user
            pedido.data_recebimento = timezone.now()
            pedido.status = Pedido.StatusChoices.RECEBIDO
            pedido.save()

            _registrar_hist_pedido(
                pedido,
                f"Recebimento confirmado por {request.user.get_full_name() or request.user.username}.",
                request.user, status_ant, 'RECEBIDO',
            )
            notificar_pedido_recebido(pedido)

            messages.success(request, f'Pedido {pedido.numero} — recebimento confirmado! ✅')
            if pedido.estoque_processado:
                messages.info(
                    request,
                    '📦 Entrada no estoque gerada automaticamente.'
                )
        else:
            messages.error(request, 'Confirme o recebimento marcando a caixa.')

        return redirect(pedido.get_absolute_url())


class PedidoEnviarView(LoginRequiredMixin, AppPermissionMixin, View):
    """RASCUNHO/REVISAO → PENDENTE."""
    app_label_required = _APP

    def post(self, request, pk):
        pedido = _get_pedido_seguro(request.user, pk)
        if pedido.status not in [Pedido.StatusChoices.RASCUNHO, Pedido.StatusChoices.REVISAO]:
            messages.error(request, 'Pedido não pode ser enviado neste status.')
            return redirect(pedido.get_absolute_url())
        if not pedido.itens.exists():
            messages.error(request, 'Adicione pelo menos um item antes de enviar.')
            return redirect(pedido.get_absolute_url())

        ok, erros = pedido.verificar_verba()
        if not ok:
            for erro in erros:
                messages.warning(request, f'⚠️ {erro}')
            notificar_pedido_verba_excedida(pedido, erros)

        status_ant = pedido.status
        pedido.status = Pedido.StatusChoices.PENDENTE
        pedido.motivo_revisao = ''
        pedido.save(update_fields=['status', 'motivo_revisao'])

        _registrar_hist_pedido(
            pedido,
            f"Enviado para aprovação por {request.user.get_full_name() or request.user.username}.",
            request.user, status_ant, 'PENDENTE',
        )
        notificar_pedido_pendente(pedido)
        messages.success(request, f'Pedido {pedido.numero} enviado para aprovação!')
        return redirect(pedido.get_absolute_url())


class PedidoDevolverView(LoginRequiredMixin, AppPermissionMixin, View):
    """PENDENTE → REVISAO (Gerente devolve para correção)."""
    app_label_required = _APP

    def post(self, request, pk):
        pedido = _get_pedido_seguro(request.user, pk)
        user = request.user

        if not (user.is_gerente or user.is_superuser):
            messages.error(request, 'Apenas Gerentes podem devolver pedidos.')
            return redirect(pedido.get_absolute_url())
        if pedido.status != Pedido.StatusChoices.PENDENTE:
            messages.error(request, 'Pedido não está pendente.')
            return redirect(pedido.get_absolute_url())

        form = DevolverPedidoForm(request.POST)
        if form.is_valid():
            status_ant = pedido.status
            pedido.status = Pedido.StatusChoices.REVISAO
            pedido.motivo_revisao = form.cleaned_data['motivo']
            pedido.save(update_fields=['status', 'motivo_revisao'])

            _registrar_hist_pedido(
                pedido,
                f"Devolvido para revisão por {user.get_full_name() or user.username}. "
                f"Motivo: {pedido.motivo_revisao}",
                user, status_ant, 'REVISAO',
            )
            try:
                from notifications.services import notificar_pedido_revisao
                notificar_pedido_revisao(pedido)
            except (ImportError, Exception):
                pass
            messages.info(request, f'Pedido {pedido.numero} devolvido para revisão.')
        else:
            messages.error(request, 'Informe o motivo da devolução.')

        return redirect(pedido.get_absolute_url())


class PedidoRevisarView(LoginRequiredMixin, AppPermissionMixin, View):
    """Solicitante corrige e reenvia (REVISAO → PENDENTE)."""
    app_label_required = _APP

    def post(self, request, pk):
        pedido = _get_pedido_seguro(request.user, pk)
        user = request.user

        if user != pedido.solicitante and not user.is_superuser:
            messages.error(request, 'Apenas o solicitante pode revisar.')
            return redirect(pedido.get_absolute_url())
        if pedido.status != Pedido.StatusChoices.REVISAO:
            messages.error(request, 'Pedido não está em revisão.')
            return redirect(pedido.get_absolute_url())

        form = RevisaoPedidoForm(request.POST, instance=pedido)
        if form.is_valid():
            status_ant = pedido.status
            pedido = form.save(commit=False)
            pedido.status = Pedido.StatusChoices.PENDENTE
            pedido.motivo_revisao = ''
            pedido.save()

            # Novos anexos
            arquivos = request.FILES.getlist('anexos')
            for arq in arquivos:
                AnexoPedido.objects.create(
                    pedido=pedido, arquivo=arq, enviado_por=user,
                )

            _registrar_hist_pedido(
                pedido,
                f"Revisado e reenviado por {user.get_full_name() or user.username}.",
                user, status_ant, 'PENDENTE',
            )
            notificar_pedido_pendente(pedido)
            messages.success(request, f'Pedido {pedido.numero} reenviado para aprovação! 📋')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')

        return redirect(pedido.get_absolute_url())


class PedidoAprovarView(LoginRequiredMixin, AppPermissionMixin, View):
    """PENDENTE → APROVADO + gera SolicitacaoCompra automaticamente."""
    app_label_required = _APP

    def post(self, request, pk):
        pedido = _get_pedido_seguro(request.user, pk)
        user = request.user

        if not (user.is_gerente or user.is_superuser):
            messages.error(request, 'Apenas Gerentes podem aprovar pedidos.')
            return redirect(pedido.get_absolute_url())
        if pedido.status != Pedido.StatusChoices.PENDENTE:
            messages.error(request, 'Pedido não está pendente.')
            return redirect(pedido.get_absolute_url())

        ok, erros = pedido.verificar_verba()
        if not ok:
            for erro in erros:
                messages.warning(request, f'⚠️ {erro}')

        status_ant = pedido.status
        pedido.status = Pedido.StatusChoices.APROVADO
        pedido.aprovador = user
        pedido.data_aprovacao = timezone.now()
        pedido.save(update_fields=['status', 'aprovador', 'data_aprovacao'])

        _registrar_hist_pedido(
            pedido,
            f"Aprovado por {user.get_full_name() or user.username}.",
            user, status_ant, 'APROVADO',
        )
        notificar_pedido_aprovado(pedido)

        # ════════════════════════════════════════
        # GERAR SOLICITAÇÃO DE COMPRA AUTOMATICAMENTE
        # ════════════════════════════════════════

        try:
            sol = pedido.gerar_solicitacao_compra()
            # ── NOTIFICAR COMPRADORES ──
            try:
                notificar_solicitacao_criada(sol)
            except Exception as e:
                logger.error(f"Erro notificação solicitação criada: {e}")

            messages.success(
                request,
                f'Pedido {pedido.numero} aprovado! ✅ '
                f'Solicitação de Compra {sol.numero} gerada automaticamente. 📋'
            )
        except Exception as e:
            logger.error(f"Erro ao gerar solicitação: {e}")
            messages.success(request, f'Pedido {pedido.numero} aprovado! ✅')
            messages.error(request, f'Erro ao gerar solicitação: {e}')
        return redirect(pedido.get_absolute_url())


# ── Anexo do Pedido ──

class PedidoAnexoView(LoginRequiredMixin, AppPermissionMixin, View):
    """Upload de anexo no pedido."""
    app_label_required = _APP

    def post(self, request, pk):
        pedido = _get_pedido_seguro(request.user, pk)
        form = AnexoPedidoForm(request.POST, request.FILES)
        if form.is_valid():
            anexo = form.save(commit=False)
            anexo.pedido = pedido
            anexo.enviado_por = request.user
            anexo.save()
            _registrar_hist_pedido(
                pedido,
                f"Anexo adicionado: {anexo.nome_arquivo}",
                request.user,
            )
            messages.success(request, f'Anexo "{anexo.nome_arquivo}" enviado! 📎')
        else:
            for error in form.errors.values():
                messages.error(request, error)
        return redirect(pedido.get_absolute_url())


class PedidoAnexoDeleteView(LoginRequiredMixin, AppPermissionMixin, View):
    """Remove anexo do pedido."""
    app_label_required = _APP

    def post(self, request, pk, anexo_pk):
        pedido = _get_pedido_seguro(request.user, pk)
        anexo = get_object_or_404(AnexoPedido, pk=anexo_pk, pedido=pedido)
        nome = anexo.nome_arquivo
        anexo.arquivo.delete(save=False)
        anexo.delete()
        _registrar_hist_pedido(pedido, f"Anexo removido: {nome}", request.user)
        messages.success(request, f'Anexo "{nome}" removido.')
        return redirect(pedido.get_absolute_url())

# ════════════════════════════════════════════
#   APIs INTERNAS (AJAX)
# ════════════════════════════════════════════

@login_required
def material_preco_api(request, pk):
    """Retorna preço unitário do material."""
    material = get_object_or_404(Material, pk=pk)
    return JsonResponse({
        'valor_unitario': str(material.valor_unitario),
        'unidade': material.get_unidade_display(),
        'classificacao': material.classificacao,
        'descricao': material.descricao,
    })


@login_required
def contrato_saldos_api(request, pk):
    """Retorna saldos do contrato no mês atual."""
    contrato = get_object_or_404(
        Contrato.objects.for_request(request) if hasattr(Contrato.objects, 'for_request')
        else Contrato.objects.filter(
            filial=request.user.filial_ativa
        ) if getattr(request.user, 'filial_ativa', None)
        else Contrato.objects.all(),
        pk=pk
    )
    verba = contrato.verba_do_mes()
    return JsonResponse({
        'verba_epi': str(verba.verba_epi),
        'verba_consumo': str(verba.verba_consumo),
        'verba_ferramenta': str(verba.verba_ferramenta),
        'compra_epi': str(verba.compra_epi),
        'compra_consumo': str(verba.compra_consumo),
        'compra_ferramenta': str(verba.compra_ferramenta),
        'saldo_epi': str(verba.saldo_epi),
        'saldo_consumo': str(verba.saldo_consumo),
        'saldo_ferramenta': str(verba.saldo_ferramenta),
        'saldo_total': str(verba.saldo_total),
    })


# ════════════════════════════════════════════
#   RELATÓRIOS GERENCIAIS
# ════════════════════════════════════════════

class RelatorioForm(forms.Form):
    """Formulário de filtros do relatório."""
    ano = forms.IntegerField(
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'min': '2024', 'max': '2030',
        }),
    )
    mes_ini = forms.IntegerField(
        label="Mês Início",
        widget=forms.Select(
            attrs={'class': 'form-select'},
            choices=[(i, f'{i:02d}') for i in range(1, 13)],
        ),
    )
    mes_fim = forms.IntegerField(
        label="Mês Fim",
        widget=forms.Select(
            attrs={'class': 'form-select'},
            choices=[(i, f'{i:02d}') for i in range(1, 13)],
        ),
    )
    contrato = forms.ModelMultipleChoiceField(
        queryset=Contrato.objects.filter(ativo=True),
        required=False,
        label="Contratos (vazio = todos)",
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': '5'}),
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('mes_ini') and cleaned.get('mes_fim'):
            if cleaned['mes_ini'] > cleaned['mes_fim']:
                self.add_error('mes_fim', 'Mês fim deve ser >= mês início.')
        return cleaned


class _RelatorioFiltraMixin:
    """Mixin reutilizável para filtrar contratos por filial nos relatórios."""

    def _get_contrato_ids(self):
        user = self.request.user
        contratos_qs = Contrato.objects.filter(ativo=True)
        if not user.is_superuser:
            filial_ativa = getattr(user, 'filial_ativa', None)
            if filial_ativa:
                contratos_qs = contratos_qs.filter(filial=filial_ativa)

        contrato_ids_param = self.request.GET.getlist('contrato')
        if contrato_ids_param:
            return contratos_qs, list(
                contratos_qs.filter(id__in=contrato_ids_param).values_list('id', flat=True)
            )
        return contratos_qs, list(contratos_qs.values_list('id', flat=True))

    def _get_periodo(self):
        hoje = timezone.now()
        ano = int(self.request.GET.get('ano', hoje.year))
        mes_ini = int(self.request.GET.get('mes_ini', 1))
        mes_fim = int(self.request.GET.get('mes_fim', hoje.month))
        return ano, mes_ini, mes_fim


class RelatorioSuprimentosView(LoginRequiredMixin, AppPermissionMixin, _RelatorioFiltraMixin, TemplateView):
    """Relatório gerencial completo de Suprimentos."""
    app_label_required = _APP
    template_name = 'suprimentos/relatorio.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        contratos_qs, contrato_ids = self._get_contrato_ids()
        ano, mes_ini, mes_fim = self._get_periodo()

        relatorio = gerar_relatorio_completo(contrato_ids, ano, mes_ini, mes_fim)

        ctx.update({
            'relatorio': relatorio,
            'filtro_ano': ano,
            'filtro_mes_ini': mes_ini,
            'filtro_mes_fim': mes_fim,
            'filtro_contratos': self.request.GET.getlist('contrato'),
            'contratos_disponiveis': contratos_qs,
            'meses_choices': [(i, f'{i:02d}') for i in range(1, 13)],
            'titulo_pagina': 'Relatório Gerencial de Suprimentos',
            'json_quantitativo_meses': json.dumps(
                relatorio['quantitativo']['por_mes'], default=str
            ),
            'json_evolucao': json.dumps(
                relatorio['qualitativo']['evolucao_mensal'], default=str
            ),
            'json_estimativas_hist': json.dumps(
                relatorio['estimativas']['historico_mensal'], default=str
            ),
            'json_estimativas_proj': json.dumps(
                relatorio['estimativas']['projecao'], default=str
            ),
        })
        return ctx


class RelatorioPDFView(LoginRequiredMixin, AppPermissionMixin, _RelatorioFiltraMixin, View):
    """Exporta o relatório completo em PDF via WeasyPrint."""
    app_label_required = _APP

    def get(self, request):
        hoje = timezone.now()
        _, contrato_ids = self._get_contrato_ids()
        ano, mes_ini, mes_fim = self._get_periodo()

        relatorio = gerar_relatorio_completo(contrato_ids, ano, mes_ini, mes_fim)

        html_string = render_to_string(
            'suprimentos/relatorio_pdf.html',
            {
                'relatorio': relatorio,
                'usuario': request.user.get_full_name() or request.user.username,
                'gerado_em': hoje,
            },
        )

        pdf = HTML(string=html_string).write_pdf()

        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'inline; filename="relatorio_suprimentos_{ano}_{mes_ini:02d}-{mes_fim:02d}.pdf"'
        )
        return response


class RelatorioExcelView(LoginRequiredMixin, AppPermissionMixin, _RelatorioFiltraMixin, View):
    """Exporta o relatório em Excel via openpyxl."""
    app_label_required = _APP

    def get(self, request):
        _, contrato_ids = self._get_contrato_ids()
        ano, mes_ini, mes_fim = self._get_periodo()

        relatorio = gerar_relatorio_completo(contrato_ids, ano, mes_ini, mes_fim)

        wb = Workbook()

        # Estilos
        titulo_font = Font(bold=True, size=14, color="FFFFFF")
        header_font = Font(bold=True, size=11, color="FFFFFF")
        titulo_fill = PatternFill(start_color="0D6EFD", end_color="0D6EFD", fill_type="solid")
        header_fill = PatternFill(start_color="495057", end_color="495057", fill_type="solid")
        danger_fill = PatternFill(start_color="F8D7DA", end_color="F8D7DA", fill_type="solid")
        success_fill = PatternFill(start_color="D1E7DD", end_color="D1E7DD", fill_type="solid")
        border = Border(
            left=Side(style='thin'), right=Side(style='thin'),
            top=Side(style='thin'), bottom=Side(style='thin'),
        )
        money_fmt = '#,##0.00'

        def add_titulo(ws, titulo, row=1):
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=8)
            cell = ws.cell(row=row, column=1, value=titulo)
            cell.font = titulo_font
            cell.fill = titulo_fill
            cell.alignment = Alignment(horizontal='center')
            return row + 2

        def add_headers(ws, headers, row):
            for col, h in enumerate(headers, 1):
                cell = ws.cell(row=row, column=col, value=h)
                cell.font = header_font
                cell.fill = header_fill
                cell.border = border
                cell.alignment = Alignment(horizontal='center')
            return row + 1

        # ═══ ABA 1: QUANTITATIVO ═══
        ws1 = wb.active
        ws1.title = "Quantitativo"
        row = add_titulo(ws1, f"RELATÓRIO QUANTITATIVO — {relatorio['parametros']['periodo_label']}")

        headers = ['Categoria', 'Pedidos', 'Linhas', 'Unidades', 'Valor Total (R$)', '% do Total']
        row = add_headers(ws1, headers, row)
        for r in relatorio['quantitativo']['resumo_geral']:
            ws1.cell(row=row, column=1, value=r['categoria_label']).border = border
            ws1.cell(row=row, column=2, value=r['qtd_pedidos']).border = border
            ws1.cell(row=row, column=3, value=r['qtd_itens_linha']).border = border
            ws1.cell(row=row, column=4, value=r['qtd_unidades']).border = border
            c = ws1.cell(row=row, column=5, value=float(r['valor_total']))
            c.number_format = money_fmt
            c.border = border
            ws1.cell(row=row, column=6, value=f"{r['pct_valor']}%").border = border
            row += 1

        row += 2
        ws1.cell(row=row, column=1, value="TOP 15 MATERIAIS MAIS COMPRADOS").font = Font(bold=True, size=12)
        row += 1
        headers_top = ['Material', 'Classificação', 'Unidade', 'Qtd Total', 'Valor Total (R$)', 'Pedidos']
        row = add_headers(ws1, headers_top, row)
        for m in relatorio['quantitativo']['top_materiais']:
            ws1.cell(row=row, column=1, value=m['material__descricao']).border = border
            ws1.cell(row=row, column=2, value=m['material__classificacao']).border = border
            ws1.cell(row=row, column=3, value=m['material__unidade']).border = border
            ws1.cell(row=row, column=4, value=m['qtd_total']).border = border
            c = ws1.cell(row=row, column=5, value=float(m['valor_total']))
            c.number_format = money_fmt
            c.border = border
            ws1.cell(row=row, column=6, value=m['vezes_pedido']).border = border
            row += 1

        for col in range(1, 9):
            ws1.column_dimensions[get_column_letter(col)].width = 20

        # ═══ ABA 2: QUALITATIVO ═══
        ws2 = wb.create_sheet("Qualitativo")
        row = add_titulo(ws2, f"VERBA × GASTO — {relatorio['parametros']['periodo_label']}")

        headers_q = ['Categoria', 'Verba (R$)', 'Gasto (R$)', 'Saldo (R$)', '% Uso', 'Status']
        row = add_headers(ws2, headers_q, row)
        for r in relatorio['qualitativo']['resumo_categorias']:
            ws2.cell(row=row, column=1, value=r['categoria_label']).border = border
            c1 = ws2.cell(row=row, column=2, value=float(r['verba']))
            c1.number_format = money_fmt
            c1.border = border
            c2 = ws2.cell(row=row, column=3, value=float(r['gasto']))
            c2.number_format = money_fmt
            c2.border = border
            c3 = ws2.cell(row=row, column=4, value=float(r['saldo']))
            c3.number_format = money_fmt
            c3.border = border
            ws2.cell(row=row, column=5, value=f"{r['pct_uso']}%").border = border
            status_cell = ws2.cell(row=row, column=6, value=r['status'].upper())
            status_cell.border = border
            if r['status'] == 'acima':
                status_cell.fill = danger_fill
            elif r['status'] == 'ok':
                status_cell.fill = success_fill
            row += 1

        row += 1
        ws2.cell(row=row, column=1, value="TOTAL GERAL").font = Font(bold=True)
        c = ws2.cell(row=row, column=2, value=float(relatorio['qualitativo']['total_verba_geral']))
        c.number_format = money_fmt
        c.font = Font(bold=True)
        c = ws2.cell(row=row, column=3, value=float(relatorio['qualitativo']['total_gasto_geral']))
        c.number_format = money_fmt
        c.font = Font(bold=True)
        c = ws2.cell(row=row, column=4, value=float(relatorio['qualitativo']['saldo_geral']))
        c.number_format = money_fmt
        c.font = Font(bold=True)

        row += 3
        ws2.cell(row=row, column=1, value="EVOLUÇÃO MENSAL").font = Font(bold=True, size=12)
        row += 1
        headers_ev = ['Mês', 'Verba EPI', 'Gasto EPI', 'Verba Consumo', 'Gasto Consumo',
                       'Verba Ferrament.', 'Gasto Ferrament.', 'Saldo Total']
        row = add_headers(ws2, headers_ev, row)
        for ev in relatorio['qualitativo']['evolucao_mensal']:
            ws2.cell(row=row, column=1, value=ev['label']).border = border
            for i, cod in enumerate(['epi', 'consumo', 'ferramenta']):
                c1 = ws2.cell(row=row, column=2 + i * 2, value=float(ev[f'verba_{cod}']))
                c1.number_format = money_fmt
                c1.border = border
                c2 = ws2.cell(row=row, column=3 + i * 2, value=float(ev[f'gasto_{cod}']))
                c2.number_format = money_fmt
                c2.border = border
            c = ws2.cell(row=row, column=8, value=float(ev['saldo_total']))
            c.number_format = money_fmt
            c.border = border
            if ev['saldo_total'] < 0:
                c.fill = danger_fill
            row += 1

        for col in range(1, 9):
            ws2.column_dimensions[get_column_letter(col)].width = 18

        # ═══ ABA 3: ALERTAS ═══
        ws3 = wb.create_sheet("Alertas - Acima da Meta")
        row = add_titulo(ws3, f"GASTOS ACIMA DA META — {relatorio['parametros']['periodo_label']}")

        if relatorio['alertas']['alertas']:
            headers_a = ['Contrato', 'Mês', 'Categoria', 'Verba (R$)', 'Gasto (R$)',
                         'Excesso (R$)', '% Excesso', 'Severidade']
            row = add_headers(ws3, headers_a, row)
            for al in relatorio['alertas']['alertas']:
                ws3.cell(row=row, column=1, value=al['contrato']).border = border
                ws3.cell(row=row, column=2, value=al['mes_label']).border = border
                ws3.cell(row=row, column=3, value=al['categoria_label']).border = border
                c1 = ws3.cell(row=row, column=4, value=float(al['verba']))
                c1.number_format = money_fmt
                c1.border = border
                c2 = ws3.cell(row=row, column=5, value=float(al['gasto']))
                c2.number_format = money_fmt
                c2.border = border
                c3 = ws3.cell(row=row, column=6, value=float(al['excesso']))
                c3.number_format = money_fmt
                c3.border = border
                c3.fill = danger_fill
                ws3.cell(row=row, column=7, value=f"{al['pct_excesso']}%").border = border
                sev = ws3.cell(row=row, column=8, value=al['severidade'].upper())
                sev.border = border
                if al['severidade'] == 'critico':
                    sev.fill = danger_fill
                row += 1
        else:
            ws3.cell(row=row, column=1, value="✅ Nenhum gasto acima da meta no período!").font = Font(size=12, color="198754")

        for col in range(1, 9):
            ws3.column_dimensions[get_column_letter(col)].width = 20

        # ═══ ABA 4: ECONOMIAS ═══
        ws4 = wb.create_sheet("Economias")
        row = add_titulo(ws4, f"ECONOMIAS — {relatorio['parametros']['periodo_label']}")

        headers_e = ['Categoria', 'Total Economizado (R$)']
        row = add_headers(ws4, headers_e, row)
        for ec in relatorio['economias']['resumo_economia']:
            ws4.cell(row=row, column=1, value=ec['categoria_label']).border = border
            c = ws4.cell(row=row, column=2, value=float(ec['total_economia']))
            c.number_format = money_fmt
            c.border = border
            c.fill = success_fill
            row += 1

        row += 1
        ws4.cell(row=row, column=1, value="TOTAL GERAL ECONOMIZADO").font = Font(bold=True)
        c = ws4.cell(row=row, column=2, value=float(relatorio['economias']['total_economia_geral']))
        c.number_format = money_fmt
        c.font = Font(bold=True)
        c.fill = success_fill

        row += 3
        ws4.cell(row=row, column=1, value="RANKING — CONTRATOS QUE MAIS ECONOMIZARAM").font = Font(bold=True, size=12)
        row += 1
        row = add_headers(ws4, ['Contrato', 'Economia (R$)'], row)
        for rk in relatorio['economias']['ranking_contratos']:
            ws4.cell(row=row, column=1, value=rk['contrato']).border = border
            c = ws4.cell(row=row, column=2, value=float(rk['economia']))
            c.number_format = money_fmt
            c.border = border
            row += 1

        for col in range(1, 9):
            ws4.column_dimensions[get_column_letter(col)].width = 22

        # ═══ ABA 5: ESTIMATIVAS ═══
        ws5 = wb.create_sheet("Estimativas")
        row = add_titulo(ws5, "PROJEÇÃO DE GASTOS — PRÓXIMOS 6 MESES")

        headers_est = ['Mês', 'Verba EPI', 'Gasto Est. EPI', 'Verba Consumo',
                       'Gasto Est. Consumo', 'Verba Ferrament.', 'Gasto Est. Ferrament.', 'Saldo Estimado']
        row = add_headers(ws5, headers_est, row)
        for pr in relatorio['estimativas']['projecao']:
            ws5.cell(row=row, column=1, value=pr['label']).border = border
            for i, cod in enumerate(['epi', 'consumo', 'ferramenta']):
                c1 = ws5.cell(row=row, column=2 + i * 2, value=float(pr[f'verba_{cod}']))
                c1.number_format = money_fmt
                c1.border = border
                c2 = ws5.cell(row=row, column=3 + i * 2, value=float(pr[f'gasto_{cod}']))
                c2.number_format = money_fmt
                c2.border = border
            c = ws5.cell(row=row, column=8, value=float(pr['saldo_total']))
            c.number_format = money_fmt
            c.border = border
            if pr['saldo_total'] < 0:
                c.fill = danger_fill
            row += 1

        row += 2
        ws5.cell(row=row, column=1, value="TENDÊNCIAS (Últimos 6 meses)").font = Font(bold=True, size=12)
        row += 1
        row = add_headers(ws5, ['Categoria', 'Média Mensal (R$)', 'Mín (R$)', 'Máx (R$)', 'Tendência', 'Variação'], row)
        for cod, label in [('EPI', 'EPI'), ('CONSUMO', 'Consumo'), ('FERRAMENTA', 'Ferramenta')]:
            m = relatorio['estimativas']['media_por_categoria'][cod]
            ws5.cell(row=row, column=1, value=label).border = border
            c1 = ws5.cell(row=row, column=2, value=float(m['media']))
            c1.number_format = money_fmt
            c1.border = border
            c2 = ws5.cell(row=row, column=3, value=float(m['min']))
            c2.number_format = money_fmt
            c2.border = border
            c3 = ws5.cell(row=row, column=4, value=float(m['max']))
            c3.number_format = money_fmt
            c3.border = border
            tend = ws5.cell(row=row, column=5, value=m['tendencia'].upper())
            tend.border = border
            if m['tendencia'] == 'subindo':
                tend.fill = danger_fill
            elif m['tendencia'] == 'descendo':
                tend.fill = success_fill
            ws5.cell(row=row, column=6, value=f"{m['variacao_tendencia']}%").border = border
            row += 1

        for col in range(1, 9):
            ws5.column_dimensions[get_column_letter(col)].width = 20

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = (
            f'attachment; filename="relatorio_suprimentos_{ano}_{mes_ini:02d}-{mes_fim:02d}.xlsx"'
        )
        return response

# ════════════════════════════════════════════════════════════════════
# ══  SOLICITAÇÃO DE COMPRA — WORKFLOW PÓS-APROVAÇÃO               ══
# ════════════════════════════════════════════════════════════════════

def _sol_qs_for_user(user):
    qs = SolicitacaoCompra.objects.select_related(
        'contrato', 'solicitante', 'aprovador_inicial',
        'comprador', 'fornecedor',
    )
    filial_ativa = getattr(user, 'filial_ativa', None)
    if filial_ativa:
        qs = qs.filter(filial=filial_ativa)
    return qs


def _get_sol_seguro(user, pk):
    return get_object_or_404(_sol_qs_for_user(user), pk=pk)


def _user_is_comprador(user):
    return (
        user.is_superuser
        or user.groups.filter(name='Comprador').exists()
        or user.groups.filter(name='Administrador').exists()
    )


def _user_is_aprovador(user):
    return user.is_gerente or user.is_superuser or user.is_administrador


def _registrar_hist_sol(sol, descricao, user, status_ant='', status_novo=''):
    HistoricoSolicitacao.registrar(
        solicitacao=sol, descricao=descricao,
        responsavel=user, status_anterior=status_ant,
        status_novo=status_novo,
    )


class SolicitacaoListView(LoginRequiredMixin, AppPermissionMixin, ListView):
    """
    Lista de Solicitações de Compra com formulários inline por etapa.
    Aprovador pode flag/liberar, Comprador pode inserir cotação direto na lista.
    """
    app_label_required = _APP
    template_name = 'suprimentos/solicitacao/solicitacao_list.html'
    context_object_name = 'solicitacoes'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        qs = SolicitacaoCompra.objects.select_related(
            'contrato', 'solicitante', 'comprador',
            'fornecedor', 'aprovador_inicial',
            'aprovador_cotacao', 'aprovador_pedido',
        ).order_by('-criado_em')

        # ── Filtro por filial ──
        if not user.is_superuser:
            filial = getattr(user, 'filial_ativa', None)
            if filial:
                qs = qs.filter(contrato__filial=filial)

        # ── Filtros GET ──
        status = self.request.GET.get('status', '')
        if status:
            qs = qs.filter(status=status)

        tipo_obra = self.request.GET.get('tipo_obra', '')
        if tipo_obra:
            qs = qs.filter(tipo_obra=tipo_obra)

        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(numero__icontains=q) |
                Q(descricao_material__icontains=q) |
                Q(contrato__cm__icontains=q) |
                Q(contrato__cliente__icontains=q) |
                Q(numero_cotacao__icontains=q) |
                Q(numero_pedido_sienge__icontains=q)
            )

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        # Permissões
        is_aprovador = _user_is_aprovador(user)
        is_comprador = _user_is_comprador(user)
        ctx['is_aprovador'] = is_aprovador
        ctx['is_comprador'] = is_comprador

        # KPIs
        base_qs = self.get_queryset()
        ctx['count_cotacao'] = base_qs.filter(status='FAZER_COTACAO').count()
        ctx['count_aprovacao'] = base_qs.filter(
            status__in=['COTACAO_ENVIADA', 'EM_APROVACAO']
        ).count()
        ctx['count_pendentes'] = base_qs.exclude(
            status__in=['CONCLUIDO', 'CANCELADO']
        ).count()

        # Filtros para o template
        ctx['filtro_q'] = self.request.GET.get('q', '')
        ctx['filtro_status'] = self.request.GET.get('status', '')
        ctx['filtro_tipo_obra'] = self.request.GET.get('tipo_obra', '')

        # Choices para selects de filtro
        ctx['status_choices'] = SolicitacaoCompra.StatusChoices.choices
        ctx['tipo_obra_choices'] = SolicitacaoCompra._meta.get_field('tipo_obra').choices

        # ── Formulários inline para cada solicitação ──
        solicitacoes = ctx['solicitacoes']
        forms_map = {}
        for sol in solicitacoes:
            sol_forms = {}

            # Comprador: Fazer Cotação
            if sol.status == 'FAZER_COTACAO' and is_comprador:
                sol_forms['form_cotacao'] = CotacaoForm(prefix=f'cot_{sol.pk}')
                sol_forms['form_anexo'] = AnexoSolicitacaoForm(prefix=f'anx_{sol.pk}')

            # Aprovador: Validar Cotação
            if sol.status == 'COTACAO_ENVIADA' and is_aprovador:
                sol_forms['form_validar'] = ValidarCotacaoForm(prefix=f'val_{sol.pk}')

            # Comprador: Criar Pedido
            if sol.status == 'CRIAR_PEDIDO_CT' and is_comprador:
                sol_forms['form_pedido'] = CriarPedidoSiengeForm(prefix=f'ped_{sol.pk}')

            # Aprovador: Aprovar Pedido
            if sol.status == 'EM_APROVACAO' and is_aprovador:
                sol_forms['form_aprovar'] = AprovarPedidoSiengeForm(prefix=f'apr_{sol.pk}')

            # Comprador: Enviar ao Fornecedor
            if sol.status == 'ENVIAR_PEDIDO' and is_comprador:
                sol_forms['form_enviar'] = EnviarPedidoFornecedorForm(prefix=f'env_{sol.pk}')

            # Comprador: Registrar Entrega
            if sol.status == 'ENTREGA_PENDENTE' and is_comprador:
                sol_forms['form_entrega'] = RegistrarEntregaForm(prefix=f'ent_{sol.pk}')
                if sol.data_entrega_efetiva:
                    sol_forms['form_encerrar'] = EncerrarSolicitacaoForm(prefix=f'enc_{sol.pk}')

            if sol_forms:
                forms_map[sol.pk] = sol_forms

        ctx['forms_map'] = forms_map

        # Dados para os forms inline
        ctx['fornecedores'] = Parceiro.objects.filter(
            eh_fornecedor=True, ativo=True
        ).order_by('nome_fantasia')

        # Choices de Tipo NF
        ctx['tipo_nf_choices'] = SolicitacaoCompra._meta.get_field('tipo_nota_fiscal').choices

        return ctx


class SolicitacaoDetailView(LoginRequiredMixin, AppPermissionMixin, DetailView):
    """Detalhe da Solicitação de Compra com formulários contextuais."""
    app_label_required = _APP
    model = SolicitacaoCompra
    template_name = 'suprimentos/solicitacao/solicitacao_detail.html'
    context_object_name = 'sol'

    def get_queryset(self):
        return SolicitacaoCompra.objects.select_related(
            'contrato', 'solicitante', 'comprador',
            'fornecedor', 'aprovador_inicial',
            'aprovador_cotacao', 'aprovador_pedido',
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        sol = self.object
        user = self.request.user
        is_aprovador = _user_is_aprovador(user)
        is_comprador = _user_is_comprador(user)

        ctx['is_aprovador'] = is_aprovador
        ctx['is_comprador'] = is_comprador

        # ── Etapas do stepper ──
        ctx['etapas'] = [
            {'num': 1, 'titulo': 'Fazer Cotação'},
            {'num': 2, 'titulo': 'Validar Cotação'},
            {'num': 3, 'titulo': 'Criar Pedido'},
            {'num': 4, 'titulo': 'Aprovar Pedido'},
            {'num': 5, 'titulo': 'Enviar Fornecedor'},
            {'num': 6, 'titulo': 'Entrega'},
            {'num': 7, 'titulo': 'Nota Fiscal'},
            {'num': 8, 'titulo': 'Concluído'},
        ]

        # ── Formulários contextuais ──
        if sol.status == 'FAZER_COTACAO' and is_comprador:
            ctx['form_cotacao'] = CotacaoForm(instance=sol)

        if sol.status == 'COTACAO_ENVIADA' and is_aprovador:
            ctx['form_validar_cotacao'] = ValidarCotacaoForm()

        if sol.status == 'CRIAR_PEDIDO_CT' and is_comprador:
            ctx['form_criar_pedido'] = CriarPedidoSiengeForm(instance=sol)

        if sol.status == 'EM_APROVACAO' and is_aprovador:
            ctx['form_aprovar_pedido'] = AprovarPedidoSiengeForm()
            # Verificar verba
            if hasattr(sol, 'verificar_verba'):
                ok, msg = sol.verificar_verba()
                ctx['verba_ok'] = ok
                ctx['verba_msg'] = msg

        if sol.status == 'ENVIAR_PEDIDO' and is_comprador:
            ctx['form_enviar_fornecedor'] = EnviarPedidoFornecedorForm()

        if sol.status == 'ENTREGA_PENDENTE' and is_comprador:
            if not sol.data_entrega_efetiva:
                ctx['form_entrega'] = RegistrarEntregaForm()
            else:
                ctx['form_encerrar'] = EncerrarSolicitacaoForm()

        # Formulários permanentes
        ctx['form_anexo'] = AnexoSolicitacaoForm()
        ctx['form_observacao'] = ObservacaoSolicitacaoForm()
        ctx['form_cancelar'] = CancelarSolicitacaoForm()

        # Anexos e Histórico
        ctx['anexos'] = sol.anexos.all() if hasattr(sol, 'anexos') else []
        ctx['historico'] = sol.historicos.all().order_by('-criado_em') if hasattr(sol, 'historicos') else []

        # Pedido de origem
        if hasattr(sol, 'pedido'):
            ctx['pedido_origem'] = sol.pedido
        elif hasattr(sol, 'pedido_origem'):
            ctx['pedido_origem'] = sol.pedido_origem

        return ctx
    

class SolicitacaoCotacaoView(LoginRequiredMixin, AppPermissionMixin, View):
    app_label_required = _APP

    def post(self, request, pk):
        sol = _get_sol_seguro(request.user, pk)
        user = request.user

        if not _user_is_comprador(user):
            messages.error(request, 'Apenas compradores podem registrar cotações.')
            return redirect(sol.get_absolute_url())
        if sol.status != 'FAZER_COTACAO':
            messages.error(request, 'Status inválido para registrar cotação.')
            return redirect(sol.get_absolute_url())

        form = CotacaoForm(request.POST, instance=sol)
        if form.is_valid():
            status_ant = sol.status
            sol = form.save(commit=False)
            sol.status = 'COTACAO_ENVIADA'
            sol.comprador = user
            sol.save()

            _registrar_hist_sol(
                sol,
                f"Cotação registrada por {user.get_full_name() or user.username}. "
                f"Nº: {sol.numero_cotacao}. CNPJ: {sol.cnpj_compra}.",
                user, status_ant, 'COTACAO_ENVIADA',
            )
            # ── NOTIFICAÇÃO ──
            try:
                notificar_cotacao_enviada(sol)
            except Exception as e:
                logger.error(f"Erro notificação cotação enviada: {e}")

            messages.success(request, 'Cotação registrada! Aguardando validação. 📊')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
        return redirect(sol.get_absolute_url())

class SolicitacaoValidarCotacaoView(LoginRequiredMixin, AppPermissionMixin, View):
    app_label_required = _APP

    def post(self, request, pk):
        sol = _get_sol_seguro(request.user, pk)
        user = request.user

        if not _user_is_aprovador(user):
            messages.error(request, 'Sem permissão para validar cotação.')
            return redirect(sol.get_absolute_url())
        if sol.status != 'COTACAO_ENVIADA':
            messages.error(request, 'Cotação não está aguardando validação.')
            return redirect(sol.get_absolute_url())

        form = ValidarCotacaoForm(request.POST)
        if form.is_valid():
            status_ant = sol.status
            sol.data_validacao_cotacao = form.cleaned_data['data_validacao']
            sol.aprovador_cotacao = user
            sol.status = 'CRIAR_PEDIDO_CT'
            sol.save(update_fields=[
                'status', 'data_validacao_cotacao',
                'aprovador_cotacao', 'atualizado_em',
            ])
            _registrar_hist_sol(
                sol,
                f"Cotação validada por {user.get_full_name() or user.username}.",
                user, status_ant, 'CRIAR_PEDIDO_CT',
            )
            # ── NOTIFICAÇÃO ──
            try:
                notificar_cotacao_validada(sol)
            except Exception as e:
                logger.error(f"Erro notificação cotação validada: {e}")

            messages.success(request, 'Cotação validada! Comprador pode criar o pedido. ✅')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
        return redirect(sol.get_absolute_url()) 


class SolicitacaoCriarPedidoView(LoginRequiredMixin, AppPermissionMixin, View):
    app_label_required = _APP

    def post(self, request, pk):
        sol = _get_sol_seguro(request.user, pk)
        user = request.user

        if not _user_is_comprador(user):
            messages.error(request, 'Apenas compradores podem criar pedidos.')
            return redirect(sol.get_absolute_url())
        if sol.status != 'CRIAR_PEDIDO_CT':
            messages.error(request, 'Status inválido para criar pedido.')
            return redirect(sol.get_absolute_url())

        form = CriarPedidoSiengeForm(request.POST, instance=sol)
        if form.is_valid():
            status_ant = sol.status
            sol = form.save(commit=False)
            sol.status = 'EM_APROVACAO'
            sol.save()

            ok, msg_verba = sol.verificar_verba()
            if not ok:
                messages.warning(request, msg_verba)

            _registrar_hist_sol(
                sol,
                f"Pedido Sienge criado por {user.get_full_name() or user.username}. "
                f"Nº: {sol.numero_pedido_sienge}. "
                f"Fornecedor: {sol.fornecedor}. Valor: R$ {sol.valor_pedido:.2f}.",
                user, status_ant, 'EM_APROVACAO',
            )
            # ── NOTIFICAÇÃO ──
            try:
                notificar_pedido_sienge_criado(sol)
            except Exception as e:
                logger.error(f"Erro notificação pedido sienge criado: {e}")

            messages.success(request, 'Pedido criado! Aguardando aprovação. 📦')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
        return redirect(sol.get_absolute_url())


class SolicitacaoAprovarPedidoView(LoginRequiredMixin, AppPermissionMixin, View):
    app_label_required = _APP

    def post(self, request, pk):
        sol = _get_sol_seguro(request.user, pk)
        user = request.user

        if not _user_is_aprovador(user):
            messages.error(request, 'Sem permissão para aprovar pedido.')
            return redirect(sol.get_absolute_url())
        if sol.status != 'EM_APROVACAO':
            messages.error(request, 'Pedido não está em aprovação.')
            return redirect(sol.get_absolute_url())

        form = AprovarPedidoSiengeForm(request.POST)
        if form.is_valid():
            status_ant = sol.status
            sol.data_aprovacao_pedido = form.cleaned_data['data_aprovacao_pedido']
            sol.aprovador_pedido = user
            sol.status = 'ENVIAR_PEDIDO'
            sol.save(update_fields=[
                'status', 'data_aprovacao_pedido',
                'aprovador_pedido', 'atualizado_em',
            ])
            _registrar_hist_sol(
                sol,
                f"Pedido aprovado por {user.get_full_name() or user.username}.",
                user, status_ant, 'ENVIAR_PEDIDO',
            )
            # ── NOTIFICAÇÃO ──
            try:
                notificar_pedido_sienge_aprovado(sol)
            except Exception as e:
                logger.error(f"Erro notificação pedido aprovado: {e}")

            messages.success(request, 'Pedido aprovado! Enviar ao fornecedor. ✅')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
        return redirect(sol.get_absolute_url())

class SolicitacaoEnviarFornecedorView(LoginRequiredMixin, AppPermissionMixin, View):
    app_label_required = _APP

    def post(self, request, pk):
        sol = _get_sol_seguro(request.user, pk)
        user = request.user

        if not _user_is_comprador(user):
            messages.error(request, 'Apenas compradores podem enviar pedidos.')
            return redirect(sol.get_absolute_url())
        if sol.status != 'ENVIAR_PEDIDO':
            messages.error(request, 'Status inválido.')
            return redirect(sol.get_absolute_url())

        form = EnviarPedidoFornecedorForm(request.POST)
        if form.is_valid():
            status_ant = sol.status
            sol.data_envio_fornecedor = form.cleaned_data['data_envio']
            sol.data_prevista_entrega = form.cleaned_data['data_prevista']
            sol.status = 'ENTREGA_PENDENTE'
            sol.save(update_fields=[
                'status', 'data_envio_fornecedor',
                'data_prevista_entrega', 'atualizado_em',
            ])
            _registrar_hist_sol(
                sol,
                f"Enviado ao fornecedor por {user.get_full_name() or user.username}. "
                f"Previsão: {sol.data_prevista_entrega}.",
                user, status_ant, 'ENTREGA_PENDENTE',
            )
            # ── NOTIFICAÇÃO ──
            try:
                notificar_pedido_enviado_fornecedor(sol)
            except Exception as e:
                logger.error(f"Erro notificação envio fornecedor: {e}")

            messages.success(request, f'Pedido enviado! Previsão: {sol.data_prevista_entrega}. 🚚')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
        return redirect(sol.get_absolute_url())

class SolicitacaoRegistrarEntregaView(LoginRequiredMixin, AppPermissionMixin, View):
    app_label_required = _APP

    def post(self, request, pk):
        sol = _get_sol_seguro(request.user, pk)
        user = request.user

        if not _user_is_comprador(user):
            messages.error(request, 'Apenas compradores.')
            return redirect(sol.get_absolute_url())
        if sol.status != 'ENTREGA_PENDENTE':
            messages.error(request, 'Status inválido.')
            return redirect(sol.get_absolute_url())

        form = RegistrarEntregaForm(request.POST)
        if form.is_valid():
            sol.data_entrega_efetiva = form.cleaned_data['data_entrega']
            sol.save(update_fields=['data_entrega_efetiva', 'atualizado_em'])
            _registrar_hist_sol(
                sol,
                f"Entrega efetiva em {sol.data_entrega_efetiva} "
                f"por {user.get_full_name() or user.username}.",
                user,
            )
            # ── NOTIFICAÇÃO ──
            try:
                notificar_entrega_registrada(sol)
            except Exception as e:
                logger.error(f"Erro notificação entrega: {e}")

            messages.success(request, f'Entrega registrada! Agora informe o Nº da NF para encerrar. 📦')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
        return redirect(sol.get_absolute_url())

class SolicitacaoEncerrarView(LoginRequiredMixin, AppPermissionMixin, View):
    app_label_required = _APP

    def post(self, request, pk):
        sol = _get_sol_seguro(request.user, pk)
        user = request.user

        if not _user_is_comprador(user):
            messages.error(request, 'Apenas compradores.')
            return redirect(sol.get_absolute_url())
        if sol.status != 'ENTREGA_PENDENTE' or not sol.data_entrega_efetiva:
            messages.error(request, 'Registre a entrega antes de encerrar.')
            return redirect(sol.get_absolute_url())

        form = EncerrarSolicitacaoForm(request.POST)
        if form.is_valid():
            status_ant = sol.status
            sol.numero_nota_fiscal = form.cleaned_data['numero_nota_fiscal']
            sol.status = 'CONCLUIDO'
            sol.save(update_fields=['status', 'numero_nota_fiscal', 'atualizado_em'])
            _registrar_hist_sol(
                sol,
                f"ENCERRADA por {user.get_full_name() or user.username}. NF: {sol.numero_nota_fiscal}.",
                user, status_ant, 'CONCLUIDO',
            )
            # ── NOTIFICAÇÃO ──
            try:
                notificar_solicitacao_concluida(sol)
            except Exception as e:
                logger.error(f"Erro notificação conclusão: {e}")

            messages.success(request, f'Solicitação {sol.numero} CONCLUÍDA! ✅🎉')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
        return redirect(sol.get_absolute_url())


class SolicitacaoCancelarView(LoginRequiredMixin, AppPermissionMixin, View):
    app_label_required = _APP

    def post(self, request, pk):
        sol = _get_sol_seguro(request.user, pk)
        user = request.user

        if not sol.pode_cancelar:
            messages.error(request, 'Não pode ser cancelada.')
            return redirect(sol.get_absolute_url())

        pode = (
            user == sol.solicitante
            or _user_is_aprovador(user)
            or _user_is_comprador(user)
        )
        if not pode:
            messages.error(request, 'Sem permissão.')
            return redirect(sol.get_absolute_url())

        form = CancelarSolicitacaoForm(request.POST)
        if form.is_valid():
            status_ant = sol.status
            sol.status = 'CANCELADO'
            sol.motivo_cancelamento = form.cleaned_data['motivo']
            timestamp = timezone.now().strftime('%d/%m/%Y %H:%M')
            sol.observacoes = (
                f"{sol.observacoes}\n"
                f"[CANCELADO em {timestamp}] Motivo: {sol.motivo_cancelamento}"
            ).strip()
            sol.save(update_fields=[
                'status', 'motivo_cancelamento', 'observacoes', 'atualizado_em',
            ])
            _registrar_hist_sol(
                sol,
                f"CANCELADA por {user.get_full_name() or user.username}. "
                f"Motivo: {sol.motivo_cancelamento}",
                user, status_ant, 'CANCELADO',
            )
            # ── NOTIFICAÇÃO ──
            try:
                notificar_solicitacao_cancelada(sol)
            except Exception as e:
                logger.error(f"Erro notificação cancelamento: {e}")

            messages.warning(request, f'Solicitação {sol.numero} cancelada.')
        else:
            messages.error(request, 'Informe o motivo do cancelamento.')
        return redirect(sol.get_absolute_url())


class SolicitacaoAnexoView(LoginRequiredMixin, AppPermissionMixin, View):
    app_label_required = _APP

    def post(self, request, pk):
        sol = _get_sol_seguro(request.user, pk)
        form = AnexoSolicitacaoForm(request.POST, request.FILES)
        if form.is_valid():
            anexo = form.save(commit=False)
            anexo.solicitacao = sol
            anexo.enviado_por = request.user
            anexo.save()
            _registrar_hist_sol(sol, f"Anexo: {anexo.nome_arquivo}", request.user)
            messages.success(request, f'Anexo enviado! 📎')
        else:
            for error in form.errors.values():
                messages.error(request, error)
        return redirect(sol.get_absolute_url())


class SolicitacaoAnexoDeleteView(LoginRequiredMixin, AppPermissionMixin, View):
    app_label_required = _APP

    def post(self, request, pk, anexo_pk):
        sol = _get_sol_seguro(request.user, pk)
        anexo = get_object_or_404(AnexoSolicitacao, pk=anexo_pk, solicitacao=sol)
        nome = anexo.nome_arquivo
        anexo.arquivo.delete(save=False)
        anexo.delete()
        _registrar_hist_sol(sol, f"Anexo removido: {nome}", request.user)
        messages.success(request, f'Anexo "{nome}" removido.')
        return redirect(sol.get_absolute_url())


class SolicitacaoObservacaoView(LoginRequiredMixin, AppPermissionMixin, View):
    app_label_required = _APP

    def post(self, request, pk):
        sol = _get_sol_seguro(request.user, pk)
        user = request.user
        form = ObservacaoSolicitacaoForm(request.POST)
        if form.is_valid():
            texto = form.cleaned_data['texto']
            timestamp = timezone.now().strftime('%d/%m/%Y %H:%M')
            nome = user.get_full_name() or user.username
            sol.observacoes = (
                f"{sol.observacoes}\n[{timestamp} — {nome}] {texto}"
            ).strip()
            sol.save(update_fields=['observacoes', 'atualizado_em'])
            _registrar_hist_sol(sol, f"Observação: {texto[:100]}", user)
            messages.success(request, 'Observação registrada! 📝')
        else:
            messages.error(request, 'Texto obrigatório.')
        return redirect(sol.get_absolute_url())
