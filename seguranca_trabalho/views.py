# seguranca_trabalho/views.py

import io
import json
from datetime import datetime, timedelta
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q, Count, Func
from django.http import Http404, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (CreateView, DeleteView, DetailView, ListView,
                                  TemplateView, UpdateView)
from django.views.generic.edit import FormMixin
from docx import Document
from weasyprint import HTML, default_url_fetcher
from core.mixins import (FilialCreateMixin, HTMXModalFormMixin, SSTPermissionMixin,
                         ViewFilialScopedMixin, TecnicoScopeMixin) 
from departamento_pessoal.models import Funcionario
from usuario.models import Filial
from usuario.views import StaffRequiredMixin
from .forms import (AssinaturaEntregaForm, EntregaEPIForm, EquipamentoForm, FichaEPIForm, FuncaoForm, CargoFuncaoForm)
from .models import (EntregaEPI, Equipamento, FichaEPI, Funcao, MatrizEPI, CargoFuncao)
import logging

logger = logging.getLogger(__name__)


def custom_url_fetcher(url):
    """ Permite que o WeasyPrint acesse arquivos de media locais. """
    if url.startswith(settings.MEDIA_URL):
        path = (settings.MEDIA_ROOT / url[len(settings.MEDIA_URL):]).as_posix()
        return default_url_fetcher(f'file://{path}')
    return default_url_fetcher(url)

# --- CRUD de Equipamentos ---

class EquipamentoListView(ViewFilialScopedMixin, SSTPermissionMixin, ListView):
    model = Equipamento
    template_name = 'seguranca_trabalho/equipamento_list.html'
    context_object_name = 'equipamentos'
    permission_required = 'seguranca_trabalho.view_equipamento'

class EquipamentoDetailView(ViewFilialScopedMixin, SSTPermissionMixin, DetailView):
    model = Equipamento
    template_name = 'seguranca_trabalho/equipamento_detail.html'
    context_object_name = 'equipamento'
    permission_required = 'seguranca_trabalho.view_equipamento'

class EquipamentoCreateView(FilialCreateMixin, SSTPermissionMixin, CreateView):
    model = Equipamento
    form_class = EquipamentoForm
    template_name = 'seguranca_trabalho/equipamento_form.html'
    success_url = reverse_lazy('seguranca_trabalho:equipamento_list')
    permission_required = 'seguranca_trabalho.add_equipamento'

class EquipamentoUpdateView(ViewFilialScopedMixin, SSTPermissionMixin, UpdateView):
    model = Equipamento
    form_class = EquipamentoForm
    template_name = 'seguranca_trabalho/equipamento_form.html'
    success_url = reverse_lazy('seguranca_trabalho:equipamento_list')
    permission_required = 'seguranca_trabalho.change_equipamento'

    def get_queryset(self):
        # Removido 'fornecedor' do select_related pois o campo não existe mais no modelo Equipamento.
        return super().get_queryset().select_related('fabricante')

class EquipamentoDeleteView(ViewFilialScopedMixin, SSTPermissionMixin, DeleteView):
    model = Equipamento
    template_name = 'seguranca_trabalho/confirm_delete.html'
    success_url = reverse_lazy('seguranca_trabalho:equipamento_list')
    context_object_name = 'object'
    permission_required = 'seguranca_trabalho.delete_equipamento'

# ========================================================================
# CRUD DE FICHAS DE EPI E AÇÕES
# ========================================================================
class FichaEPIListView(ViewFilialScopedMixin, TecnicoScopeMixin, SSTPermissionMixin, ListView):
    model = FichaEPI
    template_name = 'seguranca_trabalho/ficha_list.html'
    context_object_name = 'fichas'
    paginate_by = 30
    permission_required = 'seguranca_trabalho.view_fichaepi'
    
    # Define o lookup para o TecnicoScopeMixin
    tecnico_scope_lookup = 'funcionario__usuario'

    def get_queryset(self):
        # O super() já filtra por Filial e por TÉCNICO
        qs = super().get_queryset().select_related('funcionario', 'funcionario__cargo')
        query_text = self.request.GET.get('q')
        if query_text:
            qs = qs.filter(
                Q(funcionario__nome_completo__icontains=query_text) |
                Q(funcionario__matricula__icontains=query_text)
            )
        return qs.order_by('funcionario__nome_completo')

class FichaEPICreateView(FilialCreateMixin, SSTPermissionMixin, CreateView):
    model = FichaEPI
    form_class = FichaEPIForm
    template_name = 'seguranca_trabalho/ficha_create.html'
    success_url = reverse_lazy('seguranca_trabalho:ficha_list')
    permission_required = 'seguranca_trabalho.add_fichaepi'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        form.instance.filial = form.cleaned_data['funcionario'].filial
        messages.success(self.request, "Ficha de EPI criada com sucesso!")
        return super().form_valid(form)

class FichaEPIDetailView(ViewFilialScopedMixin, TecnicoScopeMixin, SSTPermissionMixin, FormMixin, DetailView):
    model = FichaEPI
    template_name = 'seguranca_trabalho/ficha_detail.html'
    context_object_name = 'ficha'
    form_class = EntregaEPIForm
    permission_required = 'seguranca_trabalho.view_fichaepi'
    
    # Define o lookup para o TecnicoScopeMixin
    tecnico_scope_lookup = 'funcionario__usuario'

    def get_success_url(self):
        return reverse('seguranca_trabalho:ficha_detail', kwargs={'pk': self.object.pk})
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['filial'] = self.get_object().filial
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = self.get_form()
        context['entregas'] = self.object.entregas.select_related('equipamento').order_by('-data_entrega')
        return context

    def post(self, request, *args, **kwargs):
        # (Lógica de POST inalterada. TÉCNICO não deve ter a permissão 'add_entregaepi')
        if not request.user.has_perm('seguranca_trabalho.add_entregaepi'):
            raise PermissionDenied("Você não tem permissão para registrar uma nova entrega.")
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form):
        nova_entrega = form.save(commit=False)
        nova_entrega.ficha = self.object
        nova_entrega.filial = self.object.filial
        nova_entrega.save()
        messages.success(self.request, "Nova entrega de EPI registrada com sucesso!")
        return redirect(self.get_success_url())

class FichaEPIUpdateView(ViewFilialScopedMixin, SSTPermissionMixin, UpdateView):
    model = FichaEPI
    form_class = FichaEPIForm # Reutiliza o form de criação
    template_name = 'seguranca_trabalho/ficha_form.html'
    permission_required = 'seguranca_trabalho.change_fichaepi'

    def get_success_url(self):
        return reverse('seguranca_trabalho:ficha_detail', kwargs={'pk': self.object.pk})

class FichaEPIDeleteView(ViewFilialScopedMixin, SSTPermissionMixin, DeleteView):
    model = FichaEPI
    template_name = 'seguranca_trabalho/confirm_delete.html'
    success_url = reverse_lazy('seguranca_trabalho:ficha_list')
    context_object_name = 'object'
    permission_required = 'seguranca_trabalho.delete_fichaepi'


# --- Ações de Entrega (Assinatura, Devolução, etc.) ---

class AssinarEntregaView(ViewFilialScopedMixin, TecnicoScopeMixin, SSTPermissionMixin, UpdateView):
    model = EntregaEPI
    form_class = AssinaturaEntregaForm
    template_name = 'seguranca_trabalho/entrega_sign.html'
    context_object_name = 'entrega'
    permission_required = 'seguranca_trabalho.assinar_entregaepi'
    
    # Define o lookup para o TecnicoScopeMixin
    tecnico_scope_lookup = 'ficha__funcionario__usuario'

    def get_success_url(self):
        return reverse('seguranca_trabalho:ficha_detail', kwargs={'pk': self.object.ficha.pk})

    def get(self, request, *args, **kwargs):
        self.object = self.get_object() # self.get_object() agora é filtrado pelo mixin
        if self.object.data_devolucao or self.object.data_assinatura:
            messages.info(request, "Esta entrega já foi processada e não pode mais ser assinada.")
            return redirect(self.get_success_url())
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        self.object.assinatura_recebimento = self.request.POST.get('assinatura_base64')
        self.object.data_assinatura = timezone.now()
        self.object.save()
        messages.success(self.request, "Assinatura registrada com sucesso!")
        return redirect(self.get_success_url())

class RegistrarDevolucaoView(TecnicoScopeMixin, SSTPermissionMixin, View):
    permission_required = 'seguranca_trabalho.change_entregaepi'
    http_method_names = ['post']
    
    # Define o lookup para o TecnicoScopeMixin (usado no 'scope_tecnico_queryset')
    tecnico_scope_lookup = 'ficha__funcionario__usuario'

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        filial_id = request.session.get('active_filial_id')
        
        # Constrói o queryset base
        qs = EntregaEPI.objects.all()
        
        # Aplica o escopo do TÉCNICO manualmente usando o método do mixin
        # Isso garante que um TÉCNICO só possa devolver seu próprio EPI
        qs = self.scope_tecnico_queryset(qs) 
        
        # Busca o objeto dentro do queryset filtrado (por TÉCNICO e Filial)
        entrega = get_object_or_404(qs, pk=kwargs.get('pk'), filial_id=filial_id)
        
        if entrega.data_devolucao:
            messages.warning(request, f"O EPI '{entrega.equipamento.nome}' já foi devolvido.")
        else:
            entrega.data_devolucao = timezone.now().date()
            entrega.recebedor_devolucao = request.user
            entrega.save()
            messages.success(request, f"Devolução do EPI '{entrega.equipamento.nome}' registrada.")
            
        return redirect('seguranca_trabalho:ficha_detail', pk=entrega.ficha.pk)

# --- Relatórios e Painéis ---
class GerarFichaPDFView(ViewFilialScopedMixin, TecnicoScopeMixin, SSTPermissionMixin, DetailView):
    model = FichaEPI
    permission_required = 'seguranca_trabalho.view_fichaepi'
    
    # Define o lookup para o TecnicoScopeMixin
    tecnico_scope_lookup = 'funcionario__usuario'

    def get(self, request, *args, **kwargs):
        # self.get_object() agora é filtrado por Filial e TÉCNICO
        ficha = self.get_object() 
        
        entregas = EntregaEPI.objects.filter(ficha=ficha).order_by('data_entrega')
        context = {
            'ficha': ficha,
            'entregas': entregas,
            'data_emissao': timezone.now(),
        }
        html_string = render_to_string('seguranca_trabalho/ficha_pdf_template.html', context)
        html = HTML(
            string=html_string, 
            base_url=request.build_absolute_uri(),
            url_fetcher=custom_url_fetcher
        )
        pdf = html.write_pdf()
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="ficha_epi_{ficha.funcionario.matricula}.pdf"'
        return response

# --- VIEW DO PAINEL ---

class DateAdd(Func):

    """
    Função customizada para usar o DATE_ADD do MySQL
    de forma segura, compondo as expressões corretamente.
    """
    function = 'DATE_ADD'
    template = '%(function)s(%(expressions)s)'

    def __init__(self, date_expression, days_expression, **extra):
        # Cria uma expressão interna para "INTERVAL 'N' DAY"
        # O Django irá compilar 'days_expression' para o nome da coluna corretamente
        interval_expression = Func(
            days_expression,
            template="INTERVAL %(expressions)s DAY"
        )
        super().__init__(date_expression, interval_expression, **extra)

class DashboardSSTView(ViewFilialScopedMixin, TecnicoScopeMixin, SSTPermissionMixin, TemplateView):
    template_name = 'seguranca_trabalho/dashboard.html'
    # Permissão para ver o dashboard (mesmo que filtrado)
    permission_required = 'seguranca_trabalho.view_fichaepi'
    tecnico_scope_lookup = 'funcionario__usuario'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # --- ETAPA 1: INICIALIZAR TODOS OS QUERYSETS ---
        # Primeiro, buscamos os querysets base da filial usando o 
        # método 'get_queryset_base' que você já tem.
        
        # Envolvemos em try/except para garantir que as variáveis existam
        # mesmo se o 'get_queryset_base' falhar (embora não devesse).
        try:
            equipamentos_da_filial = self.get_queryset_base(Equipamento)
            fichas_da_filial = self.get_queryset_base(FichaEPI)
            entregas_da_filial = self.get_queryset_base(EntregaEPI)
            matriz_da_filial = self.get_queryset_base(MatrizEPI)
        except Exception as e:
            logger.error(f"Erro ao buscar querysets base no DashboardSST: {e}")
            # Se falhar, define como querysets vazios para evitar o UnboundLocalError
            equipamentos_da_filial = Equipamento.objects.none()
            fichas_da_filial = FichaEPI.objects.none()
            entregas_da_filial = EntregaEPI.objects.none()
            matriz_da_filial = MatrizEPI.objects.none()

        # --- ETAPA 2: APLICAR ESCOPO DO TÉCNICO (SE APLICÁVEL) ---
        # self._is_tecnico() é um helper do TecnicoScopeMixin
        if self._is_tecnico(): 
            # TÉCNICO não vê dados agregados de equipamentos ou matriz
            equipamentos_da_filial = equipamentos_da_filial.none()
            matriz_da_filial = matriz_da_filial.none()
            
            # TÉCNICO só vê sua própria ficha (usando o lookup corrigido)
            fichas_da_filial = fichas_da_filial.filter(funcionario__usuario=self.request.user)
            
            # TÉCNICO só vê suas próprias entregas (usando o lookup corrigido)
            entregas_da_filial = entregas_da_filial.filter(ficha__funcionario__usuario=self.request.user)
        
        # --- ETAPA 3: CALCULAR DADOS PARA O CONTEXTO ---
        # Neste ponto, 'fichas_da_filial' SEMPRE existe (ou é um queryset
        # filtrado, ou um queryset vazio). O UnboundLocalError é resolvido.

        # --- 1. DADOS PARA OS CARDS DE KPI ---
        context['total_equipamentos_ativos'] = equipamentos_da_filial.filter(ativo=True).count()
        context['fichas_ativas'] = fichas_da_filial.filter(funcionario__status='ATIVO').count() # <-- Linha 302 (Agora segura)
        context['entregas_pendentes_assinatura'] = entregas_da_filial.filter(
            data_devolucao__isnull=True, 
            data_assinatura__isnull=True
        ).count()

        # --- 2. CÁLCULO DE EPIs VENCENDO ---
        today = timezone.now().date()
        thirty_days_from_now = today + timedelta(days=30)
        
        entregas_ativas = entregas_da_filial.filter(
            data_devolucao__isnull=True, data_entrega__isnull=False
        ).select_related('equipamento')

        epis_vencendo_30d_count = 0
        for entrega in entregas_ativas:
            vida_util = entrega.equipamento.vida_util_dias
            if vida_util is not None:
                vencimento = entrega.data_entrega + timedelta(days=vida_util)
                if today <= vencimento <= thirty_days_from_now:
                    epis_vencendo_30d_count += 1
        
        context['epis_vencendo_em_30_dias'] = epis_vencendo_30d_count

        # --- 3. DADOS PARA OS GRÁFICOS ---
        matriz_chart_data = matriz_da_filial.values('funcao__nome').annotate(
            num_epis=Count('equipamento')
        ).order_by('-num_epis')[:10]
        
        if matriz_chart_data: # (só será preenchido se não for TÉCNICO)
            context['matriz_labels'] = json.dumps([m['funcao__nome'] for m in matriz_chart_data])
            context['matriz_data'] = json.dumps([m['num_epis'] for m in matriz_chart_data])

        context['titulo_pagina'] = "Painel de Segurança do Trabalho"
        return context

class BaseExportView(LoginRequiredMixin, View):
    def get_scoped_queryset(self, model, related_fields=None):
        filial_id = self.request.session.get('active_filial_id')
        if not filial_id:
            messages.error(self.request, "Selecione uma filial para exportar os dados.")
            return model.objects.none()

        # Lógica de filtro baseada na estrutura do modelo
        if hasattr(model, 'filial'):
            qs = model.objects.filter(filial_id=filial_id)
        elif hasattr(model, 'funcionario'):
            qs = model.objects.filter(funcionario__filial_id=filial_id)
        else:
            return model.objects.none()
        
        if related_fields:
            qs = qs.select_related(*related_fields)
        return qs

# O nome da classe deve ser EXATAMENTE este
class ControleEPIPorFuncaoView(SSTPermissionMixin, TemplateView):
    permission_required = 'seguranca_trabalho.change_matrizepi'
    template_name = 'seguranca_trabalho/controle_epi_por_funcao.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        active_filial_id = request.session.get('active_filial_id')
        filial_atual = None

        if active_filial_id:
            try:
                filial_atual = Filial.objects.get(pk=active_filial_id)
            except Filial.DoesNotExist:
                messages.error(request, "A filial selecionada é inválida.")
        
        if not filial_atual:
            messages.warning(request, "Nenhuma filial selecionada. Por favor, escolha uma no menu superior.")
            context.update({
                'titulo_pagina': "Matriz de EPIs", 'funcoes': [], 'equipamentos': [], 'matriz_data': {}
            })
            return context

        funcoes = Funcao.objects.filter(filial=filial_atual, ativo=True).order_by('nome')
        equipamentos = Equipamento.objects.filter(ativo=True).order_by('nome')

        dados_salvos = MatrizEPI.objects.filter(funcao__in=funcoes).select_related('funcao', 'equipamento')

        matriz_data = {}
        for item in dados_salvos:
            if item.funcao_id not in matriz_data:
                matriz_data[item.funcao_id] = {}
            # Usando o nome correto do campo do modelo
            matriz_data[item.funcao_id][item.equipamento_id] = item.frequencia_troca_meses

        context.update({
            'titulo_pagina': f"Matriz de EPIs - {filial_atual.nome}",
            'funcoes': funcoes,
            'equipamentos': equipamentos,
            'matriz_data': matriz_data
        })
        return context

    @transaction.atomic
    def post(self, request, *args, **kwargs):
         

        active_filial_id = request.session.get('active_filial_id')
        if not active_filial_id:
            messages.error(request, "Sessão expirada ou filial não selecionada. Não foi possível salvar.")
            return redirect(request.path_info)

        funcoes_ids = list(Funcao.objects.filter(filial_id=active_filial_id, ativo=True).values_list('id', flat=True))
        equipamentos_ids = list(Equipamento.objects.filter(ativo=True).values_list('id', flat=True))
        
        existentes = MatrizEPI.objects.filter(funcao_id__in=funcoes_ids)
        mapa_existentes = {(item.funcao_id, item.equipamento_id): item for item in existentes}

        entries_to_create = []
        entries_to_update = []
        submitted_keys = set()

        for key, value in request.POST.items():
            if key.startswith('freq_'):
                try:
                    _, funcao_id_str, equipamento_id_str = key.split('_')
                    funcao_id = int(funcao_id_str)
                    equipamento_id = int(equipamento_id_str)
                    
                    if funcao_id not in funcoes_ids or equipamento_id not in equipamentos_ids:
                        continue

                    submitted_keys.add((funcao_id, equipamento_id))
                    
                    frequencia = int(value) if value and value.isdigit() else 0
                    if frequencia <= 0:
                        continue

                    if (funcao_id, equipamento_id) in mapa_existentes:
                        item_existente = mapa_existentes[(funcao_id, equipamento_id)]
                        # CORREÇÃO AQUI
                        if item_existente.frequencia_troca_meses != frequencia:
                            # CORREÇÃO AQUI
                            item_existente.frequencia_troca_meses = frequencia
                            entries_to_update.append(item_existente)
                    else:
                        entries_to_create.append(
                            MatrizEPI(
                                funcao_id=funcao_id,
                                equipamento_id=equipamento_id,
                                filial_id=active_filial_id,
                                # CORREÇÃO AQUI
                                frequencia_troca_meses=frequencia
                            )
                        )
                except (ValueError, IndexError):
                    continue

        keys_to_delete = set(mapa_existentes.keys()) - submitted_keys
        pks_to_delete = [mapa_existentes[key].pk for key in keys_to_delete]

        if entries_to_create:
            MatrizEPI.objects.bulk_create(entries_to_create)

        if entries_to_update:
            # CORREÇÃO AQUI
            MatrizEPI.objects.bulk_update(entries_to_update, ['frequencia_troca_meses'])

        if pks_to_delete:
            MatrizEPI.objects.filter(pk__in=pks_to_delete).delete()

        messages.success(request, "Matriz de EPIs salva com sucesso!")
        return redirect(request.path_info)

    
class RelatorioSSTPDFView(SSTPermissionMixin, View):

    permission_required = 'seguranca_trabalho.view_fichaepi'

    def get(self, request, *args, **kwargs):
        context = {
            'data_emissao': timezone.now(),
            'entregas': EntregaEPI.objects.select_related('ficha__funcionario', 'equipamento').all(),
        }
        html_string = render_to_string('seguranca_trabalho/relatorio_geral_pdf.html', context)
        html = HTML(string=html_string, base_url=request.build_absolute_uri())
        pdf = html.write_pdf()
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="relatorio_sst.pdf"'
        return response
    
class ExportarFuncionariosPDFView(StaffRequiredMixin, View): 

    def get(self, request, *args, **kwargs):
        
        funcionarios = Funcionario.objects.for_request(request).select_related('cargo', 'departamento').filter(status='ATIVO')

        context = {
            'funcionarios': funcionarios,
            'data_emissao': timezone.now().strftime('%d/%m/%Y às %H:%M'),
            'nome_filial': request.user.filial.nome if hasattr(request.user, 'filial') else 'Geral'
        }
        html_string = render_to_string('departamento_pessoal/relatorio_funcionarios_pdf.html', context)
        html = HTML(string=html_string, base_url=request.build_absolute_uri())
        pdf_file = html.write_pdf()

        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="relatorio_funcionarios.pdf"'
        return response
    
class ExportarFuncionariosWordView(StaffRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        funcionarios = Funcionario.objects.for_request(request).select_related('cargo', 'departamento').filter(status='ATIVO')
        document = Document()
        document.add_heading('Relatório de Colaboradores', level=1)
        data_emissao = timezone.now().strftime('%d/%m/%Y às %H:%M')
        document.add_paragraph(f'Relatório gerado em: {data_emissao}')
        document.add_paragraph()

        table = document.add_table(rows=1, cols=4)
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text, hdr_cells[1].text, hdr_cells[2].text, hdr_cells[3].text = 'Nome Completo', 'Cargo', 'Departamento', 'Data de Admissão'

        for f in funcionarios:
            row_cells = table.add_row().cells
            row_cells[0].text = f.nome_completo
            row_cells[1].text = f.cargo.nome if f.cargo else '-'
            row_cells[2].text = f.departamento.nome if f.departamento else '-'
            row_cells[3].text = f.data_admissao.strftime('%d/%m/%Y') if f.data_admissao else '-'

        buffer = io.BytesIO()
        document.save(buffer)
        buffer.seek(0)

        response = HttpResponse(buffer.getvalue(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = 'attachment; filename="relatorio_funcionarios.docx"'
        return response
    
# --- CRUD DE FUNÇÕES ---
class FuncaoListView(ViewFilialScopedMixin, SSTPermissionMixin, ListView):
    """
    Lista todas as funções da filial ativa.
    """
    model = Funcao
    template_name = 'seguranca_trabalho/funcao_list.html'
    context_object_name = 'funcoes'
    permission_required = 'seguranca_trabalho.view_funcao'
    paginate_by = 20


    def get_queryset(self):
        # Pega o queryset base, já filtrado pela filial pelo mixin
        qs = super().get_queryset()

        # Pega o termo de busca da URL (ex: ?q=minha-busca)
        query_text = self.request.GET.get('q')

        if query_text:
            # Filtra o nome da função (case-insensitive)
            qs = qs.filter(nome__icontains=query_text)

        # Retorna o queryset ordenado
        return qs.order_by('nome')    # Filtra as funções pela filial ativa na sessão e ordena por nome

# busca da ficha.
@login_required
def minha_ficha_redirect_view(request):
    try:
        # --- A CORREÇÃO ESTÁ AQUI ---
        funcionario_obj = get_object_or_404(Funcionario, usuario=request.user)
        
    except (Http404, AttributeError): 
        messages.error(request, "Seu usuário não está associado a um perfil de funcionário.")
        return redirect('usuario:profile')

    try:
        ficha = get_object_or_404(FichaEPI, funcionario=funcionario_obj)
        
    except Http404:
        messages.error(request, "Seu usuário (como funcionário) não possui uma ficha de EPI associada.")
        return redirect('usuario:profile')
    
    return redirect('seguranca_trabalho:ficha_detail', pk=ficha.pk)

class FuncaoCreateView(HTMXModalFormMixin, FilialCreateMixin, SSTPermissionMixin, CreateView): # <-- ADICIONE O MIXIN
    model = Funcao
    form_class = FuncaoForm
    # O template agora será escolhido dinamicamente pelo mixin
    # template_name = 'seguranca_trabalho/funcao_form.html' # <- Pode remover esta linha
    success_url = reverse_lazy('seguranca_trabalho:funcao_list')
    permission_required = 'seguranca_trabalho.add_funcao'

    def form_valid(self, form):
        messages.success(self.request, f"A função '{form.instance.nome}' foi criada com sucesso.")
        # A lógica de resposta HTMX será tratada pelo mixin
        return super().form_valid(form)


class FuncaoUpdateView(HTMXModalFormMixin, ViewFilialScopedMixin, SSTPermissionMixin, UpdateView): # <-- ADICIONE O MIXIN
    model = Funcao
    form_class = FuncaoForm
    # template_name = 'seguranca_trabalho/funcao_form.html' # <- Pode remover esta linha
    success_url = reverse_lazy('seguranca_trabalho:funcao_list')
    permission_required = 'seguranca_trabalho.change_funcao'

    def form_valid(self, form):
        messages.success(self.request, f"A função '{form.instance.nome}' foi atualizada com sucesso.")
        # A lógica de resposta HTMX será tratada pelo mixin
        return super().form_valid(form)


class FuncaoDeleteView(ViewFilialScopedMixin, SSTPermissionMixin, DeleteView):
    """
    Exclui uma função.
    """
    model = Funcao
    template_name = 'seguranca_trabalho/confirm_delete.html'  # Reutilizando o template de confirmação
    success_url = reverse_lazy('seguranca_trabalho:funcao_list')
    context_object_name = 'object'
    permission_required = 'seguranca_trabalho.delete_funcao'

    def form_valid(self, form):
        messages.success(self.request, f"A função '{self.object.nome}' foi excluída com sucesso.")
        return super().form_valid(form)

# Cenário 1: Substitui a função lista_associacoes
class AssociacaoListView(ListView):
    """
    Exibe uma lista de todas as associações entre Cargos e Funções.
    """
    model = CargoFuncao
    template_name = 'seguranca_trabalho/lista_associacoes.html'
    context_object_name = 'seguranca_trabalho:lista_de_associacoes' 


class AssociacaoListView(ListView):
    model = CargoFuncao
    template_name = 'seguranca_trabalho/lista_associacoes.html'
    context_object_name = 'lista_de_associacoes' 

    def get_queryset(self):
        # Pode deixar este método como estava antes, simples e limpo
        return CargoFuncao.objects.select_related('cargo', 'funcao').all()

        
# Cenário 3: Substitui a função associar_funcao_cargo
class AssociacaoCreateView(CreateView):
    """
    Exibe um formulário para criar uma nova associação entre Cargo e Função.
    """
    model = CargoFuncao
    # CORREÇÃO: Aponte para a classe do formulário, não do modelo.
    form_class = CargoFuncaoForm
    template_name = 'seguranca_trabalho/formulario_associacao.html'
    success_url = reverse_lazy('seguranca_trabalho:lista_associacoes')
    permission_required = 'seguranca_trabalho.add_cargofuncao'

    def form_valid(self, form):
        messages.success(self.request, "Associação criada com sucesso!")
        return super().form_valid(form)
    

    