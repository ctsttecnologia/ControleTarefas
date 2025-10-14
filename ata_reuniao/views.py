
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
        
# Decorador para exigir login em Class-Based Views
login_required_m = method_decorator(login_required, name='dispatch')


@login_required
def download_ata_reuniao_template(request):
    """
    Gera e fornece para download uma planilha Excel (.xlsx) modelo para o
    carregamento em massa de Atas de Reunião.
    """
    output = BytesIO()
    workbook = Workbook()
    
    # --- Planilha de Dados ---
    worksheet = workbook.active
    worksheet.title = "Dados das Atas"

    headers = [
        "Contrato (ID)", "Coordenador (ID)", "Responsável (ID)", "Natureza", 
        "Título", "Ação/Proposta", "Data de Entrada (DD/MM/AAAA)", 
        "Prazo Final (DD/MM/AAAA)", "Status"
    ]
    
    # Estilo do cabeçalho
    header_font = Font(bold=True, color="FFFFFF")
    header_alignment = Alignment(horizontal="center", vertical="center")
    
    for col_num, header_title in enumerate(headers, 1):
        cell = worksheet.cell(row=1, column=col_num, value=header_title)
        cell.font = header_font
        cell.alignment = header_alignment
        worksheet.column_dimensions[get_column_letter(col_num)].width = 25
        
    # Colore o cabeçalho
    for cell in worksheet["1:1"]:
        cell.fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")

    # --- Planilha de Instruções ---
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
class UploadAtaReuniaoView(View):
    template_name = 'ata_reuniao/ata_reuniao_upload.html'
    form_class = UploadAtaReuniaoForm
    success_url = reverse_lazy('ata_reuniao:ata_reuniao_list') # Altere para sua URL de listagem

    def get(self, request, *args, **kwargs):
        """
        Renderiza o formulário e verifica se há mensagens de erro 
        para exibir o botão de download do relatório.
        """
        form = self.form_class()

        # Lógica para verificar a existência de mensagens de 'warning'
        storage = get_messages(request)
        has_upload_errors = False
        for message in storage:
            if 'warning' in message.tags:
                has_upload_errors = True
                break  # Encontrou um, não precisa procurar mais
        
        # Limpa a sessão de erros antigos se não houver mais mensagens de warning
        if not has_upload_errors and 'upload_error_details' in request.session:
            del request.session['upload_error_details']

        context = {
            'form': form,
            'has_upload_errors': has_upload_errors,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        if not form.is_valid():
            # Limpa a sessão de erros se o formulário for inválido
            if 'upload_error_details' in request.session:
                del request.session['upload_error_details'] 
            return render(request, self.template_name, {'form': form})

        file = request.FILES['file']
        
        try:
            df = pd.read_excel(file, dtype=str).fillna('') # Lê tudo como texto para preservar dados originais
        except Exception as e:
            messages.error(request, f"Erro ao ler o arquivo Excel: {e}")
            return redirect(request.path)

        # Verifica se o DataFrame está vazio (nenhuma linha de dados)
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
        error_details_for_session = [] # Para armazenar dados para o relatório

        valid_natureza = AtaReuniao.Natureza.values
        valid_status = AtaReuniao.Status.values

        for index, row in df.iterrows():
            linha = index + 2
            original_row_data = row.to_dict()

            try:
                # ... (todas as suas validações, como na implementação anterior) ...
                # Validação de Contrato
                try:
                    contrato = Cliente.objects.get(pk=int(row['contrato_id']))
                except Cliente.DoesNotExist:
                    raise ValueError(f"Contrato com ID '{row['contrato_id']}' não encontrado.")
                # ... etc ...

                # Se tudo OK, cria o objeto
                # ... (código de criação do objeto) ...

                success_count += 1

            except Exception as e:
                error_message = f"Linha {linha}: {e}"
                errors.append(error_message)
                
                # Adiciona dados da linha e o erro para o relatório
                original_row_data['motivo_do_erro'] = str(e)
                error_details_for_session.append(original_row_data)

        # Armazena erros na sessão para download posterior
        if error_details_for_session:
            request.session['upload_error_details'] = error_details_for_session

        # Mensagens de Feedback para o usuário
        if success_count > 0:
            messages.success(request, f"{success_count} ata(s) de reunião importada(s) com sucesso!")

        if errors:
            error_summary = f"<strong>{len(errors)} linha(s) não puderam ser importadas.</strong><br>Baixe o relatório de erros para corrigir e tente novamente."
            messages.warning(request, error_summary, extra_tags='safe')
            
        # Redireciona para a mesma página para mostrar as mensagens e o botão de download
        return redirect(request.path)


@login_required
def download_error_report(request):
    """
    Gera um arquivo Excel com as linhas que falharam durante o upload,
    incluindo uma coluna com o motivo do erro.
    """
    error_details = request.session.get('upload_error_details')

    if not error_details:
        messages.error(request, "Nenhum relatório de erros encontrado na sessão.")
        return redirect('ata_reuniao:ata_reuniao_upload')

    # Cria um DataFrame do pandas com os detalhes do erro
    df_errors = pd.DataFrame(error_details)
    
    # Reordena as colunas para o formato original e adiciona a coluna de erro no final
    original_columns_order = [
        "contrato_id", "coordenador_id", "responsavel_id", "natureza", "titulo",
        "acao", "entrada", "prazo", "status"
    ]
    df_errors = df_errors[original_columns_order + ['motivo_do_erro']]

    # Renomeia as colunas de volta para o formato amigável do template
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
        
        # Formatação (opcional, mas recomendado)
        workbook = writer.book
        worksheet = writer.sheets['Erros_Para_Correcao']
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="C00000", end_color="C00000", fill_type="solid") # Vermelho para erros

        for col_num, value in enumerate(df_errors.columns.values, 1):
            cell = worksheet.cell(row=1, column=col_num)
            cell.font = header_font
            cell.fill = header_fill
            worksheet.column_dimensions[get_column_letter(col_num)].width = 25
        worksheet.column_dimensions[get_column_letter(len(df_errors.columns))].width = 50 # Coluna de erro maior


    output.seek(0)

    # Limpa a sessão após gerar o relatório
    del request.session['upload_error_details']

    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="relatorio_erros_importacao.xlsx"'
    return response
    

