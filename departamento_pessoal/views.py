# departamento_pessoal/views.py

import json
import io
from os import error
import pandas as pd
from docx import Document as PyDocxDocument
from docx.enum.text import WD_ALIGN_PARAGRAPH
from weasyprint import HTML
# Módulos Django
from django.db.models import Q, Count, Avg, Max, Min, F
from django.http import HttpResponse
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DetailView, TemplateView, DeleteView
from django.contrib import messages
from django.template.loader import render_to_string
from django.utils import timezone
from django.core.exceptions import PermissionDenied

from seguranca_trabalho.models import Funcao
from .models import Funcionario, Departamento, Cargo, Documento, Filial, Cliente
from .forms import AdmissaoForm, FuncionarioForm, DepartamentoForm, CargoForm, DocumentoForm
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from core.mixins import ViewFilialScopedMixin, FilialCreateMixin
from django.db import IntegrityError, transaction
from django.utils.dateparse import parse_date
from .forms import UploadFuncionariosForm
from io import BytesIO
from django.views import View
from openpyxl.styles import Font, PatternFill, Alignment, NamedStyle
from openpyxl.worksheet.datavalidation import DataValidation
from django.db import IntegrityError
import logging
from datetime import timedelta



# --- Funções Auxiliares ---

class ImportacaoError(Exception):
    """Exceção customizada para erros durante a importação da planilha."""
    def __init__(self, message, column_name=None):
        self.message = message
        self.column_name = column_name
        super().__init__(self.message)

    def __str__(self):
        if self.column_name:
            return f"Coluna '{self.column_name}': {self.message}"
        return self.message

# Nomes das colunas que estarão na planilha modelo
COLUNAS_ESPERADAS = [
    'matricula', 'nome_completo', 'data_admissao', 'data_nascimento',
    'email_pessoal', 'telefone', 'salario', 'status', 'sexo',
    'nome_cargo', 'cbo', 'nome_funcao', 'nome_departamento', 'nome_filial', 'nome_cliente'
]


class UploadFuncionariosView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    View para lidar com o upload e processamento da planilha de funcionários.
    """
    permission_required = 'departamento_pessoal.add_funcionario'
    form_class = UploadFuncionariosForm
    template_name = 'departamento_pessoal/upload_funcionarios.html'

    def get(self, request, *args, **kwargs):
        """Lida com a requisição GET, exibindo o formulário limpo."""
        # A limpeza da sessão foi movida para a view 'baixar_relatorio_erros'.
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        """
        Lida com a requisição POST, orquestrando a validação e o processamento do arquivo.
        """
        form = self.form_class(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        arquivo_excel = request.FILES['arquivo']

        # 1. Validações iniciais do arquivo e das colunas
        try:
            df = self._ler_e_validar_planilha(arquivo_excel)
        except ValueError as e:
            messages.error(request, str(e))
            return render(request, self.template_name, {'form': form})
        
        # 2. Processamento dos dados da planilha
        sucessos_count, linhas_com_erro = self._processar_dataframe(df)

        # 3. Feedback ao usuário com base no resultado
        if linhas_com_erro:
            request.session['upload_erros'] = linhas_com_erro
            msg = (f"A importação falhou. Foram encontrados {len(linhas_com_erro)} erros. "
                   "Nenhum funcionário foi salvo. Baixe o relatório de erros para corrigi-los.")
            messages.error(request, msg)
        else:
            msg = f"Importação concluída com sucesso! {sucessos_count} funcionários foram criados/atualizados."
            messages.success(request, msg)

        return redirect(reverse('departamento_pessoal:upload_funcionarios'))

    def _ler_e_validar_planilha(self, arquivo):
        """
        Lê o arquivo Excel para um DataFrame e valida sua estrutura.
        Lança ValueError se houver problemas.
        """
        if not arquivo.name.endswith('.xlsx'):
            raise ValueError('Erro: O arquivo deve ser do formato .xlsx')

        try:
            df = pd.read_excel(arquivo, dtype=str).fillna('')
        except Exception as e:
            raise ValueError(f"Erro ao ler o arquivo Excel: {e}")

        if not all(col in df.columns for col in COLUNAS_ESPERADAS):
            colunas_faltantes = set(COLUNAS_ESPERADAS) - set(df.columns)
            raise ValueError(f"Erro: As seguintes colunas obrigatórias não foram encontradas na planilha: {', '.join(colunas_faltantes)}")
        
        return df

    def _processar_dataframe(self, df):
        """
        Itera sobre o DataFrame, processando cada linha e formatando os erros de forma clara.
        """
        linhas_com_erro = []
        sucessos_count = 0

        try:
            with transaction.atomic():
                for index, row in df.iterrows():
                    linha_num = index + 2  # Número da linha como visto no Excel
                    try:
                        self._processar_linha(row)
                        sucessos_count += 1
                    except ImportacaoError as e:
                        # Captura nosso erro customizado e formata a mensagem
                        erro_msg = f"Linha {linha_num}, {e}"
                        linha_erro = row.to_dict()
                        linha_erro['Erro'] = erro_msg
                        linhas_com_erro.append(linha_erro)
                    except Exception as e:
                        # Captura qualquer outro erro inesperado e o reporta
                        erro_msg = f"Linha {linha_num}: Erro inesperado. Contate o suporte. (Detalhe: {str(e)})"
                        linha_erro = row.to_dict()
                        linha_erro['Erro'] = erro_msg
                        linhas_com_erro.append(linha_erro)
                
                if linhas_com_erro:
                    raise IntegrityError("Erros encontrados durante a importação.")
        
        except IntegrityError:
            return 0, linhas_com_erro
        
        return sucessos_count, linhas_com_erro

    def _processar_linha(self, row):
        """
        Valida e salva os dados de uma única linha.
        Exige que Filial e Cliente já existam no sistema.
        Cria Cargos, Funções e Departamentos automaticamente se necessário.
        """
        # 1. Validação de datas (sem alterações, já estava correto)
        data_admissao_str = row.get('data_admissao', '').strip()
        if not data_admissao_str:
            raise ImportacaoError("Este campo é obrigatório.", column_name='data_admissao')
        data_admissao = pd.to_datetime(data_admissao_str, dayfirst=True, errors='coerce')
        if pd.isna(data_admissao):
            raise ImportacaoError(f"O valor '{data_admissao_str}' está em um formato inválido. Use DD-MM-AAAA.", column_name='data_admissao')
        
        data_nascimento_str = row.get('data_nascimento', '').strip()
        data_nascimento = pd.to_datetime(data_nascimento_str, dayfirst=True, errors='coerce') if data_nascimento_str else None
        if data_nascimento_str and pd.isna(data_nascimento):
                raise ImportacaoError(f"O valor '{data_nascimento_str}' está em um formato inválido. Use DD-MM-AAAA.", column_name='data_nascimento')

        # 2. Busca de Objetos Relacionados
        
        nome_filial_excel = row['nome_filial'].strip()
        if not nome_filial_excel:
            raise ImportacaoError("Este campo é obrigatório.", column_name='nome_filial')
        try:
            filial = Filial.objects.get(nome__iexact=nome_filial_excel)
        except Filial.DoesNotExist:
            raise ImportacaoError(f"A Filial '{nome_filial_excel}' não foi encontrada no sistema. Cadastre-a primeiro.", column_name='nome_filial')

        # Etapa B: Garante que o CARGO exista (ou o cria), associado à filial e com o CBO correto.
        nome_cargo_excel = row['nome_cargo'].strip()
        if not nome_cargo_excel:
            raise ImportacaoError("Este campo é obrigatório.", column_name='nome_cargo')
        
        # Pega a string do CBO da planilha.
        cbo_excel = row.get('cbo', '').strip() 
        
        # cria um novo usando os valores em 'defaults', incluindo o CBO.
        cargo, _ = Cargo.objects.get_or_create(
            nome__iexact=nome_cargo_excel,
            filial=filial,
            defaults={
                'nome': nome_cargo_excel.title(), 
                'filial': filial,
                'cbo': cbo_excel  # Salva a STRING do CBO diretamente no Cargo.
            }
        )

        # Etapa C: Garante que a FUNÇÃO exista (ou a cria), se informada. (Seu código está correto)
        funcao = None
        nome_funcao_excel = row.get('nome_funcao', '').strip()
        if nome_funcao_excel:
            funcao, _ = Funcao.objects.get_or_create(
                nome__iexact=nome_funcao_excel,
                filial=filial,
                defaults={'nome': nome_funcao_excel.title(), 'filial': filial}
            )

        # Etapa D: Departamento 
        nome_dpto_excel = row['nome_departamento'].strip()
        if not nome_dpto_excel:
            raise ImportacaoError("Este campo é obrigatório.", column_name='nome_departamento')
        departamento, _ = Departamento.objects.get_or_create(
            nome__iexact=nome_dpto_excel, 
            filial=filial, 
            defaults={'nome': nome_dpto_excel.title(), 'filial': filial}
        )

        # Etapa E: Cliente 
        cliente = None
        nome_cliente_excel = row.get('nome_cliente', '').strip()
        if nome_cliente_excel:
            try:
                cliente = Cliente.objects.get(nome__iexact=nome_cliente_excel)
            except Cliente.DoesNotExist:
                raise ImportacaoError(f"O Cliente '{nome_cliente_excel}' não foi encontrado no sistema. Cadastre-o primeiro.", column_name='nome_cliente')

        # 3. Validação de campos de escolha 
        status = row.get('status', '').upper().strip()
        if not status:
            raise ImportacaoError("Este campo é obrigatório.", column_name='status')
        if status not in dict(Funcionario.STATUS_CHOICES):
            raise ImportacaoError(f"O valor '{row.get('status')}' é inválido.", column_name='status')
        
        sexo = row.get('sexo', '').upper().strip() or None
        if sexo and sexo not in dict(Funcionario.SEXO_CHOICES):
            raise ImportacaoError(f"O valor '{row.get('sexo')}' para 'sexo' é inválido.", column_name='sexo')

        # 4. Criação ou atualização do funcionário (agora com a variável `cbo` correta)
        Funcionario.objects.update_or_create(
            matricula=row['matricula'].strip(),
            defaults={
                'nome_completo': row['nome_completo'].strip().upper(),
                'data_admissao': data_admissao.date(),
                'data_nascimento': data_nascimento.date() if pd.notna(data_nascimento) else None,
                'cargo': cargo,
                'funcao': funcao,
                'departamento': departamento,
                'filial': filial,
                'cliente': cliente,
                'status': status,
                'salario': float(row['salario']) if row['salario'] else 0.00,
                'email_pessoal': row['email_pessoal'].strip() or None,
                'telefone': row['telefone'].strip(),
                'sexo': sexo,
            }
        )
    
def baixar_modelo_funcionarios(request):
    """
    Gera e fornece o arquivo .xlsx modelo, agora com formatação profissional,
    largura de colunas ajustada e validação de dados (dropdowns).
    """
    df_modelo = pd.DataFrame(columns=COLUNAS_ESPERADAS)
    
    output = BytesIO()
    
    # Usar ExcelWriter para ter acesso ao objeto da planilha (workbook/worksheet)
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_modelo.to_excel(writer, index=False, sheet_name='Funcionarios')
        
        # Obter o worksheet para poder formatá-lo
        workbook = writer.book
        worksheet = writer.sheets['Funcionarios']

        # Adicionar um estilo de texto
        text_style = NamedStyle(name='text_style', number_format='@')
        workbook.add_named_style(text_style)
        
        # 1. Definir Estilos para o Cabeçalho
        header_font = Font(bold=True, color="FFFFFF", name="Calibri")
        header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")

        # 2. Aplicar Estilos e Ajustar Largura das Colunas
        for col_num, column_title in enumerate(df_modelo.columns, 1):
            cell = worksheet.cell(row=1, column=col_num)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment

            # Se a coluna for de data, aplica o estilo de texto a ela
            if 'data_' in column_title:
                for r in range(2, 5000): # Aplica para um número grande de linhas
                    worksheet.cell(row=r, column=col_num).style = text_style
            
            # Ajustar a largura da coluna com base no tamanho do texto do cabeçalho
            column_letter = cell.column_letter
            worksheet.column_dimensions[column_letter].width = len(column_title) + 5

        # 3. Adicionar Validação de Dados (Dropdowns) para 'status' e 'sexo'
        
        # Dropdown para STATUS (assumindo que a coluna 'status' é a 8ª, ou 'H')
        status_options = f'"{",".join([choice[0] for choice in Funcionario.STATUS_CHOICES])}"'
        dv_status = DataValidation(type="list", formula1=status_options, allow_blank=True)
        dv_status.add('H2:H1048576') # Aplica a validação para toda a coluna H
        worksheet.add_data_validation(dv_status)

        # Dropdown para SEXO (assumindo que a coluna 'sexo' é a 9ª, ou 'I')
        sexo_options = f'"{",".join([choice[0] for choice in Funcionario.SEXO_CHOICES])}"'
        dv_sexo = DataValidation(type="list", formula1=sexo_options, allow_blank=True)
        dv_sexo.add('I2:I1048576') # Aplica a validação para toda a coluna I
        worksheet.add_data_validation(dv_sexo)
        
        # 4. Congelar o Painel do Cabeçalho
        worksheet.freeze_panes = 'A2'

    output.seek(0)
    
    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="modelo_importacao_funcionarios.xlsx"'
    
    return response


def baixar_relatorio_erros(request):
    """
    Gera um arquivo Excel com as linhas que continham erros durante o upload.
    """
    linhas_com_erro = request.session.get('upload_erros', [])

    if not linhas_com_erro:
        messages.warning(request, "Não há relatório de erros para baixar.")
        return redirect(reverse('departamento_pessoal:upload_funcionarios'))
    
    # Limpa a sessão LOGO APÓS usar os dados. Este é o lugar correto.
    request.session.pop('upload_erros', None)

    df_erros = pd.DataFrame(linhas_com_erro)
    
    # Limpa os dados da sessão após recuperá-los
    request.session.pop('upload_erros', None)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_erros.to_excel(writer, index=False, sheet_name='Erros')
    output.seek(0)

    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="relatorio_erros_importacao.xlsx"'
    return response


class StaffRequiredMixin(PermissionRequiredMixin):
    """
    Mixin que garante que o usuário tem permissão para acessar
    as views do departamento pessoal.
    """
    permission_required = 'usuario.view_usuario' # Exemplo: apenas quem pode ver usuários
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
   

class DocumentoListView(StaffRequiredMixin, ListView):
    model = Documento
    template_name = 'departamento_pessoal/lista_documentos.html'
    context_object_name = 'documentos'
    paginate_by = 20

    def get_queryset(self):
        # Começa com o queryset base
        queryset = super().get_queryset()
        
        # Filtro obrigatório por Filial (Segurança)
        filial_id = self.request.session.get('active_filial_id')
        if not filial_id:
            messages.error(self.request, "Por favor, selecione uma filial para ver os documentos.")
            return self.model.objects.none()
        
        queryset = queryset.filter(funcionario__filial_id=filial_id).select_related('funcionario', 'funcionario__cargo')
        
        # 1. Filtro por Tipo de Documento
        tipo_documento = self.request.GET.get('tipo', '')
        if tipo_documento:
            queryset = queryset.filter(tipo_documento=tipo_documento)

        # 2. Filtro de Pesquisa (Nome do Funcionário OU Número do Documento)
        query_text = self.request.GET.get('q', '')
        if query_text:
            queryset = queryset.filter(
                Q(funcionario__nome_completo__icontains=query_text) |
                Q(numero__icontains=query_text)
            )

        return queryset.order_by('funcionario__nome_completo', 'tipo_documento')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Passamos as opções para preencher o <select> no template
        context['tipos_documento'] = Documento.TIPO_CHOICES
        return context

class DocumentoCreateView(FilialCreateMixin, StaffRequiredMixin, CreateView):
    model = Documento
    form_class = DocumentoForm
    template_name = 'departamento_pessoal/documento_form.html'

    def get_initial(self):
        initial = super().get_initial()
        funcionario_pk = self.kwargs.get('funcionario_pk')
        if funcionario_pk:
            filial_id = self.request.session.get('active_filial_id')
            # Usando filter().first() para evitar 404 se a filial mudar durante a sessão
            funcionario = Funcionario.objects.filter(pk=funcionario_pk, filial_id=filial_id).first()
            if funcionario:
                initial['funcionario'] = funcionario
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        funcionario_pk = self.kwargs.get('funcionario_pk')
        if funcionario_pk:
            context['funcionario'] = Funcionario.objects.filter(pk=funcionario_pk).first()
        return context
        
    def form_valid(self, form):
        try:
            messages.success(self.request, "Documento adicionado com sucesso.")
            return super().form_valid(form)
        except IntegrityError:
            # Captura erro de unicidade (ex: tentar cadastrar CPF duas vezes para o mesmo funcionário)
            form.add_error('tipo_documento', 'Este funcionário já possui um documento deste tipo cadastrado.')
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse('departamento_pessoal:detalhe_funcionario', kwargs={'pk': self.object.funcionario.pk})

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
        # Retorna para o detalhe do funcionário é mais intuitivo que a lista geral
        return reverse('departamento_pessoal:detalhe_funcionario', kwargs={'pk': self.object.funcionario.pk})

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except IntegrityError:
            form.add_error('tipo_documento', 'Já existe outro registro deste tipo de documento para este funcionário.')
            return self.form_invalid(form)
    

    
# Adicione a view de exclusão de documento
class DocumentoDeleteView(DocumentoScopedMixin, StaffRequiredMixin, DeleteView):
    model = Documento
    template_name = 'departamento_pessoal/documento_confirm_delete.html' # Crie este template
    context_object_name = 'documento'

    def get_success_url(self):
        messages.success(self.request, "Documento excluído com sucesso.")
        # self.object é o documento que foi excluído
        return reverse_lazy('departamento_pessoal:detalhe_funcionario', kwargs={'pk': self.object.funcionario.pk})

    
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

        # Querysets base
        funcionarios_qs = Funcionario.objects.filter(filial_id=filial_id)
        departamentos_qs = Departamento.objects.filter(filial_id=filial_id)
        
        # KPIs básicos
        context['total_funcionarios_ativos'] = funcionarios_qs.filter(status='ATIVO').count()
        context['total_departamentos'] = departamentos_qs.filter(ativo=True).count()
        context['total_cargos'] = Cargo.objects.filter(filial_id=filial_id, ativo=True).count()

        # --- DADOS PARA OS NOVOS GRÁFICOS ---

        # 1. Gráfico de Pizza - Funcionários por Departamento
        func_por_depto = departamentos_qs.filter(ativo=True).annotate(
            num_funcionarios=Count('funcionarios', filter=Q(funcionarios__status='ATIVO'))
        ).values('nome', 'num_funcionarios').order_by('-num_funcionarios')
                
        context['depto_labels'] = [d['nome'] for d in func_por_depto]
        context['depto_data'] = [d['num_funcionarios'] for d in func_por_depto]

        # 2. Gráfico de Status
        dist_status = funcionarios_qs.values('status').annotate(total=Count('status')).order_by('status')
        status_display_map = dict(Funcionario.STATUS_CHOICES)
        
        status_labels = []
        status_data = []
        for s in dist_status:
            label_amigavel = status_display_map.get(s['status'], s['status'])
            status_labels.append(label_amigavel)
            status_data.append(s['total'])

        context['status_labels'] = status_labels
        context['status_data'] = status_data

        # 3. Gráfico de Barras - Distribuição Salarial por Cargo (TOP 10)
        salarios_por_cargo = funcionarios_qs.filter(
            status='ATIVO', 
            salario__gt=0
        ).values(
            'cargo__nome'
        ).annotate(
            salario_medio=Avg('salario'),
            total_funcionarios=Count('id')
        ).order_by('-salario_medio')[:10]

        context['cargo_salario_labels'] = [item['cargo__nome'] for item in salarios_por_cargo]
        context['cargo_salario_data'] = [float(item['salario_medio']) for item in salarios_por_cargo]

        # 4. Gráfico de Linha - Admissões por Mês (Últimos 12 meses)
        doze_meses_atras = timezone.now().date() - timedelta(days=365)
        admissoes_por_mes = funcionarios_qs.filter(
            data_admissao__gte=doze_meses_atras
        ).extra(
            {'mes': "EXTRACT(month FROM data_admissao)", 'ano': "EXTRACT(year FROM data_admissao)"}
        ).values('ano', 'mes').annotate(
            total=Count('id')
        ).order_by('ano', 'mes')

        meses = []
        totais = []
        for adm in admissoes_por_mes:
            mes_ano = f"{int(adm['mes'])}/{int(adm['ano'])}"
            meses.append(mes_ano)
            totais.append(adm['total'])

        context['admissoes_meses_labels'] = meses
        context['admissoes_meses_data'] = totais

        # 5. Gráfico de Dispersão - Idade vs Salário
        funcionarios_com_idade_salario = funcionarios_qs.filter(
            status='ATIVO',
            data_nascimento__isnull=False,
            salario__gt=0
        ).values('data_nascimento', 'salario', 'sexo')[:50]  # Limitar para performance

        dispersao_data = []
        for func in funcionarios_com_idade_salario:
            if func['data_nascimento']:
                idade = (timezone.now().date() - func['data_nascimento']).days // 365
                dispersao_data.append({
                    'x': idade,
                    'y': float(func['salario']),
                    'sexo': func['sexo'] or 'N/A'
                })

        context['dispersao_data'] = dispersao_data

        # 6. Estatísticas Detalhadas
        salarios_ativos = funcionarios_qs.filter(status='ATIVO', salario__gt=0)
        
        if salarios_ativos.exists():
            context['salario_medio'] = salarios_ativos.aggregate(Avg('salario'))['salario__avg']
            context['salario_maximo'] = salarios_ativos.aggregate(Max('salario'))['salario__max']
            context['salario_minimo'] = salarios_ativos.aggregate(Min('salario'))['salario__min']
            
            # Cálculo da idade média
            from datetime import date
            hoje = date.today()
            idades = []
            for func in funcionarios_qs.filter(status='ATIVO', data_nascimento__isnull=False):
                idade = hoje.year - func.data_nascimento.year - (
                    (hoje.month, hoje.day) < (func.data_nascimento.month, func.data_nascimento.day)
                )
                idades.append(idade)
            
            context['idade_media'] = sum(idades) / len(idades) if idades else 0
        else:
            context['salario_medio'] = 0
            context['salario_maximo'] = 0
            context['salario_minimo'] = 0
            context['idade_media'] = 0

        # 7. Distribuição por Gênero
        dist_genero = funcionarios_qs.filter(status='ATIVO').values('sexo').annotate(
            total=Count('id')
        )
        
        genero_labels = []
        genero_data = []
        genero_display_map = dict(Funcionario.SEXO_CHOICES)
        
        for g in dist_genero:
            label = genero_display_map.get(g['sexo'], g['sexo'] or 'Não informado')
            genero_labels.append(label)
            genero_data.append(g['total'])

        context['genero_labels'] = genero_labels
        context['genero_data'] = genero_data

        context['titulo_pagina'] = "Painel de Controle DP - Analytics"
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
    
