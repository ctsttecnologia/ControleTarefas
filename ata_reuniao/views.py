
# ata_reuniao/views.py

import csv
import io
import json
from typing import Any
from django.shortcuts import get_object_or_404, redirect
import openpyxl
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count, F
from django.http import HttpRequest, HttpResponse
from django.template.loader import get_template
from django.urls import reverse_lazy
from django.utils import timezone  
from django.views.generic import (CreateView, DeleteView, ListView, TemplateView, UpdateView, View, DetailView)
from openpyxl.styles import Font 
from xhtml2pdf import pisa
from cliente.models import Cliente
from core.mixins import ViewFilialScopedMixin
from .forms import AtaReuniaoForm, HistoricoAtaForm
from .models import AtaReuniao, HistoricoAta


User = get_user_model()


# --- Mixins (sem alterações) ---

class AtaReuniaoBaseMixin(LoginRequiredMixin, ViewFilialScopedMixin):
    model = AtaReuniao
    form_class = AtaReuniaoForm
    # Corrigido o argumento de reverse_lazy
    success_url = reverse_lazy('ata_reuniao:ata_reuniao_list')


class FilteredAtaReuniaoMixin:
    def get_filtered_queryset(self, request: HttpRequest):
        queryset = AtaReuniao.objects.for_request(request)
        filtros = {
            'contrato_id': request.GET.get('contrato'),
            'status': request.GET.get('status'),
            'coordenador_id': request.GET.get('coordenador'),
        }
        filtros_validos = {k: v for k, v in filtros.items() if v}
        if filtros_validos:
            queryset = queryset.filter(**filtros_validos)
        return queryset.select_related('contrato', 'coordenador', 'responsavel').order_by('-entrada')


# --- Views de CRUD ---

class AtaReuniaoListView(LoginRequiredMixin, FilteredAtaReuniaoMixin, ListView):
    model = AtaReuniao
    template_name = 'ata_reuniao/ata_reuniao_list.html'
    context_object_name = 'atas'
    paginate_by = 20

    def get_queryset(self):
        return self.get_filtered_queryset(self.request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Otimização da busca da queryset sem paginação
        # object_list já contém a queryset filtrada, não precisa chamar get_queryset() de novo.
        queryset_sem_paginacao = self.object_list

        coordenador_ids = queryset_sem_paginacao.values_list('coordenador_id', flat=True).distinct()
        context['coordenadores'] = User.objects.filter(id__in=coordenador_ids).order_by('first_name')

        contrato_ids = queryset_sem_paginacao.values_list('contrato_id', flat=True).distinct()
        context['contratos'] = Cliente.objects.filter(id__in=contrato_ids).order_by('nome')

        context['current_contrato'] = self.request.GET.get('contrato', '')
        context['current_status'] = self.request.GET.get('status', '')
        context['current_coordenador'] = self.request.GET.get('coordenador', '')
        return context

# Simplificadas as views Create e Update
class AtaReuniaoCreateView(AtaReuniaoBaseMixin, SuccessMessageMixin, CreateView):
    template_name = 'ata_reuniao/ata_form.html'
    success_message = "✅ Ata de reunião criada com sucesso!"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs


class AtaReuniaoUpdateView(AtaReuniaoBaseMixin, SuccessMessageMixin, UpdateView):
    template_name = 'ata_reuniao/ata_form.html'
    success_message = "🔄 Ata de reunião atualizada com sucesso!"
    # Removido success_url redundante (já está no mixin)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        comentario_texto = form.cleaned_data.get('comentario')
        if comentario_texto:
            HistoricoAta.objects.create(
                ata=self.object,
                usuario=self.request.user,
                comentario=comentario_texto
            )
        return response

class AtaReuniaoDetailView(AtaReuniaoBaseMixin, DetailView):
    """
    Exibe os detalhes de uma Ata de Reunião específica, incluindo seu histórico.
    """
    template_name = 'ata_reuniao/ata_reuniao_detail.html'
    context_object_name = 'ata'  # Usaremos 'ata' no template para clareza

    def get_queryset(self):
        """
        Otimiza a consulta para buscar a ata e todo o seu histórico relacionado
        (incluindo o usuário de cada entrada do histórico) em apenas duas queries.
        """
        # Chama a queryset base do mixin, que já filtra por filial
        queryset = super().get_queryset()
        return queryset.prefetch_related('historico__usuario')
    

# Adicione esta nova view ao final do arquivo
class AtaReuniaoAddCommentView(LoginRequiredMixin, View):
    """
    View dedicada para lidar com a adição de comentários via POST.
    """
    def post(self, request, pk):
        # Garante que a ata existe e pertence à filial do usuário
        ata = get_object_or_404(AtaReuniao.objects.for_request(request), pk=pk)
        
        form = HistoricoAtaForm(request.POST)

        if form.is_valid():
            comentario = form.save(commit=False)
            comentario.ata = ata
            comentario.usuario = request.user
            comentario.save()
            messages.success(request, "✅ Comentário adicionado com sucesso!")
        else:
            # Se houver um erro no formulário, exibe uma mensagem
            messages.error(request, "Ocorreu um erro ao adicionar o comentário.")

        # Redireciona de volta para a página de detalhes da ata
        return redirect('ata_reuniao:ata_reuniao_detail', pk=ata.pk)


class AtaReuniaoDeleteView(AtaReuniaoBaseMixin, SuccessMessageMixin, DeleteView):
    template_name = 'ata_reuniao/ata_confirm_delete.html'
    success_message = "🗑️ Ata de reunião excluída com sucesso!"

    # Simplificada a lógica de mensagem (usando o padrão do mixin)
    def form_valid(self, form):
        messages.success(self.request, self.success_message)
        return super().form_valid(form)
# ata_reuniao/views.py

# ... (suas importações existentes)
import json
from django.db.models import Count, F
# ...

# --- View do Dashboard (COM IMPLEMENTAÇÕES) ---
class AtaReuniaoDashboardView(LoginRequiredMixin, TemplateView):
    """
    Exibe os indicadores de performance e o quadro Kanban,
    com todos os dados filtrados pela filial ativa do usuário.
    """
    template_name = 'ata_reuniao/ata_reuniao_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        base_queryset = AtaReuniao.objects.for_request(self.request)
        
        # --- 1. CÁLCULO DOS INDICADORES (KPIs) PARA OS CARDS ---
        concluidas_qs = base_queryset.filter(status=AtaReuniao.Status.CONCLUIDO)
        pendentes_qs = base_queryset.exclude(status__in=[AtaReuniao.Status.CONCLUIDO, AtaReuniao.Status.CANCELADO])

        total_concluido = concluidas_qs.count()
        total_cancelado = base_queryset.filter(status=AtaReuniao.Status.CANCELADO).count()
        total_pendente = pendentes_qs.count()
        
        concluido_no_prazo = concluidas_qs.filter(prazo__isnull=False, atualizado_em__date__lte=F('prazo')).count()
        concluido_com_atraso = concluidas_qs.filter(prazo__isnull=False, atualizado_em__date__gt=F('prazo')).count()

        # Cálculo de porcentagens com segurança (evita divisão por zero)
        if total_concluido > 0:
            percentual_no_prazo = (concluido_no_prazo / total_concluido) * 100
            percentual_com_atraso = (concluido_com_atraso / total_concluido) * 100
        else:
            percentual_no_prazo = 0
            percentual_com_atraso = 0

        # --- 2. DADOS PARA OS GRÁFICOS ---
        # Gráfico 1: Pendências por Responsável
        pendencias_por_responsavel = pendentes_qs.values('responsavel__nome_completo').annotate(count=Count('id')).order_by('-count')
        
        # Gráfico 2: Qualidade das Atividades Concluídas (já estava correto)
        qualidade_data = [concluido_no_prazo, concluido_com_atraso]

        # --- 3. DADOS PARA O QUADRO KANBAN ---
        tasks = base_queryset.select_related('responsavel', 'contrato', 'filial').order_by('prazo')
        kanban_columns = {label: [] for _, label in AtaReuniao.Status.choices}
        for task in tasks:
            kanban_columns[task.get_status_display()].append(task)
        
        colunas_ordenadas = [s.label for s in AtaReuniao.Status]
        kanban_ordenado = {label: kanban_columns[label] for label in colunas_ordenadas}

        # --- 4. ATUALIZAÇÃO DO CONTEXTO ---
        context.update({
            'titulo_pagina': 'Dashboard de Atas',
            # KPIs para os Cards
            'total_concluido': total_concluido,
            'total_cancelado': total_cancelado,
            'total_pendente': total_pendente,
            'concluido_no_prazo': concluido_no_prazo,
            'concluido_com_atraso': concluido_com_atraso,
            'percentual_no_prazo': percentual_no_prazo,
            'percentual_com_atraso': percentual_com_atraso,
            # Dados para Gráficos
            'pendencias_labels': json.dumps([item['responsavel__nome_completo'] for item in pendencias_por_responsavel]),
            'pendencias_data': json.dumps([item['count'] for item in pendencias_por_responsavel]),
            'qualidade_labels': json.dumps(['No Prazo', 'Com Atraso']),
            'qualidade_data': json.dumps(qualidade_data),
            # Itens para o Kanban
            'kanban_items': kanban_ordenado,
        })
        return context

# --- Mixin de Filtro (COM FILTRO DE DATA) ---
class FilteredAtaReuniaoMixin:
    def get_filtered_queryset(self, request: HttpRequest):
        queryset = AtaReuniao.objects.for_request(request) # Passa o request para o manager

        # Filtros de status, contrato, etc.
        filtros = {
            'contrato_id': request.GET.get('contrato'),
            'status': request.GET.get('status'),
            'coordenador_id': request.GET.get('coordenador'),
        }
        filtros_validos = {k: v for k, v in filtros.items() if v}
        if filtros_validos:
            queryset = queryset.filter(**filtros_validos)
            
        # --- NOVO: FILTRO POR INTERVALO DE DATAS ---
        data_inicio = request.GET.get('data_inicio')
        data_fim = request.GET.get('data_fim')
        if data_inicio and data_fim:
            # Filtra pela data de 'entrada' da ata
            queryset = queryset.filter(entrada__range=[data_inicio, data_fim])

        return queryset.select_related('contrato', 'coordenador', 'responsavel', 'filial').order_by('-entrada')


# --- Views de Exportação (ATUALIZADAS) ---
class AtaReuniaoPDFExportView(LoginRequiredMixin, FilteredAtaReuniaoMixin, View):
    """
    Exporta a lista de atas para PDF, respeitando filtros de status e DATA.
    """
    def get(self, request, *args, **kwargs):
        atas = self.get_filtered_queryset(request)
        
        # --- NOVO: Adiciona o período do relatório ao contexto ---
        periodo_relatorio = "Período: Todas as datas"
        data_inicio = request.GET.get('data_inicio')
        data_fim = request.GET.get('data_fim')
        if data_inicio and data_fim:
            data_inicio_fmt = timezone.datetime.strptime(data_inicio, '%Y-%m-%d').strftime('%d/%m/%Y')
            data_fim_fmt = timezone.datetime.strptime(data_fim, '%Y-%m-%d').strftime('%d/%m/%Y')
            periodo_relatorio = f"Período: {data_inicio_fmt} a {data_fim_fmt}"

        template = get_template('ata_reuniao/ata_pdf.html')
        context = {
            'atas': atas,
            'data_exportacao': timezone.now(),
            'usuario_exportacao': request.user.get_full_name(),
            'periodo_relatorio': periodo_relatorio, # Passa para o template
        }
        html = template.render(context)
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="relatorio_atas.pdf"'
        
        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            messages.error(request, "Ocorreu um erro ao gerar o PDF.")
            return HttpResponse('Erro ao gerar PDF', status=500)
            
        return response


# ata_reuniao/views.py

# ... (suas outras views e importações) ...

class AtaReuniaoExcelExportView(LoginRequiredMixin, FilteredAtaReuniaoMixin, View):
    """
    Exporta a lista de atas para Excel, respeitando filtros de status e DATA
    e incluindo mais colunas para um relatório detalhado.
    """
    def get(self, request, *args, **kwargs):
        atas = self.get_filtered_queryset(request)
        buffer = io.BytesIO()
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Relatório de Atas"
        
        headers = [
            'ID', 'Título', 'Contrato', 'Coordenador', 'Responsável', 'Natureza', 
            'Ação', 'Entrada', 'Prazo', 'Status', 'Filial', 'Última Atualização'
        ]
        sheet.append(headers)
        
        for cell in sheet[1]:
            cell.font = Font(bold=True)
            
        for ata in atas:
            # Formata as datas para um formato legível
            entrada_fmt = ata.entrada.strftime('%d/%m/%Y') if ata.entrada else ''
            prazo_fmt = ata.prazo.strftime('%d/%m/%Y') if ata.prazo else ''
            atualizado_fmt = ata.atualizado_em.strftime('%d/%m/%Y %H:%M') if ata.atualizado_em else ''

            row_data = [
                ata.id,
                ata.titulo,
                ata.contrato.nome if ata.contrato else '',
                
                # Trocado de ata.coordenador.get_full_name() para ata.coordenador.nome_completo
                ata.coordenador.nome_completo if ata.coordenador else '',
                
                ata.responsavel.nome_completo if ata.responsavel else '',
                ata.get_natureza_display(),
                ata.acao,
                entrada_fmt,
                prazo_fmt,
                ata.get_status_display(),
                ata.filial.nome if ata.filial else '',
                atualizado_fmt,
            ]
            sheet.append(row_data)
            
        for column_cells in sheet.columns:
            length = max(len(str(cell.value) or "") for cell in column_cells)
            sheet.column_dimensions[column_cells[0].column_letter].width = length + 2
            
        workbook.save(buffer)
        buffer.seek(0)
        
        response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        filename = f'relatorio_atas_{timezone.now().strftime("%Y-%m-%d")}.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    
