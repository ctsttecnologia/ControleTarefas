# departamento_pessoal/views.py

import json
import io
import pandas as pd
from docx import Document as PyDocxDocument
from docx.enum.text import WD_ALIGN_PARAGRAPH
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
from django.core.exceptions import PermissionDenied

# Módulos Locais
from usuario.models import Filial
from .models import Funcionario, Departamento, Cargo, Documento
from .forms import AdmissaoForm, FuncionarioForm, DepartamentoForm, CargoForm, DocumentoForm
from core.mixins import ViewFilialScopedMixin, FilialCreateMixin



class StaffRequiredMixin(PermissionRequiredMixin):
    """
    Mixin que garante que o usuário tem permissão para acessar
    as views do departamento pessoal.
    """
    permission_required = 'auth.view_user' # Exemplo: apenas quem pode ver usuários
    raise_exception = True # Levanta um erro 403 (Forbidden) se não tiver permissão

# --- VIEWS PARA FUNCIONÁRIOS ---

class FuncionarioListView(ViewFilialScopedMixin, StaffRequiredMixin, ListView):
    model = Funcionario
    template_name = 'departamento_pessoal/lista_funcionarios.html'
    context_object_name = 'funcionarios'
    paginate_by = 15

    def get_queryset(self):
        # A chamada super() agora é limpa. O mixin cuida da filtragem por filial.
        queryset = super().get_queryset().select_related('cargo', 'departamento').order_by('nome_completo')
        
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(nome_completo__icontains=query) |
                Q(matricula__icontains=query) |
                Q(cargo__nome__icontains=query)
            )
        return queryset

class FuncionarioCreateView(FilialCreateMixin, StaffRequiredMixin, CreateView):
    model = Funcionario
    form_class = FuncionarioForm
    template_name = 'departamento_pessoal/funcionario_form.html'
    extra_context = {'titulo_pagina': "Cadastrar Novo Funcionário"}
    
    def get_success_url(self):
        # A mensagem de sucesso já é tratada pelo FilialCreateMixin.
        return reverse_lazy('departamento_pessoal:detalhe_funcionario', kwargs={'pk': self.object.pk})


class FuncionarioDetailView(ViewFilialScopedMixin, StaffRequiredMixin, DetailView):
    model = Funcionario
    template_name = 'departamento_pessoal/detalhe_funcionario.html'
    context_object_name = 'funcionario'

    def get_queryset(self):
        # Adiciona otimização, mantendo a filtragem do mixin.
        return super().get_queryset().select_related('usuario', 'cargo', 'departamento')

    
class FuncionarioUpdateView(ViewFilialScopedMixin, StaffRequiredMixin, UpdateView):
    model = Funcionario
    form_class = FuncionarioForm
    template_name = 'departamento_pessoal/funcionario_form.html'

    def get_queryset(self):
        # Otimização da query. A filtragem por filial é herdada do mixin.
        return super().get_queryset().select_related('usuario', 'cargo', 'departamento')

    def get_success_url(self):
        messages.success(self.request, "Dados do funcionário atualizados com sucesso!")
        return reverse_lazy('departamento_pessoal:detalhe_funcionario', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f"Editar: {self.object.nome_completo}"
        return context

class FuncionarioDeleteView(ViewFilialScopedMixin, StaffRequiredMixin, DetailView):
    model = Funcionario
    template_name = 'departamento_pessoal/confirm_delete.html'
    context_object_name = 'funcionario'
    
    def post(self, request, *args, **kwargs):
        funcionario = self.get_object()
        action = request.POST.get('action')

        if action == 'inativar':
            funcionario.status = 'INATIVO'
            funcionario.save()
            messages.warning(request, f"O funcionário '{funcionario.nome_completo}' foi INATIVADO.")
        elif action == 'excluir':
            nome_completo = funcionario.nome_completo
            funcionario.delete()
            messages.error(request, f"O funcionário '{nome_completo}' foi EXCLUÍDO PERMANENTEMENTE.")

        return redirect(reverse_lazy('departamento_pessoal:lista_funcionarios'))


# --- VIEWS PARA O PROCESSO DE ADMISSÃO (NOVAS) ---

class FuncionarioAdmissaoView(ViewFilialScopedMixin, StaffRequiredMixin, UpdateView):
    model = Funcionario
    form_class = AdmissaoForm
    template_name = 'departamento_pessoal/admissao_form.html'

    def get_success_url(self):
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
class DepartamentoListView(ViewFilialScopedMixin, StaffRequiredMixin, ListView):
    model = Departamento
    template_name = 'departamento_pessoal/lista_departamento.html'
    context_object_name = 'departamentos'

    def get_queryset(self):
        # Adiciona filtro extra sobre o queryset já filtrado pelo mixin.
        return super().get_queryset().filter(ativo=True)


class DepartamentoCreateView(FilialCreateMixin, StaffRequiredMixin, CreateView):
    model = Departamento
    form_class = DepartamentoForm
    template_name = 'departamento_pessoal/departamento_form.html'
    success_url = reverse_lazy('departamento_pessoal:lista_departamento')
    extra_context = {'titulo_pagina': 'Novo Departamento'}


class DepartamentoUpdateView(ViewFilialScopedMixin, StaffRequiredMixin, UpdateView):
    model = Departamento
    form_class = DepartamentoForm
    template_name = 'departamento_pessoal/departamento_form.html'
    success_url = reverse_lazy('departamento_pessoal:lista_departamento')

    def form_valid(self, form):
        messages.success(self.request, "Departamento atualizado com sucesso.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f"Editar Departamento: {self.object.nome}"
        return context
    
# --- VIEWS PARA CARGOS ---

class CargoListView(ViewFilialScopedMixin, StaffRequiredMixin, ListView):
    model = Cargo
    template_name = 'departamento_pessoal/lista_cargo.html'
    context_object_name = 'cargos'

    def get_queryset(self):
        return super().get_queryset().filter(ativo=True)

class CargoCreateView(FilialCreateMixin, StaffRequiredMixin, CreateView):
    model = Cargo
    form_class = CargoForm
    template_name = 'departamento_pessoal/cargo_form.html'
    success_url = reverse_lazy('departamento_pessoal:lista_cargo')
    extra_context = {'titulo_pagina': 'Novo Cargo'}

class CargoUpdateView(ViewFilialScopedMixin, StaffRequiredMixin, UpdateView):
    model = Cargo
    form_class = CargoForm
    template_name = 'departamento_pessoal/cargo_form.html'
    success_url = reverse_lazy('departamento_pessoal:lista_cargo')

    def form_valid(self, form):
        messages.success(self.request, "Cargo atualizado com sucesso.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f"Editar Cargo: {self.object.nome}"
        return context

# --- VIEWS PARA DOCUMENTOS (ADICIONADAS) 
# O mixin padrão não funcionará. Precisamos de uma lógica customizada.
#class DocumentoListView(StaffRequiredMixin, ListView): 
#    model = Documento
#    template_name = 'departamento_pessoal/lista_documentos.html'
#    context_object_name = 'documentos'
#    paginate_by = 10

#    def get_queryset(self):
#        # A chave da sessão que você usa é 'active_filial_id'
#        filial_id = self.request.session.get('active_filial_id') 
#        
#        # SE a linha acima não encontrar nada (retornar None),
#        # a condição abaixo se torna verdadeira e o erro é lançado.
#        if not filial_id: 
 #           raise PermissionDenied("Nenhuma filial selecionada.")
        
        # O resto do código, que filtra os documentos, nem chega a ser executado.
#        queryset = super().get_queryset().filter(funcionario__filial_id=filial_id)
        
#        return queryset
    

class DocumentoListView(StaffRequiredMixin, ListView):
    model = Documento
    template_name = 'departamento_pessoal/lista_documentos.html'
    context_object_name = 'documentos'
    paginate_by = 10

    def get_queryset(self):
        filial_id = self.request.session.get('active_filial_id')
        if not filial_id:
            messages.error(self.request, "Por favor, selecione uma filial para ver os documentos.")
            return self.model.objects.none() # Retorna queryset vazia em vez de erro
        
        # Filtra documentos cujo funcionário pertence à filial ativa.
        queryset = super().get_queryset().filter(funcionario__filial_id=filial_id).select_related('funcionario')
        return queryset


# A segurança aqui é garantir que o funcionário ao qual estamos adicionando
# o documento pertence à filial ativa.
class DocumentoCreateView(StaffRequiredMixin, CreateView):
    model = Documento
    form_class = DocumentoForm
    template_name = 'departamento_pessoal/documento_form.html'

    def form_valid(self, form):
        filial_id = self.request.session.get('active_filial_id')
        if not filial_id:
            raise PermissionDenied("Nenhuma filial selecionada.")

        # Garante que o funcionário ao qual estamos adicionando o documento
        # pertence à filial ativa na sessão, prevenindo manipulação de ID na URL.
        funcionario_pk = self.kwargs.get('funcionario_pk')
        funcionario = get_object_or_404(Funcionario, pk=funcionario_pk, filial_id=filial_id)
        
        form.instance.funcionario = funcionario
        messages.success(self.request, f"Documento adicionado com sucesso para {funcionario.nome_completo}.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('departamento_pessoal:detalhe_funcionario', kwargs={'pk': self.kwargs['funcionario_pk']})

# A lógica de update de documento precisa garantir que o usuário não edite
# um documento de outra filial. Podemos criar um mixin simples para isso.
class DocumentoScopedMixin:
    def get_queryset(self):
        qs = super().get_queryset()
        filial_id = self.request.session.get('active_filial_id')
        if not filial_id:
            raise PermissionDenied("Nenhuma filial selecionada.")
        return qs.filter(funcionario__filial_id=filial_id)

class DocumentoUpdateView(DocumentoScopedMixin, StaffRequiredMixin, UpdateView):
    model = Documento
    form_class = DocumentoForm
    template_name = 'departamento_pessoal/documento_form.html'

    def get_success_url(self):
        messages.success(self.request, "Documento atualizado com sucesso.")
        # Retorna para a lista geral, pois o contexto do funcionário pode se perder.
        return reverse_lazy('departamento_pessoal:lista_documentos')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f'Editar Documento de {self.object.funcionario.nome_completo}'
        return context
    
# --- VIEW DO PAINEL ---

class PainelDPView(LoginRequiredMixin, StaffRequiredMixin, TemplateView):
    template_name = 'departamento_pessoal/painel_dp.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filial_id = self.request.session.get('active_filial_id')
        if not filial_id:
            context['permission_denied'] = True
            messages.error(self.request, "Selecione uma filial para visualizar o painel.")
            return context

        # CORREÇÃO CRÍTICA: Filtrar todas as querysets pela filial da sessão.
        funcionarios_qs = Funcionario.objects.filter(filial_id=filial_id)
        departamentos_qs = Departamento.objects.filter(filial_id=filial_id)
        
        context['total_funcionarios_ativos'] = funcionarios_qs.filter(status='ATIVO').count()
        context['total_departamentos'] = departamentos_qs.filter(ativo=True).count()
        context['total_cargos'] = Cargo.objects.filter(filial_id=filial_id, ativo=True).count()

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
    def get_scoped_queryset(self):
        filial_id = self.request.session.get('active_filial_id')
        if not filial_id:
            raise PermissionDenied("Nenhuma filial selecionada para exportar dados.")
        return Funcionario.objects.filter(filial_id=filial_id).select_related('cargo', 'departamento')


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
    
# Unificando as views de PDF e fazendo herdar da BaseExportView
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
        # 1. Obter os dados já filtrados pela filial ativa e com status 'ATIVO'
        funcionarios = self.get_scoped_queryset().filter(status='ATIVO')

        # 2. Criar um documento Word em branco na memória
        document = PyDocxDocument()

        # --- Início da Construção do Documento ---

        # Adicionar um título principal ao documento
        document.add_heading('Relatório de Colaboradores Ativos', level=1)

        # Adicionar metadados do relatório (data de emissão e filial)
        data_emissao = timezone.now().strftime('%d/%m/%Y às %H:%M')
        # Pega o nome da filial a partir do primeiro funcionário (se existir)
        nome_filial = funcionarios.first().filial.nome if funcionarios.exists() else "N/A"
        
        document.add_paragraph(f"Filial: {nome_filial}")
        document.add_paragraph(f"Data de Emissão: {data_emissao}")
        document.add_paragraph(f"Total de Colaboradores Listados: {len(funcionarios)}")

        # Adicionar um espaço antes da tabela
        document.add_paragraph()

        # 3. Criar a tabela de dados
        # Definir os cabeçalhos das colunas
        colunas = ['Matrícula', 'Nome Completo', 'Cargo', 'Departamento', 'Data de Admissão']
        
        tabela = document.add_table(rows=1, cols=len(colunas))
        tabela.style = 'Table Grid' # Estilo de tabela com bordas

        # Preencher a linha de cabeçalho
        hdr_cells = tabela.rows[0].cells
        for i, nome_coluna in enumerate(colunas):
            cell = hdr_cells[i]
            cell.text = nome_coluna
            # Deixar o texto do cabeçalho em negrito
            cell.paragraphs[0].runs[0].font.bold = True
            # Centralizar o texto do cabeçalho
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

        # 4. Preencher a tabela com os dados dos funcionários
        for f in funcionarios:
            row_cells = tabela.add_row().cells
            row_cells[0].text = f.matricula or '-'
            row_cells[1].text = f.nome_completo
            row_cells[2].text = f.cargo.nome if f.cargo else '-'
            row_cells[3].text = f.departamento.nome if f.departamento else '-'
            row_cells[4].text = f.data_admissao.strftime('%d/%m/%Y') if f.data_admissao else '-'

        # --- Fim da Construção do Documento ---

        # 5. Salvar o documento em um buffer de memória
        buffer = io.BytesIO()
        document.save(buffer)
        # É crucial "rebobinar" o buffer para o início antes de lê-lo.
        buffer.seek(0) 

        # 6. Criar a HttpResponse com o conteúdo do buffer
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        response['Content-Disposition'] = 'attachment; filename="relatorio_colaboradores_ativos.docx"'
        
        return response
    
