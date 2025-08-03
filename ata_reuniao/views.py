# ata_reuniao/views.py

import csv
import json
from typing import Any
from django.db.models import Count, F, Q, QuerySet
from django.http import HttpRequest, HttpResponse
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.template.loader import get_template
from django.views.generic import (
    ListView, CreateView, UpdateView, DeleteView, TemplateView, View
)

from gerenciandoTarefas.settings import AUTH_USER_MODEL
from .models import AtaReuniao, HistoricoAta
from xhtml2pdf import pisa

from .forms import AtaReuniaoForm
from django.contrib.auth import get_user_model # Melhor forma de pegar o modelo User

User = get_user_model() # Carrega a classe do usuário


class FilialScopedMixin:
    """
    Mixin que automaticamente filtra a queryset principal de uma View
    pela filial do usuário logado. Garante a segregação de dados.
    """
    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_authenticated and hasattr(self.request.user, 'filial'):
            return qs.for_request(self.request)
        return qs.none() # Impede acesso a usuários sem filial ou não logados.

# --- Mixin Base para Evitar Repetição ---
class AtaReuniaoBaseMixin(LoginRequiredMixin):
    """
    Mixin que compartilha atributos comuns entre as views de CRUD de AtaReuniao.
    """
    model = AtaReuniao
    form_class = AtaReuniaoForm
    success_url = reverse_lazy('ata_reuniao_list')
    context_object_name = 'atas'


# --- Views de CRUD (List, Create, Update, Delete) ---

class AtaReuniaoListView(LoginRequiredMixin, FilialScopedMixin, ListView):
    model = AtaReuniao
    template_name = 'ata_reuniao/ata_reuniao_list.html'
    context_object_name = 'atas'
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        """
        Define os atributos de filtro a partir dos parâmetros GET.
        Usa nomes consistentes que serão usados em outros métodos.
        """
        # ✅ Padronizando os nomes dos atributos
        self.current_contrato = request.GET.get('contrato', '')
        self.current_status = request.GET.get('status', '')
        self.current_coordenador = request.GET.get('coordenador', '')
        
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """
        Usa os atributos consistentes definidos no dispatch() para filtrar.
        """
        queryset = super().get_queryset()

        # ✅ Usando os nomes padronizados para filtrar
        if self.current_contrato:
            queryset = queryset.filter(contrato_id=self.current_contrato)
        if self.current_status:
            queryset = queryset.filter(status=self.current_status)
        if self.current_coordenador:
            queryset = queryset.filter(coordenador_id=self.current_coordenador)

        return queryset.order_by('-entrada')

    def get_context_data(self, **kwargs):
        """
        Adiciona os filtros e outras informações ao contexto do template.
        """
        context = super().get_context_data(**kwargs)

        coordenador_ids = AtaReuniao.objects.order_by().values_list('coordenador_id', flat=True).distinct()
        context['coordenadores'] = User.objects.filter(id__in=coordenador_ids).order_by('first_name', 'last_name')
        
        ContratoModel = self.model._meta.get_field('contrato').related_model
        context['contratos'] = ContratoModel.objects.all().order_by('nome')
        
        # ✅ Passando os valores com os nomes corretos e consistentes para o template
        context['current_contrato'] = self.current_contrato
        context['current_status'] = self.current_status
        context['current_coordenador'] = self.current_coordenador

        return context

class AtaReuniaoCreateView(AtaReuniaoBaseMixin, FilialScopedMixin, SuccessMessageMixin, CreateView):
    """
    Cria uma nova Ata de Reunião.
    """
    template_name = 'ata_reuniao/ata_form.html'
    success_message = "✅ Ata de reunião criada com sucesso!"

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs


class AtaReuniaoUpdateView(AtaReuniaoBaseMixin, FilialScopedMixin, SuccessMessageMixin, UpdateView):
    """
    Atualiza uma Ata de Reunião existente e salva um registro no histórico.
    """
    template_name = 'ata_reuniao/ata_form.html'
    success_message = "🔄 Ata de reunião atualizada com sucesso!"

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    # --- MÉTODO form_valid ADICIONADO ---
    def form_valid(self, form):
        # Primeiro, salva o formulário principal da Ata de Reunião
        response = super().form_valid(form)
        
        # Pega o comentário do formulário
        comentario_texto = form.cleaned_data.get('comentario')

        # Se o usuário escreveu um comentário, cria um registro no histórico
        if comentario_texto:
            HistoricoAta.objects.create(
                ata=self.object,
                usuario=self.request.user,
                comentario=comentario_texto
            )
            
        return response


class AtaReuniaoDeleteView(AtaReuniaoBaseMixin, DeleteView):
    """
    Exclui uma Ata de Reunião.
    """
    template_name = 'ata_reuniao/ata_confirm_delete.html'
    success_message = "🗑️ Ata de reunião excluída com sucesso!"

    def delete(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)


# --- View do Dashboard ---

class AtaReuniaoDashboardView(LoginRequiredMixin, TemplateView):
    """
    Exibe os indicadores de performance e o quadro Kanban.
    """
    template_name = 'ata_reuniao/dashboard.html'

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        
        # --- Indicador 1: Pendências por Responsável ---
        pendencias_queryset = AtaReuniao.objects.exclude(
            status__in=[AtaReuniao.Status.CONCLUIDO, AtaReuniao.Status.CANCELADO]
        ).values('responsavel__nome_completo').annotate(count=Count('id')).order_by('-count')
        
        # --- Indicador 2: Qualidade das Atividades Concluídas ---
        concluidas = AtaReuniao.objects.filter(status=AtaReuniao.Status.CONCLUIDO)
        concluido_no_prazo = concluidas.filter(prazo__isnull=False, atualizado_em__date__lte=F('prazo')).count()
        concluido_com_atraso = concluidas.filter(prazo__isnull=False, atualizado_em__date__gt=F('prazo')).count()

        # --- Dados para o Quadro Kanban ---
        tasks = AtaReuniao.objects.all().select_related('responsavel', 'contrato').order_by('prazo')
        kanban_columns = {label: [] for _, label in AtaReuniao.Status.choices}
        for task in tasks:
            kanban_columns[task.get_status_display()].append(task)
        
        colunas_ordenadas = [s.label for s in AtaReuniao.Status]
        kanban_ordenado = {label: kanban_columns[label] for label in colunas_ordenadas}

        context.update({
            'titulo_pagina': 'Dashboard de Atas',
            'pendencias_labels': json.dumps([item['responsavel__nome_completo'] for item in pendencias_queryset]),
            'pendencias_data': json.dumps([item['count'] for item in pendencias_queryset]),
            'total_concluido': concluidas.count(),
            'total_cancelado': AtaReuniao.objects.filter(status=AtaReuniao.Status.CANCELADO).count(),
            'concluido_no_prazo': concluido_no_prazo,
            'concluido_com_atraso': concluido_com_atraso,
            'qualidade_labels': json.dumps(['Concluído no Prazo', 'Concluído com Atraso']),
            'qualidade_data': json.dumps([concluido_no_prazo, concluido_com_atraso]),
            'kanban_items': kanban_ordenado,
        })
        return context


# --- Views de Exportação ---

class AtaReuniaoPDFExportView(LoginRequiredMixin, View):
    """
    Exporta a lista de atas para um arquivo PDF.
    """
    def get(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        atas = AtaReuniao.objects.all().order_by('-entrada')
        context = {'atas': atas}
        template = get_template('ata_reuniao/ata_pdf.html')
        html = template.render(context)
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="atas_reuniao.pdf"'
        
        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            return HttpResponse('Erro ao gerar PDF')
        return response


class AtaReuniaoExcelExportView(LoginRequiredMixin, View):
    """
    Exporta a lista de atas para um arquivo CSV (compatível com Excel).
    """
    def get(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="atas_reuniao.csv"'
        
        writer = csv.writer(response, delimiter=';')
        writer.writerow([
            'ID', 'Contrato', 'Coordenador', 'Responsável', 'Natureza', 
            'Ação', 'Entrada', 'Prazo', 'Status'
        ])
        
        atas = AtaReuniao.objects.all().select_related('contrato', 'coordenador', 'responsavel').order_by('-entrada')
        for ata in atas:
            writer.writerow([
                ata.id,
                ata.contrato,
                ata.coordenador,
                ata.responsavel,
                ata.get_natureza_display(),
                ata.acao,
                ata.entrada.strftime('%d/%m/%Y'),
                ata.prazo.strftime('%d/%m/%Y') if ata.prazo else '',
                ata.get_status_display(),
            ])
        
        return response