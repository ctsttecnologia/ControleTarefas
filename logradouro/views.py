from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View
from django.http import HttpResponse, Http404
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
import openpyxl
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter

from .models import Logradouro, Filial 
from .forms import LogradouroForm, UploadFileForm
from .constant import ESTADOS_BRASIL
from core.mixins import SSTPermissionMixin, ViewFilialScopedMixin

import pandas as pd
import io
from django.db import transaction
from django.core.exceptions import ValidationError
from openpyxl import load_workbook
from openpyxl.worksheet.datavalidation import DataValidation
import base64 


# --- Views de Logradouro (CRUD) ---

class LogradouroListView(LoginRequiredMixin, SSTPermissionMixin, ViewFilialScopedMixin, ListView):
    """
    Lista os logradouros cadastrados, aplicando escopo de filial e filtros de busca.
    """
    model = Logradouro
    # O template é o que você definiu no seu código
    template_name = 'logradouro/listar_logradouros.html' 
    context_object_name = 'logradouros'
    paginate_by = 15

    # Permissão do Nível 1 (Página)
    permission_required = 'logradouro.view_logradouro'

    def get_queryset(self):
        """
        Sobrescreve o método para aplicar os filtros de busca sobre o
        queryset que já foi filtrado por filial pelo `ViewFilialScopedMixin`.
        """
        # 1. `super().get_queryset()` chama o `ViewFilialScopedMixin` primeiro,
        #    garantindo que `queryset` contém apenas dados da filial correta.
        queryset = super().get_queryset()

        # Armazena a contagem total para o cabeçalho da página
        self.total_logradouros_na_filial = queryset.count()

        # 2. Pega os valores dos campos de busca da URL (parâmetros GET)
        query_endereco = self.request.GET.get('q_endereco', '').strip()
        query_cep = self.request.GET.get('q_cep', '').strip()

        # 3. Aplica o filtro de endereço se algo foi digitado
        if query_endereco:
            # 'icontains' faz uma busca case-insensitive que contém o texto
            queryset = queryset.filter(endereco__icontains=query_endereco)
        
        # 4. Aplica o filtro de CEP se algo foi digitado
        if query_cep:
            # Filtra pelo campo 'cep' que contém o número digitado.
            queryset = queryset.filter(cep__icontains=query_cep)

        return queryset.order_by('endereco')

    def get_context_data(self, **kwargs):
        """
        Adiciona o total de logradouros (antes de filtrar) ao contexto.
        """
        context = super().get_context_data(**kwargs)
        # Adiciona a contagem total de endereços na filial (antes da busca)
        # para ser usado no cabeçalho.
        context['total_logradouros'] = getattr(self, 'total_logradouros_na_filial', 0)
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

    def get_initial(self):
        """Pré-seleciona a filial atual do usuário no formulário."""
        initial = super().get_initial()
        if hasattr(self.request.user, 'filial_atual'):
            initial['filial'] = self.request.user.filial_atual
        return initial

    def get_queryset(self):
        """Garante que o usuário só edite endereços da sua filial."""
        return super().get_queryset()

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
class LogradouroUpdateView(ViewFilialScopedMixin, LoginRequiredMixin, UpdateView):
    model = Logradouro
    form_class = LogradouroForm
    template_name = 'logradouro/form_logradouro.html'
    success_url = reverse_lazy('logradouro:listar_logradouros')

    def get_queryset(self):
        """Garante que o usuário só edite endereços da sua filial."""
        return super().get_queryset()
    
    def form_valid(self, form):
        messages.success(self.request, _('Endereço atualizado com sucesso!'))
        return super().form_valid(form)

# Nenhuma alteração necessária aqui, o mixin já garante a segurança.
class LogradouroDeleteView(ViewFilialScopedMixin, LoginRequiredMixin, DeleteView):
    model = Logradouro
    template_name = 'logradouro/confirmar_exclusao.html'
    success_url = reverse_lazy('logradouro:listar_logradouros')

    def get_queryset(self):
        """Garante que o usuário só edite endereços da sua filial."""
        return super().get_queryset()

    def form_valid(self, form):
        messages.success(self.request, _('Endereço excluído com sucesso!'))
        return super().form_valid(form)

# --- View de Exportação ---

class LogradouroExportExcelView(LoginRequiredMixin, View):
    """
    Exporta a lista de logradouros para Excel, respeitando o escopo da filial.
    """
    def get_queryset(self):
        """Garante que o usuário só edite endereços da sua filial."""
        return super().get_queryset()
    
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
    

class UploadLogradourosView(View):
    form_class = UploadFileForm
    template_name = 'logradouro/upload_logradouros.html'

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        if 'relatorio_erros' in request.session:
            del request.session['relatorio_erros']
        return render(request, self.template_name, {'form': form})

    # SUBSTITUA SEU MÉTODO POST INTEIRO POR ESTE
    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        context = {'form': form}

        if not form.is_valid():
            return render(request, self.template_name, context)

        file = request.FILES['file']

        # --- ETAPA 1: VALIDAÇÃO ESTRUTURAL DO ARQUIVO ---
        try:
            df = pd.read_excel(file)
            df.dropna(how='all', inplace=True)
        except Exception as e:
            messages.error(request, f"Não foi possível ler o arquivo. Ele pode estar corrompido ou em um formato inválido. Erro: {e}")
            return render(request, self.template_name, context)

        required_cols = ['filial_id', 'endereco', 'numero', 'bairro', 'cep', 'cidade', 'estado']
        if not all(col in df.columns for col in required_cols):
            cols_faltando = ", ".join([col for col in required_cols if col not in df.columns])
            msg = f"O arquivo não contém as colunas obrigatórias: {cols_faltando}. Verifique o modelo e tente novamente."
            messages.error(request, msg)
            return render(request, self.template_name, context)

        # --- ETAPA 2: VALIDAÇÃO DOS DADOS (LINHA A LINHA) ---
        linhas_com_erro = []
        enderecos_para_criar = []
        
        try:
            with transaction.atomic():
                for index, row in df.iterrows():
                    try:
                        if row[required_cols].isnull().any():
                            raise ValueError("Contém valores vazios em colunas obrigatórias.")

                        filial = Filial.objects.get(pk=int(row['filial_id']))
                        cep_limpo = str(row['cep']).split('.')[0]

                        # Pega os valores da linha
                        lat = row.get('latitude')
                        lon = row.get('longitude')
                        
                        logradouro_data = {
                            'filial': filial,
                            'endereco': row['endereco'],
                            'numero': int(row['numero']),
                            'complemento': row.get('complemento'),
                            'bairro': row['bairro'],
                            'cep': cep_limpo.zfill(8),
                            'cidade': row['cidade'],
                            'estado': row['estado'],
                            'pais': row.get('pais', 'Brasil') or 'Brasil',
                            'ponto_referencia': row.get('ponto_referencia'),
                            'latitude': None if pd.isna(lat) else lat,
                            'longitude': None if pd.isna(lon) else lon
                        }
                        
                        logradouro_obj = Logradouro(**logradouro_data)
                        logradouro_obj.full_clean()
                        enderecos_para_criar.append(logradouro_obj)

                    except Exception as e:
                        linha_original = row.to_dict()
                        linha_original['Erro_Detectado'] = f"Linha {index + 2}: {e}"
                        linhas_com_erro.append(linha_original)
                
                # Se encontramos erros, revertemos a transação
                if linhas_com_erro:
                    raise ValueError("A importação foi cancelada devido a erros de dados.")

            # Se chegamos aqui sem erros, salvamos no banco
            Logradouro.objects.bulk_create(enderecos_para_criar)
            messages.success(request, f"{len(enderecos_para_criar)} endereços importados com sucesso!")
            return redirect('logradouro:listar_logradouros')

        except ValueError:
            # Este 'except' é acionado APENAS se houveram erros de dados
            messages.error(request, "A importação falhou. Verifique os erros no relatório abaixo para corrigir.")
            
            # --- GERAÇÃO DO RELATÓRIO DE ERROS ---
            df_erros = pd.DataFrame(linhas_com_erro)
            buffer = io.BytesIO()
            df_erros.to_excel(buffer, index=False)
            buffer.seek(0)
            
            file_base64 = base64.b64encode(buffer.read()).decode('utf-8')
            request.session['relatorio_erros'] = {
                'filename': 'relatorio_de_erros_logradouros.xlsx',
                'content': file_base64
            }
            context['relatorio_disponivel'] = True
            context['total_erros'] = len(linhas_com_erro)

        return render(request, self.template_name, context)


# NOVA VIEW PARA O DOWNLOAD DO RELATÓRIO
class DownloadErroRelatorioView(View):
    def get(self, request, *args, **kwargs):
        relatorio_data = request.session.get('relatorio_erros')
        
        if not relatorio_data:
            raise Http404("Nenhum relatório de erros encontrado.")

        # Decodifica o conteúdo do arquivo de base64 para bytes
        file_content = base64.b64decode(relatorio_data['content'])
        filename = relatorio_data['filename']
        
        # Limpa a sessão para não permitir o download novamente
        del request.session['relatorio_erros']

        response = HttpResponse(
            file_content,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    

# Download da planilha de inserção em massa
class DownloadTemplateView(View):
    """
    Gera e fornece um arquivo de modelo .xlsx formatado para download,
    visando uma melhor experiência do usuário.
    """
    def get(self, request, *args, **kwargs):
        headers = [
            'filial_id', 'endereco', 'numero', 'complemento', 'bairro', 
            'cep', 'cidade', 'estado', 'pais', 'ponto_referencia', 
            'latitude', 'longitude'
        ]
        
        # 1. DADOS DE EXEMPLO PARA GUIAR O USUÁRIO
        example_data = [
            [1, 'Avenida Paulista', 1578, 'Andar 10', 'Bela Vista', '01310200', 'São Paulo', 'SP', 'Brasil', 'Em frente ao MASP', -23.561350, -46.656530]
        ]
        
        df = pd.DataFrame(example_data, columns=headers)
        
        buffer = io.BytesIO()
        
        # 2. ESCRITA INICIAL COM PANDAS
        df.to_excel(buffer, index=False, sheet_name='Enderecos')
        
        # 3. FORMATAÇÃO AVANÇADA COM OPENPYXL
        # Reposiciona o "cursor" do buffer para o início
        buffer.seek(0)
        
        workbook = load_workbook(buffer)
        ws_enderecos = workbook['Enderecos']
        
        # --- Estilos ---
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid") # Azul Royal
        center_align = Alignment(horizontal='center', vertical='center')

        # 4. APLICAR ESTILOS AO CABEÇALHO E AJUSTAR LARGURA DAS COLUNAS
        for col_num, column_cell in enumerate(ws_enderecos[1], 1):
            # Estilo do cabeçalho
            column_cell.font = header_font
            column_cell.fill = header_fill
            column_cell.alignment = center_align

            # Ajuste da largura da coluna
            max_length = 0
            column = ws_enderecos.cell(row=1, column=col_num).column_letter
            for cell in ws_enderecos[column]:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 4)
            ws_enderecos.column_dimensions[column].width = adjusted_width

        # 5. VALIDAÇÃO DE DADOS PARA A COLUNA 'ESTADO' (COLUNA H)
        # Cria a lista de estados formatada para a regra de validação
        estados_list = [item[0] for item in ESTADOS_BRASIL]
        validation_formula = f'"{",".join(estados_list)}"'
        
        dv = DataValidation(type="list", formula1=validation_formula, allow_blank=True)
        dv.error = 'O valor deve ser uma sigla de estado válida.'
        dv.errorTitle = 'Entrada Inválida'
        dv.prompt = 'Selecione um estado da lista'
        dv.promptTitle = 'Seleção de Estado'
        # Aplica a validação da segunda linha em diante
        ws_enderecos.add_data_validation(dv)
        dv.add('H2:H1048576') # Coluna H inteira

        # 6. CONGELAR PAINEL DO CABEÇALHO
        ws_enderecos.freeze_panes = 'A2'
        
        # 7. CRIAR ABA DE INSTRUÇÕES
        ws_instrucoes = workbook.create_sheet(title="Instruções", index=0) # Coloca como primeira aba
        ws_instrucoes.append(['Coluna', 'Descrição', 'Obrigatório?', 'Exemplo'])
        
        # Estilizando o cabeçalho da aba de instruções
        for cell in ws_instrucoes[1]:
            cell.font = header_font
            cell.fill = header_fill

        # Adicionando o conteúdo das instruções
        instructions = [
            ['filial_id', 'ID numérico da Filial. Deve existir no sistema.', 'Sim', '1','CETEST-SP', '2', 'CETEST-MG', '3', 'CETEST-RJ', '4', 'CETEST-ND'],
            ['endereco', 'Nome da rua, avenida, etc. (Máx: 150 caracteres)', 'Sim', 'Avenida Paulista'],
            ['numero', 'Número do imóvel. Deve ser um inteiro positivo.', 'Sim', '1578'],
            ['complemento', 'Andar, sala, bloco, etc. (Máx: 50 caracteres)', 'Não', 'Andar 10'],
            ['bairro', 'Nome do bairro. (Máx: 60 caracteres)', 'Sim', 'Bela Vista'],
            ['cep', 'CEP com 8 dígitos, sem pontos ou traços.', 'Sim', '01310200'],
            ['cidade', 'Nome da cidade. (Máx: 60 caracteres)', 'Sim', 'São Paulo'],
            ['estado', 'Sigla do estado (selecione da lista).', 'Sim', 'SP'],
            ['pais', 'Nome do país. Padrão: Brasil.', 'Não', 'Brasil'],
            ['ponto_referencia', 'Referência para localização. (Máx: 100 caracteres)', 'Não', 'Em frente ao MASP'],
            ['latitude', 'Coordenada de latitude (formato decimal com ponto).', 'Não', '-23.561350'],
            ['longitude', 'Coordenada de longitude (formato decimal com ponto).', 'Não', '-46.656530']
        ]
        for row in instructions:
            ws_instrucoes.append(row)

        # Ajustando a largura das colunas na aba de instruções
        for col_letter in ['A', 'B', 'C', 'D']:
            ws_instrucoes.column_dimensions[col_letter].auto_size = True
            
        # Define a aba de preenchimento como a aba ativa ao abrir
        workbook.active = ws_enderecos
        
        # 8. SALVAR WORKBOOK FORMATADO E CRIAR A RESPOSTA
        final_buffer = io.BytesIO()
        workbook.save(final_buffer)
        
        filename = "enderecos.xlsx"
        
        response = HttpResponse(
            final_buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response