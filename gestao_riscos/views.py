from django.urls import reverse_lazy
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import TemplateView, CreateView

from .models import Incidente, Inspecao
from .forms import IncidenteForm, InspecaoForm

# -----------------------------------------------------------------------------
# MIXIN DE SEGURANÇA (Opcional para ListViews, mas bom de ter)
# -----------------------------------------------------------------------------
class FilialScopedMixin:
    """
    Mixin que filtra a queryset principal de uma View (ListView, DetailView)
    pela filial do usuário logado.
    """
    def get_queryset(self):
        # Chama o get_queryset da classe pai (ex: ListView)
        qs = super().get_queryset()
        # Usa o manager customizado para filtrar pela request
        return qs.for_request(self.request)

# -----------------------------------------------------------------------------
# VIEWS REATORADAS
# -----------------------------------------------------------------------------

class GestaoRiscosDashboardView(LoginRequiredMixin, TemplateView):
    """
    View principal que exibe um dashboard de incidentes e inspeções,
    filtrando os dados pela filial do usuário logado.
    """
    template_name = 'gestao_riscos/lista_riscos.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Usamos nosso manager customizado para buscar apenas dados da filial do usuário
        incidentes_da_filial = Incidente.objects.for_request(self.request)
        inspecoes_da_filial = Inspecao.objects.for_request(self.request)

        # Aplicamos a lógica de negócio sobre os dados já filtrados
        context['incidentes'] = incidentes_da_filial.order_by('-data_ocorrencia')[:10]
        context['inspecoes'] = inspecoes_da_filial.filter(status='PENDENTE').order_by('data_agendada')
        
        context['titulo_pagina'] = 'Dashboard de Gestão de Riscos'
        context['data_atual'] = timezone.now()
        
        return context


class RegistrarIncidenteView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """
    View para registrar um novo incidente, associando-o automaticamente
    ao usuário e à sua filial.
    """
    model = Incidente
    form_class = IncidenteForm
    template_name = 'gestao_riscos/registrar_incidente.html' # Um template genérico
    success_url = reverse_lazy('gestao_riscos:lista_riscos')
    success_message = "Incidente registrado com sucesso!"

    def form_valid(self, form):
        """
        Este método é chamado quando o formulário é válido.
        É o local perfeito para adicionar dados que não vêm do formulário.
        """
        # Pega o objeto do formulário, mas não salva no banco ainda (commit=False)
        incidente = form.save(commit=False)
        # Associa o usuário logado
        incidente.registrado_por = self.request.user
        # Associa a filial do usuário logado (CRUCIAL PARA A SEGURANÇA)
        if hasattr(self.request.user, 'filial'):
            incidente.filial = self.request.user.filial
        # Agora salva o objeto no banco com todos os dados
        incidente.save()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Adiciona dados extras ao contexto do template."""
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Registrar Novo Incidente'
        context['botao_submit_texto'] = 'Registrar Incidente'
        return context


class AgendarInspecaoView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """
    View para agendar uma nova inspeção, associando-a automaticamente
    à filial do usuário.
    """
    model = Inspecao
    form_class = InspecaoForm
    template_name = 'gestao_riscos/formulario_inspecao.html' # Reutilizando o template
    success_url = reverse_lazy('gestao_riscos:lista_riscos')
    success_message = "Inspeção agendada com sucesso!"

    def get_form_kwargs(self):
        """Passa o usuário logado como um argumento para o __init__ do formulário."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        """Associa a filial do usuário à nova inspeção."""
        inspecao = form.save(commit=False)
        if hasattr(self.request.user, 'filial'):
            inspecao.filial = self.request.user.filial
        inspecao.save()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Adiciona dados extras ao contexto do template."""
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Agendar Nova Inspeção'
        context['botao_submit_texto'] = 'Agendar Inspeção'
        return context
