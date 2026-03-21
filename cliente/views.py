
# MÃ³dulos Django e de Terceiros
from django.contrib import messages 
from django.db import models
from django.db.models import Q
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin

from dashboard.views import get_filial_ativa
# MÃ³dulos Locais
from .models import Cliente
from .forms import ClienteForm
# Bibliotecas para Excel
import openpyxl
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter
from core.mixins import ViewFilialScopedMixin
from usuario.models import Filial
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import models as db_models
from logradouro.models import Logradouro
 

# --- VIEWS DE CLIENTE (CRUD) ---

class ClienteListView(LoginRequiredMixin, ViewFilialScopedMixin, ListView):
    model = Cliente
    template_name = 'cliente/cliente_list.html'
    context_object_name = 'clientes'
    paginate_by = 10
    
    def get_queryset(self):
        # A filtragem por filial jÃ¡ foi feita pelo FilialScopedMixin.
        # Agora, aplicamos apenas ordenaÃ§Ã£o, otimizaÃ§Ãµes e a busca do usuÃ¡rio.
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
        # Usa o 'paginator.count' que jÃ¡ foi calculado pelo ListView,
        # em vez de fazer uma nova query com .count().
        if context.get('paginator'):
            context['total_clientes'] = context['paginator'].count
        else:
            # Fallback para o caso de a paginaÃ§Ã£o estar desativada
            context['total_clientes'] = self.object_list.count()
            
        return context


class ClienteCreateView(LoginRequiredMixin, ViewFilialScopedMixin, SuccessMessageMixin, CreateView):
    model = Cliente
    form_class = ClienteForm
    template_name = 'cliente/cliente_form.html'
    success_url = reverse_lazy('cliente:lista_clientes')
    success_message = "Cliente cadastrado com sucesso!"

    def get_queryset(self):
        """
        Garante que o mixin de filial receba o request para filtrar o cliente
        corretamente pela filial do usuÃ¡rio logado.
        """
        return super().get_queryset()
    
    def form_valid(self, form):
        form.instance.criado_por = self.request.user
        messages.success(self.request, 'Cliente cadastrado com sucesso!')
        """
        Atribui a filial ativa do usuÃ¡rio Ã  nova empresa antes de salvar.
        """
        # Pega a filial ativa do usuÃ¡rio logado
        filial_do_usuario = self.request.user.filial_ativa
        # Atribui essa filial Ã  instÃ¢ncia do objeto que estÃ¡ sendo criado
        form.instance.filial = filial_do_usuario
        # Chama o comportamento padrÃ£o (salvar o objeto
        return super().form_valid(form)


class ClienteUpdateView(LoginRequiredMixin, ViewFilialScopedMixin, SuccessMessageMixin, UpdateView):
    model = Cliente
    form_class = ClienteForm
    template_name = 'cliente/cliente_form.html'
    success_url = reverse_lazy('cliente:lista_clientes')
    success_message = "Cliente atualizado com sucesso!"

    def get_queryset(self):
        """
        Garante que o mixin de filial receba o request para filtrar o cliente
        corretamente pela filial do usuÃ¡rio logado.
        """
        return super().get_queryset()  

class ClienteDeleteView(LoginRequiredMixin, ViewFilialScopedMixin, SuccessMessageMixin, DeleteView):
    model = Cliente
    template_name = 'cliente/cliente_confirm_delete.html'
    success_url = reverse_lazy('cliente:lista_clientes')
    success_message = "Cliente excluÃ­do com sucesso!"

    def get_queryset(self):
        """
        Garante que o mixin de filial receba o request para filtrar o cliente
        corretamente pela filial do usuÃ¡rio logado.
        """
        return super().get_queryset()

# --- VIEW DE EXPORTAÃ‡ÃƒO ---

class ExportarClientesExcelView(LoginRequiredMixin, ViewFilialScopedMixin, ListView):
    """
    Esta view agora herda de FilialScopedMixin e ListView.
    Isso garante que a exportaÃ§Ã£o respeitarÃ¡ a filial do usuÃ¡rio,
    reutilizando a lÃ³gica segura do mixin e prevenindo vazamento de dados.
    """
    model = Cliente # NecessÃ¡rio para o ListView e o mixin saberem qual queryset base buscar

    def get(self, request, *args, **kwargs):
        # 1. Usa self.get_queryset() para obter a lista de clientes JÃ FILTRADA pelo mixin.
        clientes = self.get_queryset().select_related('logradouro').order_by('nome')

        # 2. O restante do cÃ³digo para gerar o Excel permanece o mesmo.
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Clientes"

        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="0d6efd", end_color="0d6efd", fill_type="solid")
        
        headers = ["ID", "Nome Fantasia", "RazÃ£o Social", "CNPJ", "Contrato", "EndereÃ§o", "Telefone", "Email", "Status"]
        
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
    
class ClienteDetailView(LoginRequiredMixin, ViewFilialScopedMixin, DetailView):
    model = Cliente
    template_name = 'cliente/cliente_detail.html'
    context_object_name = 'cliente'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Busca os arquivos relacionados a este cliente
        # O 'prefetch_related' otimiza a consulta para evitar lentidÃ£o no banco
        context['arquivos_cliente'] = self.object.documentos_cliente.all()
        return context

# --- NOVA VIEW PARA O AUTOCOMPLETAR ---
@login_required
def cliente_autocomplete_view(request):
    """
    View que retorna clientes para o Select2.
    """
    term = request.GET.get('term', '')

    qs_filtrado_por_filial = Cliente.objects.for_request(request)
    clientes = qs_filtrado_por_filial.filter(
        razao_social__icontains=term
    ).values('id', 'razao_social')[:10]

    return JsonResponse(list(clientes), safe=False)

#___AJAX___

def ajax_buscar_logradouros(request):
    """
    Retorna logradouros filtrados para o autocomplete TomSelect.
    GET /cliente/ajax/logradouros/?q=termo
    """
    q = request.GET.get("q", "").strip()

    if len(q) < 2:
        return JsonResponse([], safe=False)

    qs = Logradouro.objects.filter(
        db_models.Q(endereco__icontains=q)
        | db_models.Q(bairro__icontains=q)
        | db_models.Q(cidade__icontains=q)
        | db_models.Q(cep__icontains=q)
    )[:20]

    results = [
        {
            "id": log.pk,
            "text": f"{log.endereco}, {log.numero} - {log.bairro} - {log.cidade}/{log.estado} - CEP: {log.cep}",
        }
        for log in qs
    ]

    return JsonResponse(results, safe=False)
    

