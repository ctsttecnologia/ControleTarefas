# seguranca_trabalho/views.py

import io
import json
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
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

from core.mixins import (FilialCreateMixin, SSTPermissionMixin,
                         ViewFilialScopedMixin)
from departamento_pessoal.models import Funcionario
from usuario.models import Filial
from usuario.views import StaffRequiredMixin

# Imports de Forms e Models atualizados
from .forms import (AssinaturaEntregaForm, EntregaEPIForm, EquipamentoForm, FichaEPIForm)
from .models import (EntregaEPI, Equipamento, FichaEPI, Funcao, MatrizEPI)


# --- Ações de Entrega ---
import logging
logger = logging.getLogger(__name__)


# --- Funções Auxiliares ---

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
        # CORRIGIDO: Removido 'fornecedor' do select_related pois o campo não existe mais no modelo Equipamento.
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

class FichaEPIListView(ViewFilialScopedMixin, SSTPermissionMixin, ListView):
    model = FichaEPI
    template_name = 'seguranca_trabalho/ficha_list.html'
    context_object_name = 'fichas'
    paginate_by = 20
    permission_required = 'seguranca_trabalho.view_fichaepi'

    def get_queryset(self):
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

class FichaEPIDetailView(ViewFilialScopedMixin, SSTPermissionMixin, FormMixin, DetailView):
    model = FichaEPI
    template_name = 'seguranca_trabalho/ficha_detail.html'
    context_object_name = 'ficha'
    form_class = EntregaEPIForm
    permission_required = 'seguranca_trabalho.view_fichaepi'

    def get_success_url(self):
        return reverse('seguranca_trabalho:ficha_detail', kwargs={'pk': self.object.pk})
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Passa a filial da ficha para o formulário de entrega
        kwargs['filial'] = self.get_object().filial
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = self.get_form()
        context['entregas'] = self.object.entregas.select_related('equipamento').order_by('-data_entrega')
        return context

    def post(self, request, *args, **kwargs):
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

@login_required
def minha_ficha_redirect_view(request):
    try:
        ficha = FichaEPI.objects.get(funcionario=request.user.funcionario)
        return redirect('seguranca_trabalho:ficha_detail', pk=ficha.pk)
    except (FichaEPI.DoesNotExist, AttributeError):
        messages.error(request, "Seu usuário não possui uma ficha de EPI associada.")
        return redirect('usuario:profile')

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

class AssinarEntregaView(ViewFilialScopedMixin, SSTPermissionMixin, UpdateView):
    model = EntregaEPI
    form_class = AssinaturaEntregaForm
    template_name = 'seguranca_trabalho/entrega_sign.html'
    context_object_name = 'entrega'
    permission_required = 'seguranca_trabalho.assinar_entregaepi'

    def get_success_url(self):
        return reverse('seguranca_trabalho:ficha_detail', kwargs={'pk': self.object.ficha.pk})

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.data_devolucao or self.object.data_assinatura:
            messages.info(request, "Esta entrega já foi processada e não pode mais ser assinada.")
            return redirect(self.get_success_url())
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        # A lógica para salvar a assinatura (seja base64 ou imagem) é melhor tratada aqui
        # assumindo que o formulário está apenas validando a presença dos dados.
        self.object.assinatura_recebimento = self.request.POST.get('assinatura_base64')
        self.object.data_assinatura = timezone.now()
        self.object.save()
        messages.success(self.request, "Assinatura registrada com sucesso!")
        return redirect(self.get_success_url())

class RegistrarDevolucaoView(SSTPermissionMixin, View):
    permission_required = 'seguranca_trabalho.change_entregaepi' # Permissão para 'mudar' a entrega
    http_method_names = ['post']

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        filial_id = request.session.get('active_filial_id')
        entrega = get_object_or_404(EntregaEPI, pk=kwargs.get('pk'), filial_id=filial_id)
        
        if entrega.data_devolucao:
            messages.warning(request, f"O EPI '{entrega.equipamento.nome}' já foi devolvido.")
        else:
            entrega.data_devolucao = timezone.now().date()
            entrega.recebedor_devolucao = request.user
            entrega.save()
            messages.success(request, f"Devolução do EPI '{entrega.equipamento.nome}' registrada.")
            
        return redirect('seguranca_trabalho:ficha_detail', pk=entrega.ficha.pk)


# --- Relatórios e Painéis ---

class GerarFichaPDFView(ViewFilialScopedMixin, SSTPermissionMixin, DetailView):
    model = FichaEPI  # ADICIONADO: Informa ao DetailView qual modelo usar
    permission_required = 'seguranca_trabalho.view_fichaepi'

    def get(self, request, *args, **kwargs):
        # A filial já é verificada pelo seu mixin, não precisamos repetir aqui.
        
        # AGORA FUNCIONA: self.get_object() é fornecido pelo DetailView
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

class DashboardSSTView(ViewFilialScopedMixin, SSTPermissionMixin, TemplateView):

    template_name = 'seguranca_trabalho/dashboard.html'
    permission_required = 'seguranca_trabalho.view_equipamento'


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # O método get_queryset já filtra pela filial, vamos usá-lo
        equipamentos_da_filial = self.get_queryset(Equipamento)
        fichas_da_filial = self.get_queryset(FichaEPI)
        entregas_da_filial = self.get_queryset(EntregaEPI)
        matriz_da_filial = self.get_queryset(MatrizEPI)

        # --- 1. DADOS PARA OS CARDS DE KPI (COM NOMES CORRIGIDOS) ---
        context['total_equipamentos_ativos'] = equipamentos_da_filial.filter(ativo=True).count()
        # O template espera 'fichas_ativas'
        context['fichas_ativas'] = fichas_da_filial.filter(funcionario__status='ATIVO').count()
        # O template espera 'entregas_pendentes_assinatura'
        context['entregas_pendentes_assinatura'] = entregas_da_filial.filter(
            data_devolucao__isnull=True, 
            data_assinatura__isnull=True # Simplificado, já que a assinatura é uma data
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
        
        # O template espera 'epis_vencendo_em_30_dias'
        context['epis_vencendo_em_30_dias'] = epis_vencendo_30d_count

        # --- 3. DADOS PARA OS GRÁFICOS (mantido como JSON) ---
        # Gráfico da Matriz de EPI por Função
        matriz_chart_data = matriz_da_filial.values('funcao__nome').annotate(
            num_epis=Count('equipamento')
        ).order_by('-num_epis')[:10] # Limita aos 10 maiores
        
        if matriz_chart_data:
            # CORREÇÃO: Nomes que o novo template usará
            context['matriz_labels'] = json.dumps([m['funcao__nome'] for m in matriz_chart_data])
            context['matriz_data'] = json.dumps([m['num_epis'] for m in matriz_chart_data])

        # (A lógica do outro gráfico de situação foi removida para simplificar,
        # pois o template não a usava e pode ser complexa. Focamos no que pode ser exibido.)

        context['titulo_pagina'] = "Painel de Segurança do Trabalho"
        return context

    def get_queryset(self, model):
        """
        Método auxiliar para obter o queryset filtrado de forma robusta.
        """
        active_filial_id = self.request.session.get('active_filial_id')
        
        qs = model.objects.all()

        if active_filial_id:
            if hasattr(model, 'filial'):
                return qs.filter(filial_id=active_filial_id)
            # Para modelos como FichaEPI e EntregaEPI, o filtro pode ser através do funcionário
            elif hasattr(model, 'funcionario') and hasattr(model.funcionario.field.related_model, 'filial'):
                return qs.filter(funcionario__filial_id=active_filial_id)
            return qs.none() # Se não sabe como filtrar, não mostra nada
        
        if self.request.user.is_superuser:
            return qs

        return qs.none()

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
            # CORREÇÃO AQUI: Usando o nome correto do campo do modelo
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
    

