# ata_reuniao/views.py

# ata_reuniao/views.py

import csv
import io
import json
from typing import Any
from django.shortcuts import get_object_or_404, redirect, render
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
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from xhtml2pdf import pisa
from cliente.models import Cliente
from departamento_pessoal.models import Funcionario
from core.mixins import ViewFilialScopedMixin
from .forms import AtaReuniaoForm, HistoricoAtaForm, ComentarioForm
from .models import AtaReuniao, HistoricoAta, Filial, Comentario
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db.models import Q
import pandas as pd
from io import BytesIO
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from django.contrib.auth.decorators import login_required
from .forms import UploadAtaReuniaoForm
from django.contrib.messages import get_messages
from django.core.exceptions import ObjectDoesNotExist
from usuario.models import Usuario
from django import template


User = get_user_model()


# ═══════════════════════════════════════════════════════════════════════════════
# MIXIN CENTRAL DE FILIAL - USADO POR TODAS AS VIEWS
# ═══════════════════════════════════════════════════════════════════════════════

class FilialAtivaMixin:
    """
    Mixin central para obter a filial ativa do usuário.
    Usa a chave 'active_filial_id' da sessão (definida pelo seletor do header).
    """
    
    def get_filial_ativa(self):
        """
        Retorna o objeto Filial ativa ou None.
        Prioridade:
        1. Filial selecionada na sessão (active_filial_id)
        2. Filial do funcionário vinculado ao usuário
        3. None (superusuário sem filial selecionada vê tudo)
        """
        # 1. Pegar da sessão (seletor do header)
        filial_id = self.request.session.get('active_filial_id')
        
        if filial_id:
            try:
                return Filial.objects.get(pk=filial_id)
            except Filial.DoesNotExist:
                pass
        
        # 2. Fallback: filial do funcionário
        user = self.request.user
        filial_ativa = getattr(user, 'filial_ativa', None)
        if filial_ativa:
            return filial_ativa
            
        try:
            funcionario = Funcionario.objects.select_related('filial').get(usuario=user)
            return funcionario.filial
        except Funcionario.DoesNotExist:
            pass
        
        # 3. Superusuário sem filial = vê tudo
        return None
    
    def get_filial_ativa_id(self):
        """Retorna apenas o ID da filial ativa ou None."""
        filial = self.get_filial_ativa()
        return filial.id if filial else None

    def filter_queryset_by_filial(self, queryset):
        """Aplica o filtro de filial ao queryset."""
        filial = self.get_filial_ativa()
        if filial:
            return queryset.filter(filial=filial)
        elif not self.request.user.is_superuser:
            return queryset.none()
        return queryset
    
    def filter_related_by_filial(self, queryset, filial_field='filial'):
        """
        Filtra querysets de modelos relacionados (Cliente, Funcionario, etc).
        """
        filial = self.get_filial_ativa()
        if filial:
            return queryset.filter(**{filial_field: filial})
        return queryset


# ═══════════════════════════════════════════════════════════════════════════════
# MIXINS BASE
# ═══════════════════════════════════════════════════════════════════════════════

class AtaReuniaoBaseMixin(LoginRequiredMixin, FilialAtivaMixin, ViewFilialScopedMixin):
    """
    Mixin base para as views de Ata de Reunião.
    """
    model = AtaReuniao
    form_class = AtaReuniaoForm
    success_url = reverse_lazy('ata_reuniao:ata_reuniao_list')


class AtaQuerysetMixin(FilialAtivaMixin):
    """
    Mixin para filtrar o queryset de AtaReuniao com base na filial ativa
    e em parâmetros de busca da requisição.
    """
    
    def get_ata_queryset(self, request, model_class):
        """
        Retorna queryset filtrado por filial e parâmetros GET.
        """
        # Usar o manager for_request se disponível
        if hasattr(model_class.objects, 'for_request'):
            queryset = model_class.objects.for_request(request)
        else:
            queryset = model_class.objects.all()
            queryset = self.filter_queryset_by_filial(queryset)

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
        
        return queryset.order_by('prazo', '-criado_em')


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE TAGS
# ═══════════════════════════════════════════════════════════════════════════════

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Permite acessar um dicionário com uma chave variável no template.
    """
    if dictionary is None:
        return []
    return dictionary.get(key, [])


# ═══════════════════════════════════════════════════════════════════════════════
# VIEWS DE CRUD
# ═══════════════════════════════════════════════════════════════════════════════

# No AtaReuniaoListView, ajuste o get_context_data:

class AtaReuniaoListView(LoginRequiredMixin, AtaQuerysetMixin, ListView):
    model = AtaReuniao
    template_name = 'ata_reuniao/ata_reuniao_list.html'
    context_object_name = 'atas'
    paginate_by = 25

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            try:
                _ = request.user.funcionario
            except ObjectDoesNotExist:
                return render(request, 'ata_reuniao/acesso_negado.html', {
                    'titulo': 'Acesso Restrito',
                    'mensagem': (
                        'Sua conta de usuário não está vinculada a um registro de funcionário, '
                        'por isso você não pode acessar o módulo de Atas de Reunião.'
                    )
                }, status=403)
        
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.get_ata_queryset(self.request, model_class=self.model)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        filial_ativa = self.get_filial_ativa()
        context['filial_ativa'] = filial_ativa
        context['user_data'] = {
            'username': self.request.user.username,
            'filial': str(filial_ativa) if filial_ativa else 'Todas as filiais'
        }
        
        # ═══════════════════════════════════════════════════════════════
        # FILTROS - Baseados na filial ativa
        # ═══════════════════════════════════════════════════════════════
        
        # Coordenadores da filial ativa (não das atas existentes!)
        coordenadores_qs = Funcionario.objects.filter(status='ATIVO')
        if filial_ativa:
            coordenadores_qs = coordenadores_qs.filter(filial=filial_ativa)
        context['coordenadores'] = coordenadores_qs.select_related('usuario').order_by('nome_completo')
        
        # Contratos/Clientes da filial ativa
        clientes_qs = Cliente.objects.filter(estatus=True)
        if filial_ativa:
            clientes_qs = clientes_qs.filter(filial=filial_ativa)
        context['contratos'] = clientes_qs.order_by('nome')
        
        context['current_contrato'] = self.request.GET.get('contrato', '')
        context['current_status'] = self.request.GET.get('status', '')
        context['current_coordenador'] = self.request.GET.get('coordenador', '')
        
        return context

        

class AtaReuniaoCreateView(AtaReuniaoBaseMixin, SuccessMessageMixin, CreateView):
    template_name = 'ata_reuniao/ata_form.html'
    success_message = "✅ Ata de reunião criada com sucesso!"
   
    def form_valid(self, form):
        # Define a filial da ata com base na filial ativa
        filial_ativa = self.get_filial_ativa()
        if filial_ativa:
            form.instance.filial = filial_ativa
        elif hasattr(self.request.user, 'funcionario'):
            form.instance.filial = self.request.user.funcionario.filial
        
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filial_ativa'] = self.get_filial_ativa()
        return context


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
                comentario=comentario_texto,
                filial=self.object.filial
            )
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filial_ativa'] = self.get_filial_ativa()
        return context


class AtaReuniaoDetailView(AtaReuniaoBaseMixin, DetailView):
    """Exibe os detalhes de uma Ata de Reunião específica."""
    template_name = 'ata_reuniao/ata_reuniao_detail.html'
    context_object_name = 'ata'

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.prefetch_related('historico__usuario')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filial_ativa'] = self.get_filial_ativa()
        return context


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
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filial_ativa'] = self.get_filial_ativa()
        return context


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD VIEW
# ═══════════════════════════════════════════════════════════════════════════════

class AtaReuniaoDashboardView(LoginRequiredMixin, AtaQuerysetMixin, TemplateView):
    template_name = 'ata_reuniao/ata_reuniao_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # ═══════════════════════════════════════════════════════════════
        # FILIAL ATIVA (da sessão: active_filial_id)
        # ═══════════════════════════════════════════════════════════════
        filial_ativa = self.get_filial_ativa()
        is_superuser = self.request.user.is_superuser

        # ═══════════════════════════════════════════════════════════════
        # QUERYSET BASE (filtrado por filial via manager ou mixin)
        # ═══════════════════════════════════════════════════════════════
        base_queryset = self.get_ata_queryset(self.request, model_class=AtaReuniao)

        # ═══════════════════════════════════════════════════════════════
        # 1. KPIs
        # ═══════════════════════════════════════════════════════════════
        total_concluido = base_queryset.filter(status=AtaReuniao.Status.CONCLUIDO).count()
        total_cancelado = base_queryset.filter(status=AtaReuniao.Status.CANCELADO).count()
        
        concluido_no_prazo = 0
        concluido_com_atraso = 0
        
        atas_concluidas = base_queryset.filter(status=AtaReuniao.Status.CONCLUIDO).only(
            'prazo', 'atualizado_em'
        )
        for ata in atas_concluidas:
            if ata.prazo and ata.atualizado_em:
                if ata.prazo >= ata.atualizado_em.date():
                    concluido_no_prazo += 1
                else:
                    concluido_com_atraso += 1
            else:
                concluido_no_prazo += 1

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

        # ═══════════════════════════════════════════════════════════════
        # 2. GRÁFICO: Pendências por Responsável
        # ═══════════════════════════════════════════════════════════════
        pendencias_por_responsavel = base_queryset.filter(
            status__in=[AtaReuniao.Status.PENDENTE, AtaReuniao.Status.ANDAMENTO]
        ).values(
            'responsavel__nome_completo'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:10]

        context['pendencias_labels'] = [
            item['responsavel__nome_completo'] or 'Sem responsável' 
            for item in pendencias_por_responsavel
        ]
        context['pendencias_data'] = [item['count'] for item in pendencias_por_responsavel]

        # ═══════════════════════════════════════════════════════════════
        # 3. GRÁFICO: Qualidade das Conclusões
        # ═══════════════════════════════════════════════════════════════
        context['qualidade_labels'] = ['No Prazo', 'Com Atraso']
        context['qualidade_data'] = [concluido_no_prazo, concluido_com_atraso]

        # ═══════════════════════════════════════════════════════════════
        # 4. KANBAN
        # ═══════════════════════════════════════════════════════════════
        context['kanban_status_choices'] = AtaReuniao.Status.choices
        
        kanban_items = {}
        for status_value, status_label in AtaReuniao.Status.choices:
            kanban_items[status_label] = list(
                base_queryset.filter(status=status_value)
                .select_related(
                    'responsavel', 
                    'responsavel__usuario', 
                    'contrato', 
                    'coordenador', 
                    'coordenador__usuario'
                )
                .order_by('prazo')
            )

        context['kanban_items'] = kanban_items
        context['titulo_pagina'] = "Dashboard de Atas"

        # ═══════════════════════════════════════════════════════════════
        # 5. FILTROS DO KANBAN - COM ESCOPO DE FILIAL
        # ═══════════════════════════════════════════════════════════════
        
        # Coordenadores da filial ativa
        coordenadores_qs = Funcionario.objects.filter(status='ATIVO')
        coordenadores_qs = self.filter_related_by_filial(coordenadores_qs)
        context['coordenadores'] = coordenadores_qs.select_related('usuario').order_by('nome_completo')
        
        # Clientes da filial ativa
        clientes_qs = Cliente.objects.filter(estatus=True)
        clientes_qs = self.filter_related_by_filial(clientes_qs)
        context['clientes'] = clientes_qs.order_by('nome')[:100]
        
        # Info da filial para template
        context['filial_ativa'] = filial_ativa
        context['is_superuser'] = is_superuser

        return context


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT VIEWS
# ═══════════════════════════════════════════════════════════════════════════════

class AtaReuniaoPDFExportView(LoginRequiredMixin, AtaQuerysetMixin, View):
    def get(self, request, *args, **kwargs):
        atas = self.get_ata_queryset(request, model_class=AtaReuniao)
        filial_ativa = self.get_filial_ativa()
        
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
            'kanban_status_choices': AtaReuniao.Status.choices,
            'filial_ativa': filial_ativa,
        }
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="relatorio_atas.pdf"'
        
        pisa_status = pisa.CreatePDF(template.render(context), dest=response)
        if pisa_status.err:
            messages.error(request, "Ocorreu um erro ao gerar o PDF.")
            return HttpResponse('Erro ao gerar PDF', status=500)
            
        return response


class AtaReuniaoExcelExportView(LoginRequiredMixin, AtaQuerysetMixin, View):
    def get(self, request, *args, **kwargs):
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


# ═══════════════════════════════════════════════════════════════════════════════
# API VIEWS - ATUALIZAÇÃO DE STATUS
# ═══════════════════════════════════════════════════════════════════════════════

class AtaUpdateStatusAPIView(LoginRequiredMixin, FilialAtivaMixin, View):
    """API endpoint para atualizar o status de uma ata via drag & drop."""
    
    def post(self, request, pk):
        try:
            data = json.loads(request.body)
            new_status = data.get('new_status')
            
            if not new_status:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Status não informado'
                }, status=400)
            
            # Buscar a ata respeitando a filial
            filial_ativa = self.get_filial_ativa()
            
            try:
                if filial_ativa:
                    ata = AtaReuniao.objects.get(pk=pk, filial=filial_ativa)
                elif request.user.is_superuser:
                    ata = AtaReuniao.objects.get(pk=pk)
                else:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Ata não encontrada ou acesso negado'
                    }, status=404)
            except AtaReuniao.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Ata não encontrada'
                }, status=404)
            
            # Verificar se o status é válido
            valid_statuses = [choice[0] for choice in AtaReuniao.Status.choices]
            if new_status not in valid_statuses:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Status inválido: {new_status}'
                }, status=400)
            
            # Atualizar o status
            old_status = ata.status
            ata.status = new_status
            ata.save(update_fields=['status', 'atualizado_em'])
            
            return JsonResponse({
                'status': 'success',
                'message': f'Status alterado de "{old_status}" para "{new_status}"',
                'data': {
                    'id': ata.pk,
                    'old_status': old_status,
                    'new_status': new_status,
                    'updated_at': ata.atualizado_em.isoformat() if ata.atualizado_em else None
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': 'JSON inválido'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class UpdateTaskStatusView(LoginRequiredMixin, FilialAtivaMixin, View):
    """Endpoint alternativo para atualizar status (drag and drop Kanban)."""
    
    def post(self, request, pk, *args, **kwargs):
        try:
            data = json.loads(request.body)
            new_status = data.get('new_status')
            
            filial_ativa = self.get_filial_ativa()

            if filial_ativa:
                ata = get_object_or_404(AtaReuniao, pk=pk, filial=filial_ativa)
            elif request.user.is_superuser:
                ata = get_object_or_404(AtaReuniao, pk=pk)
            else:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Ata não encontrada ou acesso negado'
                }, status=404)

            valid_statuses = [choice[0] for choice in AtaReuniao.Status.choices]
            if new_status not in valid_statuses:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Status inválido'
                }, status=400)

            ata.status = new_status
            ata.save()

            return JsonResponse({
                'status': 'success', 
                'message': 'Status atualizado com sucesso.'
            })

        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error', 
                'message': 'Formato de requisição inválido'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'status': 'error', 
                'message': str(e)
            }, status=500)


# ═══════════════════════════════════════════════════════════════════════════════
# VIEWS DE UPLOAD/DOWNLOAD
# ═══════════════════════════════════════════════════════════════════════════════

login_required_m = method_decorator(login_required, name='dispatch')


@login_required
def download_ata_reuniao_template(request):
    """Gera planilha Excel modelo para importação em massa."""
    output = BytesIO()
    workbook = Workbook()
    
    worksheet = workbook.active
    worksheet.title = "Dados das Atas"

    headers = [
        "Contrato (ID)", "Coordenador (ID)", "Responsável (ID)", "Natureza", 
        "Título", "Ação/Proposta", "Data de Entrada (DD/MM/AAAA)", 
        "Prazo Final (DD/MM/AAAA)", "Status"
    ]
    
    header_font = Font(bold=True, color="FFFFFF")
    header_alignment = Alignment(horizontal="center", vertical="center")
    
    for col_num, header_title in enumerate(headers, 1):
        cell = worksheet.cell(row=1, column=col_num, value=header_title)
        cell.font = header_font
        cell.alignment = header_alignment
        worksheet.column_dimensions[get_column_letter(col_num)].width = 25
        
    for cell in worksheet["1:1"]:
        cell.fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")

    instructions_ws = workbook.create_sheet(title="Instruções e Opções")
    instructions_ws.column_dimensions['A'].width = 30
    instructions_ws.column_dimensions['B'].width = 50

    instructions_data = [
        ("INSTRUÇÕES GERAIS", ""),
        ("Contrato (ID)", "Insira o número ID do cliente/contrato. Ex: 15"),
        ("Coordenador (ID)", "Insira o número ID do funcionário coordenador. Ex: 7"),
        ("Responsável (ID)", "Insira o número ID do funcionário responsável. Ex: 12"),
        ("Datas", "Use o formato DD/MM/AAAA. Ex: 25/12/2025"),
        ("", ""),
        ("OPÇÕES VÁLIDAS", "Não altere os valores desta coluna."),
        ("Natureza", ", ".join([choice[0] for choice in AtaReuniao.Natureza.choices])),
        ("Status", ", ".join([choice[0] for choice in AtaReuniao.Status.choices])),
    ]

    for row, data in enumerate(instructions_data, 1):
        instructions_ws.cell(row=row, column=1, value=data[0]).font = Font(bold=True)
        instructions_ws.cell(row=row, column=2, value=data[1])

    workbook.save(output)
    output.seek(0)

    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="modelo_importacao_atas.xlsx"'
    return response


@login_required_m
class UploadAtaReuniaoView(FilialAtivaMixin, View):
    template_name = 'ata_reuniao/ata_reuniao_upload.html'
    form_class = UploadAtaReuniaoForm
    success_url = reverse_lazy('ata_reuniao:ata_reuniao_list')

    def get(self, request, *args, **kwargs):
        form = self.form_class()

        storage = get_messages(request)
        has_upload_errors = False
        for message in storage:
            if 'warning' in message.tags:
                has_upload_errors = True
                break
        
        if not has_upload_errors and 'upload_error_details' in request.session:
            del request.session['upload_error_details']

        context = {
            'form': form,
            'has_upload_errors': has_upload_errors,
            'filial_ativa': self.get_filial_ativa(),
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        if not form.is_valid():
            if 'upload_error_details' in request.session:
                del request.session['upload_error_details'] 
            return render(request, self.template_name, {'form': form})

        file = request.FILES['file']
        filial_ativa = self.get_filial_ativa()
        
        # Validar se há filial selecionada para importação
        if not filial_ativa and not request.user.is_superuser:
            messages.error(request, "Nenhuma filial selecionada. Selecione uma filial no menu superior.")
            return redirect(request.path)
        
        try:
            df = pd.read_excel(file, dtype=str).fillna('')
        except Exception as e:
            messages.error(request, f"Erro ao ler o arquivo Excel: {e}")
            return redirect(request.path)

        if df.empty:
            messages.warning(request, "A planilha está vazia ou não contém dados para importar.")
            return redirect(request.path)
        
        headers_map = {
            "Contrato (ID)": "contrato_id",
            "Coordenador (ID)": "coordenador_id",
            "Responsável (ID)": "responsavel_id",
            "Natureza": "natureza",
            "Título": "titulo",
            "Ação/Proposta": "acao",
            "Data de Entrada (DD/MM/AAAA)": "entrada",
            "Prazo Final (DD/MM/AAAA)": "prazo",
            "Status": "status"
        }
        df.rename(columns=headers_map, inplace=True)

        success_count = 0
        errors = []
        error_details_for_session = []

        valid_natureza = AtaReuniao.Natureza.values
        valid_status = AtaReuniao.Status.values

        for index, row in df.iterrows():
            linha = index + 2
            original_row_data = row.to_dict()

            try:
                # Validação de Contrato (respeitando filial)
                try:
                    contrato_qs = Cliente.objects.filter(pk=int(row['contrato_id']))
                    if filial_ativa:
                        contrato_qs = contrato_qs.filter(filial=filial_ativa)
                    contrato = contrato_qs.get()
                except (Cliente.DoesNotExist, ValueError):
                    raise ValueError(f"Contrato com ID '{row['contrato_id']}' não encontrado na filial atual.")
                
                # Validação de Coordenador (respeitando filial)
                try:
                    coord_qs = Funcionario.objects.filter(pk=int(row['coordenador_id']))
                    if filial_ativa:
                        coord_qs = coord_qs.filter(filial=filial_ativa)
                    coordenador = coord_qs.get()
                except (Funcionario.DoesNotExist, ValueError):
                    raise ValueError(f"Coordenador com ID '{row['coordenador_id']}' não encontrado na filial atual.")
                
                # Validação de Responsável (respeitando filial)
                try:
                    resp_qs = Funcionario.objects.filter(pk=int(row['responsavel_id']))
                    if filial_ativa:
                        resp_qs = resp_qs.filter(filial=filial_ativa)
                    responsavel = resp_qs.get()
                except (Funcionario.DoesNotExist, ValueError):
                    raise ValueError(f"Responsável com ID '{row['responsavel_id']}' não encontrado na filial atual.")
                
                # Validação de Natureza
                if row['natureza'] not in valid_natureza:
                    raise ValueError(f"Natureza '{row['natureza']}' inválida.")
                
                # Validação de Status
                if row['status'] not in valid_status:
                    raise ValueError(f"Status '{row['status']}' inválido.")
                
                # Parse de datas
                entrada = None
                if row['entrada']:
                    try:
                        entrada = pd.to_datetime(row['entrada'], dayfirst=True).date()
                    except:
                        raise ValueError(f"Data de entrada '{row['entrada']}' inválida.")
                
                prazo = None
                if row['prazo']:
                    try:
                        prazo = pd.to_datetime(row['prazo'], dayfirst=True).date()
                    except:
                        raise ValueError(f"Prazo '{row['prazo']}' inválido.")
                
                # Criar a Ata com a filial ativa
                AtaReuniao.objects.create(
                    contrato=contrato,
                    coordenador=coordenador,
                    responsavel=responsavel,
                    natureza=row['natureza'],
                    titulo=row['titulo'],
                    acao=row['acao'],
                    entrada=entrada,
                    prazo=prazo,
                    status=row['status'],
                    filial=filial_ativa
                )

                success_count += 1

            except Exception as e:
                error_message = f"Linha {linha}: {e}"
                errors.append(error_message)
                original_row_data['motivo_do_erro'] = str(e)
                error_details_for_session.append(original_row_data)

        if error_details_for_session:
            request.session['upload_error_details'] = error_details_for_session

        if success_count > 0:
            messages.success(request, f"{success_count} ata(s) de reunião importada(s) com sucesso!")

        if errors:
            error_summary = f"<strong>{len(errors)} linha(s) não puderam ser importadas.</strong><br>Baixe o relatório de erros para corrigir e tente novamente."
            messages.warning(request, error_summary, extra_tags='safe')
            
        return redirect(request.path)


@login_required
def download_error_report(request):
    """Gera arquivo Excel com linhas que falharam durante upload."""
    error_details = request.session.get('upload_error_details')

    if not error_details:
        messages.error(request, "Nenhum relatório de erros encontrado na sessão.")
        return redirect('ata_reuniao:ata_reuniao_upload')

    df_errors = pd.DataFrame(error_details)
    
    original_columns_order = [
        "contrato_id", "coordenador_id", "responsavel_id", "natureza", "titulo",
        "acao", "entrada", "prazo", "status"
    ]
    df_errors = df_errors[original_columns_order + ['motivo_do_erro']]

    friendly_headers = {
        "contrato_id": "Contrato (ID)", "coordenador_id": "Coordenador (ID)",
        "responsavel_id": "Responsável (ID)", "natureza": "Natureza", "titulo": "Título",
        "acao": "Ação/Proposta", "entrada": "Data de Entrada (DD/MM/AAAA)",
        "prazo": "Prazo Final (DD/MM/AAAA)", "status": "Status",
        "motivo_do_erro": "Motivo do Erro"
    }
    df_errors.rename(columns=friendly_headers, inplace=True)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_errors.to_excel(writer, index=False, sheet_name='Erros_Para_Correcao')
        
        workbook = writer.book
        worksheet = writer.sheets['Erros_Para_Correcao']
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="C00000", end_color="C00000", fill_type="solid")

        for col_num, value in enumerate(df_errors.columns.values, 1):
            cell = worksheet.cell(row=1, column=col_num)
            cell.font = header_font
            cell.fill = header_fill
            worksheet.column_dimensions[get_column_letter(col_num)].width = 25
        worksheet.column_dimensions[get_column_letter(len(df_errors.columns))].width = 50

    output.seek(0)

    del request.session['upload_error_details']

    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="relatorio_erros_importacao.xlsx"'
    return response


