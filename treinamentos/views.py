"""
Módulo de views para o app 'treinamentos'.
"""
from urllib import request
from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count, Q, Sum
from django.forms import inlineformset_factory
from django.urls import reverse_lazy
from django.views.generic import (CreateView, DeleteView, DetailView, ListView, UpdateView)
from django.shortcuts import render
from django.views.generic import TemplateView
from django.utils import timezone
from django.db import models
from django.db.models.functions import ExtractMonth

from .forms import (BaseParticipanteFormSet, ParticipanteForm, TipoCursoForm, TreinamentoForm, ParticipanteFormSet)
from .models import Participante, TipoCurso, Treinamento




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
        context = self.get_context_data()
        form_participantes = context['form_participantes']
        
        if form.is_valid() and form_participantes.is_valid():
            self.object = form.save()
            form_participantes.instance = self.object
            form_participantes.save()
            return super().form_valid(form)
        return self.render_to_response(self.get_context_data(form=form))

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

class EditarTreinamentoView(LoginRequiredMixin, PermissionRequiredMixin, TreinamentoFormsetMixin, SuccessMessageMixin, UpdateView):
    """View para editar um treinamento existente e seus participantes."""
    model = Treinamento
    form_class = TreinamentoForm
    template_name = 'treinamentos/editar_treinamento.html'
    permission_required = 'treinamentos.change_treinamento'
    success_message = "Treinamento atualizado com sucesso!"

    def get_success_url(self):
        """Redireciona para a página de detalhes do treinamento atualizado."""
        return reverse_lazy('treinamentos:detalhe_treinamento', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        """Adiciona o título da página ao contexto."""
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Treinamento'
        return context


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

class RelatorioTreinamentosView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Gera um relatório de treinamentos com base em filtros."""
    model = Treinamento
    template_name = 'treinamentos/relatorio_treinamentos.html'
    permission_required = 'treinamentos.view_report' # Garanta que essa permissão exista

    def get_queryset(self):
        """Filtra os treinamentos por ano e tipo de curso."""
        queryset = Treinamento.objects.all()

        ano = self.request.GET.get('ano')
        if ano:
            queryset = queryset.filter(data_inicio__year=ano)

        tipo_curso = self.request.GET.get('tipo_curso')
        if tipo_curso:
            queryset = queryset.filter(tipo_curso_id=tipo_curso)

        return queryset.select_related('tipo_curso')

    def get_context_data(self, **kwargs):
        """Adiciona os anos e tipos de curso disponíveis para os filtros."""
        context = super().get_context_data(**kwargs)
        context['anos'] = Treinamento.objects.dates('data_inicio', 'year', order='DESC')
        context['tipos_curso'] = TipoCurso.objects.filter(ativo=True)
        return context
    
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

        # Custo total por área
        custo_por_area = Treinamento.objects.values(
            'tipo_curso__area'
        ).annotate(
            total=Sum('custo')
        ).order_by('-total')

        # Treinamentos recentes
        treinamentos_recentes = Treinamento.objects.order_by('-data_inicio')[:5]

         # Calcular totais
        total_treinamentos = sum(item['total'] for item in treinamentos_por_area)
        total_participantes = sum(item['total'] for item in participacao_mensal)
        total_custo = sum(item['total'] for item in custo_por_area)
        
        # Obter treinamentos em andamento
        em_andamento = next(
            (item['total'] for item in status_treinamentos if item['status'] == 'A'), 
            0
        )

        context.update({
            'treinamentos_por_area': list(treinamentos_por_area),
            'participacao_mensal': list(participacao_mensal),
            'status_treinamentos': list(status_treinamentos),
            'treinamentos_por_modalidade': list(treinamentos_por_modalidade),
            'custo_por_area': list(custo_por_area),
            'treinamentos_recentes': treinamentos_recentes,
            'total_treinamentos': total_treinamentos,
            'total_participantes': total_participantes,
            'total_custo': total_custo,
            'em_andamento': em_andamento,
        })
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return render(request, self.template_name, context)