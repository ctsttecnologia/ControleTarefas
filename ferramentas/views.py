# ferramentas/views.py

import base64
import json
from datetime import timedelta, datetime
from io import BytesIO
import subprocess
import sys
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (CreateView, DetailView, FormView, ListView, TemplateView, UpdateView)
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from core.mixins import SSTPermissionMixin, ViewFilialScopedMixin, AtividadeLogMixin
from usuario.models import Filial
from .forms import (DevolucaoForm, FerramentaForm, MovimentacaoForm, UploadFileForm, MalaFerramentasForm) 
from .models import Atividade, Ferramenta, MalaFerramentas, Movimentacao




# =============================================================================
# == VIEWS PRINCIPAIS (ATUALIZADO)
# =============================================================================

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'ferramentas/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request

        # 1. BUSCA AS QUERYSETS BASE
        malas_da_filial = MalaFerramentas.objects.for_request(request)
        movimentacoes_da_filial = Movimentacao.objects.for_request(request)
        atividades_da_filial = Atividade.objects.for_request(request)
        todas_as_ferramentas = Ferramenta.objects.for_request(request).exclude(status=Ferramenta.Status.DESCARTADA)

        # 2. LÓGICA CENTRAL PARA CALCULAR OS STATUS REAIS DAS FERRAMENTAS
        # Ferramentas que estão EM USO (diretamente ou via mala em uso)
        ferramentas_em_uso_qs = todas_as_ferramentas.filter(
            Q(status=Ferramenta.Status.EM_USO) | Q(mala__status=MalaFerramentas.Status.EM_USO)
        ).distinct()
        
        # Ferramentas que estão EM MANUTENÇÃO (apenas status direto)
        ferramentas_em_manutencao_qs = todas_as_ferramentas.filter(
            status=Ferramenta.Status.EM_MANUTENCAO
        )

        # Ferramentas DISPONÍVEIS (não estão em uso e não estão em manutenção)
        ferramentas_disponiveis_qs = todas_as_ferramentas.exclude(
            pk__in=ferramentas_em_uso_qs.values_list('pk', flat=True)
        ).exclude(
            pk__in=ferramentas_em_manutencao_qs.values_list('pk', flat=True)
        )
        
        # 3. CALCULA ESTATÍSTICAS DE MALAS
        stats_malas = malas_da_filial.aggregate(
            total=Count('id'),
            disponivel=Count('id', filter=Q(status=MalaFerramentas.Status.DISPONIVEL)),
            em_uso=Count('id', filter=Q(status=MalaFerramentas.Status.EM_USO))
        )

        # 4. COMBINA OS TOTAIS PARA OS CARDS PRINCIPAIS
        # (Usando as contagens corretas que acabamos de calcular)
        context['stats_total'] = {
            'total': todas_as_ferramentas.count() + stats_malas.get('total', 0),
            'disponivel': ferramentas_disponiveis_qs.count() + stats_malas.get('disponivel', 0),
            'em_uso': ferramentas_em_uso_qs.count() + stats_malas.get('em_uso', 0),
            'em_manutencao': ferramentas_em_manutencao_qs.count()
        }
        
        # 5. PREPARA DADOS PARA OS GRÁFICOS
        # (Agora as variáveis necessárias existem e os dados estarão corretos)
        context['ferramentas_chart_data'] = {
            'labels': ['Disponível', 'Em Uso', 'Em Manutenção'],
            'data': [
                ferramentas_disponiveis_qs.count(),
                ferramentas_em_uso_qs.count(),
                ferramentas_em_manutencao_qs.count()
            ],
            'title': 'Distribuição de Ferramentas'
        }
        
        context['malas_chart_data'] = {
            'labels': ['Disponível', 'Em Uso'],
            'data': [
                stats_malas.get('disponivel', 0),
                stats_malas.get('em_uso', 0)
            ],
            'title': 'Distribuição de Malas/Kits'
        }

        # 6. PREPARA LISTAS DE ITENS EM USO E ATIVIDADES
        context['ferramentas_em_uso'] = movimentacoes_da_filial.filter(
            data_devolucao__isnull=True, ferramenta__isnull=False
        ).select_related('ferramenta', 'retirado_por')
        
        context['malas_em_uso'] = movimentacoes_da_filial.filter(
            data_devolucao__isnull=True, mala__isnull=False
        ).select_related('mala', 'retirado_por')
        
        context['ultimas_atividades'] = atividades_da_filial.order_by('-timestamp')[:10]
        context['titulo_pagina'] = "Dashboard de Operações"
        
        return context
# =============================================================================
# == VIEWS DE FERRAMENTAS
# =============================================================================

class FerramentaListView(LoginRequiredMixin, ViewFilialScopedMixin, ListView):
    model = Ferramenta
    template_name = 'ferramentas/ferramenta_list.html'
    context_object_name = 'ferramentas'
    paginate_by = 30
    queryset = Ferramenta.objects.select_related('mala', 'filial').order_by('nome')

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('q')
        status_filter = self.request.GET.get('status')

        if search_query:
            queryset = queryset.filter(
                Q(nome__icontains=search_query) |
                Q(codigo_identificacao__icontains=search_query) |
                Q(patrimonio__icontains=search_query)
            )

        if status_filter:
            if status_filter == Ferramenta.Status.EM_USO:
                queryset = queryset.filter(Q(status=status_filter) | Q(mala__status=status_filter))
            elif status_filter == Ferramenta.Status.DISPONIVEL:
                queryset = queryset.filter(status=status_filter).filter(
                    Q(mala__isnull=True) | Q(mala__status=status_filter)
                )
            else:
                queryset = queryset.filter(status=status_filter)
        else:
            queryset = queryset.exclude(status=Ferramenta.Status.DESCARTADA)
            
        return queryset.distinct().order_by('nome')

class FerramentaDetailView(LoginRequiredMixin, ViewFilialScopedMixin, DetailView):
    model = Ferramenta
    template_name = 'ferramentas/ferramenta_detail.html'
    context_object_name = 'ferramenta'
    
    def get_queryset(self):
        return super().get_queryset().prefetch_related('movimentacoes__retirado_por', 'atividades__usuario')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ferramenta = self.object
        
        context['status_efetivo'] = ferramenta.status_efetivo
        context['status_efetivo_display'] = dict(Ferramenta.Status.choices).get(ferramenta.status_efetivo)
        
        context['movimentacoes'] = ferramenta.movimentacoes.all()
        context['atividades'] = ferramenta.atividades.all()[:20]
        context['movimentacao_ativa'] = next((m for m in context['movimentacoes'] if m.esta_ativa), None)
        
        six_months_ago = timezone.now() - timedelta(days=180)
        usage_data = (
            Movimentacao.objects.filter(ferramenta=ferramenta, data_retirada__gte=six_months_ago)
            .annotate(month=TruncMonth('data_retirada')).values('month')
            .annotate(count=Count('id')).order_by('month')
        )
        context['chart_labels'] = json.dumps([d['month'].strftime('%b/%Y') for d in usage_data])
        context['chart_data'] = json.dumps([d['count'] for d in usage_data])
        context['titulo_pagina'] = f"Painel de Controle: {ferramenta.nome}"
        return context

class FerramentaCreateView(LoginRequiredMixin, AtividadeLogMixin, CreateView):
    model = Ferramenta
    form_class = FerramentaForm
    template_name = 'ferramentas/ferramenta_form.html'

    def form_valid(self, form):
        if self.request.user.is_superuser and self.request.session.get('active_filial_id'):
            form.instance.filial_id = self.request.session.get('active_filial_id')
        else:
            form.instance.filial = self.request.user.filial_ativa
        
        messages.success(self.request, "Ferramenta adicionada com sucesso.")
        response = super().form_valid(form) 
        self._log_atividade(
            ferramenta=self.object, 
            tipo=Atividade.TipoAtividade.CRIACAO, 
            descricao=f"Ferramenta '{self.object.nome}' registrada."
        )
        return response

    def get_success_url(self):
        return self.object.get_absolute_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = "Adicionar Nova Ferramenta"
        return context

class FerramentaUpdateView(LoginRequiredMixin, ViewFilialScopedMixin, AtividadeLogMixin, UpdateView):
    model = Ferramenta
    form_class = FerramentaForm
    template_name = 'ferramentas/ferramenta_form.html'
    
    def form_valid(self, form):
        messages.success(self.request, "Dados da ferramenta atualizados com sucesso.")
        response = super().form_valid(form)
        self._log_atividade(
            ferramenta=self.object, 
            tipo=Atividade.TipoAtividade.ALTERACAO, 
            descricao="Dados da ferramenta foram atualizados."
        )
        return response

    def get_success_url(self):
        return self.object.get_absolute_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f"Editar: {self.object.nome}"
        return context
    
# =============================================================================
# == NOVAS VIEWS PARA MALAS DE FERRAMENTAS
# =============================================================================

class MalaListView(LoginRequiredMixin, ViewFilialScopedMixin, ListView):
    model = MalaFerramentas
    template_name = 'ferramentas/mala_list.html'
    context_object_name = 'malas'
    # Adicionamos annotate para contar os itens
    queryset = MalaFerramentas.objects.annotate(
        item_count=Count('itens')
    ).prefetch_related('itens').order_by('nome')

class MalaDetailView(LoginRequiredMixin, ViewFilialScopedMixin, DetailView):
    model = MalaFerramentas
    template_name = 'ferramentas/mala_detail.html' # CRIAR ESTE TEMPLATE
    context_object_name = 'mala'
    
    def get_queryset(self):
        return super().get_queryset().prefetch_related('movimentacoes__retirado_por', 'atividades__usuario', 'itens')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        mala = self.object
        context['movimentacoes'] = mala.movimentacoes.all()
        context['atividades'] = mala.atividades.all()[:20]
        context['movimentacao_ativa'] = next((m for m in context['movimentacoes'] if m.esta_ativa), None)
        context['titulo_pagina'] = f"Painel de Controle: {mala.nome}"
        return context

class MalaCreateView(LoginRequiredMixin, AtividadeLogMixin, CreateView):
    model = MalaFerramentas
    form_class = MalaFerramentasForm # CRIAR ESTE FORM
    template_name = 'ferramentas/mala_form.html' # CRIAR ESTE TEMPLATE

    def form_valid(self, form):
        if self.request.user.is_superuser and self.request.session.get('active_filial_id'):
            form.instance.filial_id = self.request.session.get('active_filial_id')
        else:
            form.instance.filial = self.request.user.filial_ativa
        
        response = super().form_valid(form)
        self._log_atividade(
            mala=self.object,
            tipo=Atividade.TipoAtividade.CRIACAO,
            descricao=f"Mala '{self.object.nome}' registrada."
        )
        messages.success(self.request, "Mala de ferramentas criada com sucesso.")
        return response

    def get_success_url(self):
        return self.object.get_absolute_url()

class MalaUpdateView(LoginRequiredMixin, ViewFilialScopedMixin, AtividadeLogMixin, UpdateView):
    model = MalaFerramentas
    form_class = MalaFerramentasForm
    template_name = 'ferramentas/mala_form.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        self._log_atividade(
            mala=self.object,
            tipo=Atividade.TipoAtividade.ALTERACAO,
            descricao=f"Dados da mala '{self.object.nome}' foram atualizados."
        )
        messages.success(self.request, "Dados da mala atualizados com sucesso.")
        return response

    def get_success_url(self):
        return self.object.get_absolute_url()

# =============================================================================
# == VIEWS DE AÇÕES (Retirada, Devolução, Manutenção, etc.)
# =============================================================================

class AcaoFerramentaBaseView(LoginRequiredMixin, AtividadeLogMixin, View):
    """ View base para ações POST. Agora usa .for_request(). """
    def get_ferramenta(self):
        # CORREÇÃO: Usa .for_request() para segurança
        qs = Ferramenta.objects.for_request(self.request)
        return get_object_or_404(qs, pk=self.kwargs['pk'])

class IniciarManutencaoView(AcaoFerramentaBaseView):
    def post(self, request, *args, **kwargs):
        ferramenta = self.get_ferramenta()
        if ferramenta.status == Ferramenta.Status.DISPONIVEL:
            ferramenta.status = Ferramenta.Status.EM_MANUTENCAO
            ferramenta.save()
            self._log_atividade(ferramenta, Atividade.TipoAtividade.MANUTENCAO_INICIO, "Parada para manutenção iniciada.")
            messages.success(request, f"'{ferramenta.nome}' foi colocada em manutenção.")
        else:
            messages.error(request, "Ação não permitida. A ferramenta precisa estar 'Disponível'.")
        return redirect(ferramenta.get_absolute_url())

class FinalizarManutencaoView(AcaoFerramentaBaseView):
    def post(self, request, *args, **kwargs):
        ferramenta = self.get_ferramenta()
        if ferramenta.status == Ferramenta.Status.EM_MANUTENCAO:
            ferramenta.status = Ferramenta.Status.DISPONIVEL
            ferramenta.save()
            self._log_atividade(ferramenta, Atividade.TipoAtividade.MANUTENCAO_FIM, "Manutenção finalizada.")
            messages.success(request, f"A manutenção de '{ferramenta.nome}' foi finalizada.")
        else:
            messages.error(request, "Ação não permitida. A ferramenta precisa estar 'Em Manutenção'.")
        return redirect(ferramenta.get_absolute_url())

class InativarFerramentaView(AcaoFerramentaBaseView):
    def post(self, request, *args, **kwargs):
        ferramenta = self.get_ferramenta()
        if ferramenta.status == Ferramenta.Status.DISPONIVEL:
            ferramenta.status = Ferramenta.Status.DESCARTADA
            ferramenta.save()
            self._log_atividade(ferramenta, "Descarte", f"Ferramenta marcada como descartada/inativa.")
            messages.success(request, f"'{ferramenta.nome}' foi inativada com sucesso.")
            return redirect('ferramentas:ferramenta_list')
        else:
            messages.error(request, "Ação não permitida. A ferramenta precisa estar 'Disponível' para ser inativada.")
            return redirect(ferramenta.get_absolute_url())

# =============================================================================
# == VIEWS DE AÇÕES (Retirada, Devolução, etc.) - ATUALIZADO
# =============================================================================

class MovimentacaoCreateView(LoginRequiredMixin, AtividadeLogMixin, CreateView):
    model = Movimentacao
    form_class = MovimentacaoForm
    template_name = 'ferramentas/retirada_form.html'

    def dispatch(self, request, *args, **kwargs):
        """ Identifica se a retirada é de uma ferramenta ou de uma mala. """
        self.ferramenta = None
        self.mala = None
        
        if 'ferramenta_pk' in self.kwargs:
            qs = Ferramenta.objects.for_request(self.request)
            self.ferramenta = get_object_or_404(qs, pk=self.kwargs['ferramenta_pk'])
        elif 'mala_pk' in self.kwargs:
            qs = MalaFerramentas.objects.for_request(self.request)
            self.mala = get_object_or_404(qs, pk=self.kwargs['mala_pk'])
        
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """ Passa a ferramenta ou a mala para o formulário. """
        kwargs = super().get_form_kwargs()
        kwargs['ferramenta'] = self.ferramenta
        kwargs['mala'] = self.mala
        return kwargs

    def get_context_data(self, **kwargs):
        """ Adiciona o item (ferramenta ou mala) ao contexto do template. """
        context = super().get_context_data(**kwargs)
        context['item'] = self.ferramenta or self.mala
        context['titulo_pagina'] = f"Checklist de Retirada: {context['item'].nome}"
        return context

    @transaction.atomic
    def form_valid(self, form):
        # 1. Define o item (ferramenta ou mala) e verifica sua disponibilidade
        item = self.ferramenta or self.mala
        if item.status != 'disponivel':
            messages.error(self.request, f"'{item.nome}' não está disponível para retirada.")
            return redirect(item.get_absolute_url())

        # 2. Prepara o objeto de movimentação sem salvar no banco ainda
        movimentacao = form.save(commit=False)
        movimentacao.filial = self.request.user.filial_ativa

        # 3. Processa e anexa a assinatura digital
        assinatura_data = form.cleaned_data.get('assinatura_base64')
        if assinatura_data:
            format, imgstr = assinatura_data.split(';base64,')
            ext = format.split('/')[-1]
            file_name = f'sig_ret_{item.pk}_{timezone.now().timestamp()}.{ext}'
            movimentacao.assinatura_retirada = ContentFile(base64.b64decode(imgstr), name=file_name)

        # 4. Salva a movimentação no banco de dados
        movimentacao.save()
        
        # 5. Atualiza o status do item retirado
        item.status = 'em_uso'
        item.save(update_fields=['status'])

        # 6. Cria a mensagem de log e chama a função de log refatorada
        log_message = f"Retirada por {movimentacao.retirado_por.get_username()}."
        self._log_atividade(
            tipo=Atividade.TipoAtividade.RETIRADA,
            descricao=log_message,
            ferramenta=self.ferramenta,  # Será o objeto Ferramenta ou None
            mala=self.mala               # Será o objeto Mala ou None
        )
        
        # 7. Informa o usuário do sucesso e o redireciona
        messages.success(self.request, f"'{item.nome}' retirada com sucesso.")
        return redirect(item.get_absolute_url())

class DevolucaoUpdateView(LoginRequiredMixin, AtividadeLogMixin, UpdateView):
    model = Movimentacao
    form_class = DevolucaoForm
    template_name = 'ferramentas/devolucao_form.html'
    context_object_name = 'movimentacao'
    
    def get_queryset(self):
        # Garante que só pegamos devoluções de ferramentas individuais
        return Movimentacao.objects.for_request(self.request).filter(ferramenta__isnull=False)

    @transaction.atomic
    def form_valid(self, form):
        movimentacao = form.save(commit=False)
        movimentacao.data_devolucao = timezone.now()
        movimentacao.recebido_por = self.request.user
        # ... processamento de assinatura ...
        movimentacao.save()
        
        ferramenta = movimentacao.ferramenta
        ferramenta.status = Ferramenta.Status.DISPONIVEL
        ferramenta.save(update_fields=['status'])

        self._log_atividade(
            ferramenta=ferramenta,
            tipo=Atividade.TipoAtividade.DEVOLUCAO,
            descricao=f"Devolvida. Responsável pela retirada: {movimentacao.retirado_por.get_username()}."
        )
        messages.success(self.request, f"'{ferramenta.nome}' devolvida com sucesso.")
        return redirect(self.get_success_url())
    
    def get_success_url(self):
        return self.object.ferramenta.get_absolute_url()

# =============================================================================
# == NOVAS VIEWS DE AÇÃO PARA MALAS
# =============================================================================

class MalaRetiradaCreateView(LoginRequiredMixin, AtividadeLogMixin, CreateView):
    model = Movimentacao
    form_class = MovimentacaoForm 
    template_name = 'ferramentas/mala_retirada_form.html' # CRIAR TEMPLATE

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = MalaFerramentas.objects.for_request(self.request)
        context['mala'] = get_object_or_404(qs, pk=self.kwargs['mala_pk'])
        context['titulo_pagina'] = f"Retirar Mala: {context['mala'].nome}"
        return context

    @transaction.atomic
    def form_valid(self, form):
        qs = MalaFerramentas.objects.for_request(self.request)
        mala = get_object_or_404(qs, pk=self.kwargs['mala_pk'])

        if mala.status != MalaFerramentas.Status.DISPONIVEL:
            messages.error(self.request, "Esta mala não está disponível para retirada.")
            return redirect(mala.get_absolute_url())

        movimentacao = form.save(commit=False)
        movimentacao.mala = mala
        movimentacao.filial = self.request.user.filial_ativa
        # ... processamento de assinatura ...
        movimentacao.save()
        
        # LÓGICA DE ATUALIZAÇÃO EM MASSA
        mala.status = MalaFerramentas.Status.EM_USO
        mala.save(update_fields=['status'])
        mala.itens.all().update(status=Ferramenta.Status.EM_USO)

        self._log_atividade(
            mala=mala,
            tipo=Atividade.TipoAtividade.RETIRADA,
            descricao=f"Retirada por {movimentacao.retirado_por.get_username()}."
        )
        messages.success(self.request, f"Mala '{mala.nome}' retirada com sucesso.")
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy('ferramentas:mala_detail', kwargs={'pk': self.kwargs['mala_pk']})

class MalaDevolucaoUpdateView(LoginRequiredMixin, AtividadeLogMixin, UpdateView):
    model = Movimentacao
    form_class = DevolucaoForm # Pode reutilizar
    template_name = 'ferramentas/mala_devolucao_form.html' # CRIAR TEMPLATE
    context_object_name = 'movimentacao'

    def get_queryset(self):
        return Movimentacao.objects.for_request(self.request).filter(mala__isnull=False)

    @transaction.atomic
    def form_valid(self, form):
        movimentacao = form.save(commit=False)
        movimentacao.data_devolucao = timezone.now()
        movimentacao.recebido_por = self.request.user
        # ... processamento de assinatura ...
        movimentacao.save()
        
        mala = movimentacao.mala
        mala.status = MalaFerramentas.Status.DISPONIVEL
        mala.save(update_fields=['status'])
        # Apenas ferramentas que não estão em manutenção podem voltar a ficar disponíveis
        mala.itens.exclude(status=Ferramenta.Status.EM_MANUTENCAO).update(status=Ferramenta.Status.DISPONIVEL)

        self._log_atividade(
            mala=mala,
            tipo=Atividade.TipoAtividade.DEVOLUCAO,
            descricao=f"Devolvida. Responsável: {movimentacao.retirado_por.get_username()}."
        )
        messages.success(self.request, f"Mala '{mala.nome}' devolvida com sucesso.")
        return redirect(self.get_success_url())

    def get_success_url(self):
        return self.object.mala.get_absolute_url()

class DownloadTemplateView(LoginRequiredMixin, View):
    """
    Gera e oferece para download a planilha modelo formatada para o usuário preencher.
    """
    def get(self, request, *args, **kwargs):
        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.title = "Modelo de Importação"
        # --- Estilos do Cabeçalho ---
        header_font = Font(name='Calibri', bold=True, color='FFFFFF', size=12)
        header_fill = PatternFill(start_color='004C99', end_color='004C99', fill_type='solid') # Tom de azul escuro
        header_alignment = Alignment(horizontal='center', vertical='center')
        thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        # --- Cabeçalhos das Colunas ---
        headers = [
            "Nome da Ferramenta*",
            "Código de Identificação* (para QR Code)",
            "Data de Aquisição (dd/mm/aaaa)*",
            "Localização Padrão*",
            "Nº de Patrimônio",
            "Fabricante",
            "Modelo",
            "Série",
            "Tamanho da Polegada",
            'Numero Laudo técnico',
            'Mala',
            "Filial",
            "Observações", 
        ]
        
        # Aplica os cabeçalhos e estilos
        for col_num, header_title in enumerate(headers, 1):
            cell = worksheet.cell(row=1, column=col_num)
            cell.value = header_title
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border
            # Ajusta a largura da coluna
            column_letter = get_column_letter(col_num)
            worksheet.column_dimensions[column_letter].width = 30

        # --- Instruções e Exemplo ---
        instructions = [
            [], # Linha em branco
            ["Instruções:"],
            ["1. Preencha as colunas com os dados das ferramentas. Campos com * são obrigatórios."],
            ["2. O 'Código de Identificação' deve ser único para cada ferramenta (ex: PAT123-FURADEIRA). É este código que será usado para gerar o QR Code."],
            ["3. A data de aquisição deve estar no formato Dia/Mês/Ano (ex: 21/09/2025)."],
            [],
            ["Exemplo de preenchimento:"]
        ]
        for row_data in instructions:
            worksheet.append(row_data)

        # Adiciona uma linha de exemplo
        example_row = ["Furadeira de Impacto", "87521-FURADEIRA", "01/09/2025", "Almolxarifado", "87521",
                       "DeWalt", "DCD777", "1/2", "LAUDO-001", "mala", "CETEST-SP" 
                       "Ferramenta volante",
        ]
        worksheet.append(example_row)

        # Prepara a resposta HTTP para o download
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = 'attachment; filename="modelo_importacao_ferramentas.xlsx"'
        workbook.save(response)
        return response

class ImportarFerramentasView(LoginRequiredMixin, FormView):
    """
    View que renderiza a página de upload e processa a planilha enviada.
    Versão final corrigida para garantir a leitura de todas as colunas.
    """
    template_name = 'ferramentas/importar_ferramentas.html'
    form_class = UploadFileForm
    success_url = reverse_lazy('ferramentas:ferramenta_list')

    def form_valid(self, form):
        file = form.cleaned_data['file']
        active_filial_id = self.request.session.get('active_filial_id')

        if not active_filial_id:
            messages.error(self.request, "Nenhuma filial ativa selecionada. Por favor, selecione uma filial antes de importar.")
            return self.form_invalid(form)

        try:
            workbook = openpyxl.load_workbook(file)
            worksheet = workbook.active
            ferramentas_para_criar, erros = [], []
            codigos_ja_processados = set()

            # --- LINHA CORRIGIDA AQUI ---
            # Adicionamos max_col=13 para forçar a leitura de todas as 13 colunas
            for i, row in enumerate(worksheet.iter_rows(min_row=2, max_col=13, values_only=True), start=2):
                if all(cell is None for cell in row):
                    continue  # Pula linhas totalmente em branco

                # Como agora garantimos 13 colunas, a verificação len(row) < 13 não é mais necessária.
                
                # Descompacta todas as 13 colunas da planilha
                (
                    nome, codigo, data_str, localizacao, patrimonio,
                    fabricante, modelo, serie, tamanho, laudo,
                    mala_nome, filial_nome, observacoes
                ) = row

                # Validações dos campos obrigatórios
                if not all([nome, codigo, data_str, localizacao]):
                    erros.append(f"Linha {i}: Dados obrigatórios faltando (Nome, Código, Data ou Localização).")
                    continue
                
                # Validação para códigos duplicados na mesma planilha
                codigo = str(codigo).strip() # Limpa espaços em branco
                if codigo in codigos_ja_processados:
                    erros.append(f"Linha {i}: O Código de Identificação '{codigo}' está duplicado na planilha.")
                    continue
                
                # Validação de data
                try:
                    if isinstance(data_str, datetime):
                        data_aquisicao = data_str.date()
                    else:
                        data_aquisicao = datetime.strptime(str(data_str).split(" ")[0], '%d/%m/%Y').date()
                except (ValueError, TypeError):
                    erros.append(f"Linha {i}: Formato de data inválido para '{data_str}'. Use dd/mm/aaaa.")
                    continue

                # Validação de existência do código no banco de dados
                if Ferramenta.objects.filter(codigo_identificacao=codigo).exists():
                    erros.append(f"Linha {i}: Código de Identificação '{codigo}' já existe no sistema.")
                    continue
                
                # Busca a Filial pelo nome (se fornecido)
                filial_obj = None
                if filial_nome:
                    try:
                        filial_obj = Filial.objects.get(nome__iexact=str(filial_nome).strip())
                    except Filial.DoesNotExist:
                        erros.append(f"Linha {i}: A filial '{filial_nome}' não foi encontrada no sistema.")
                        continue
                else:
                    filial_obj = Filial.objects.get(pk=active_filial_id)

                # Busca a Mala pelo nome (se fornecida)
                mala_obj = None
                if mala_nome:
                    try:
                        mala_obj = MalaFerramentas.objects.get(nome__iexact=str(mala_nome).strip(), filial=filial_obj)
                    except MalaFerramentas.DoesNotExist:
                        erros.append(f"Linha {i}: A mala '{mala_nome}' não foi encontrada na filial '{filial_obj.nome}'.")
                        continue

                ferramentas_para_criar.append(Ferramenta(
                    nome=nome,
                    codigo_identificacao=codigo.upper(),
                    data_aquisicao=data_aquisicao,
                    localizacao_padrao=localizacao,
                    patrimonio=(patrimonio or None),
                    fabricante_marca=(fabricante or None),
                    modelo=(modelo or None),
                    serie=(serie or None),
                    tamanho_polegadas=(tamanho or None),
                    numero_laudo_tecnico=(laudo or None),
                    mala=mala_obj,
                    filial=filial_obj,
                    observacoes=(observacoes or None)
                ))
                codigos_ja_processados.add(codigo)

            if erros:
                for erro in erros:
                    messages.error(self.request, erro)
                return self.form_invalid(form)

            with transaction.atomic():
                Ferramenta.objects.bulk_create(ferramentas_para_criar)

            messages.success(self.request, f"{len(ferramentas_para_criar)} ferramentas importadas com sucesso!")
        except Exception as e:
            messages.error(self.request, f"Ocorreu um erro inesperado ao processar o arquivo: {e}")
            return self.form_invalid(form)

        return super().form_valid(form)
    
class ImprimirQRCodesView(LoginRequiredMixin, ViewFilialScopedMixin, ListView):
    model = Ferramenta
    template_name = 'ferramentas/imprimir_qrcodes.html'
    context_object_name = 'ferramentas'

    def get_queryset(self):
        # Pega apenas ferramentas da filial ativa que não foram descartadas e que possuem QR Code
        return super().get_queryset().exclude(
            status=Ferramenta.Status.DESCARTADA
        ).filter(
            qr_code__isnull=False
        ).exclude(
            qr_code=''
        ).order_by('nome')

class ResultadoScanView(LoginRequiredMixin, DetailView):
    model = Ferramenta
    template_name = 'ferramentas/resultado_scan.html'
    context_object_name = 'ferramenta'
    # Informa à DetailView para buscar pelo campo 'codigo_identificacao' em vez do 'pk'
    slug_field = 'codigo_identificacao'
    slug_url_kwarg = 'codigo_identificacao'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ferramenta = self.object
        # Pega a última movimentação ativa, se houver
        context['movimentacao_ativa'] = ferramenta.movimentacoes.filter(esta_ativa=True).first()
        return context
    
# View para o usuário com permissão gerar os QR coldes

class GerarQRCodesView(LoginRequiredMixin, SSTPermissionMixin, View):
    """
    Aciona o comando de gerenciamento `generate_qrcodes` em segundo plano,
    agora protegido pelo SSTPermissionMixin.
    """
    # Define a permissão específica necessária para acessar esta view.
    # Um usuário precisa ter a permissão "Can change ferramenta" para continuar.
    permission_required = 'ferramentas.change_ferramenta'

    # O método test_func() não é mais necessário, pode ser removido.

    def post(self, request, *args, **kwargs):
        command = [
            sys.executable,
            str(settings.BASE_DIR / "manage.py"),
            "generate_qrcodes",
        ]
        
        subprocess.Popen(command)

        messages.success(
            request, 
            "A geração de QR Codes foi iniciada em segundo plano. Os novos QR Codes aparecerão na lista em breve."
        )

        return redirect('ferramentas:ferramenta_list')
    
    