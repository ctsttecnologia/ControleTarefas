
# departamento_pessoal/views.py

import json
import io
import pandas as pd
from docx import Document as PyDocxDocument
from weasyprint import HTML

# Módulos Django
from django.db.models import Q, Count
from django.http import HttpResponse
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DetailView, TemplateView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.template.loader import render_to_string
from django.utils import timezone

# Módulos Locais
from .models import Funcionario, Departamento, Cargo, Documento
from .forms import AdmissaoForm, FuncionarioForm, DepartamentoForm, CargoForm, DocumentoForm

# --- MIXINS ---

class FilialScopedMixin:
    """
    Mixin que filtra a queryset principal de uma View baseada na 'filial'
    do usuário logado. Requer que o modelo associado à view possua um
    manager com o método `for_request`.
    """
    def get_queryset(self):
        # A lógica começa buscando a queryset da classe pai na hierarquia (MRO).
        qs = super().get_queryset()

        # O filtro de filial é delegado ao manager customizado do modelo.
        # Isso centraliza a lógica de segregação de dados no manager.
        # Assumimos que todos os modelos relevantes têm o manager `FilialManager`.
        return qs.model.objects.for_request(self.request)


class StaffRequiredMixin(PermissionRequiredMixin):
    """
    Mixin que garante que o usuário tem permissão para acessar
    as views do departamento pessoal.
    """
    permission_required = 'auth.view_user' # Exemplo: apenas quem pode ver usuários
    raise_exception = True # Levanta um erro 403 (Forbidden) se não tiver permissão


# --- VIEWS PARA FUNCIONÁRIOS ---

class FuncionarioListView(FilialScopedMixin, StaffRequiredMixin, ListView):
    model = Funcionario
    template_name = 'departamento_pessoal/lista_funcionarios.html'
    context_object_name = 'funcionarios'
    paginate_by = 15

    def get_queryset(self):
        # A filtragem de filial já foi feita pelo mixin. Aqui aplicamos apenas a busca.
        queryset = super().get_queryset().select_related('cargo', 'departamento').order_by('nome_completo')
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(nome_completo__icontains=query) |
                Q(matricula__icontains=query) |
                Q(cargo__nome__icontains=query)
            )
        return queryset

class FuncionarioDetailView(FilialScopedMixin, StaffRequiredMixin, DetailView):
    model = Funcionario
    template_name = 'departamento_pessoal/detalhe_funcionario.html'
    context_object_name = 'funcionario'
    queryset = Funcionario.objects.select_related('usuario', 'cargo', 'departamento').all()

    def get_queryset(self):
        """
        Otimiza a consulta para o novo modelo.
        Agora só precisamos de select_related para os ForeignKeys diretos.
        """
        return super().get_queryset().select_related('usuario', 'cargo', 'departamento')

class FuncionarioCreateView(FilialScopedMixin, StaffRequiredMixin, CreateView):
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

class FuncionarioUpdateView(FilialScopedMixin, StaffRequiredMixin, UpdateView):
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

class FuncionarioDeleteView(FilialScopedMixin, StaffRequiredMixin, DetailView):
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

class FuncionarioAdmissaoView(FilialScopedMixin, StaffRequiredMixin, UpdateView):
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
class DepartamentoListView(FilialScopedMixin, StaffRequiredMixin, ListView):
    model = Departamento
    template_name = 'departamento_pessoal/lista_departamento.html'
    context_object_name = 'departamentos'

class DepartamentoCreateView(FilialScopedMixin, StaffRequiredMixin, CreateView):
    model = Departamento
    form_class = DepartamentoForm
    template_name = 'departamento_pessoal/departamento_form.html'
    success_url = reverse_lazy('departamento_pessoal:lista_departamento')
    extra_context = {'titulo_pagina': 'Novo Departamento'}

    def form_valid(self, form):
        messages.success(self.request, "Departamento criado com sucesso.")
        return super().form_valid(form)


class DepartamentoUpdateView(FilialScopedMixin, StaffRequiredMixin, UpdateView):
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
class CargoListView(FilialScopedMixin, StaffRequiredMixin, ListView):
    model = Cargo
    template_name = 'departamento_pessoal/lista_cargo.html'
    context_object_name = 'cargos'

class CargoCreateView(FilialScopedMixin, StaffRequiredMixin, CreateView):
    model = Cargo
    form_class = CargoForm
    template_name = 'departamento_pessoal/cargo_form.html'
    success_url = reverse_lazy('departamento_pessoal:lista_cargo')
    extra_context = {'titulo_pagina': 'Novo Cargo'}

    def form_valid(self, form):
        messages.success(self.request, "Cargo criado com sucesso.")
        return super().form_valid(form)

class CargoUpdateView(FilialScopedMixin, StaffRequiredMixin, UpdateView):
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

class DocumentoListView(FilialScopedMixin, StaffRequiredMixin, ListView):
    model = Documento
    template_name = 'departamento_pessoal/lista_documentos.html'
    context_object_name = 'documentos'
    paginate_by = 10

    def get_queryset(self):
        # CORREÇÃO: A consulta agora começa com `super().get_queryset()`,
        # invocando o FilialScopedMixin e garantindo a filtragem por filial.
        queryset = super().get_queryset().select_related('funcionario').order_by('funcionario__nome_completo', 'tipo')
        
        tipo_query = self.request.GET.get('tipo')
        if tipo_query:
            queryset = queryset.filter(tipo=tipo_query)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tipos_documento'] = Documento.TIPO_CHOICES
        return context

# departamento_pessoal/views.py

class DocumentoCreateView(FilialScopedMixin, StaffRequiredMixin, CreateView):
    model = Documento
    form_class = DocumentoForm
    template_name = 'departamento_pessoal/documento_form.html'

    def form_valid(self, form):
        # CORREÇÃO DE SEGURANÇA: A busca pelo funcionário é feita DENTRO
        # do escopo de filiais do usuário, para impedir a associação cruzada.
        funcionario_pk = self.kwargs.get('funcionario_pk')
        if not funcionario_pk:
            messages.error(self.request, "ID do funcionário não fornecido.")
            return redirect('departamento_pessoal:lista_funcionarios')

        # Busca o funcionário apenas dentro do conjunto de dados permitido.
        funcionario = get_object_or_404(Funcionario.objects.for_request(self.request), pk=funcionario_pk)
        
        form.instance.funcionario = funcionario
        messages.success(self.request, f"Documento adicionado com sucesso para {funcionario.nome_completo}.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('departamento_pessoal:detalhe_funcionario', kwargs={'pk': self.kwargs['funcionario_pk']})

class DocumentoUpdateView(FilialScopedMixin, StaffRequiredMixin, UpdateView):
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

class PainelDPView(LoginRequiredMixin, StaffRequiredMixin, TemplateView):
    template_name = 'departamento_pessoal/painel_dp.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # CORREÇÃO CRÍTICA: Todas as consultas agora usam o manager escopado
        # `for_request` para garantir que os dados sejam APENAS da filial do usuário.
        funcionarios_qs = Funcionario.objects.for_request(self.request)
        departamentos_qs = Departamento.objects.for_request(self.request)
        cargos_qs = Cargo.objects.for_request(self.request)
        
        # --- KPIs escopados por filial ---
        context['total_funcionarios_ativos'] = funcionarios_qs.filter(status='ATIVO').count()
        context['total_departamentos'] = departamentos_qs.filter(ativo=True).count()
        context['total_cargos'] = cargos_qs.filter(ativo=True).count()

        # --- Gráficos escopados por filial ---
        func_por_depto = departamentos_qs.filter(ativo=True).annotate(
        num_funcionarios=Count('funcionarios', filter=Q(funcionarios__status='ATIVO'))
        ).values('nome', 'num_funcionarios').order_by('-num_funcionarios')
            
        context['depto_labels'] = json.dumps([d['nome'] for d in func_por_depto])
        context['depto_data'] = json.dumps([d['num_funcionarios'] for d in func_por_depto])

        dist_status = funcionarios_qs.values('status').annotate(total=Count('status')).order_by('status')
        context['status_labels'] = json.dumps([s['status'] for s in dist_status])
        context['status_data'] = json.dumps([s['total'] for s in dist_status])

        context['titulo_pagina'] = "Painel de Controle DP"
        return context

class BaseExportView(LoginRequiredMixin, StaffRequiredMixin, View):
    """
    Classe base para views de exportação, para evitar repetição de código.
    A lógica principal de filtragem por filial está aqui.
    """
    def get_scoped_queryset(self):
        # CORREÇÃO CRÍTICA: Centraliza a busca de dados escopados.
        return Funcionario.objects.for_request(self.request).select_related('cargo', 'departamento')


# Relatório Excel #    
class ExportarFuncionariosExcelView(BaseExportView):
    def get(self, request, *args, **kwargs):
        funcionarios = self.get_scoped_queryset().all()
        
        data = [
            {
                'Matrícula': f.matricula, 'Nome Completo': f.nome_completo, 'Cargo': f.cargo.nome if f.cargo else '-',
                'Departamento': f.departamento.nome if f.departamento else '-',
                'Data de Admissão': f.data_admissao.strftime('%d/%m/%Y') if f.data_admissao else '-',
                'Status': f.get_status_display()
            }
            for f in funcionarios
        ]
        df = pd.DataFrame(data)

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="relatorio_funcionarios.xlsx"'
        df.to_excel(response, index=False)
        return response
    
class ExportarFuncionariosPDFView(FilialScopedMixin, StaffRequiredMixin, View):
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

class ExportarFuncionariosPDFView(BaseExportView):
    def get(self, request, *args, **kwargs):
        funcionarios = self.get_scoped_queryset().filter(status='ATIVO')
        
        context = {
            'funcionarios': funcionarios,
            'data_emissao': timezone.now().strftime('%d/%m/%Y às %H:%M'),
        }
        html_string = render_to_string('departamento_pessoal/relatorio_funcionarios_pdf.html', context)
        html = HTML(string=html_string, base_url=request.build_absolute_uri())
        pdf_file = html.write_pdf()

        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="relatorio_funcionarios.pdf"'
        return response


class ExportarFuncionariosWordView(BaseExportView):
    def get(self, request, *args, **kwargs):
        funcionarios = self.get_scoped_queryset().filter(status='ATIVO')
        
        document = PyDocxDocument()
        document.add_heading('Relatório de Colaboradores', level=1)
        # ... (lógica completa de criação do DOCX) ...
        table = document.add_table(rows=1, cols=4)
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Nome Completo'; hdr_cells[1].text = 'Cargo'; hdr_cells[2].text = 'Departamento'; hdr_cells[3].text = 'Data de Admissão'
        for f in funcionarios:
            row_cells = table.add_row().cells
            row_cells[0].text = f.nome_completo; row_cells[1].text = f.cargo.nome if f.cargo else '-'; # ... etc

        buffer = io.BytesIO()
        document.save(buffer)
        buffer.seek(0)

        response = HttpResponse(buffer.getvalue(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = 'attachment; filename="relatorio_funcionarios.docx"'
        return response
    
