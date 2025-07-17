# seguranca_trabalho/views.py


from django.http import HttpResponse
from django.template.loader import get_template
from django.shortcuts import render
from django.conf import settings
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.http import Http404, HttpResponseForbidden
from django.db import transaction, IntegrityError
from django.utils import timezone
from django.db.models import Count, Q, ProtectedError
from django.contrib.staticfiles import finders

from io import BytesIO
from datetime import timedelta
from .models import (
    Equipamento, FichaEPI, EntregaEPI, Fabricante, Fornecedor, Funcao,
    MatrizEPI, MovimentacaoEstoque
)
from .forms import (
    EquipamentoForm, FichaEPIForm, EntregaEPIForm, AssinaturaForm,
    FabricanteForm, FornecedorForm
)
from departamento_pessoal.models import Funcionario
# Supondo que você queira manter isso no dashboard
from tarefas.models import Tarefas
from xhtml2pdf import pisa
# --- MIXINS E CLASSES BASE ---


class SSTPermissionMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """
    Mixin para verificar se o usuário tem permissão para acessar a área de SST.
    Altere a permissão para uma mais específica do seu app.
    """
    permission_required = 'auth.view_user'  # Ex: 'seguranca_trabalho.view_equipamento'

    def handle_no_permission(self):
        messages.error(
            self.request, "Você não tem permissão para acessar esta página.")
        # Redireciona para o dashboard ou uma página de acesso negado
        return redirect(reverse_lazy('core:dashboard'))


class PaginationMixin:
    """Adiciona paginação a uma ListView."""
    paginate_by = 15


class SuccessDeleteMessageMixin:
    """Adiciona uma mensagem de sucesso ao deletar um objeto."""
    success_message = "Registro excluído com sucesso."

    def form_valid(self, form):
        messages.success(self.request, self.success_message)
        return super().form_valid(form)

# --- VIEWS DO DASHBOARD ---
class DashboardSSTView(SSTPermissionMixin, TemplateView):
    template_name = 'seguranca_trabalho/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Dashboard de Segurança do Trabalho'

        hoje = timezone.now().date()
        trinta_dias_frente = hoje + timezone.timedelta(days=30)

        # KPIs de SST - Agora todos são consultas diretas e eficientes
        context['total_equipamentos_ativos'] = Equipamento.objects.filter(
            ativo=True).count()
        context['fichas_ativas'] = FichaEPI.objects.filter(
            funcionario__status='ATIVO').count()
        context['entregas_pendentes_assinatura'] = EntregaEPI.objects.filter(
            assinatura_recebimento__isnull=True).count()

        # KPI Otimizado: Filtra e conta tudo diretamente no banco de dados
        # Acessando o campo de data através do relacionamento com Equipamento
        context['epis_vencendo_em_30_dias'] = EntregaEPI.objects.filter(
            data_devolucao__isnull=True,
            assinatura_recebimento__isnull=False,
            # Use o caminho: 'campo_de_relacionamento__campo_no_outro_modelo'
            equipamento__data_validade_ca__gte=hoje,
            equipamento__data_validade_ca__lte=trinta_dias_frente
        ).count()

        # Outras métricas (ex: de Tarefas, se aplicável)
        if 'tarefas' in settings.INSTALLED_APPS:
            try:
                # Adicionar filtro por categoria, se houver
                tarefas_sst = Tarefas.objects.filter(
                    responsavel=self.request.user)
                context['tarefas_pendentes_usuario'] = tarefas_sst.filter(
                    status__in=['pendente', 'andamento']).count()
            except:
                # Caso o modelo Tarefas não exista ou dê erro, evita quebrar o dashboard
                context['tarefas_pendentes_usuario'] = 0

        return context

# --- CRUDs DE CATÁLOGO (Equipamento, Fabricante, Fornecedor) ---

# Fabricante
class FabricanteListView(SSTPermissionMixin, PaginationMixin, ListView):
    model = Fabricante
    template_name = 'seguranca_trabalho/fabricante_list.html'


class FabricanteDetailView(SSTPermissionMixin, DetailView):
    model = Fabricante
    template_name = 'seguranca_trabalho/fabricante_detail.html'


class FabricanteCreateView(SSTPermissionMixin, SuccessMessageMixin, CreateView):
    model = Fabricante
    form_class = FabricanteForm
    template_name = 'seguranca_trabalho/fabricante_form.html'
    success_message = "Fabricante cadastrado com sucesso!"
    success_url = reverse_lazy('seguranca_trabalho:fabricante_list')


class FabricanteUpdateView(SSTPermissionMixin, SuccessMessageMixin, UpdateView):
    model = Fabricante
    form_class = FabricanteForm
    template_name = 'seguranca_trabalho/fabricante_form.html'
    success_message = "Fabricante atualizado com sucesso!"
    success_url = reverse_lazy('seguranca_trabalho:fabricante_list')


class FabricanteDeleteView(SSTPermissionMixin, SuccessDeleteMessageMixin, DeleteView):
    model = Fabricante
    template_name = 'seguranca_trabalho/confirm_delete.html'
    success_url = reverse_lazy('seguranca_trabalho:fabricante_list')
    success_message = "Fabricante excluído com sucesso."

# Fornecedor
class FornecedorListView(SSTPermissionMixin, PaginationMixin, ListView):
    model = Fornecedor
    template_name = 'seguranca_trabalho/ornecedor_list.html'


class FornecedorDetailView(SSTPermissionMixin, DetailView):
    model = Fornecedor
    template_name = 'seguranca_trabalho/fornecedor_detail.html'


class FornecedorCreateView(SSTPermissionMixin, SuccessMessageMixin, CreateView):
    model = Fornecedor
    form_class = FornecedorForm
    template_name = 'seguranca_trabalho/fornecedor_form.html'
    success_message = "Fornecedor cadastrado com sucesso!"
    success_url = reverse_lazy('seguranca_trabalho:fornecedor_list')


class FornecedorUpdateView(SSTPermissionMixin, SuccessMessageMixin, UpdateView):
    model = Fornecedor
    form_class = FornecedorForm
    template_name = 'seguranca_trabalho/fornecedor_form.html'
    success_message = "Fornecedor atualizado com sucesso!"
    success_url = reverse_lazy('seguranca_trabalho:fornecedor_list')

# Equipamento
class EquipamentoListView(SSTPermissionMixin, PaginationMixin, ListView):
    model = Equipamento
    queryset = Equipamento.objects.select_related(
        'fabricante').filter(ativo=True)
    template_name = 'seguranca_trabalho/equipamento_list.html'
    context_object_name = 'equipamentos'

    def get_context_data(self, **kwargs):
        # Primeiro, chama a implementação base para pegar o contexto existente
        context = super().get_context_data(**kwargs)

        # Agora, adiciona a sua própria informação ao contexto
        # Aqui contamos TODOS os equipamentos, ignorando o filtro 'ativo=True'
        context['total_geral_equipamentos'] = Equipamento.objects.count()

        return context


class EquipamentoDetailView(SSTPermissionMixin, DetailView):
    model = Equipamento
    queryset = Equipamento.objects.select_related(
        'fabricante', 'fornecedor_padrao')
    template_name = 'seguranca_trabalho/equipamento_detail.html'


class EquipamentoCreateView(SSTPermissionMixin, SuccessMessageMixin, CreateView):
    model = Equipamento
    form_class = EquipamentoForm
    template_name = 'seguranca_trabalho/equipamento_form.html'
    success_message = "Equipamento cadastrado com sucesso!"
    success_url = reverse_lazy('seguranca_trabalho:equipamento_list')


class EquipamentoUpdateView(SSTPermissionMixin, SuccessMessageMixin, UpdateView):
    model = Equipamento
    form_class = EquipamentoForm
    template_name = 'seguranca_trabalho/equipamento_form.html'
    success_message = "Equipamento atualizado com sucesso!"

    def get_success_url(self):
        return reverse('seguranca_trabalho:equipamento_detail', kwargs={'pk': self.object.pk})


class EquipamentoDeleteView(SSTPermissionMixin, SuccessDeleteMessageMixin, DeleteView):
    model = Equipamento
    # Um template genérico de confirmação
    template_name = 'seguranca_trabalho/confirm_delete.html'
    success_url = reverse_lazy('seguranca_trabalho:equipamento_list')
    success_message = "Equipamento excluído com sucesso."


# --- CRUD DE FICHAS DE EPI E ENTREGAS ---
class FichaEPIListView(SSTPermissionMixin, PaginationMixin, ListView):
    model = FichaEPI
    template_name = 'seguranca_trabalho/ficha_list.html'
    context_object_name = 'fichas'
    queryset = FichaEPI.objects.select_related(
        'funcionario__cargo').filter(funcionario__status='ATIVO')


class FichaEPICreateView(SSTPermissionMixin, CreateView):
    model = FichaEPI
    form_class = FichaEPIForm
    template_name = 'seguranca_trabalho/ficha_create.html'

    def form_valid(self, form):
        try:
            # Garante que o usuário do request seja o criador (se houver campo)
            # form.instance.criado_por = self.request.user
            self.object = form.save()
            messages.success(
                self.request, f"Ficha de EPI para {self.object.funcionario.nome_completo} criada com sucesso!")
            return redirect(self.get_success_url())
        except IntegrityError:
            messages.error(
                self.request, "Este funcionário já possui uma ficha de EPI.")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse('seguranca_trabalho:ficha_detail', kwargs={'pk': self.object.pk})


class FichaEPIDetailView(SSTPermissionMixin, DetailView):
    model = FichaEPI
    template_name = 'seguranca_trabalho/ficha_detail.html'
    context_object_name = 'ficha'

    def get_queryset(self):
        # Otimiza a query para buscar dados relacionados de uma só vez
        return FichaEPI.objects.select_related(
            'funcionario__cargo', 
            'funcao',
            'funcionario__cliente' # Busca o cliente (que contém o contrato) do funcionário
        ).prefetch_related(
            'entregas__equipamento'
        ).all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['entrega_form'] = EntregaEPIForm()
        context['assinatura_form'] = AssinaturaForm()
        return context
    
class FichaEPIUpdateView(SSTPermissionMixin, SuccessMessageMixin, UpdateView):
    model = FichaEPI
    form_class = FichaEPIForm # Reutiliza o mesmo formulário da criação
    template_name = 'seguranca_trabalho/ficha_create.html' # Reutiliza o template
    success_message = "Ficha de EPI atualizada com sucesso!"

    def get_success_url(self):
        return reverse('seguranca_trabalho:ficha_detail', kwargs={'pk': self.object.pk})


class FichaEPIDeleteView(DeleteView): # Se você usa um Mixin de permissão, adicione-o aqui também
    model = FichaEPI
    template_name = 'seguranca_trabalho/ficha_delete.html'  # Certifique-se que este template existe
    success_url = reverse_lazy('seguranca_trabalho:ficha_list')  # Mude 'ficha_list' para o nome da sua URL da lista de fichas

    def post(self, request, *args, **kwargs):
        """
        Sobrescreve o método post para tratar o ProtectedError.
        """
        self.object = self.get_object()
        try:
            # Tenta deletar o objeto normalmente
            response = self.object.delete()
            messages.success(request, f"A Ficha de EPI para '{self.object.funcionario}' foi excluída com sucesso.")
            return redirect(self.success_url)

        except ProtectedError:
            # Se a exclusão for bloqueada, entra aqui
            messages.error(
                request, 
                "Exclusão não permitida. Esta ficha possui um histórico de entregas de EPIs associado. Por favor, contate o administrador do sistema."
            )
            # Redireciona de volta para a página de detalhes da ficha que falhou em ser excluída
            return redirect('seguranca_trabalho:ficha_detail', pk=self.object.pk) # Mude 'ficha_detail' para o nome da sua URL de detalhes


# --- VIEWS DE AÇÃO (Entregas, Assinaturas, Devoluções) ---
class AdicionarEntregaView(SSTPermissionMixin, View):
    """
    Processa o formulário para adicionar um novo EPI a uma Ficha.
    """
    @transaction.atomic # Garante que a entrega e a movimentação de estoque ocorram juntas
    def post(self, request, *args, **kwargs):
        ficha = get_object_or_404(FichaEPI, pk=kwargs.get('ficha_pk'))
        form = EntregaEPIForm(request.POST)

        if form.is_valid():
            entrega = form.save(commit=False)
            entrega.ficha = ficha
            entrega.save()

            # Lógica para abater do estoque, se aplicável
            MovimentacaoEstoque.objects.create(
                equipamento=entrega.equipamento,
                tipo='SAIDA',
                quantidade=-entrega.quantidade, # Negativo para indicar saída
                responsavel=request.user,
                justificativa=f"Entrega para {ficha.funcionario.nome_completo}",
                entrega_associada=entrega
            )

            messages.success(request, f"Entrega de '{entrega.equipamento.nome}' registrada. Aguardando assinatura do colaborador.")
        else:
            # Concatena os erros do formulário em uma única mensagem
            error_list = [f"{field}: {', '.join(errors)}" for field, errors in form.errors.items()]
            error_message = "Erro ao registrar entrega. " + " ".join(error_list)
            messages.error(request, error_message)

        return redirect('seguranca_trabalho:ficha_detail', pk=ficha.pk)


class AssinarEntregaView(SSTPermissionMixin, View):
    def post(self, request, *args, **kwargs):
        pk_da_entrega = kwargs.get('pk')
        entrega = get_object_or_404(EntregaEPI, pk=pk_da_entrega)

        # --- LÓGICA ATUALIZADA ---
        # Prioriza o upload de arquivo se ele existir
        if request.FILES.get('assinatura_imagem'):
            entrega.assinatura_imagem = request.FILES['assinatura_imagem']
            # Limpa o campo de assinatura base64, se houver, para evitar duplicidade
            entrega.assinatura_recebimento = None
            messages.success(request, "Assinatura anexada com sucesso!")
        
        # Se não houver arquivo, procura pela assinatura desenhada
        elif request.POST.get('assinatura_base64'):
            form = AssinaturaForm(request.POST)
            if form.is_valid():
                entrega.assinatura_recebimento = form.cleaned_data['assinatura_base64']
                # Limpa o campo de imagem, se houver
                entrega.assinatura_imagem = None
                messages.success(request, "Assinatura desenhada salva com sucesso!")
            else:
                messages.error(request, "Erro no formulário de assinatura desenhada.")
                return redirect('seguranca_trabalho:ficha_detail', pk=entrega.ficha.pk)
        
        else:
             messages.error(request, "Nenhuma assinatura foi fornecida (desenhada ou anexada).")
             return redirect('seguranca_trabalho:ficha_detail', pk=entrega.ficha.pk)

        # Salva as alterações para ambos os casos
        entrega.data_entrega = timezone.now()
        entrega.save()

        return redirect('seguranca_trabalho:ficha_detail', pk=entrega.ficha.pk)


class RegistrarDevolucaoView(SSTPermissionMixin, View):
    """
    Registra a data da devolução de um EPI.
    """
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        entrega = get_object_or_404(EntregaEPI, pk=kwargs.get('pk'), data_devolucao__isnull=True)

        entrega.data_devolucao = timezone.now()
        entrega.recebedor_devolucao = request.user
        entrega.save(update_fields=['data_devolucao', 'recebedor_devolucao'])

        # Opcional: Lógica para retornar o item ao estoque, se for reutilizável
        # MovimentacaoEstoque.objects.create(...)

        messages.success(request, "Devolução de EPI registrada com sucesso!")
        return redirect('seguranca_trabalho:ficha_detail', pk=entrega.ficha.pk)


# Gerador de relatório PDF
class GerarFichaPDFView(SSTPermissionMixin, DetailView):
    model = FichaEPI
    template_name = 'seguranca_trabalho/ficha_pdf_template.html'

    def render_to_pdf(self, template_src, context_dict={}):
        template = get_template(template_src)
        html = template.render(context_dict)
        result = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
        if not pdf.err:
            return HttpResponse(result.getvalue(), content_type='application/pdf')
        return None

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        
        # Otimiza a query para buscar todos os dados necessários para o PDF
        context['ficha'] = FichaEPI.objects.select_related(
            'funcionario__cargo', 'funcao'
        ).prefetch_related(
            'entregas__equipamento'
        ).get(pk=self.object.pk)

        # Encontra o caminho absoluto da logomarca nos arquivos estáticos
        logo_path = finders.find('seguranca_trabalho/images/logocetest.png')
        
        context['logo_path'] = logo_path

        pdf = self.render_to_pdf(self.template_name, context)
        if pdf:
            response = HttpResponse(pdf, content_type='application/pdf')
            # Define o nome do arquivo para download
            filename = f"Ficha_EPI_{self.object.funcionario.nome_completo}.pdf"
            content = f"inline; filename='{filename}'"
            response['Content-Disposition'] = content
            return response
        return HttpResponse("Erro ao gerar PDF", status=400)
    

