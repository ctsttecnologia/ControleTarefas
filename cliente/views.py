
# Módulos Django e de Terceiros
from django.db.models import Q
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
# Módulos Locais
from .models import Cliente
from .forms import ClienteForm
# Bibliotecas para Excel
import openpyxl
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter
from core.mixins import FilialScopedQuerysetMixin


# --- VIEWS DE CLIENTE (CRUD) ---

class ClienteListView(LoginRequiredMixin, FilialScopedQuerysetMixin, ListView):
    model = Cliente
    template_name = 'cliente/cliente_list.html'
    context_object_name = 'clientes'
    paginate_by = 10

    def get_queryset(self):
        # A filtragem por filial já foi feita pelo FilialScopedMixin.
        # Agora, aplicamos apenas ordenação, otimizações e a busca do usuário.
        queryset = super().get_queryset().select_related('logradouro').order_by('nome')
        
        termo_pesquisa = self.request.GET.get('q', '')
        if termo_pesquisa:
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

        # MELHORIA DE PERFORMANCE:
        # Usa o 'paginator.count' que já foi calculado pelo ListView,
        # em vez de fazer uma nova query com .count().
        if context.get('paginator'):
            context['total_clientes'] = context['paginator'].count
        else:
            # Fallback para o caso de a paginação estar desativada
            context['total_clientes'] = self.object_list.count()
            
        return context


class ClienteCreateView(LoginRequiredMixin, FilialScopedQuerysetMixin, SuccessMessageMixin, CreateView):
    model = Cliente
    form_class = ClienteForm
    template_name = 'cliente/cliente_form.html'
    success_url = reverse_lazy('cliente:lista_clientes')
    success_message = "Cliente cadastrado com sucesso!"


class ClienteUpdateView(LoginRequiredMixin, FilialScopedQuerysetMixin, SuccessMessageMixin, UpdateView):
    model = Cliente
    form_class = ClienteForm
    template_name = 'cliente/cliente_form.html'
    success_url = reverse_lazy('cliente:lista_clientes')
    success_message = "Cliente atualizado com sucesso!"


class ClienteDeleteView(LoginRequiredMixin, FilialScopedQuerysetMixin, SuccessMessageMixin, DeleteView):
    model = Cliente
    template_name = 'cliente/cliente_confirm_delete.html'
    success_url = reverse_lazy('cliente:lista_clientes')
    success_message = "Cliente excluído com sucesso!"


# --- VIEW DE EXPORTAÇÃO ---

class ExportarClientesExcelView(LoginRequiredMixin, FilialScopedQuerysetMixin, ListView):
    """
    Esta view agora herda de FilialScopedMixin e ListView.
    Isso garante que a exportação respeitará a filial do usuário,
    reutilizando a lógica segura do mixin e prevenindo vazamento de dados.
    """
    model = Cliente # Necessário para o ListView e o mixin saberem qual queryset base buscar

    def get(self, request, *args, **kwargs):
        # 1. Usa self.get_queryset() para obter a lista de clientes JÁ FILTRADA pelo mixin.
        clientes = self.get_queryset().select_related('logradouro').order_by('nome')

        # 2. O restante do código para gerar o Excel permanece o mesmo.
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Clientes"

        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="0d6efd", end_color="0d6efd", fill_type="solid")
        
        headers = ["ID", "Nome Fantasia", "Razão Social", "CNPJ", "Contrato", "Endereço", "Telefone", "Email", "Status"]
        
        for col_num, header_title in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num)
            cell.value = header_title
            cell.font = header_font
            cell.fill = header_fill
            ws.column_dimensions[get_column_letter(col_num)].width = 25 # Aumentei um pouco

        for row_num, cliente in enumerate(clientes, 2):
            ws.cell(row=row_num, column=1, value=cliente.pk)
            ws.cell(row=row_num, column=2, value=cliente.nome)
            ws.cell(row=row_num, column=3, value=cliente.razao_social)
            ws.cell(row=row_num, column=4, value=cliente.cnpj_formatado)
            ws.cell(row=row_num, column=5, value=cliente.contrato)
            ws.cell(row=row_num, column=6, value=cliente.data_de_inicio)
            ws.cell(row=row_num, column=7, value=str(cliente.logradouro) if cliente.logradouro else "-")
            ws.cell(row=row_num, column=8, value=cliente.telefone)
            ws.cell(row=row_num, column=9, value=cliente.email)
            ws.cell(row=row_num, column=10, value="Ativo" if cliente.estatus else "Inativo")

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="clientes.xlsx"'
        wb.save(response)
        
        return response
