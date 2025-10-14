# suprimentos/views.py

from django.db import transaction, IntegrityError
from django.urls import reverse, reverse_lazy
from openpyxl.styles import Font, PatternFill, Alignment, NamedStyle
from openpyxl.worksheet.datavalidation import DataValidation
from streamlit import form
from .models import Parceiro, Filial, Logradouro
from .forms import UploadFileForm
from django.db.models import Q
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView, FormView, View
from core.mixins import ViewFilialScopedMixin, FilialCreateMixin, SSTPermissionMixin
from usuario.views import LoginRequiredMixin
from .models import Parceiro, Filial, Logradouro
from .forms import ParceiroForm
import pandas as pd
from io import BytesIO
from django.shortcuts import redirect, render
from django.http import HttpResponse
from django.contrib import messages
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from openpyxl import Workbook
from .forms import UploadFileForm
import json


# =========================================================================
# 1. EXCEÇÃO CUSTOMIZADA (Padrão do seu projeto)
# =========================================================================
class ImportacaoParceiroError(Exception):
    def __init__(self, message, column_name=None):
        self.message = message
        self.column_name = column_name
        super().__init__(self.message)
    def __str__(self):
        if self.column_name:
            return f"Coluna '{self.column_name}': {self.message}"
        return self.message

# =========================================================================
# 2. VIEW DE DOWNLOAD DO MODELO
# =========================================================================
def parceiro_download_template(request):
    columns = ['Nome da Filial*', 'Nome Fantasia*', 'Razão Social', 'CNPJ', 'Inscrição Estadual', 'Pessoa de Contato', 'Telefone', 'Celular', 'E-mail', 'Site', 'É Fabricante? (SIM/NAO)*', 'É Fornecedor? (SIM/NAO)*', 'CEP do Endereço', 'Observações']
    df_modelo = pd.DataFrame(columns=columns)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_modelo.to_excel(writer, index=False, sheet_name='Parceiros')
        workbook = writer.book
        worksheet = writer.sheets['Parceiros']
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4F81BD", fill_type="solid")
        for i, col_title in enumerate(columns, 1):
            cell = worksheet.cell(row=1, column=i)
            cell.font = header_font
            cell.fill = header_fill
            worksheet.column_dimensions[cell.column_letter].width = len(col_title) + 5
        dv = DataValidation(type="list", formula1='"SIM,NAO"', allow_blank=True)
        worksheet.add_data_validation(dv)
        dv.add('K2:L1048576')
        filiais = Filial.objects.all().values_list('nome',)
        df_filiais = pd.DataFrame(filiais, columns=['Nomes de Filiais Válidas'])
        df_filiais.to_excel(writer, index=False, sheet_name='Filiais para Consulta')
        worksheet.freeze_panes = 'A2'
    output.seek(0)
    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheet.sheet')
    response['Content-Disposition'] = 'attachment; filename="modelo_importacao_parceiros.xlsx"'
    return response

# =========================================================================
# 3. VIEW DE UPLOAD (Padrão 'Funcionarios')
# =========================================================================
class ParceiroBulkUploadView(SSTPermissionMixin, View):
    permission_required = 'suprimentos.add_parceiro'
    template_name = 'suprimentos/upload_parceiros.html'
    form_class = UploadFileForm

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        if 'parceiros_upload_erros' in request.session:
            del request.session['parceiros_upload_erros']
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})
        try:
            df = self._ler_e_validar_planilha(request.FILES['file'])
            with transaction.atomic():
                sucessos_count, linhas_com_erro = self._processar_dataframe(df)
                if linhas_com_erro:
                    raise IntegrityError()
            messages.success(request, f"Importação concluída! {sucessos_count} parceiros foram criados/atualizados.")
            return redirect(reverse('suprimentos:parceiro_upload_massa'))
        except (ValueError, IntegrityError, ImportacaoParceiroError) as e:
            msg = str(e) if str(e) else "A importação foi cancelada devido a erros."
            if 'linhas_com_erro' in locals() and linhas_com_erro:
                request.session['parceiros_upload_erros'] = linhas_com_erro
                msg = f"A importação falhou com {len(linhas_com_erro)} erros. Nenhum parceiro foi salvo."
            messages.error(request, msg)
            context = {'form': form, 'errors': [erro['Erro'] for erro in locals().get('linhas_com_erro', [])], 'error_report_available': 'linhas_com_erro' in locals() and bool(linhas_com_erro)}
            return render(request, self.template_name, context)

    def _ler_e_validar_planilha(self, arquivo):
        if not arquivo.name.endswith('.xlsx'):
            raise ValueError('Erro: O arquivo deve ser do formato .xlsx')
        df = pd.read_excel(arquivo, dtype=str).fillna('')
        colunas_esperadas = ['Nome da Filial*', 'Nome Fantasia*', 'Razão Social']
        if not all(col in df.columns for col in colunas_esperadas):
            colunas_faltantes = set(colunas_esperadas) - set(df.columns)
            raise ValueError(f"Erro: Colunas obrigatórias não encontradas: {', '.join(colunas_faltantes)}")
        return df

    def _processar_dataframe(self, df):
        linhas_com_erro, sucessos_count = [], 0
        for index, row in df.iterrows():
            try:
                # A chamada agora está correta, passando apenas a linha (row)
                self._processar_linha(row)
                sucessos_count += 1
            except ImportacaoParceiroError as e:
                linha_erro = row.to_dict()
                linha_erro['Erro'] = f"Linha {index + 2}, {e}"
                linhas_com_erro.append(linha_erro)
        return sucessos_count, linhas_com_erro

    def _processar_linha(self, row):
        # ATENÇÃO: A definição da função agora recebe apenas 'row', como esperado.

        # --- LÓGICA FINAL DA BUSCA MANUAL EM PYTHON ---
        nome_filial_raw = row.get('Nome da Filial*', '').strip()
        if not nome_filial_raw:
            raise ImportacaoParceiroError("Este campo é obrigatório.", column_name='Nome da Filial*')

        todas_as_filiais = Filial.objects.all()
        filial_encontrada = None
        nome_buscado_lower = nome_filial_raw.lower()
        
        for filial_db in todas_as_filiais:
            if filial_db.nome.lower() == nome_buscado_lower:
                filial_encontrada = filial_db
                break

        if not filial_encontrada:
            raise ImportacaoParceiroError(f"A Filial '{nome_filial_raw}' não foi encontrada em uma busca manual.", column_name='Nome da Filial*')
        
        # A variável 'filial' agora contém o objeto correto
        filial = filial_encontrada
        
        # --- O RESTO DA SUA LÓGICA CONTINUA NORMALMENTE ---
        razao_social = row.get('Razão Social', '').strip()
        if not razao_social:
            raise ImportacaoParceiroError("Este campo é obrigatório.", column_name='Razão Social')
        nome_fantasia = row.get('Nome Fantasia*', '').strip()
        if not nome_fantasia:
            raise ImportacaoParceiroError("Este campo é obrigatório.", column_name='Nome Fantasia*')

        endereco = None
        cep = row.get('CEP do Endereço', '').strip()
        if cep:
            endereco = Logradouro.objects.filter(cep=cep).first()
            if not endereco:
                raise ImportacaoParceiroError(f"O CEP '{cep}' não foi encontrado.", column_name='CEP do Endereço')
        
        eh_fabricante = str(row.get('É Fabricante? (SIM/NAO)*', '')).strip().upper() in ['SIM', 'S', 'YES', 'Y', '1']
        eh_fornecedor = str(row.get('É Fornecedor? (SIM/NAO)*', '')).strip().upper() in ['SIM', 'S', 'YES', 'Y', '1']
        cnpj = row.get('CNPJ', '').strip() or None
        
        try:
            if not cnpj:
                identificador = {'razao_social': razao_social, 'filial': filial}
            else:
                identificador = {'cnpj': cnpj}

            Parceiro.objects.update_or_create(
                **identificador,
                defaults={
                    'filial': filial,
                    'nome_fantasia': nome_fantasia,
                    'razao_social': razao_social,
                    'inscricao_estadual': row.get('Inscrição Estadual', '').strip(),
                    'contato': row.get('Pessoa de Contato', '').strip(),
                    'telefone': row.get('Telefone', '').strip(),
                    'celular': row.get('Celular', '').strip(),
                    'email': row.get('E-mail', '').strip(),
                    'site': row.get('Site', '').strip(),
                    'endereco': endereco,
                    'observacoes': row.get('Observações', '').strip(),
                    'eh_fabricante': eh_fabricante,
                    'eh_fornecedor': eh_fornecedor,
                    'ativo': True,
                }
            )
        except Exception as e:
            raise ImportacaoParceiroError(f"Erro ao salvar no banco de dados: {str(e)}")
# =========================================================================
# 4. VIEW PARA DOWNLOAD DO RELATÓRIO DE ERROS
# =========================================================================
def parceiro_download_erros(request):
    """Gera e fornece o download do relatório com as linhas que falharam."""
    linhas_com_erro = request.session.pop('parceiros_upload_erros', [])
    if not linhas_com_erro:
        messages.warning(request, "Não há relatório de erros para baixar.")
        return redirect(reverse('suprimentos:parceiro_upload_massa'))

    df_erros = pd.DataFrame(linhas_com_erro)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_erros.to_excel(writer, index=False, sheet_name='Parceiros_Com_Erros')
    output.seek(0)

    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheet.sheet')
    response['Content-Disposition'] = 'attachment; filename="relatorio_erros_parceiros.xlsx"'
    return response


class ParceiroListView(ViewFilialScopedMixin, SSTPermissionMixin, ListView):
    model = Parceiro
    template_name = 'suprimentos/parceiro_list.html'
    context_object_name = 'parceiros'
    paginate_by = 20
    permission_required = 'suprimentos.view_parceiro' # Adapte as permissões conforme necessário

    def get_queryset(self):
        # Pega o queryset original
        queryset = super().get_queryset().order_by('nome_fantasia')
       # Pega o parâmetro 'q' da URL (o termo de busca)
        query = self.request.GET.get('q')

        # Se houver um termo de busca, filtra o queryset
        if query:
            # Usamos Q objects para fazer uma busca OR em múltiplos campos
            # __icontains faz a busca case-insensitive (ignorando maiúsculas/minúsculas)
            queryset = queryset.filter(
                Q(nome_fantasia__icontains=query) |
                Q(razao_social__icontains=query) |
                Q(cnpj__icontains=query)
            ).distinct()
            
        return queryset
    
class ParceiroDetailView(ViewFilialScopedMixin, SSTPermissionMixin, DetailView):
    model = Parceiro
    template_name = 'suprimentos/parceiro_detail.html'
    context_object_name = 'parceiro'
    permission_required = 'suprimentos.view_parceiro'

class ParceiroCreateView(FilialCreateMixin, SSTPermissionMixin, CreateView):
    model = Parceiro
    form_class = ParceiroForm
    template_name = 'suprimentos/parceiro_form.html'
    success_url = reverse_lazy('suprimentos:parceiro_list')
    permission_required = 'suprimentos.add_parceiro'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Cadastrar Novo Fornecedor'
        return context

class ParceiroUpdateView(ViewFilialScopedMixin, SSTPermissionMixin, UpdateView):
    model = Parceiro
    form_class = ParceiroForm
    template_name = 'suprimentos/parceiro_form.html'
    success_url = reverse_lazy('suprimentos:parceiro_list')
    permission_required = 'suprimentos.change_parceiro'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Editar Fornecedor'
        return context

class ParceiroDeleteView(ViewFilialScopedMixin, SSTPermissionMixin, DeleteView):
    model = Parceiro
    template_name = 'suprimentos/parceiro_confirm_delete.html'
    success_url = reverse_lazy('suprimentos:parceiro_list')
    context_object_name = 'object'
    permission_required = 'suprimentos.delete_parceiro'

