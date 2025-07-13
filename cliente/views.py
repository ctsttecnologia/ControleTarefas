
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponse
from .models import Cliente
from .forms import ClienteForm

import openpyxl
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter

class ClienteListView(LoginRequiredMixin, ListView):
    model = Cliente
    template_name = 'cliente/cliente_list.html'
    context_object_name = 'clientes'
    paginate_by = 10  # Adiciona paginação

    def get_queryset(self):
        queryset = super().get_queryset().select_related('logradouro').order_by('nome')
        termo_pesquisa = self.request.GET.get('q', '')
        if termo_pesquisa:
            # Busca por nome, razão social, CNPJ ou contrato
            queryset = queryset.filter(
                Q(nome__icontains=termo_pesquisa) |
                Q(razao_social__icontains=termo_pesquisa) |
                Q(cnpj__icontains=termo_pesquisa) |
                Q(contrato__icontains=termo_pesquisa)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['termo_pesquisa'] = self.request.GET.get('q', '')
        context['total_clientes'] = self.get_queryset().count()
        return context

class ClienteCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Cliente
    form_class = ClienteForm
    template_name = 'cliente/cliente_form.html'
    success_url = reverse_lazy('cliente:lista_clientes')
    success_message = "Cliente cadastrado com sucesso!"

class ClienteUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Cliente
    form_class = ClienteForm
    template_name = 'cliente/cliente_form.html'
    success_url = reverse_lazy('cliente:lista_clientes')
    success_message = "Cliente atualizado com sucesso!"

class ClienteDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Cliente
    template_name = 'cliente/cliente_confirm_delete.html'
    success_url = reverse_lazy('cliente:lista_clientes')
    success_message = "Cliente excluído com sucesso!"

class ExportarClientesExcelView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        clientes = Cliente.objects.select_related('logradouro').order_by('nome')
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Clientes"

        # Estilos (simplificados para brevidade)
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="0d6efd", end_color="0d6efd", fill_type="solid")
        
        headers = ["ID", "Nome Fantasia", "Razão Social", "CNPJ", "Contrato", "Endereço", "Telefone", "Email", "Status"]
        
        for col_num, header_title in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num)
            cell.value = header_title
            cell.font = header_font
            cell.fill = header_fill
            ws.column_dimensions[get_column_letter(col_num)].width = 20

        for row_num, cliente in enumerate(clientes, 2):
            ws.cell(row=row_num, column=1, value=cliente.pk)
            ws.cell(row=row_num, column=2, value=cliente.nome)
            ws.cell(row=row_num, column=3, value=cliente.razao_social)
            ws.cell(row=row_num, column=4, value=cliente.cnpj_formatado)
            ws.cell(row=row_num, column=5, value=cliente.contrato)
            ws.cell(row=row_num, column=6, value=str(cliente.logradouro))
            ws.cell(row=row_num, column=7, value=cliente.telefone)
            ws.cell(row=row_num, column=8, value=cliente.email)
            ws.cell(row=row_num, column=9, value="Ativo" if cliente.estatus else "Inativo")

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="clientes.xlsx"'
        wb.save(response)
        return response


