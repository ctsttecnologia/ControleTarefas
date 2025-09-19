
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
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.template.loader import get_template
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import (CreateView, DeleteView, ListView, TemplateView, UpdateView, View, DetailView)
from openpyxl.styles import Font
from xhtml2pdf import pisa
from cliente.models import Cliente
from departamento_pessoal.models import Funcionario
from core.mixins import ViewFilialScopedMixin
from .forms import AtaReuniaoForm, HistoricoAtaForm, ComentarioForm
from .models import AtaReuniao, HistoricoAta, Filial, Comentario
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db.models import Q


User = get_user_model()

# --- Mixins Refatorados ---

class AtaReuniaoBaseMixin(LoginRequiredMixin, ViewFilialScopedMixin):
    """
    Mixin base para as views de Ata de Reunião, com login e escopo de filial.
    """
    model = AtaReuniao
    form_class = AtaReuniaoForm
    success_url = reverse_lazy('ata_reuniao:ata_reuniao_list')


class AtaQuerysetMixin:
    """
    Mixin para filtrar o queryset de AtaReuniao com base na filial do usuário
    e em parâmetros de busca da requisição.
    """
    def get_ata_queryset(self, request, model_class):
        user = request.user
        try:
            funcionario = Funcionario.objects.get(usuario=user)
            user_filial = funcionario.filial
        except Funcionario.DoesNotExist:
            user_filial = None

        if user.is_superuser:
            queryset = model_class.objects.all()
        elif user_filial:
            queryset = model_class.objects.filter(filial=user_filial)
        else:
            queryset = model_class.objects.none()

        # Aplica filtros com base nos parâmetros da URL (GET)
        contrato_id = request.GET.get('contrato')
        status = request.GET.get('status')
        coordenador_id = request.GET.get('coordenador')

        if contrato_id:
            queryset = queryset.filter(contrato_id=contrato_id)
        if status:
            queryset = queryset.filter(status=status)
        if coordenador_id:
            queryset = queryset.filter(coordenador__usuario__id=coordenador_id)
        
        # AQUI ESTÁ A CORREÇÃO: Usar apenas campos válidos para ordenação.
        # Ordenação sugerida: por prazo (as mais urgentes primeiro), depois por criado_em.
        return queryset.order_by('prazo', '-criado_em')


# --- Views de CRUD (Refatoradas) ---

class AtaReuniaoListView(LoginRequiredMixin, AtaQuerysetMixin, ListView):
    model = AtaReuniao
    template_name = 'ata_reuniao/ata_reuniao_list.html'
    context_object_name = 'atas'
    paginate_by = 20

    def get_queryset(self):
        # Passe o modelo para a mixin
        queryset = self.get_ata_queryset(self.request, model_class=self.model)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Garanta que o objeto do usuário seja serializável
        user_data = {
            'username': self.request.user.username,
            'filial': str(self.request.user.funcionario.filial) if self.request.user.is_authenticated else None
        }
        context['user_data'] = user_data 
        
        # Filtros para o contexto da página
        current_queryset = self.get_queryset()
        
        coordenador_ids = current_queryset.values_list('coordenador__usuario__id', flat=True).distinct()
        context['coordenadores'] = User.objects.filter(id__in=coordenador_ids).order_by('first_name')
        
        contrato_ids = current_queryset.values_list('contrato_id', flat=True).distinct()
        context['contratos'] = Cliente.objects.filter(id__in=contrato_ids).order_by('nome')
        
        context['current_contrato'] = self.request.GET.get('contrato', '')
        context['current_status'] = self.request.GET.get('status', '')
        context['current_coordenador'] = self.request.GET.get('coordenador', '')
        return context


class AtaReuniaoCreateView(AtaReuniaoBaseMixin, SuccessMessageMixin, CreateView):
    template_name = 'ata_reuniao/ata_form.html'
    success_message = "✅ Ata de reunião criada com sucesso!"
   
    def form_valid(self, form):
        # AQUI ESTÁ A CORREÇÃO
        # Define a filial da ata com base na filial do usuário logado, se existir
        if self.request.user.is_authenticated and hasattr(self.request.user, 'funcionario'):
            form.instance.filial = self.request.user.funcionario.filial
        
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs


class AtaReuniaoUpdateView(AtaReuniaoBaseMixin, SuccessMessageMixin, UpdateView):
    template_name = 'ata_reuniao/ata_form.html'
    success_message = "🔄 Ata de reunião atualizada com sucesso!"
    
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
    context_object_name = 'ata'

    def get_queryset(self):
        # Garante que a query do DetailView use o escopo de filial
        queryset = super().get_queryset()
        return queryset.prefetch_related('historico__usuario')


class AtaReuniaoAddCommentView(AtaReuniaoBaseMixin, DetailView):
    model = AtaReuniao

    def post(self, request, pk, *args, **kwargs):
        ata = self.get_object() 
        form = ComentarioForm(request.POST)
        if form.is_valid():
            HistoricoAta.objects.create(
                ata=ata,
                usuario=request.user,
                comentario=form.cleaned_data['comentario'],
                filial=ata.filial
            )
            messages.success(request, 'Comentário adicionado com sucesso!')
        else:
            messages.error(request, 'Erro ao adicionar o comentário.')
            
        return redirect('ata_reuniao:ata_reuniao_detail', pk=pk)


class AtaReuniaoDeleteView(AtaReuniaoBaseMixin, SuccessMessageMixin, DeleteView):
    template_name = 'ata_reuniao/ata_confirm_delete.html'
    success_message = "🗑️ Ata de reunião excluída com sucesso!"

    def form_valid(self, form):
        messages.success(self.request, self.success_message)
        return super().form_valid(form)


class AtaReuniaoDashboardView(LoginRequiredMixin, AtaQuerysetMixin, TemplateView):
    template_name = 'ata_reuniao/ata_reuniao_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Obter o queryset base com os filtros aplicados pela mixin
        base_queryset = self.get_ata_queryset(self.request, model_class=AtaReuniao)

        # 1. Dados para os KPIs (cartões)
        total_concluido = base_queryset.filter(status=AtaReuniao.Status.CONCLUIDO).count()
        concluido_no_prazo = base_queryset.filter(status=AtaReuniao.Status.CONCLUIDO, prazo__gte=F('atualizado_em')).count()
        concluido_com_atraso = base_queryset.filter(status=AtaReuniao.Status.CONCLUIDO, prazo__lt=F('atualizado_em')).count()
        total_cancelado = base_queryset.filter(status=AtaReuniao.Status.CANCELADO).count()
        total_concluido_efetivo = concluido_no_prazo + concluido_com_atraso

        percentual_no_prazo = (concluido_no_prazo / total_concluido_efetivo * 100) if total_concluido_efetivo > 0 else 0
        percentual_com_atraso = (concluido_com_atraso / total_concluido_efetivo * 100) if total_concluido_efetivo > 0 else 0

        context.update({
            'total_concluido': total_concluido,
            'concluido_no_prazo': concluido_no_prazo,
            'concluido_com_atraso': concluido_com_atraso,
            'total_cancelado': total_cancelado,
            'percentual_no_prazo': percentual_no_prazo,
            'percentual_com_atraso': percentual_com_atraso,
    })

        # 2. Dados para o gráfico de Pendências por Responsável
        # Filtra apenas tarefas pendentes e agrupa por responsável
        pendencias_por_responsavel = base_queryset.filter(
            status__in=[AtaReuniao.Status.PENDENTE, AtaReuniao.Status.ANDAMENTO]
        ).values(
            'responsavel__usuario__first_name'
        ).annotate(
            count=Count('responsavel')
        ).order_by('-count')

        # Extrai labels e dados
        pendencias_labels = [item['responsavel__usuario__first_name'] for item in pendencias_por_responsavel]
        pendencias_data = [item['count'] for item in pendencias_por_responsavel]

        context['pendencias_labels'] = pendencias_labels
        context['pendencias_data'] = pendencias_data

        # 3. Dados para o gráfico de Qualidade das Conclusões
        qualidade_labels = ['No Prazo', 'Com Atraso']
        qualidade_data = [concluido_no_prazo, concluido_com_atraso]

        context['qualidade_labels'] = qualidade_labels
        context['qualidade_data'] = qualidade_data

        # 4. Dados para o Kanban
        kanban_items = {}
         # Itera sobre as escolhas de status do modelo para garantir que todas as colunas sejam criadas
        for status_value, status_label in AtaReuniao.Status.choices:
            kanban_items[status_label] = list(base_queryset.filter(status=status_value).order_by('prazo'))

        context['kanban_items'] = kanban_items
        context['titulo_pagina'] = "Dashboard"

        return context

# ... (restante das classes de views) ...

class AtaReuniaoPDFExportView(LoginRequiredMixin, AtaQuerysetMixin, View):
    def get(self, request, *args, **kwargs):
        atas = self.get_ata_queryset(request, model_class=AtaReuniao)
        
        periodo_relatorio = "Período: Todas as datas"
        data_inicio = request.GET.get('data_inicio')
        data_fim = request.GET.get('data_fim')
        
        if data_inicio and data_fim:
            
            atas = atas.filter(criado_em__range=[data_inicio, data_fim])
            data_inicio_fmt = timezone.datetime.strptime(data_inicio, '%Y-%m-%d').strftime('%d/%m/%Y')
            data_fim_fmt = timezone.datetime.strptime(data_fim, '%Y-%m-%d').strftime('%d/%m/%Y')
            periodo_relatorio = f"Período: {data_inicio_fmt} a {data_fim_fmt}"

        template = get_template('ata_reuniao/ata_pdf.html')
        context = {
            'atas': atas,
            'data_exportacao': timezone.now(),
            'usuario_exportacao': request.user.get_full_name(),
            'periodo_relatorio': periodo_relatorio,
        }
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="relatorio_atas.pdf"'
        
        pisa_status = pisa.CreatePDF(template.render(context), dest=response)
        if pisa_status.err:
            messages.error(request, "Ocorreu um erro ao gerar o PDF.")
            return HttpResponse('Erro ao gerar PDF', status=300)
            
        return response


class AtaReuniaoExcelExportView(LoginRequiredMixin, AtaQuerysetMixin, View):
    def get(self, request, *args, **kwargs):
        # Passe o modelo para a mixin
        atas = self.get_ata_queryset(request, model_class=AtaReuniao)
        
        buffer = io.BytesIO()
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Relatório de Atas"
        
        headers = [
            'ID', 'Título', 'Contrato', 'Coordenador', 'Responsável', 'Natureza', 
            'Ação', 'Entrada', 'Prazo', 'Status', 'Filial', 'Última Atualização', 'Comentário'
        ]
        sheet.append(headers)
        
        for cell in sheet[1]:
            cell.font = Font(bold=True)
            
        for ata in atas:
            entrada_fmt = ata.entrada.strftime('%d/%m/%Y') if ata.entrada else ''
            prazo_fmt = ata.prazo.strftime('%d/%m/%Y') if ata.prazo else ''
            atualizado_fmt = ata.atualizado_em.strftime('%d/%m/%Y %H:%M') if ata.atualizado_em else ''

            row_data = [
                ata.id,
                ata.titulo,
                ata.contrato.nome if ata.contrato else '',
                ata.coordenador.nome_completo if ata.coordenador else '',
                ata.responsavel.nome_completo if ata.responsavel else '',
                ata.get_natureza_display(),
                ata.acao,
                entrada_fmt,
                prazo_fmt,
                ata.get_status_display(),
                ata.filial.nome if ata.filial else '',
                atualizado_fmt,
                ata.historico.last().comentario if ata.historico.exists() else '',
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


# ===================================================
# NOVA VIEW: ATUALIZAÇÃO DE STATUS VIA API
# ===================================================

@method_decorator(csrf_exempt, name='dispatch')
class UpdateTaskStatusView(LoginRequiredMixin, View):
    """
    Endpoint da API para atualizar o status de uma ata de reunião.
    Permite a funcionalidade de arrastar e soltar (drag and drop) no Kanban.
    """
    def post(self, request, pk, *args, **kwargs):
        try:
            data = json.loads(request.body)
            new_status = data.get('new_status')

            # Obtém a filial do usuário logado
            try:
                user_filial = request.user.funcionario.filial
            except Funcionario.DoesNotExist:
                user_filial = None

            # Busca a ata e verifica permissão de filial
            if request.user.is_superuser:
                ata = get_object_or_404(AtaReuniao, pk=pk)
            elif user_filial:
                ata = get_object_or_404(AtaReuniao, pk=pk, filial=user_filial)
            else:
                # Se não for superusuário e não tiver filial, não pode acessar nenhuma ata
                return JsonResponse({'status': 'error', 'message': 'Ata não encontrada ou acesso negado'}, status=404)

            # Verifica se o novo status é válido
            valid_statuses = [choice[0] for choice in AtaReuniao.Status.choices]
            if new_status not in valid_statuses:
                return JsonResponse({'status': 'error', 'message': 'Status inválido'}, status=300)

            # Atualiza o status e salva
            ata.status = new_status
            ata.save()

            return JsonResponse({'status': 'success', 'message': 'Status atualizado com sucesso.'})

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Formato de requisição inválido'}, status=400)
        except AtaReuniao.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Ata de Reunião não encontrada'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=300)
        

