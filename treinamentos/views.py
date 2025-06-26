
# Importe seus modelos e o módulo gerador
from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count, Q, Sum, F
from django.forms import inlineformset_factory
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (CreateView, DeleteView, DetailView, ListView, UpdateView, TemplateView)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.db import models
from django.db.models.functions import Coalesce, ExtractMonth
from django.db.models.fields import FloatField

import os
import io
import json
import traceback

from datetime import datetime
from urllib import request
from treinamentos import treinamento_generators
from .models import Treinamento, TipoCurso, Participante
from .forms import (BaseParticipanteFormSet, ParticipanteForm, TipoCursoForm, TreinamentoForm, ParticipanteFormSet)


class TreinamentoFormsetMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['form_participantes'] = ParticipanteFormSet(
                self.request.POST,
                instance=self.object,
                prefix='participantes'
            )
        else:
            context['form_participantes'] = ParticipanteFormSet(
                instance=self.object,
                prefix='participantes'
            )
        return context

    def form_valid(self, form):
        self.object = form.save(commit=False)
        context = self.get_context_data()
        form_participantes = ParticipanteFormSet(self.request.POST, instance=self.object, prefix='participantes')

        if form.is_valid() and form_participantes.is_valid():
            self.object.save()
            form_participantes.instance = self.object
            form_participantes.save()
            return super().form_valid(form)
        else:
            return self.form_invalid(form, form_participantes)

    def form_invalid(self, form, form_participantes):
        return self.render_to_response(self.get_context_data(form=form, form_participantes=form_participantes))

    
class CriarTreinamentoView(LoginRequiredMixin, PermissionRequiredMixin,
                            TreinamentoFormsetMixin, SuccessMessageMixin, CreateView):
    model = Treinamento
    form_class = TreinamentoForm
    template_name = 'treinamentos/criar_treinamento.html'
    permission_required = 'treinamentos.add_treinamento'
    success_message = "Treinamento criado com sucesso!"

    def get_success_url(self):
        return reverse_lazy('treinamentos:detalhe_treinamento', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Novo Treinamento'
        return context


# --- Visualizações para Treinamento (CRUD) ---

class TreinamentoListView(LoginRequiredMixin, ListView):
    """Lista todos os treinamentos com filtros de busca."""
    model = Treinamento
    template_name = 'treinamentos/lista_treinamentos.html'
    context_object_name = 'treinamentos'
    paginate_by = 15

    def get_queryset(self):
        """Aplica filtros de status, tipo de curso e busca textual."""
        queryset = Treinamento.objects.select_related('tipo_curso').order_by('-data_inicio')

        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        tipo_curso = self.request.GET.get('tipo_curso')
        if tipo_curso:
            queryset = queryset.filter(tipo_curso_id=tipo_curso)

        busca = self.request.GET.get('busca')
        if busca:
            queryset = queryset.filter(
                Q(nome__icontains=busca) |
                Q(local__icontains=busca) |
                Q(palestrante__icontains=busca)
            )
        return queryset

    def get_context_data(self, **kwargs):
        """Adiciona dados extras ao contexto para os filtros do template."""
        context = super().get_context_data(**kwargs)
        context['tipos_curso'] = TipoCurso.objects.filter(ativo=True)
        context['total_treinamentos'] = Treinamento.objects.count()
        return context

class EditarTreinamentoView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Treinamento
    form_class = TreinamentoForm
    template_name = 'treinamentos/editar_treinamento.html'
    permission_required = 'treinamentos.change_treinamento'
    success_message = "Treinamento atualizado com sucesso!"

    def get_success_url(self):
        return reverse_lazy('treinamentos:detalhe_treinamento', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Treinamento'
        context['participantes_formset'] = ParticipanteFormSet(instance=self.object, prefix='participantes')
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        participantes_formset = ParticipanteFormSet(request.POST, instance=self.object, prefix='participantes')

        if form.is_valid() and participantes_formset.is_valid():
            self.object = form.save()
            participantes_formset.save()
            return self.form_valid(form) # Aqui, você pode redirecionar ou fazer o que for necessário após o sucesso
        else:
            return self.form_invalid(form, participantes_formset)

    def form_valid(self, form):
        return super().form_valid(form)

    def form_invalid(self, form, participantes_formset):
        return self.render_to_response(self.get_context_data(form=form, participantes_formset=participantes_formset))


class DetalheTreinamentoView(LoginRequiredMixin, DetailView):
    """Exibe os detalhes de um treinamento específico."""
    model = Treinamento
    template_name = 'treinamentos/detalhe_treinamento.html'

    def get_context_data(self, **kwargs):
        """Adiciona a lista de participantes otimizada ao contexto."""
        context = super().get_context_data(**kwargs)
        # Otimiza a consulta para buscar funcionários junto com os participantes
        context['participantes'] = self.object.participantes.select_related('funcionario')
        return context


class ExcluirTreinamentoView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, DeleteView):
    """View para confirmar e excluir um treinamento."""
    model = Treinamento
    template_name = 'treinamentos/confirmar_exclusao_treinamento.html'
    success_url = reverse_lazy('treinamentos:lista_treinamentos')
    permission_required = 'treinamentos.delete_treinamento'
    success_message = "Treinamento excluído com sucesso!"


class TipoCursoListView(LoginRequiredMixin, ListView):
    """Lista todos os tipos de curso com filtros."""
    model = TipoCurso
    template_name = 'treinamentos/lista_tipo_curso.html'
    context_object_name = 'cursos'
    paginate_by = 10

    def get_queryset(self):
        """Aplica filtros de status e busca textual."""
        queryset = TipoCurso.objects.all().order_by('nome')

        status = self.request.GET.get('status')
        if status == 'ativo':
            queryset = queryset.filter(ativo=True)
        elif status == 'inativo':
            queryset = queryset.filter(ativo=False)

        busca = self.request.GET.get('busca')
        if busca:
            queryset = queryset.filter(
                Q(nome__icontains=busca) |
                Q(descricao__icontains=busca)
            )
        return queryset

    def get_context_data(self, **kwargs):
        """Adiciona a contagem de cursos ativos ao contexto."""
        context = super().get_context_data(**kwargs)
        context['total_ativos'] = TipoCurso.objects.filter(ativo=True).count()
        return context


class CriarTipoCursoView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    """View para criar um novo tipo de curso."""
    model = TipoCurso
    form_class = TipoCursoForm
    template_name = 'treinamentos/criar_tipo_curso.html'
    success_url = reverse_lazy('treinamentos:lista_tipo_curso')
    permission_required = 'treinamentos.add_tipocurso'
    success_message = "Tipo de curso cadastrado com sucesso!"

    def get_context_data(self, **kwargs):
        """Adiciona o título da página ao contexto."""
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastrar Tipo de Curso'
        return context


class EditarTipoCursoView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    """View para editar um tipo de curso existente."""
    model = TipoCurso
    form_class = TipoCursoForm
    template_name = 'treinamentos/editar_tipo_curso.html'
    success_url = reverse_lazy('treinamentos:lista_tipo_curso')
    permission_required = 'treinamentos.change_tipocurso'
    success_message = "Tipo de curso atualizado com sucesso!"

    def get_context_data(self, **kwargs):
        """Adiciona o título da página ao contexto."""
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Tipo de Curso'
        return context


class ExcluirTipoCursoView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, DeleteView):
    """View para confirmar e excluir um tipo de curso."""
    model = TipoCurso
    template_name = 'treinamentos/excluir_tipo_curso.html'
    success_url = reverse_lazy('treinamentos:lista_tipo_curso')
    permission_required = 'treinamentos.delete_tipocurso'
    success_message = "Tipo de curso excluído com sucesso!"


# --- Visualizações para Relatórios ---

class RelatorioTreinamentosView(LoginRequiredMixin, ListView):
    """
    Gera um relatório de treinamentos com base em filtros.
    Agora herda de ListView para buscar e listar os treinamentos.
    """
    model = Treinamento
    template_name = 'treinamentos/relatorio_treinamentos.html'
    context_object_name = 'object_list'  # O nome padrão, mas é bom ser explícito
    paginate_by = 20 # Opcional: Adiciona paginação

    def get_queryset(self):
        """
        Filtra os treinamentos por ano e tipo de curso, conforme os parâmetros da URL.
        """
        # Começa com todos os treinamentos e aplica os filtros
        queryset = super().get_queryset().select_related('tipo_curso', 'responsavel')

        ano = self.request.GET.get('ano')
        if ano:
            queryset = queryset.filter(data_inicio__year=ano)

        tipo_curso_id = self.request.GET.get('tipo_curso')
        if tipo_curso_id:
            queryset = queryset.filter(tipo_curso_id=tipo_curso_id)

        return queryset.order_by('-data_inicio')

    def get_context_data(self, **kwargs):
        """
        Adiciona os dados necessários para os menus de filtro (dropdowns) ao contexto.
        """
        context = super().get_context_data(**kwargs)
        # Para o filtro de anos
        context['anos'] = Treinamento.objects.dates('data_inicio', 'year', order='DESC')
        # Para o filtro de tipos de curso
        context['tipos_curso'] = TipoCurso.objects.filter(ativo=True).order_by('nome')
        return context
  
class RelatorioTreinamentoWordView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Gera e oferece para download o relatório de um treinamento específico em .docx.
    """
    permission_required = 'treinamentos.view_treinamento'

    def get(self, request, *args, **kwargs):
        """
        Este método lida com a requisição GET, gera o relatório e o retorna.
        """
        try:
            # 1. Obter o objeto do treinamento a partir da URL
            treinamento_pk = self.kwargs.get('pk')
            treinamento = get_object_or_404(Treinamento, pk=treinamento_pk)

            # 2. Construir o caminho para o arquivo da logomarca (Cenário A)
            caminho_logo = os.path.join(settings.MEDIA_ROOT, 'imagens', 'logocetest.png')

            # 3. (Opcional, mas recomendado) Adicionar prints para depuração
            #    Verifique a saída no console onde você rodou 'runserver'
            print(f"--- Gerando Relatório para Treinamento PK: {treinamento_pk} ---")
            print(f"Buscando logomarca em: {caminho_logo}")

            # 4. Verificar se a logomarca realmente existe no caminho especificado
            if not os.path.exists(caminho_logo):
                print("!! ATENÇÃO: Arquivo de logomarca NÃO ENCONTRADO. O relatório será gerado sem a logo.")
                caminho_logo = None  # Define como None se não encontrado
            else:
                print("OK: Arquivo de logomarca encontrado.")

            # 5. Chamar a função geradora, passando o treinamento E o caminho da logo
            buffer = treinamento_generators.gerar_relatorio_word(treinamento, caminho_logo)

            # 6. Preparar e retornar a resposta HTTP com o arquivo .docx
            response = HttpResponse(
                buffer,
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            # Limpa o nome do arquivo para evitar caracteres inválidos
            nome_arquivo = ''.join(c for c in treinamento.nome if c.isalnum() or c in (' ', '_')).rstrip()
            response['Content-Disposition'] = f'attachment; filename="relatorio_{nome_arquivo[:30]}.docx"'
            
            print("--- Relatório gerado e enviado com sucesso. ---")
            return response

        except Treinamento.DoesNotExist:
            # Este bloco é um backup, mas get_object_or_404 já lida com isso levantando um erro 404.
            messages.error(request, "Treinamento não encontrado.")
            return redirect('treinamentos:lista_treinamentos')

        except Exception as e:
            # Captura qualquer outro erro que possa ocorrer durante o processo
            print(f"ERRO CRÍTICO AO GERAR WORD: {str(e)}")
            print(traceback.format_exc())  # Mostra o erro completo no console
            messages.error(request, f"Ocorreu um erro inesperado ao gerar o relatório Word.")
            # Redireciona de volta para a página de detalhes do treinamento
            return redirect('treinamentos:detalhe_treinamento', pk=self.kwargs.get('pk'))

class RelatorioGeralExcelView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Gera e oferece para download um relatório geral de treinamentos em .xlsx.
    """
    permission_required = 'treinamentos.view_report'

    def get(self, request, *args, **kwargs):
        # Esta linha assume que TreinamentoListView está definida acima neste mesmo arquivo.
        list_view = TreinamentoListView() 
        list_view.request = self.request
        queryset = list_view.get_queryset()

        try:
            # --- MUDANÇA 3: Chamamos a função a partir do novo módulo ---
            buffer = treinamento_generators.gerar_relatorio_excel(queryset)

            response = HttpResponse(
                buffer,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            data_hoje = datetime.now().strftime('%Y-%m-%d')
            response['Content-Disposition'] = f'attachment; filename="relatorio_geral_treinamentos_{data_hoje}.xlsx"'
            return response
            
        except Exception as e:
            print(f"ERRO REAL AO GERAR EXCEL: {e}")
            messages.error(request, f"Ocorreu um erro ao gerar o relatório Excel.")
            return redirect('treinamentos:lista_treinamentos')

class DashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'treinamentos/dashboard.html'
    permission_required = 'treinamentos.view_report'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Treinamentos por área
        treinamentos_por_area = Treinamento.objects.values(
            'tipo_curso__area'
        ).annotate(
            total=Count('id')
        ).order_by('-total')

        # Participação mensal
        participacao_mensal = Participante.objects.filter(
            presente=True
        ).annotate(
            month=ExtractMonth('data_registro')
        ).values(
            'month'
        ).annotate(
            total=Count('id')
        ).order_by('month')

        # Status dos treinamentos
        status_treinamentos = Treinamento.objects.values(
            'status'
        ).annotate(
            total=Count('id')
        ).order_by('-total')

        # Treinamentos por modalidade
        treinamentos_por_modalidade = Treinamento.objects.values(
            'tipo_curso__modalidade'
        ).annotate(
            total=Count('id')
        ).order_by('-total')

        # Custo total por área (VERSÃO CORRIGIDA)
        custo_por_area = Treinamento.objects.values(
            'tipo_curso__area'
        ).annotate(
            # Coalesce trata custos nulos, e output_field garante um float
            total=Coalesce(Sum('custo'), 0.0, output_field=FloatField())
        ).order_by('tipo_curso__area') # Ordenar por área para consistência

        # Treinamentos recentes
        treinamentos_recentes = Treinamento.objects.order_by('-data_inicio')[:5]

        # --- CÁLCULOS TOTAIS ---
        todos_treinamentos = Treinamento.objects.all()
        total_treinamentos = todos_treinamentos.count()
        total_participantes = Participante.objects.filter(presente=True).count()
        total_custo_agregado = todos_treinamentos.aggregate(
            total=Coalesce(Sum('custo'), 0.0, output_field=FloatField())
        )
        total_custo = total_custo_agregado['total']
        em_andamento = todos_treinamentos.filter(status='A').count()

        # Obter treinamentos em andamento
        em_andamento = next(
            (item['total'] for item in status_treinamentos if item['status'] == 'A'),
            0
        )

        # --- ATUALIZAÇÃO DO CONTEXTO ---
        context.update({
            'total_treinamentos': total_treinamentos,
            'total_participantes': total_participantes,
            'total_custo': total_custo,
            'em_andamento': em_andamento,
            'treinamentos_recentes': treinamentos_recentes,
            
            # Dados para os gráficos, agora em JSON
            'treinamentos_por_area': json.dumps(list(treinamentos_por_area)),
            'participacao_mensal': json.dumps(list(participacao_mensal)),
            'status_treinamentos': json.dumps(list(status_treinamentos)),
            'treinamentos_por_modalidade': json.dumps(list(treinamentos_por_modalidade)),
            'custo_por_area_json': json.dumps(list(custo_por_area)),
        })
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)   
        return render(request, self.template_name, context)



