
# Importe seus modelos e o módulo gerador
from django.conf import settings
from django.contrib import messages
from django.db.models import Sum, Count, F, Q, FloatField
from django.forms import inlineformset_factory
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (CreateView, DeleteView, DetailView, ListView, UpdateView, TemplateView)
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models.functions import Coalesce, ExtractMonth
from django.db.models.fields import FloatField
from decimal import Decimal
import os
import io
import json
import traceback
from datetime import datetime, timedelta
from requests import request
from treinamentos import treinamento_generators
from treinamentos.forms import ParticipanteFormSet, TipoCursoForm, TreinamentoForm
from treinamentos.models import TentativaAvaliacaoEAD, ProgressoAulaEAD
from django.db import transaction
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from core.mixins import TecnicoScopeMixin 
from core.mixins import ViewFilialScopedMixin
from .models import CursoEAD, MatriculaEAD, CertificadoEAD
from django.utils import timezone
from django.template.loader import render_to_string, get_template
from django.views.generic import View # Garanta que 'View' está importado
from django.http import HttpResponse, Http404, HttpResponseRedirect, JsonResponse
from .models import GabaritoCertificado, Assinatura, Participante, Treinamento, TipoCurso
from num2words import num2words # Biblioteca para converter números em extenso
import qrcode
import qrcode.image.svg
from base64 import b64encode

    # ... demais impor
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_DISPONIVEL = True
except ImportError:
    WEASYPRINT_DISPONIVEL = False
    print("AVISO: WeasyPrint não instalado. Geração de PDF falhará.")
    # TODO: Adicione aqui a importação do xhtml2pdf como fallback se desejar


# ==========================================================================
# MIXIN - Agora é a fonte única de lógica para formsets
# ==========================================================================
class TreinamentoFormsetMixin:
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['form_participantes'] = ParticipanteFormSet(self.request.POST, instance=self.object)
        else:
            context['form_participantes'] = ParticipanteFormSet(instance=self.object)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object() if isinstance(self, UpdateView) else None
        form = self.get_form()
        form_participantes = ParticipanteFormSet(self.request.POST, instance=self.object)

        if form.is_valid() and form_participantes.is_valid():
            return self.form_valid(form, form_participantes)
        else:
            return self.form_invalid(form, form_participantes)

    def form_valid(self, form, form_participantes):
        with transaction.atomic():
            form.instance.filial = self.request.user.filial_ativa
            self.object = form.save()
            form_participantes.instance = self.object
            form_participantes.save()
        
        # A chamada a super().form_valid(form) da View original cuida da mensagem de sucesso e do redirect
        return super().form_valid(form)

    def form_invalid(self, form, form_participantes):
        return self.render_to_response(self.get_context_data(form=form, form_participantes=form_participantes))

    
class CriarTreinamentoView(LoginRequiredMixin, TreinamentoFormsetMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = Treinamento
    form_class = TreinamentoForm
    template_name = 'treinamentos/criar_treinamento.html'
    success_url = reverse_lazy('treinamentos:treinamento_list')
    success_message = "✅ Treinamento cadastrado com sucesso!"

    permission_required = 'treinamentos.add_treinamento'

    def get_form_kwargs(self):
        """ Passa o request para o formulário. """
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastrar Novo Treinamento'
        return context


# --- Visualizações para Treinamento (CRUD) ---

class TreinamentoListView(LoginRequiredMixin, ViewFilialScopedMixin, TecnicoScopeMixin, ListView):
    """Lista todos os treinamentos com filtros de busca."""
    model = Treinamento
    template_name = 'treinamentos/treinamento_list.html'
    context_object_name = 'treinamentos'
    paginate_by = 30
    tecnico_scope_lookup = 'participantes__funcionario'

    def get_queryset(self):
        """Aplica filtros de status, tipo de curso e busca textual.
        Exclui treinamentos vinculados a tipos Online (gerenciados pelo EAD)."""
        queryset = super().get_queryset().select_related('tipo_curso')

        # ✅ Exclui tipos Online — esses são gerenciados pelo fluxo EAD
        queryset = queryset.exclude(tipo_curso__modalidade='O')

        # Filtro por status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        # Filtro por tipo de curso
        tipo_curso = self.request.GET.get('tipo_curso')
        if tipo_curso:
            queryset = queryset.filter(tipo_curso_id=tipo_curso)

        # Busca textual
        busca = self.request.GET.get('q')
        if busca:
            queryset = queryset.filter(
                Q(nome__icontains=busca) |
                Q(local__icontains=busca) |
                Q(palestrante__icontains=busca)
            )

        return queryset.order_by('-data_inicio')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # ✅ Só mostra tipos presenciais/híbridos nos filtros
        context['tipos_curso'] = TipoCurso.objects.filter(ativo=True).exclude(modalidade='O')
        context['total_treinamentos'] = Treinamento.objects.exclude(tipo_curso__modalidade='O').count()
        return context


class EditarTreinamentoView(LoginRequiredMixin, PermissionRequiredMixin, TreinamentoFormsetMixin, SuccessMessageMixin, UpdateView):
    model = Treinamento
    form_class = TreinamentoForm
    template_name = 'treinamentos/criar_treinamento.html' # Reutilizando o mesmo template
    success_message = "🔄 Treinamento atualizado com sucesso!"
    permission_required = 'treinamentos.change_treinamento'

    # O DetailView/UpdateView também usa get_queryset() para buscar o objeto.
    # Se um técnico tentar editar a URL, ele receberá um 404.
    tecnico_scope_lookup = 'participantes__funcionario'

    def get_success_url(self):
        return reverse_lazy('treinamentos:detalhe_treinamento', kwargs={'pk': self.object.pk})

    def get_form_kwargs(self):
        """ Passa o request para o formulário. """
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Treinamento'
        return context

class DetalheTreinamentoView(LoginRequiredMixin, TecnicoScopeMixin, DetailView):
    """Exibe os detalhes de um treinamento específico."""
    model = Treinamento
    template_name = 'treinamentos/detalhe_treinamento.html'
    permission_required = 'treinamentos.view_treinamento'
    # O técnico só pode ver o detalhe se o lookup for verdadeiro
    tecnico_scope_lookup = 'participantes__funcionario'

    def get_context_data(self, **kwargs):
        """Adiciona a lista de participantes otimizada ao contexto."""
        context = super().get_context_data(**kwargs)
        # Otimiza a consulta para buscar funcionários junto com os participantes
        context['participantes'] = self.object.participantes.select_related('funcionario')
        return context

class ExcluirTreinamentoView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Treinamento
    permission_required = 'treinamentos.delete_treinamento'
    success_url = reverse_lazy('treinamentos:treinamento_list')
    tecnico_scope_lookup = 'participantes__funcionario'
    
    def get(self, request, *args, **kwargs):
        # Bloqueia acesso GET direto — exclusão só via POST do modal
        return HttpResponseRedirect(
            reverse('treinamentos:detalhe_treinamento', kwargs={'pk': self.get_object().pk})
        )
    
    def delete(self, request, *args, **kwargs):
        treinamento = self.get_object()
        messages.success(request, f'Treinamento "{treinamento.nome}" excluído com sucesso.')
        return super().delete(request, *args, **kwargs)


class TipoCursoListView(LoginRequiredMixin, PermissionRequiredMixin, ViewFilialScopedMixin, ListView):
    """Lista todos os tipos de curso com filtros."""
    model = TipoCurso
    template_name = 'treinamentos/lista_tipo_curso.html'
    context_object_name = 'cursos'
    paginate_by = 30
    permission_required = 'treinamentos.view_tipocurso'

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
    model = TipoCurso
    form_class = TipoCursoForm
    template_name = 'treinamentos/criar_tipo_curso.html'
    success_url = reverse_lazy('treinamentos:lista_tipos_curso')
    permission_required = 'treinamentos.add_tipocurso'
    success_message = "✅ Tipo de curso cadastrado com sucesso!"
    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastrar Tipo de Curso'
        return context

    def form_valid(self, form):
        """
        Este método é chamado APENAS se o formulário for válido.
        Aqui, nós associamos a filial do usuário antes de salvar.
        """
        # Define a filial na instância do modelo ANTES que o método save() seja chamado.
        # Estamos assumindo que a filial ativa está em 'self.request.user.filial_ativa'
        form.instance.filial = self.request.user.filial_ativa
        
        # A chamada super().form_valid(form) irá salvar o objeto e redirecionar
        return super().form_valid(form)


class EditarTipoCursoView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    """View para editar um tipo de curso existente."""
    model = TipoCurso
    form_class = TipoCursoForm
    template_name = 'treinamentos/editar_tipo_curso.html'
    success_url = reverse_lazy('treinamentos:lista_tipos_curso')
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
    success_url = reverse_lazy('treinamentos:lista_tipos_curso')
    permission_required = 'treinamentos.delete_tipocurso'
    permission_required = 'treinamentos.ver_relatorios'
    success_message = "Tipo de curso excluído com sucesso!"


# --- Visualizações para Relatórios ---

class RelatorioTreinamentosView(LoginRequiredMixin, PermissionRequiredMixin, ViewFilialScopedMixin, TecnicoScopeMixin, ListView):
    """
    Gera um relatório de treinamentos com base em filtros.
    Agora herda de ListView para buscar e listar os treinamentos.
    """
    model = Treinamento
    template_name = 'treinamentos/relatorio_treinamentos.html'
    context_object_name = 'object_list'  # O nome padrão, mas é bom ser explícito
    paginate_by = 30 # Opcional: Adiciona paginação
    permission_required = 'treinamentos.ver_relatorios'
    tecnico_scope_lookup = 'participantes__funcionario'

    def get_queryset(self):
        """
        Filtra os treinamentos por ano e tipo de curso, conforme os parâmetros da URL.
        """
        # Começa com todos os treinamentos e aplica os filtros
        # O super().get_queryset() aqui refere-se ao ListView, que já aplica
        # os mixins de escopo (Filial e Tecnico) se eles estiverem corretamente
        # configurados para modificar o queryset base do ListView.
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
        # Usar o queryset filtrado (sem data) para pegar os anos pode ser mais performático
        anos_qs = Treinamento.objects.dates('data_inicio', 'year', order='DESC')
        context['anos'] = anos_qs
        
        # Para o filtro de tipos de curso
        context['tipos_curso'] = TipoCurso.objects.filter(ativo=True).order_by('nome')
        
        # Passa os filtros atuais de volta para o template
        context['current_ano'] = self.request.GET.get('ano')
        context['current_tipo_curso'] = self.request.GET.get('tipo_curso')
        return context
 
 
class RelatorioTreinamentoWordView(LoginRequiredMixin, PermissionRequiredMixin, TecnicoScopeMixin, View):
    """
    Gera e oferece para download o relatório de um treinamento específico em .docx.
    """
    permission_required = 'treinamentos.view_treinamento'
    tecnico_scope_lookup = 'participantes__funcionario'

    def get(self, request, *args, **kwargs):
        """
        Este método lida com a requisição GET, gera o relatório e o retorna.
        """
        try:
            treinamento_pk = self.kwargs.get('pk')
            
            # 1. Define o queryset base (todos os treinamentos)
            base_qs = Treinamento.objects.select_related(
                'tipo_curso', 'responsavel'
            ).prefetch_related(
                
                # 'participantes__funcionario' já é suficiente para o gerador de relatório.
                'participantes__funcionario'
            )

            # 2. Isso aplica o filtro de TÉCNICO (se for o caso)
            scoped_qs = self.scope_tecnico_queryset(base_qs)

            # 3. Busca o objeto DIRETAMENTE do queryset escopado e otimizado.
            treinamento = get_object_or_404(scoped_qs, pk=treinamento_pk)
            # -----------------

            # 4. Construir o caminho para o arquivo da logomarca
            caminho_logo = os.path.join(settings.MEDIA_ROOT, 'imagens', 'logocetest.png')
            
            print(f"--- Gerando Relatório para Treinamento PK: {treinamento_pk} ---")
            print(f"Buscando logomarca em: {caminho_logo}")

            # 5. Verificar se a logomarca realmente existe no caminho especificado
            if not os.path.exists(caminho_logo):
                print("!! ATENÇÃO: Arquivo de logomarca NÃO ENCONTRADO. O relatório será gerado sem a logo.")
                caminho_logo = None  # Define como None se não encontrado
            else:
                print("OK: Arquivo de logomarca encontrado.")

            # 6. Chamar a função geradora, passando o treinamento E o caminho da logo
            buffer = treinamento_generators.gerar_relatorio_word(treinamento, caminho_logo)

            # 7. Preparar e retornar a resposta HTTP com o arquivo .docx
            response = HttpResponse(
                buffer,
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            # Limpa o nome do arquivo para evitar caracteres inválidos
            nome_arquivo = ''.join(c for c in treinamento.nome if c.isalnum() or c in (' ', '_')).rstrip()
            response['Content-Disposition'] = f'attachment; filename="relatorio_{nome_arquivo[:30]}.docx"'
            
            print("--- Relatório gerado e enviado com sucesso. ---")
            return response

        except Http404:
            messages.error(request, "Treinamento não encontrado ou você não tem permissão para acessá-lo.")
            return redirect('treinamentos:treinamento_list')

        except Exception as e:
            # Captura qualquer outro erro que possa ocorrer durante o processo
            print(f"ERRO CRÍTICO AO GERAR WORD: {str(e)}")
            print(traceback.format_exc())  # Mostra o erro completo no console
            messages.error(request, f"Ocorreu um erro inesperado ao gerar o relatório Word.")
            # Redireciona de volta para a página de detalhes do treinamento
            return redirect('treinamentos:detalhe_treinamento', pk=self.kwargs.get('pk'))

class RelatorioGeralExcelView(LoginRequiredMixin, ViewFilialScopedMixin, PermissionRequiredMixin, View):
    """
    Gera e oferece para download um relatório geral de treinamentos em .xlsx.
    """
    permission_required = 'treinamentos.ver_relatorios'
    
    def get(self, request, *args, **kwargs):
        
        # 1. Instancia a View que contém a lógica de filtro
        list_view = RelatorioTreinamentosView() 
        
        # 2. Passa o request atual para a instância da view
        list_view.request = self.request
        
        # 3. Chama o get_queryset() da RelatorioTreinamentosView
        queryset = list_view.get_queryset()

        try:
            # 4. Chama a função geradora de Excel
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
            return redirect('treinamentos:relatorio_treinamentos')

# --- Classe auxiliar para o JSON (mantenha como está) ---
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

# --- Sua View, com a correção de lógica ---
class DashboardView(LoginRequiredMixin, PermissionRequiredMixin, TecnicoScopeMixin, TemplateView):
    template_name = 'treinamentos/dashboard.html'
    permission_required = 'treinamentos.ver_relatorios' # Verifique se o nome da app está correto
    tecnico_scope_lookup = 'participantes__funcionario'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # --- 1. FILTRAGEM PRIMEIRO! ---
        base_queryset = Treinamento.objects.all()
        base_queryset = self.scope_tecnico_queryset(base_queryset)

        area_map = dict(TipoCurso.AREA_CHOICES)
        status_map = dict(Treinamento.STATUS_CHOICES)
        modalidade_map = dict(TipoCurso.MODALIDADE_CHOICES)

        # --- 2. DADOS PRESENCIAIS (Existentes) ---
        area_data_db = base_queryset.values('tipo_curso__area').annotate(total=Count('id'))
        treinamentos_por_area = [
            {'nome_legivel': area_map.get(item['tipo_curso__area'], item['tipo_curso__area']), 'total': item['total']}
            for item in area_data_db
        ]

        status_data_db = base_queryset.values('status').annotate(total=Count('id'))
        status_treinamentos = [
            {'nome_legivel': status_map.get(item['status'], item['status']), 'total': item['total']}
            for item in status_data_db
        ]

        modalidade_data_db = base_queryset.values('tipo_curso__modalidade').annotate(total=Count('id'))
        treinamentos_por_modalidade = [
            {'nome_legivel': modalidade_map.get(item['tipo_curso__modalidade'], item['tipo_curso__modalidade']), 'total': item['total']}
            for item in modalidade_data_db
        ]

        custo_data_db = base_queryset.values('tipo_curso__area').annotate(
            total=Coalesce(Sum('custo'), 0.0, output_field=FloatField())
        )
        custo_por_area = [
            {'nome_legivel': area_map.get(item['tipo_curso__area'], item['tipo_curso__area']), 'total': item['total']}
            for item in custo_data_db
        ]

        # --- 3. DADOS EAD (NOVO!) ---
        ead_total_cursos = CursoEAD.objects.filter(status='publicado').count()
        ead_total_matriculas = MatriculaEAD.objects.count()
        ead_em_andamento = MatriculaEAD.objects.filter(status='em_andamento').count()  # ← minúsculo!
        ead_certificados = CertificadoEAD.objects.count()
        # Matrículas por status (para gráfico donut)
        ead_status_map = dict(MatriculaEAD._meta.get_field('status').choices)  # ← via _meta
        ead_status_data = (
            MatriculaEAD.objects
            .values('status')
            .annotate(total=Count('id'))
            .order_by('-total')
        )
        ead_status_chart = [
            {
                'status': item['status'],
                'nome_legivel': ead_status_map.get(item['status'], item['status']),
                'total': item['total'],
            }
            for item in ead_status_data
        ]
        # Top cursos com mais matrículas
        ead_top_cursos = list(
            CursoEAD.objects
            .filter(status='publicado')
            .annotate(total=Count('matriculas_ead'))
            .filter(total__gt=0)
            .order_by('-total')
            .values('titulo', 'total')[:10]
        )

        # --- 4. MONTANDO O JSON ÚNICO ---
        dashboard_data = {
            'area': treinamentos_por_area,
            'status': status_treinamentos,
            'modalidade': treinamentos_por_modalidade,
            'custo': custo_por_area,
            # EAD
            'ead_status': ead_status_chart,
            'ead_top_cursos': ead_top_cursos,
        }

        # --- 5. KPIs PRESENCIAIS ---
        total_treinamentos = base_queryset.count()
        em_andamento = base_queryset.filter(status='A').count()
        total_custo = base_queryset.aggregate(
            total=Coalesce(Sum('custo'), 0.0, output_field=FloatField())
        )['total']
        total_participantes = Participante.objects.filter(
            treinamento__in=base_queryset
        ).count()
        treinamentos_recentes = base_queryset.select_related('tipo_curso').order_by('-data_inicio')[:5]

        # --- 6. CONTEXT FINAL ---
        context.update({
            # Presencial
            'total_treinamentos': total_treinamentos,
            'total_participantes': total_participantes,
            'total_custo': total_custo,
            'em_andamento': em_andamento,
            'treinamentos_recentes': treinamentos_recentes,
            # EAD KPIs
            'ead_total_cursos': ead_total_cursos,
            'ead_total_matriculas': ead_total_matriculas,
            'ead_em_andamento': ead_em_andamento,
            'ead_certificados': ead_certificados,
            # JSON
            'dashboard_data_json': json.dumps(dashboard_data, cls=DecimalEncoder),
        })

        return context


class VerificarCertificadoView(View):
    """
    Página PÚBLICA para validar um certificado através do protocolo (QR Code).
    Não requer login.
    """
    template_name = 'treinamentos/verificar_certificado.html'

    def get(self, request, *args, **kwargs):
        protocolo = self.kwargs.get('protocolo')
        try:
            participante = Participante.objects.select_related(
                'funcionario',
                'treinamento__tipo_curso',
            ).get(protocolo_validacao=protocolo)
            
            context = {
                'valido': True,
                'participante': participante,
                'treinamento': participante.treinamento,
                'data_emissao': participante.data_registro, # Ou a data de conclusão do curso
            }
            
        except Participante.DoesNotExist:
            context = {
                'valido': False,
                'protocolo': protocolo,
            }
            
        return render(request, self.template_name, context)


class PaginaAssinaturaView(LoginRequiredMixin, View):
    """
    Página onde o usuário (participante ou instrutor) desenha 
    e salva sua assinatura digital.
    """
    template_name = 'treinamentos/pagina_assinatura.html'
    
    def get_assinatura_obj(self, token):
        try:
            # Otimiza a consulta buscando os dados relacionados
            return Assinatura.objects.select_related(
                'participante__funcionario',
                'treinamento_responsavel__responsavel'
            ).get(token_acesso=token)
        except Assinatura.DoesNotExist:
            return None

    def get(self, request, *args, **kwargs):
        token = self.kwargs.get('token')
        assinatura_obj = self.get_assinatura_obj(token)

        if not assinatura_obj:
            messages.error(request, "Link de assinatura inválido ou expirado.")
            return redirect('core:index') # Redireciona para a home

        # Verifica se o usuário logado é quem deve assinar
        usuario_deve_assinar = None
        if assinatura_obj.participante:
            usuario_deve_assinar = assinatura_obj.participante.funcionario
        elif assinatura_obj.treinamento_responsavel:
            usuario_deve_assinar = assinatura_obj.treinamento_responsavel.responsavel
            
        if request.user != usuario_deve_assinar:
            messages.warning(request, "Você está logado com um usuário diferente do esperado para esta assinatura. Por favor, acesse com o usuário correto.")
            # Você pode optar por bloquear descomentando a linha abaixo:
            # return redirect('core:index')

        if assinatura_obj.esta_assinada:
            messages.info(request, "Este documento já foi assinado.")

        context = {
            'titulo': 'Coleta de Assinatura',
            'assinatura_obj': assinatura_obj,
            'nome_assinante': assinatura_obj.get_signer(),
            'token': token,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        token = self.kwargs.get('token')
        assinatura_obj = self.get_assinatura_obj(token)
        
        if not assinatura_obj:
            messages.error(request, "Link de assinatura inválido ou expirado.")
            return redirect('core:index')
            
        if assinatura_obj.esta_assinada:
            messages.error(request, "Este documento já foi assinado.")
            return redirect('treinamentos:pagina_assinatura', token=token)

        # Dados da assinatura vêm do JavaScript (ex: signature_pad.js)
        # Estamos salvando como SVG (Base64), que é mais leve e vetorial
        assinatura_data_svg_base64 = request.POST.get('assinatura_json')

        if not assinatura_data_svg_base64:
            messages.error(request, "Nenhuma assinatura foi fornecida.")
            return render(request, self.template_name, {'assinatura_obj': assinatura_obj, 'nome_assinante': assinatura_obj.get_signer()})

        # Salva a assinatura
        assinatura_obj.assinatura_json = assinatura_data_svg_base64
        assinatura_obj.data_assinatura = timezone.now()
        assinatura_obj.save()

        messages.success(request, "✅ Assinatura registrada com sucesso!")
        return redirect('core:index') # Redireciona para home

def mark_safe(value):
    raise NotImplementedError

def reverse(participante):
    raise NotImplementedError


class GerarCertificadoPDFView(LoginRequiredMixin, TecnicoScopeMixin, View):
    """
    Gera o certificado em PDF (Frente e Verso) para um participante.
    """
    # O técnico só pode ver o detalhe se o lookup for verdadeiro
    # Corrigido para apontar para o treinamento via 'participante'
    tecnico_scope_lookup = 'treinamento__participantes__funcionario'

    def get_qrcode_svg(self, participante):
        """
Gera o QR Code para a URL de validação e retorna como uma string SVG.
"""
        # Monta a URL completa de verificação
        url_validacao = self.request.build_absolute_uri(
            reverse('treinamentos:verificar_certificado', 
                    kwargs={'protocolo': participante.protocolo_validacao})
        )
        
        # Gera o QR Code em memória
        factory = qrcode.image.svg.SvgPathImage
        img = qrcode.make(url_validacao, image_factory=factory, border=1)
        
        # Converte o SVG para uma string
        buffer = io.BytesIO()
        img.save(buffer)
        svg_string = buffer.getvalue().decode('utf-8')
        return svg_string

    def get_context_data(self, participante):
        treinamento = participante.treinamento
        gabarito = GabaritoCertificado.objects.filter(ativo=True).first()
        
        if not gabarito:
            raise Exception("Nenhum Gabarito de Certificado ativo foi encontrado.")
            
        documento = getattr(participante.funcionario, 'cpf', 
                        getattr(participante.funcionario, 'rg', 'Não informado'))

        data_inicio = treinamento.data_inicio.strftime('%d/%m/%Y')
        data_fim = treinamento.data_fim.strftime('%d/%m/%Y') if treinamento.data_fim else data_inicio

        try:
            carga_horaria_extenso = num2words(treinamento.duracao, lang='pt_BR')
        except Exception:
            carga_horaria_extenso = str(treinamento.duracao)

        # Contexto para a FRENTE
        context_frente = {
            'participante_nome': participante.funcionario.get_full_name(),
            'participante_documento': documento,
            'empresa_nome': gabarito.empresa_nome,
            'nome_curso': treinamento.tipo_curso.nome,
            'conteudo_programatico': treinamento.tipo_curso.descricao_no_certificado or "",
            'referencia_normativa': treinamento.tipo_curso.referencia_normativa or "",
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'carga_horaria': treinamento.duracao,
            'carga_horaria_extenso': carga_horaria_extenso,
            'local': treinamento.local,
        }
        
        # Contexto para o VERSO
        qr_code_svg = self.get_qrcode_svg(participante)
        
        # Formata a grade curricular (troca quebras de linha por <br>)
        grade_formatada = (treinamento.tipo_curso.grade_curricular or "").replace('\n', '<br>')
        
        context_verso = {
            'grade_curricular': mark_safe(grade_formatada),
            'protocolo': str(participante.protocolo_validacao),
            'qr_code_svg': mark_safe(qr_code_svg), # Passa o SVG do QR Code
        }

        # Assinaturas (passamos o OBJETO para o template)
        assinatura_participante = getattr(participante, 'assinatura', None)
        assinatura_responsavel = getattr(treinamento, 'assinatura_responsavel', None)

        return {
            'gabarito': gabarito,
            'contexto_frente': context_frente,
            'contexto_verso': context_verso,
            'participante': participante,
            'treinamento': treinamento,
            'assinatura_participante': assinatura_participante,
            'assinatura_responsavel': assinatura_responsavel,
            'data_emissao': timezone.now()
        }

    def get(self, request, *args, **kwargs):
        if not WEASYPRINT_DISPONIVEL:
            messages.error(request, "A biblioteca 'WeasyPrint' não foi encontrada. Geração de PDF está desabilitada.")
            return redirect(request.META.get('HTTP_REFERER', 'treinamentos:treinamento_list'))

        try:
            # Aplica o filtro de escopo do Técnico
            base_qs = Participante.objects.select_related(
                'funcionario',
                'treinamento__tipo_curso',
                'treinamento__responsavel',
                'assinatura', # OnetoOne (participante)
                'treinamento__assinatura_responsavel' # OnetoOne (treinamento)
            )
            
            # O get_queryset do TecnicoScopeMixin espera ser chamado por uma ListView
            # Vamos adaptar para usá-lo manualmente aqui
            if hasattr(self, 'scope_tecnico_queryset'):
                 base_qs = self.scope_tecnico_queryset(base_qs)

            participante = get_object_or_404(base_qs, pk=self.kwargs.get('pk'))
        
        except Http404:
            messages.error(request, "Participante não encontrado ou você não tem permissão.")
            return redirect('treinamentos:treinamento_list')
            
        except Exception as e:
            messages.error(request, f"Erro ao buscar participante: {e}")
            return redirect('treinamentos:treinamento_list')


        # --- Validações de Negócio ---
        if not participante.treinamento.status == 'F':
            messages.error(request, "Este treinamento ainda não foi finalizado.")
            return redirect('treinamentos:detalhe_treinamento', pk=participante.treinamento.pk)
            
        if not participante.presente:
            messages.error(request, "Este participante não teve a presença confirmada.")
            return redirect('treinamentos:detalhe_treinamento', pk=participante.treinamento.pk)

        # Descomente estas verificações quando o fluxo de assinatura estiver 100%
        if not getattr(participante, 'assinatura', None) or not participante.assinatura.esta_assinada:
             messages.error(request, "O participante ainda não assinou o certificado.")
             return redirect('treinamentos:detalhe_treinamento', pk=participante.treinamento.pk)
        
        if not getattr(participante.treinamento, 'assinatura_responsavel', None) or not participante.treinamento.assinatura_responsavel.esta_assinada:
             messages.error(request, "O instrutor responsável ainda não assinou o certificado.")
             return redirect('treinamentos:detalhe_treinamento', pk=participante.treinamento.pk)


        # --- Geração do PDF ---
        try:
            context_data = self.get_context_data(participante)
            
            # Renderiza o HTML do certificado
            template = get_template('treinamentos/certificado_template.html')
            html_string = template.render(context_data)

            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="certificado_{participante.funcionario.username}.pdf"'
            
            # Crie um arquivo CSS para estilizar seu PDF
            css_path = os.path.join(settings.STATIC_ROOT, 'css', 'certificado.css')
            css_files = []
            if os.path.exists(css_path):
                 css_files.append(CSS(css_path))
            
            HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(
                response,
                stylesheets=css_files
            )
            
            # Marca o certificado como emitido
            if not participante.certificado_emitido:
                 participante.certificado_emitido = True
                 participante.save(update_fields=['certificado_emitido'])

            return response
            
        except Exception as e:
            print(f"ERRO CRÍTICO AO GERAR PDF: {str(e)}")
            print(traceback.format_exc())
            messages.error(request, f"Ocorreu um erro inesperado ao gerar o PDF: {e}")
            return redirect('treinamentos:detalhe_treinamento', pk=participante.treinamento.pk)
        
# =============================================================================
# =============================================================================
#
#  EAD — VIEWS (Catálogo, Player, Avaliação, Certificado)
#
# =============================================================================
# =============================================================================

from .models import (
    CursoEAD, ModuloEAD, AulaEAD, MatriculaEAD,
    ProgressoAulaEAD, AvaliacaoEAD, QuestaoEAD, AlternativaEAD,
    TentativaAvaliacaoEAD, RespostaAlunoEAD, CertificadoEAD,
    PlanoEstudo,
)
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
import random


# =============================================================================
# CATÁLOGO DE CURSOS EAD
# =============================================================================

class EADCatalogoView(LoginRequiredMixin, ListView):
    """Lista de cursos EAD publicados."""
    model = CursoEAD
    template_name = "treinamentos/ead/catalogo.html"
    context_object_name = "cursos"
    paginate_by = 12

    def get_queryset(self):
        qs = CursoEAD.objects.filter(
            status=CursoEAD.Status.PUBLICADO,
            filial=self.request.user.filial_ativa,
        ).select_related("tipo_curso").annotate(
            total_modulos_count=Count("modulos_ead", distinct=True),
            total_aulas_count=Count("modulos_ead__aulas_ead", distinct=True),
            total_matriculados_count=Count("matriculas_ead", distinct=True),
        )

        # Filtro por busca
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(
                Q(titulo__icontains=q) | Q(descricao__icontains=q)
            )

        # Filtro por tipo
        tipo = self.request.GET.get("tipo")
        if tipo:
            qs = qs.filter(tipo_curso_id=tipo)

        # Filtro por nível
        nivel = self.request.GET.get("nivel")
        if nivel:
            qs = qs.filter(nivel=nivel)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["tipos_curso"] = TipoCurso.objects.filter(ativo=True).order_by("nome")
        ctx["niveis"] = CursoEAD.Nivel.choices
        ctx["filtro_q"] = self.request.GET.get("q", "")
        ctx["filtro_tipo"] = self.request.GET.get("tipo", "")
        ctx["filtro_nivel"] = self.request.GET.get("nivel", "")

        # Matrícula do usuário em cada curso
        if self.request.user.is_authenticated:
            try:
                funcionario = self.request.user.funcionario
                matriculas = MatriculaEAD.objects.filter(
                    funcionario=funcionario,
                ).values_list("curso_id", "status", "progresso_percentual")
                ctx["matriculas_map"] = {
                    str(m[0]): {"status": m[1], "progresso": m[2]} for m in matriculas
                }
            except Exception:
                ctx["matriculas_map"] = {}
        return ctx

# =============================================================================
# DETALHE DO CURSO EAD
# =============================================================================

class EADCursoDetailView(LoginRequiredMixin, DetailView):
    """Página de detalhe do curso com módulos, aulas e resultado da avaliação."""
    model = CursoEAD
    template_name = "treinamentos/ead/curso_detail.html"
    context_object_name = "curso"
    slug_field = "slug"

    def get_queryset(self):
        return CursoEAD.objects.filter(
            status=CursoEAD.Status.PUBLICADO,
            filial=self.request.user.filial_ativa,
        ).select_related("tipo_curso", "criado_por")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        curso = self.object

        # Módulos com aulas
        ctx["modulos"] = curso.modulos_ead.filter(
            ativo=True,
        ).prefetch_related("aulas_ead").order_by("ordem")

        # Valores padrão
        ctx["matricula"] = None
        ctx["progressos_concluidos"] = set()
        ctx["ultima_tentativa"] = None
        ctx["tentativas_restantes"] = 0
        ctx["nota_ok"] = False
        ctx["ch_ok"] = False

        try:
            funcionario = self.request.user.funcionario
            matricula = MatriculaEAD.objects.filter(
                funcionario=funcionario, curso=curso,
            ).first()
            ctx["matricula"] = matricula

            if matricula:
                # IDs de aulas concluídas
                ctx["progressos_concluidos"] = set(
                    ProgressoAulaEAD.objects.filter(
                        matricula=matricula, concluida=True,
                    ).values_list("aula_id", flat=True)
                )

                # Última tentativa finalizada
                ultima = TentativaAvaliacaoEAD.objects.filter(
                    matricula=matricula, finalizada_em__isnull=False,
                ).order_by("-numero_tentativa").first()
                ctx["ultima_tentativa"] = ultima

                # Tentativas restantes
                ctx["tentativas_restantes"] = max(
                    0, curso.max_tentativas_avaliacao - matricula.tentativas_avaliacao
                )

                # Status dos dois critérios (para feedback no template)
                if ultima and ultima.nota is not None:
                    ctx["nota_ok"] = ultima.nota >= curso.nota_minima
                ctx["ch_ok"] = matricula.carga_horaria_atingida

        except Exception:
            pass

        return ctx

# =============================================================================
# MEUS CURSOS (Área do Aluno)
# =============================================================================

class EADMeusCursosView(LoginRequiredMixin, ListView):
    """Cursos em que o aluno está matriculado."""
    model = MatriculaEAD
    template_name = "treinamentos/ead/meus_cursos.html"
    context_object_name = "matriculas"

    def get_queryset(self):
        try:
            funcionario = self.request.user.funcionario
            return MatriculaEAD.objects.filter(
                funcionario=funcionario,
                filial=self.request.user.filial_ativa,
            ).select_related("curso", "curso__tipo_curso").order_by(
                "-data_matricula"
            )
        except Exception:
            return MatriculaEAD.objects.none()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        matriculas = ctx["matriculas"]
        ctx["em_andamento"] = [m for m in matriculas if m.status == MatriculaEAD.Status.EM_ANDAMENTO]
        ctx["concluidos"] = [m for m in matriculas if m.status in (
            MatriculaEAD.Status.APROVADO, MatriculaEAD.Status.CONCLUIDO
        )]
        return ctx


# =============================================================================
# MATRICULAR
# =============================================================================

class EADMatricularView(LoginRequiredMixin, View):
    """Matricula o funcionário no curso EAD."""

    def post(self, request, slug):
        curso = get_object_or_404(
            CursoEAD,
            slug=slug,
            status=CursoEAD.Status.PUBLICADO,
            filial=request.user.filial_ativa,
        )

        try:
            funcionario = request.user.funcionario
        except Exception:
            messages.error(request, "Seu usuário não está vinculado a um funcionário.")
            return redirect("treinamentos:ead_curso_detail", slug=slug)

        # Verifica se já está matriculado
        if MatriculaEAD.objects.filter(funcionario=funcionario, curso=curso).exists():
            messages.warning(request, "Você já está matriculado neste curso.")
            return redirect("treinamentos:ead_curso_detail", slug=slug)

        # Cria matrícula
        MatriculaEAD.objects.create(
            funcionario=funcionario,
            curso=curso,
            filial=request.user.filial_ativa,
            matriculado_por=request.user,
            prazo_limite=timezone.now() + timedelta(days=90),
        )

        messages.success(request, f"Matrícula confirmada! Bons estudos no curso: {curso.titulo}")
        return redirect("treinamentos:ead_curso_detail", slug=slug)


# =============================================================================
# PLAYER DE AULA
# ============================================================================
class EADAulaPlayerView(LoginRequiredMixin, DetailView):
    """Player de vídeo / conteúdo da aula."""
    model = AulaEAD
    template_name = "treinamentos/ead/aula_player.html"
    context_object_name = "aula"

    def get_queryset(self):
        return AulaEAD.objects.filter(
            ativo=True,
            modulo__curso__filial=self.request.user.filial_ativa,
        ).select_related("modulo", "modulo__curso")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        aula = self.object
        curso = aula.modulo.curso

        # Matrícula e progresso
        try:
            funcionario = self.request.user.funcionario
            matricula = MatriculaEAD.objects.get(
                funcionario=funcionario, curso=curso,
            )
            ctx["matricula"] = matricula

            progresso, _ = ProgressoAulaEAD.objects.get_or_create(
                matricula=matricula,
                aula=aula,
                defaults={"iniciado_em": timezone.now()},
            )
            ctx["progresso"] = progresso
        except (MatriculaEAD.DoesNotExist, Exception):
            ctx["matricula"] = None
            ctx["progresso"] = None

        # Navegação: aulas do mesmo módulo
        modulos = curso.modulos_ead.filter(
            ativo=True
        ).prefetch_related("aulas_ead").order_by("ordem")
        ctx["modulos"] = modulos

        # Aula anterior / próxima
        todas_aulas = list(
            AulaEAD.objects.filter(
                modulo__curso=curso, ativo=True,
            ).order_by("modulo__ordem", "ordem")
        )
        idx = next(
            (i for i, a in enumerate(todas_aulas) if a.pk == aula.pk), None
        )
        ctx["aula_anterior"] = todas_aulas[idx - 1] if idx and idx > 0 else None
        ctx["aula_proxima"] = todas_aulas[idx + 1] if idx is not None and idx < len(todas_aulas) - 1 else None

        # Progressos de todas as aulas (para sidebar)
        if ctx.get("matricula"):
            progs = ProgressoAulaEAD.objects.filter(
                matricula=ctx["matricula"],
            ).values_list("aula_id", "concluida")
            ctx["progressos_map"] = {p[0]: p[1] for p in progs}
        else:
            ctx["progressos_map"] = {}

        return ctx


# =============================================================================
# SALVAR PROGRESSO (AJAX/HTMX)
# =============================================================================

@method_decorator(require_POST, name="dispatch")
class EADSalvarProgressoView(LoginRequiredMixin, View):
    """Salva progresso parcial da aula (posição do vídeo, tempo gasto)."""

    def post(self, request, pk):
        aula = get_object_or_404(AulaEAD, pk=pk)

        try:
            funcionario = request.user.funcionario
            matricula = MatriculaEAD.objects.get(
                funcionario=funcionario, curso=aula.modulo.curso,
            )
        except Exception:
            return JsonResponse({"error": "Matrícula não encontrada"}, status=404)

        progresso, _ = ProgressoAulaEAD.objects.get_or_create(
            matricula=matricula, aula=aula,
            defaults={"iniciado_em": timezone.now()},
        )

        # Atualiza dados enviados via POST/JSON
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            data = request.POST

        if "video_posicao_segundos" in data:
            progresso.video_posicao_segundos = int(data["video_posicao_segundos"])
        if "video_duracao_total" in data:
            progresso.video_duracao_total = int(data["video_duracao_total"])
        if "tempo_gasto_segundos" in data:
            progresso.tempo_gasto_segundos = int(data["tempo_gasto_segundos"])
        if "percentual_assistido" in data:
            progresso.percentual_assistido = Decimal(str(data["percentual_assistido"]))

        progresso.save()
        return JsonResponse({"ok": True, "percentual": float(progresso.percentual_assistido)})


# =============================================================================
# CONCLUIR AULA
# =============================================================================

@method_decorator(require_POST, name="dispatch")
class EADConcluirAulaView(LoginRequiredMixin, View):
    """Marca aula como concluída."""

    def post(self, request, pk):
        aula = get_object_or_404(AulaEAD, pk=pk)

        try:
            funcionario = request.user.funcionario
            matricula = MatriculaEAD.objects.get(
                funcionario=funcionario, curso=aula.modulo.curso,
            )
        except Exception:
            return JsonResponse({"error": "Matrícula não encontrada"}, status=404)

        progresso, _ = ProgressoAulaEAD.objects.get_or_create(
            matricula=matricula, aula=aula,
            defaults={"iniciado_em": timezone.now()},
        )

        progresso.marcar_concluida()

        return JsonResponse({
            "ok": True,
            "concluida": True,
            "progresso_curso": float(matricula.progresso_percentual),
            "pode_avaliar": matricula.pode_fazer_avaliacao,
        })


# =============================================================================
# AVALIAÇÃO
# =============================================================================

class EADAvaliacaoView(LoginRequiredMixin, View):
    """GET: exibe prova / POST: submete respostas."""
    template_name = "treinamentos/ead/avaliacao.html"

    def get_matricula(self, request, matricula_id):
        try:
            funcionario = request.user.funcionario
            return MatriculaEAD.objects.select_related(
                "curso", "curso__avaliacao_ead",
            ).get(pk=matricula_id, funcionario=funcionario)
        except MatriculaEAD.DoesNotExist:
            return None

    def get(self, request, matricula_id):
        matricula = self.get_matricula(request, matricula_id)
        if not matricula:
            messages.error(request, "Matrícula não encontrada.")
            return redirect("treinamentos:ead_meus_cursos")

        if not matricula.pode_fazer_avaliacao:
            messages.warning(
                request,
                "Você ainda não pode fazer a avaliação. "
                f"Complete pelo menos {matricula.curso.percentual_minimo_assistido}% das aulas."
            )
            return redirect("treinamentos:ead_curso_detail", slug=matricula.curso.slug)

        try:
            avaliacao = matricula.curso.avaliacao_ead
        except AvaliacaoEAD.DoesNotExist:
            messages.error(request, "Este curso não possui avaliação cadastrada.")
            return redirect("treinamentos:ead_curso_detail", slug=matricula.curso.slug)

        # Questões
        questoes = list(avaliacao.questoes_ead.filter(
            ativo=True
        ).prefetch_related("alternativas_ead"))

        if avaliacao.embaralhar_questoes:
            random.shuffle(questoes)

        for q in questoes:
            alts = list(q.alternativas_ead.all())
            if avaliacao.embaralhar_alternativas:
                random.shuffle(alts)
            q.alternativas_embaralhadas = alts

        return render(request, self.template_name, {
            "matricula": matricula,
            "avaliacao": avaliacao,
            "questoes": questoes,
            "tentativa_numero": matricula.tentativas_avaliacao + 1,
        })

    def post(self, request, matricula_id):
        matricula = self.get_matricula(request, matricula_id)
        if not matricula or not matricula.pode_fazer_avaliacao:
            messages.error(request, "Não é possível realizar a avaliação.")
            return redirect("treinamentos:ead_meus_cursos")

        avaliacao = matricula.curso.avaliacao_ead

        with transaction.atomic():
            # Cria tentativa
            tentativa = TentativaAvaliacaoEAD.objects.create(
                matricula=matricula,
                avaliacao=avaliacao,
                numero_tentativa=matricula.tentativas_avaliacao + 1,
            )

            # Salva respostas
            questoes = avaliacao.questoes_ead.filter(ativo=True)
            for questao in questoes:
                alt_id = request.POST.get(f"questao_{questao.pk}")
                alternativa = None
                if alt_id:
                    try:
                        alternativa = AlternativaEAD.objects.get(
                            pk=alt_id, questao=questao,
                        )
                    except AlternativaEAD.DoesNotExist:
                        pass

                RespostaAlunoEAD.objects.create(
                    tentativa=tentativa,
                    questao=questao,
                    alternativa_escolhida=alternativa,
                )

            # Calcula nota
            tentativa.calcular_nota()

        return redirect("treinamentos:ead_resultado", tentativa_id=tentativa.pk)


# =============================================================================
# RESULTADO DA AVALIAÇÃO
# =============================================================================

class EADResultadoView(LoginRequiredMixin, DetailView):
    """Exibe resultado da tentativa com gabarito. Colaborador confirma a nota."""
    model = TentativaAvaliacaoEAD
    template_name = "treinamentos/ead/resultado.html"
    context_object_name = "tentativa"
    pk_url_kwarg = "tentativa_id"

    def get_queryset(self):
        try:
            funcionario = self.request.user.funcionario
            return TentativaAvaliacaoEAD.objects.filter(
                matricula__funcionario=funcionario,
            ).select_related(
                "matricula", "matricula__curso", "avaliacao",
            )
        except Exception:
            return TentativaAvaliacaoEAD.objects.none()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tentativa = self.object
        matricula = tentativa.matricula
        curso = matricula.curso

        respostas = tentativa.respostas_ead.select_related(
            "questao", "alternativa_escolhida",
        ).order_by("questao__ordem")

        gabarito = []
        for resp in respostas:
            correta = resp.questao.alternativas_ead.filter(correta=True).first()
            gabarito.append({
                "questao": resp.questao,
                "alternativas": resp.questao.alternativas_ead.all(),
                "escolhida": resp.alternativa_escolhida,
                "correta_obj": correta,
                "acertou": (
                    resp.alternativa_escolhida
                    and resp.alternativa_escolhida.correta
                ),
            })

        ctx["gabarito"] = gabarito
        ctx["matricula"] = matricula
        ctx["total_questoes"] = len(gabarito)
        ctx["total_acertos"] = sum(1 for g in gabarito if g["acertou"])

        # Critérios separados para feedback
        nota_ok = tentativa.nota is not None and tentativa.nota >= curso.nota_minima
        ch_ok = matricula.carga_horaria_atingida
        ctx["nota_ok"] = nota_ok
        ctx["ch_ok"] = ch_ok
        ctx["aprovado_completo"] = nota_ok and ch_ok

        return ctx



# =============================================================================
# CERTIFICADO EAD (visualização pública por UUID)
# =============================================================================

class EADCertificadoView(DetailView):
    """Página pública de verificação do certificado EAD."""
    model = CertificadoEAD
    template_name = "treinamentos/ead/certificado.html"
    context_object_name = "certificado"
    slug_field = "uuid"
    slug_url_kwarg = "uuid"

# =============================================================================
# GESTÃO DE AVALIAÇÕES (Área do Gestor)
# =============================================================================

class GestaoAvaliacoesCursoView(LoginRequiredMixin, DetailView):
    """Gestor vê todas as tentativas de avaliação de um curso."""
    model = CursoEAD
    template_name = "treinamentos/ead/gestao_avaliacoes.html"
    context_object_name = "curso"
    slug_field = "slug"
    permission_required = 'treinamentos.ver_relatorios'
    
    

    def get_queryset(self):
        return CursoEAD.objects.filter(
            filial=self.request.user.filial_ativa,
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        curso = self.object

        matriculas = MatriculaEAD.objects.filter(
            curso=curso,
        ).select_related("funcionario").order_by("funcionario__nome")

        dados = []
        for mat in matriculas:
            tentativas = TentativaAvaliacaoEAD.objects.filter(
                matricula=mat, finalizada_em__isnull=False,
            ).order_by("-numero_tentativa")

            dados.append({
                "matricula": mat,
                "tentativas": tentativas,
                "ultima": tentativas.first(),
            })

        ctx["dados_alunos"] = dados
        return ctx


class GestaoTentativaDetailView(LoginRequiredMixin, DetailView):
    """Gestor revisa a prova de um colaborador (gabarito completo)."""
    model = TentativaAvaliacaoEAD
    template_name = "treinamentos/ead/gestao_tentativa.html"
    context_object_name = "tentativa"
    pk_url_kwarg = "tentativa_id"
    permission_required = 'treinamentos.ver_relatorios'
    

    def get_queryset(self):
        return TentativaAvaliacaoEAD.objects.filter(
            matricula__curso__filial=self.request.user.filial_ativa,
        ).select_related(
            "matricula", "matricula__funcionario",
            "matricula__curso", "avaliacao",
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tentativa = self.object

        respostas = tentativa.respostas_ead.select_related(
            "questao", "alternativa_escolhida",
        ).order_by("questao__ordem")

        gabarito = []
        for resp in respostas:
            correta = resp.questao.alternativas_ead.filter(correta=True).first()
            gabarito.append({
                "questao": resp.questao,
                "alternativas": resp.questao.alternativas_ead.all(),
                "escolhida": resp.alternativa_escolhida,
                "correta_obj": correta,
                "acertou": (
                    resp.alternativa_escolhida
                    and resp.alternativa_escolhida.correta
                ),
            })

        ctx["gabarito"] = gabarito
        ctx["matricula"] = tentativa.matricula
        ctx["total_questoes"] = len(gabarito)
        ctx["total_acertos"] = sum(1 for g in gabarito if g["acertou"])
        return ctx


class GestaoLiberarTentativaView(LoginRequiredMixin, View):
    """Gestor libera uma nova tentativa para o colaborador."""
    permission_required = 'treinamentos.alterar_status'

    def post(self, request, matricula_id):
        try:
            matricula = MatriculaEAD.objects.get(
                pk=matricula_id,
                curso__filial=request.user.filial_ativa,
            )
        except MatriculaEAD.DoesNotExist:
            messages.error(request, "Matrícula não encontrada.")
            return redirect("treinamentos:ead_catalogo")

        curso = matricula.curso

        if matricula.status == MatriculaEAD.Status.APROVADO:
            messages.info(request, "Este colaborador já está aprovado.")
        elif matricula.tentativas_avaliacao >= curso.max_tentativas_avaliacao:
            # Reseta para permitir mais uma tentativa
            matricula.tentativas_avaliacao = max(
                0, matricula.tentativas_avaliacao - 1
            )
            matricula.status = MatriculaEAD.Status.EM_ANDAMENTO
            matricula.save(update_fields=["tentativas_avaliacao", "status"])
            messages.success(
                request,
                f"Nova tentativa liberada para {matricula.funcionario}."
            )
        else:
            messages.info(
                request,
                f"O colaborador ainda tem "
                f"{curso.max_tentativas_avaliacao - matricula.tentativas_avaliacao} "
                f"tentativa(s) disponível(is)."
            )

        return redirect(
            "treinamentos:gestao_avaliacoes_curso",
            slug=curso.slug,
        )


class GestaoImprimirProvaView(LoginRequiredMixin, DetailView):
    """Versão para impressão da prova com respostas do colaborador."""
    model = TentativaAvaliacaoEAD
    template_name = "treinamentos/ead/imprimir_prova.html"
    context_object_name = "tentativa"
    pk_url_kwarg = "tentativa_id"
    permission_required = 'treinamentos.ver_relatorios'

    def get_queryset(self):
        return TentativaAvaliacaoEAD.objects.filter(
            matricula__curso__filial=self.request.user.filial_ativa,
        ).select_related(
            "matricula", "matricula__funcionario",
            "matricula__curso", "avaliacao",
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tentativa = self.object

        respostas = tentativa.respostas_ead.select_related(
            "questao", "alternativa_escolhida",
        ).order_by("questao__ordem")

        gabarito = []
        for resp in respostas:
            correta = resp.questao.alternativas_ead.filter(correta=True).first()
            gabarito.append({
                "questao": resp.questao,
                "alternativas": resp.questao.alternativas_ead.all(),
                "escolhida": resp.alternativa_escolhida,
                "correta_obj": correta,
                "acertou": (
                    resp.alternativa_escolhida
                    and resp.alternativa_escolhida.correta
                ),
            })

        ctx["gabarito"] = gabarito
        ctx["total_questoes"] = len(gabarito)
        ctx["total_acertos"] = sum(1 for g in gabarito if g["acertou"])
        return ctx


class GestaoGerarCertificadoEADView(LoginRequiredMixin, View):
    """Gestor gera o certificado EAD para um colaborador aprovado."""
    permission_required = 'treinamentos.gerar_certificados'

    def post(self, request, matricula_id):
        try:
            matricula = MatriculaEAD.objects.select_related(
                "curso", "curso__tipo_curso", "funcionario",
            ).get(
                pk=matricula_id,
                curso__filial=request.user.filial_ativa,
            )
        except MatriculaEAD.DoesNotExist:
            messages.error(request, "Matrícula não encontrada.")
            return redirect("treinamentos:ead_catalogo")

        # Verificações
        if matricula.status != MatriculaEAD.Status.APROVADO:
            messages.error(request, "O colaborador precisa estar aprovado.")
            return redirect(
                "treinamentos:gestao_avaliacoes_curso",
                slug=matricula.curso.slug,
            )

        # Verifica se já existe certificado
        if hasattr(matricula, "certificado_ead"):
            messages.info(request, "Certificado já foi emitido anteriormente.")
            return redirect(matricula.certificado_ead.get_absolute_url())

        # Cria o certificado
        funcionario = matricula.funcionario
        curso = matricula.curso

        certificado = CertificadoEAD.objects.create(
            matricula=matricula,
            nome_funcionario=getattr(funcionario, "nome_completo", str(funcionario)),
            cpf_funcionario=getattr(funcionario, "cpf", ""),
            nome_curso=curso.titulo,
            nome_tipo_curso=curso.tipo_curso.nome if curso.tipo_curso else "",
            carga_horaria_exigida=curso.carga_horaria_total,
            carga_horaria_cumprida=matricula.carga_horaria_cumprida_horas,
            nota=matricula.nota_final or Decimal("0.0"),
            nome_instrutor=curso.instrutor_nome,
            filial=curso.filial,
            emitido_por=request.user,
        )

        messages.success(
            request,
            f"Certificado emitido com sucesso para {certificado.nome_funcionario}."
        )
        return redirect(certificado.get_absolute_url())
