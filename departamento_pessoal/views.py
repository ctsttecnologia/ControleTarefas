
# departamento_pessoal/views.py

import pandas as pd
from django.http import HttpResponse
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.db.models import Q,  Prefetch 
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Count, Avg
from django.utils import timezone
from django.template.loader import render_to_string

from weasyprint import HTML
from .models import Funcionario, Departamento, Cargo, Documento
from .forms import AdmissaoForm, FuncionarioForm, DepartamentoForm, CargoForm, DocumentoForm
from .mixins import StaffRequiredMixin # Seu mixin
import json
import io
from docx import Document

from departamento_pessoal import models



class StaffRequiredMixin(PermissionRequiredMixin):
    """
    Mixin que garante que o usuário tem permissão para acessar
    as views do departamento pessoal. Altere a permissão conforme necessário.
    """
    permission_required = 'auth.view_user' # Exemplo: apenas quem pode ver usuários
    raise_exception = True # Levanta um erro 403 se não tiver permissão

# --- VIEWS PARA FUNCIONÁRIOS ---

class FuncionarioListView(StaffRequiredMixin, ListView):
    model = Funcionario
    template_name = 'departamento_pessoal/lista_funcionarios.html'
    context_object_name = 'funcionarios'
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset().select_related('cargo', 'departamento').order_by('nome_completo')
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(nome_completo__icontains=query) |
                Q(matricula__icontains=query) |
                Q(cargo__nome__icontains=query)
            )
        return queryset

class FuncionarioDetailView(StaffRequiredMixin, DetailView):
    model = Funcionario
    template_name = 'departamento_pessoal/detalhe_funcionario.html'
    context_object_name = 'funcionario'

    def get_queryset(self):
        """
        Otimiza a consulta para o novo modelo.
        Agora só precisamos de select_related para os ForeignKeys diretos.
        """
        return super().get_queryset().select_related('usuario', 'cargo', 'departamento')

class FuncionarioCreateView(StaffRequiredMixin, CreateView):
    model = Funcionario
    form_class = FuncionarioForm
    template_name = 'departamento_pessoal/funcionario_form.html'
    
    def get_success_url(self):
        messages.success(self.request, "Funcionário cadastrado com sucesso!")
        return reverse_lazy('departamento_pessoal:detalhe_funcionario', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = "Cadastrar Novo Funcionário"
        return context

class FuncionarioUpdateView(StaffRequiredMixin, UpdateView):
    model = Funcionario
    form_class = FuncionarioForm
    template_name = 'departamento_pessoal/funcionario_form.html'

    def get_success_url(self):
        messages.success(self.request, "Dados do funcionário atualizados com sucesso!")
        return reverse_lazy('departamento_pessoal:detalhe_funcionario', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f"Editar: {self.object.nome_completo}"
        return context

class FuncionarioDeleteView(StaffRequiredMixin, DetailView):
    model = Funcionario
    template_name = 'departamento_pessoal/confirm_delete.html'
    context_object_name = 'funcionario' # Adicionado para clareza no template

    def post(self, request, *args, **kwargs):
        """
        Este método é chamado quando o formulário é enviado.
        Ele verifica qual botão foi pressionado ('inativar' ou 'excluir').
        """
        # Carrega o objeto funcionário que está sendo visualizado
        funcionario = self.get_object()
        
        # Pega a ação do botão que foi clicado no formulário
        action = request.POST.get('action')

        if action == 'inativar':
            # Ação de "Soft Delete": Apenas muda o status
            funcionario.status = 'INATIVO'
            funcionario.save()
            messages.warning(request, f"O funcionário '{funcionario.nome_completo}' foi INATIVADO, mas seus dados foram mantidos.")

        elif action == 'excluir':
            # Ação de Exclusão Permanente: Deleta o registro do banco de dados
            nome_completo = funcionario.nome_completo
            funcionario.delete()
            messages.error(request, f"O funcionário '{nome_completo}' foi EXCLUÍDO PERMANENTEMENTE.")

        # Redireciona para a lista de funcionários após qualquer uma das ações
        return redirect(reverse_lazy('departamento_pessoal:lista_funcionarios'))

# --- VIEWS PARA O PROCESSO DE ADMISSÃO (NOVAS) ---

class FuncionarioAdmissaoView(StaffRequiredMixin, UpdateView):
    """
    View para preencher os dados de admissão de um funcionário.
    Usa o formulário focado 'AdmissaoForm'.
    """
    model = Funcionario
    form_class = AdmissaoForm
    template_name = 'departamento_pessoal/admissao_form.html' # Usaremos um template único

    def get_success_url(self):
        # Após salvar a admissão, volta para a página de detalhes do funcionário
        messages.success(self.request, f"Dados de admissão de '{self.object.nome_completo}' salvos com sucesso!")
        return reverse('departamento_pessoal:detalhe_funcionario', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object.data_admissao:
             context['titulo_pagina'] = f"Editar Admissão de {self.object.nome_completo}"
        else:
             context['titulo_pagina'] = f"Registrar Admissão para {self.object.nome_completo}"
        return context

# --- VIEWS PARA DEPARTAMENTO ---
class DepartamentoListView(StaffRequiredMixin, ListView):
    model = Departamento
    template_name = 'departamento_pessoal/lista_departamento.html'
    context_object_name = 'departamentos'

class DepartamentoCreateView(StaffRequiredMixin, CreateView):
    model = Departamento
    form_class = DepartamentoForm
    template_name = 'departamento_pessoal/departamento_form.html'
    success_url = reverse_lazy('departamento_pessoal:lista_departamento')
    extra_context = {'titulo_pagina': 'Novo Departamento'}

    def form_valid(self, form):
        messages.success(self.request, "Departamento criado com sucesso.")
        return super().form_valid(form)


class DepartamentoUpdateView(StaffRequiredMixin, UpdateView):
    model = Departamento
    form_class = DepartamentoForm
    template_name = 'departamento_pessoal/departamento_form.html'
    success_url = reverse_lazy('departamento_pessoal:lista_departamento')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f"Editar Departamento: {self.object.nome}"
        return context
    
    def form_valid(self, form):
        messages.success(self.request, "Departamento atualizado com sucesso.")
        return super().form_valid(form)


# --- VIEWS PARA CARGOS ---
class CargoListView(StaffRequiredMixin, ListView):
    model = Cargo
    template_name = 'departamento_pessoal/lista_cargo.html'
    context_object_name = 'cargos'

class CargoCreateView(StaffRequiredMixin, CreateView):
    model = Cargo
    form_class = CargoForm
    template_name = 'departamento_pessoal/cargo_form.html'
    success_url = reverse_lazy('departamento_pessoal:lista_cargo')
    extra_context = {'titulo_pagina': 'Novo Cargo'}

    def form_valid(self, form):
        messages.success(self.request, "Cargo criado com sucesso.")
        return super().form_valid(form)

class CargoUpdateView(StaffRequiredMixin, UpdateView):
    model = Cargo
    form_class = CargoForm
    template_name = 'departamento_pessoal/cargo_form.html'
    success_url = reverse_lazy('departamento_pessoal:lista_cargo')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f"Editar Cargo: {self.object.nome}"
        return context

    def form_valid(self, form):
        messages.success(self.request, "Cargo atualizado com sucesso.")
        return super().form_valid(form)


# --- VIEWS PARA DOCUMENTOS (ADICIONADAS) ---

class DocumentoListView(StaffRequiredMixin, ListView):
    model = Documento
    template_name = 'departamento_pessoal/lista_documentos.html'
    context_object_name = 'documentos'
    paginate_by = 10

    def get_initial(self):
        """Passa o funcionário (se existir na URL) como valor inicial para o form."""
        if 'funcionario_pk' in self.kwargs:
            return {'funcionario': self.kwargs['funcionario_pk']}
        return {}

    def get_queryset(self):
        queryset = Documento.objects.select_related('funcionario').order_by('funcionario__nome_completo', 'tipo')
        
        # Filtro por tipo de documento
        tipo_query = self.request.GET.get('tipo')
        if tipo_query:
            queryset = queryset.filter(tipo=tipo_query)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tipos_documento'] = Documento.TIPO_CHOICES
        return context

# departamento_pessoal/views.py

class DocumentoCreateView(StaffRequiredMixin, CreateView):
    model = Documento
    form_class = DocumentoForm
    template_name = 'departamento_pessoal/documento_form.html' # Ajuste o caminho se necessário

    def form_valid(self, form):
        """
        Este método é chamado quando o formulário é válido.
        Aqui associamos o documento ao funcionário correto antes de salvar.
        """
        # Pega o objeto do funcionário usando o 'funcionario_pk' vindo da URL
        funcionario = get_object_or_404(Funcionario, pk=self.kwargs['funcionario_pk'])
        
        # Define o campo 'funcionario' do objeto documento que está sendo criado
        form.instance.funcionario = funcionario
        
        messages.success(self.request, f"Documento adicionado com sucesso para {funcionario.nome_completo}.")
        return super().form_valid(form)

    def get_success_url(self):
        """
        Define para onde o usuário será redirecionado após o sucesso.
        Neste caso, de volta para a página de detalhes do funcionário.
        """
        return reverse('departamento_pessoal:detalhe_funcionario', kwargs={'pk': self.kwargs['funcionario_pk']})
    
    def form_valid(self, form):
        # Se um funcionário foi passado pela URL, associa-o ao documento
        if 'funcionario_pk' in self.kwargs:
            form.instance.funcionario = get_object_or_404(Funcionario, pk=self.kwargs['funcionario_pk'])
        messages.success(self.request, "Documento cadastrado com sucesso!")
        return super().form_valid(form)


class DocumentoUpdateView(StaffRequiredMixin, UpdateView):
    model = Documento
    form_class = DocumentoForm
    template_name = 'departamento_pessoal/documento_form.html'
    success_url = reverse_lazy('departamento_pessoal:lista_documentos')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f'Editar Documento de {self.object.funcionario.nome_completo}'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, "Documento atualizado com sucesso.")
        return super().form_valid(form)

# --- VIEW DO PAINEL ---

class PainelDPView(StaffRequiredMixin, TemplateView):
    template_name = 'departamento_pessoal/painel_dp.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # --- DADOS PARA OS CARDS DE KPI ---
        funcionarios_ativos = Funcionario.objects.filter(status='ATIVO')
        context['total_funcionarios_ativos'] = funcionarios_ativos.count()
        context['total_departamentos'] = Departamento.objects.filter(ativo=True).count()
        context['total_cargos'] = Cargo.objects.filter(ativo=True).count() # Adicionado para seu card

        # --- DADOS PARA OS GRÁFICOS ---
        # 1. Gráfico de Funcionários por Departamento
        func_por_depto = Departamento.objects.filter(ativo=True).annotate(
            num_funcionarios=Count('funcionario', filter=Q(funcionario__status='ATIVO'))
        ).values('nome', 'num_funcionarios').order_by('-num_funcionarios')
        
        context['depto_labels'] = json.dumps([d['nome'] for d in func_por_depto])
        context['depto_data'] = json.dumps([d['num_funcionarios'] for d in func_por_depto])

        # 2. Gráfico de Distribuição por Status
        dist_status = Funcionario.objects.values('status').annotate(
            total=Count('status')
        ).order_by('status')
        
        context['status_labels'] = json.dumps([s['status'] for s in dist_status])
        context['status_data'] = json.dumps([s['total'] for s in dist_status])

        context['titulo_pagina'] = "Painel de Controle DP"
        return context
# Relatório Excel #    
class ExportarFuncionariosExcelView(StaffRequiredMixin, View):
    """
    Class-Based View para gerar um relatório de funcionários em formato .xlsx
    usando um DataFrame do Pandas.
    """
    def get(self, request, *args, **kwargs):
        
        # 1. Busca os dados no banco de dados, otimizando a consulta
        funcionarios = Funcionario.objects.select_related('cargo', 'departamento').all()

        # 2. Prepara os dados em uma lista de dicionários
        data = []
        for f in funcionarios:
            data.append({
                'Matrícula': f.matricula,
                'Nome Completo': f.nome_completo,
                'Email Pessoal': f.email_pessoal,
                'Telefone': f.telefone,
                'Cargo': f.cargo.nome if f.cargo else '-',
                'Departamento': f.departamento.nome if f.departamento else '-',
                'Data de Admissão': f.data_admissao.strftime('%d/%m/%Y') if f.data_admissao else '-',
                'Salário': f.salario,
                'Status': f.get_status_display(),
            })

        # 3. Cria o DataFrame do Pandas a partir da lista de dados
        df = pd.DataFrame(data)

        # 4. Cria a resposta HTTP com o tipo de conteúdo correto para .xlsx
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        # Define o cabeçalho para forçar o download com o nome de arquivo correto
        response['Content-Disposition'] = 'attachment; filename="relatorio_funcionarios.xlsx"'

        # 5. Usa o motor do pandas para escrever o DataFrame na resposta HTTP
        # `index=False` impede que o índice do DataFrame (0, 1, 2...) seja salvo na planilha
        df.to_excel(response, index=False)

        return response
    
class ExportarFuncionariosPDFView(StaffRequiredMixin, View):
    """
    Gera um relatório de funcionários em formato PDF usando um template HTML.
    """
    def get(self, request, *args, **kwargs):
        # Filtra apenas funcionários ativos para o relatório
        funcionarios = Funcionario.objects.select_related('cargo', 'departamento').filter(status='ATIVO')

        context = {
            'funcionarios': funcionarios,
            'data_emissao': timezone.now().strftime('%d/%m/%Y às %H:%M'),
        }

        # Renderiza o template HTML como uma string
        html_string = render_to_string('departamento_pessoal/relatorio_funcionarios_pdf.html', context)

        # Gera o PDF a partir da string HTML
        # O base_url é necessário para encontrar arquivos estáticos, se houver
        html = HTML(string=html_string, base_url=request.build_absolute_uri())
        pdf_file = html.write_pdf()

        # Cria a resposta HTTP com o tipo de conteúdo para PDF
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="relatorio_funcionarios.pdf"'

        return response
    
class ExportarFuncionariosWordView(StaffRequiredMixin, View):
    """
    Gera um relatório de funcionários em formato .docx usando python-docx.
    """
    def get(self, request, *args, **kwargs):
        # 1. Busca os dados
        funcionarios = Funcionario.objects.select_related('cargo', 'departamento').filter(status='ATIVO')

        # 2. Cria um documento Word em memória
        document = Document()
        document.add_heading('Relatório de Colaboradores', level=1)
        
        # Adiciona um parágrafo com a data de emissão
        data_emissao = timezone.now().strftime('%d/%m/%Y às %H:%M')
        document.add_paragraph(f'Relatório gerado em: {data_emissao}', style='Caption')
        document.add_paragraph() # Adiciona um espaço

        # 3. Cria a tabela com cabeçalhos
        table = document.add_table(rows=1, cols=4)
        table.style = 'Table Grid' # Estilo de tabela com bordas

        # Define os cabeçalhos
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Nome Completo'
        hdr_cells[1].text = 'Cargo'
        hdr_cells[2].text = 'Departamento'
        hdr_cells[3].text = 'Data de Admissão'

        # 4. Preenche a tabela com os dados dos funcionários
        for f in funcionarios:
            row_cells = table.add_row().cells
            row_cells[0].text = f.nome_completo
            row_cells[1].text = f.cargo.nome if f.cargo else '-'
            row_cells[2].text = f.departamento.nome if f.departamento else '-'
            row_cells[3].text = f.data_admissao.strftime('%d/%m/%Y') if f.data_admissao else '-'

        # 5. Salva o documento em um buffer de memória
        buffer = io.BytesIO()
        document.save(buffer)
        buffer.seek(0) # Retorna o "cursor" do buffer para o início

        # 6. Cria a resposta HTTP com o tipo de conteúdo para .docx
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        response['Content-Disposition'] = 'attachment; filename="relatorio_funcionarios.docx"'
        
        return response    
