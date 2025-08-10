from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _

import openpyxl
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter

from .models import Logradouro
from .forms import LogradouroForm
from .constant import ESTADOS_BRASIL

# --- Mixin de Segurança (Correto, sem alterações) ---
class FilialScopedMixin:
    """
    Mixin que filtra a queryset principal de uma View baseada na 'filial'
    do usuário logado.
    """
    def get_queryset(self):
        qs = super().get_queryset()
        # A delegação para o manager customizado do modelo é a abordagem correta.
        return qs.model.objects.for_request(self.request)

# --- Views de Logradouro (CRUD) Corrigidas ---

class LogradouroListView(FilialScopedMixin, LoginRequiredMixin, ListView):
    """
    Lista os logradouros cadastrados, respeitando o escopo da filial.
    """
    model = Logradouro
    template_name = 'logradouro/listar_logradouros.html'
    context_object_name = 'logradouros'
    paginate_by = 15

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # CORREÇÃO: Conta apenas os objetos da queryset já filtrada pelo mixin.
        # 'object_list' é a variável de contexto que armazena a lista filtrada.
        context['total_logradouros'] = self.object_list.count()
        return context

# Removido o FilialScopedMixin, pois não tem efeito em CreateView.
class LogradouroCreateView(LoginRequiredMixin, CreateView):
    """
    Cria um novo logradouro, associando-o automaticamente à filial do usuário.
    """
    model = Logradouro
    form_class = LogradouroForm
    template_name = 'logradouro/form_logradouro.html'
    success_url = reverse_lazy('logradouro:listar_logradouros')

    def form_valid(self, form):
        # CORREÇÃO: Associa a filial do usuário ao novo objeto antes de salvar.
        logradouro = form.save(commit=False)
        if hasattr(self.request.user, 'filial'):
            logradouro.filial = self.request.user.filial
        logradouro.save()
        messages.success(self.request, _('Endereço cadastrado com sucesso!'))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _('Por favor, corrija os erros abaixo.'))
        return super().form_invalid(form)

# Nenhuma alteração necessária aqui, o mixin já garante a segurança.
class LogradouroUpdateView(FilialScopedMixin, LoginRequiredMixin, UpdateView):
    model = Logradouro
    form_class = LogradouroForm
    template_name = 'logradouro/form_logradouro.html'
    success_url = reverse_lazy('logradouro:listar_logradouros')

    def form_valid(self, form):
        messages.success(self.request, _('Endereço atualizado com sucesso!'))
        return super().form_valid(form)

# Nenhuma alteração necessária aqui, o mixin já garante a segurança.
class LogradouroDeleteView(FilialScopedMixin, LoginRequiredMixin, DeleteView):
    model = Logradouro
    template_name = 'logradouro/confirmar_exclusao.html'
    success_url = reverse_lazy('logradouro:listar_logradouros')

    def form_valid(self, form):
        messages.success(self.request, _('Endereço excluído com sucesso!'))
        return super().form_valid(form)

# --- View de Exportação ---

class LogradouroExportExcelView(LoginRequiredMixin, View):
    """
    Exporta a lista de logradouros para Excel, respeitando o escopo da filial.
    """
    def get(self, request, *args, **kwargs):
        # FALHA DE SEGURANÇA CORRIGIDA:
        # Substituímos .all() pelo manager seguro que filtra pela filial do usuário.
        logradouros = Logradouro.objects.for_request(request).order_by('endereco')

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Logradouros"
        
        # Estilos (mesma lógica da sua função original)
        headers = [
            "Endereço", "Número", "CEP", "Complemento", "Bairro", "Cidade", 
            "Estado", "País", "Ponto Referência", "Latitude", "Longitude",
            "Data Cadastro", "Data Atualização"
        ]
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
        thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        center_aligned = Alignment(horizontal='center')
        
               
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num)
            cell.value = header
            cell.font = header_font
            cell.fill = header_fill
            cell.border = thin_border
            cell.alignment = center_aligned
            ws.column_dimensions[get_column_letter(col_num)].width = 20

        for row_num, logradouro in enumerate(logradouros, 2):
            row_data = [
                logradouro.endereco, logradouro.numero, logradouro.cep_formatado(),
                logradouro.complemento, logradouro.bairro, logradouro.cidade,
                logradouro.get_estado_display(), logradouro.pais, logradouro.ponto_referencia,
                logradouro.latitude, logradouro.longitude,
                logradouro.data_cadastro.strftime('%d/%m/%Y %H:%M') if logradouro.data_cadastro else "",
                logradouro.data_atualizacao.strftime('%d/%m/%Y %H:%M') if logradouro.data_atualizacao else ""
            ]
            for col_num, value in enumerate(row_data, 1):
                cell = ws.cell(row=row_num, column=col_num)
                cell.value = value
                cell.border = thin_border

        ws.freeze_panes = 'A2'
        
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': 'attachment; filename="logradouros.xlsx"'}
        )
        wb.save(response)
        return response
