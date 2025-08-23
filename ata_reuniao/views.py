
# ata_reuniao/views.py

import csv
import io
import json
from typing import Any

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
from django.views.generic import (CreateView, DeleteView, ListView,
                                  TemplateView, UpdateView, View, DetailView)
from openpyxl.styles import Font 
from xhtml2pdf import pisa

from cliente.models import Cliente
from core.mixins import ViewFilialScopedMixin

from .forms import AtaReuniaoForm
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

class AtaReuniaoDeleteView(AtaReuniaoBaseMixin, SuccessMessageMixin, DeleteView):
    template_name = 'ata_reuniao/ata_confirm_delete.html'
    success_message = "🗑️ Ata de reunião excluída com sucesso!"

    # Simplificada a lógica de mensagem (usando o padrão do mixin)
    def form_valid(self, form):
        messages.success(self.request, self.success_message)
        return super().form_valid(form)

# --- View do Dashboard (sem alterações significativas, já está boa) ---
class AtaReuniaoDashboardView(LoginRequiredMixin, TemplateView):
    """
    Exibe os indicadores de performance e o quadro Kanban,
    com todos os dados filtrados pela filial ativa do usuário.
    """
    template_name = 'ata_reuniao/ata_reuniao_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # PONTO CHAVE: Começa com a queryset já filtrada pela filial do usuário
        base_queryset = AtaReuniao.objects.for_request(self.request)
        
        # Indicador 1: Pendências por Responsável
        pendencias_queryset = base_queryset.exclude(
            status__in=[AtaReuniao.Status.CONCLUIDO, AtaReuniao.Status.CANCELADO]
        ).values('responsavel__nome_completo').annotate(count=Count('id')).order_by('-count')
        
        # Indicador 2: Qualidade das Atividades Concluídas
        concluidas = base_queryset.filter(status=AtaReuniao.Status.CONCLUIDO)
        concluido_no_prazo = concluidas.filter(prazo__isnull=False, atualizado_em__date__lte=F('prazo')).count()
        concluido_com_atraso = concluidas.filter(prazo__isnull=False, atualizado_em__date__gt=F('prazo')).count()
        
        # Dados para o Quadro Kanban
        tasks = base_queryset.select_related('responsavel', 'contrato').order_by('prazo')
        kanban_columns = {label: [] for _, label in AtaReuniao.Status.choices}
        for task in tasks:
            kanban_columns[task.get_status_display()].append(task)
        
        colunas_ordenadas = [s.label for s in AtaReuniao.Status]
        kanban_ordenado = {label: kanban_columns[label] for label in colunas_ordenadas}

        context.update({
            'titulo_pagina': 'Dashboard de Atas',
            'pendencias_labels': json.dumps([item['responsavel__nome_completo'] for item in pendencias_queryset]),
            'pendencias_data': json.dumps([item['count'] for item in pendencias_queryset]),
            'qualidade_labels': json.dumps(['No Prazo', 'Com Atraso']),
            'qualidade_data': json.dumps([concluido_no_prazo, concluido_com_atraso]),
            'kanban_items': kanban_ordenado,
        })
        return context
    
# --- Views de Exportação ---
class AtaReuniaoPDFExportView(LoginRequiredMixin, FilteredAtaReuniaoMixin, View):
    """
    Exporta a lista de atas (respeitando os filtros aplicados) para um arquivo PDF.
    """
    def get(self, request, *args, **kwargs):
        # Usa a mesma lógica de filtro da ListView, garantindo consistência e segurança
        atas = self.get_filtered_queryset(request)
        
        template = get_template('ata_reuniao/ata_pdf.html')
        context = {
            'atas': atas,
            'data_exportacao': timezone.now(),
            'usuario_exportacao': request.user.get_full_name(),
        }
        html = template.render(context)
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="atas_reuniao.pdf"'
        
        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            messages.error(request, "Ocorreu um erro ao gerar o PDF.")
            return HttpResponse('Erro ao gerar PDF', status=500)
            
        return response


class AtaReuniaoExcelExportView(LoginRequiredMixin, FilteredAtaReuniaoMixin, View):
    def get(self, request, *args, **kwargs):
        atas = self.get_filtered_queryset(request)
        buffer = io.BytesIO()
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Atas de Reunião"
        headers = ['ID', 'Contrato', 'Coordenador', 'Responsável', 'Natureza', 'Ação', 'Entrada', 'Prazo', 'Status']
        sheet.append(headers)
        for cell in sheet[1]:
            cell.font = Font(bold=True)
        for ata in atas:
            row_data = [
                ata.id,
                ata.contrato.nome if ata.contrato else '',
                ata.coordenador.get_full_name() if ata.coordenador else '',
                ata.responsavel.nome_completo if ata.responsavel else '',
                ata.get_natureza_display(),
                ata.acao,
                ata.entrada,
                ata.prazo if ata.prazo else '',
                ata.get_status_display(),
            ]
            sheet.append(row_data)
        for column_cells in sheet.columns:
            length = max(len(str(cell.value) or "") for cell in column_cells)
            sheet.column_dimensions[column_cells[0].column_letter].width = length + 2
        workbook.save(buffer)
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        filename = f'atas_reuniao_{timezone.now().strftime("%Y-%m-%d")}.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
