
# controle_de_telefone/views.py
import os
from pyexpat.errors import messages
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from automovel.views import SuccessMessageMixin
from .models import Aparelho, LinhaTelefonica, Vinculo, Marca, Modelo, Operadora, Plano
from .forms import AparelhoForm, LinhaTelefonicaForm, VinculoForm, MarcaForm, ModeloForm, OperadoraForm, PlanoForm

from core.mixins import ViewFilialScopedMixin, FilialCreateMixin
from django.views.generic import TemplateView
from django.db.models import Count
import json
from django.db.models import ProtectedError, Q





class StaffRequiredMixin(PermissionRequiredMixin):
    """
    Mixin que garante que o usuário tem permissão para acessar
    as views do departamento pessoal.
    """
    permission_required = 'auth.view_user' # Exemplo: apenas quem pode ver usuários
    raise_exception = True # Levanta um erro 403 (Forbidden) se não tiver permissão

# --- CRUD para Aparelhos (Existente) ---
class AparelhoListView(LoginRequiredMixin, PermissionRequiredMixin, ViewFilialScopedMixin, ListView):
    model = Aparelho
    permission_required = 'controle_de_telefone.view_aparelho'
    template_name = 'controle_de_telefone/aparelho_list.html'
    context_object_name = 'aparelhos'
    paginate_by = 10

class AparelhoDetailView(LoginRequiredMixin, PermissionRequiredMixin, ViewFilialScopedMixin, DetailView):
    model = Aparelho
    permission_required = 'controle_de_telefone.view_aparelho'
    template_name = 'controle_de_telefone/aparelho_detail.html'

class AparelhoCreateView(LoginRequiredMixin, PermissionRequiredMixin, FilialCreateMixin, CreateView):
    model = Aparelho
    form_class = AparelhoForm
    permission_required = 'controle_de_telefone.add_aparelho'
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:aparelho_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastrar Novo Aparelho'
        context['voltar_url'] = reverse_lazy('controle_de_telefone:aparelho_list')
        return context

class AparelhoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, ViewFilialScopedMixin, UpdateView):
    model = Aparelho
    form_class = AparelhoForm
    permission_required = 'controle_de_telefone.change_aparelho'
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:aparelho_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Aparelho'
        context['voltar_url'] = reverse_lazy('controle_de_telefone:aparelho_list')
        return context

class AparelhoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, ViewFilialScopedMixin, DeleteView):
    model = Aparelho
    permission_required = 'controle_de_telefone.delete_aparelho'
    template_name = 'controle_de_telefone/generic_confirm_delete.html'
    success_url = reverse_lazy('controle_de_telefone:aparelho_list')



class LinhaTelefonicaListView(LoginRequiredMixin, PermissionRequiredMixin, ViewFilialScopedMixin, ListView):
    model = LinhaTelefonica
    permission_required = 'controle_de_telefone.view_linhatelefonica'
    template_name = 'controle_de_telefone/linhatelefonica_list.html'
    context_object_name = 'linhas'
    paginate_by = 15 # Adicionando paginação para listas longas

    def get_queryset(self):
        """
        Sobrescreve o queryset para:
        1. Otimizar a performance com select_related.
        2. Implementar a funcionalidade de busca.
        """
        queryset = super().get_queryset().select_related('plano', 'plano__operadora', 'filial')
        
        # Lógica de Busca
        search_query = self.request.GET.get('q', None)
        if search_query:
            # Filtra por número da linha OU nome do plano
            queryset = queryset.filter(
                Q(numero__icontains=search_query) | 
                Q(plano__nome__icontains=search_query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        """ Adiciona o termo de busca ao contexto para mantê-lo no input do formulário. """
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context


class LinhaTelefonicaDetailView(LoginRequiredMixin, PermissionRequiredMixin, ViewFilialScopedMixin, DetailView):
    model = LinhaTelefonica
    permission_required = 'controle_de_telefone.view_linhatelefonica'
    template_name = 'controle_de_telefone/linhatelefonica_detail.html'

    def get_queryset(self):
        """ Otimiza a busca do objeto principal e seus relacionados. """
        return super().get_queryset().select_related('plano', 'plano__operadora', 'filial')


class LinhaTelefonicaCreateView(LoginRequiredMixin, PermissionRequiredMixin, FilialCreateMixin, SuccessMessageMixin, CreateView):
    model = LinhaTelefonica
    form_class = LinhaTelefonicaForm
    permission_required = 'controle_de_telefone.add_linhatelefonica'
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:linhatelefonica_list')
    success_message = "Linha telefônica cadastrada com sucesso!" # Mensagem de sucesso

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastrar Nova Linha Telefônica'
        context['voltar_url'] = self.success_url
        return context


class LinhaTelefonicaUpdateView(LoginRequiredMixin, PermissionRequiredMixin, ViewFilialScopedMixin, SuccessMessageMixin, UpdateView):
    model = LinhaTelefonica
    form_class = LinhaTelefonicaForm
    permission_required = 'controle_de_telefone.change_linhatelefonica'
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:linhatelefonica_list')
    success_message = "Linha telefônica atualizada com sucesso!" # Mensagem de sucesso

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Linha Telefônica'
        context['voltar_url'] = self.success_url
        return context


class LinhaTelefonicaDeleteView(LoginRequiredMixin, PermissionRequiredMixin, ViewFilialScopedMixin, DeleteView):
    model = LinhaTelefonica
    permission_required = 'controle_de_telefone.delete_linhatelefonica'
    template_name = 'controle_de_telefone/generic_confirm_delete.html'
    success_url = reverse_lazy('controle_de_telefone:linhatelefonica_list')
    
    def post(self, request, *args, **kwargs):
        """
        Trata a exclusão para evitar erro 500 se a linha estiver protegida (em uso).
        """
        try:
            response = super().delete(request, *args, **kwargs)
            messages.success(request, "Linha telefônica excluída com sucesso!")
            return response
        except ProtectedError:
            messages.error(request, "Erro: Esta linha não pode ser excluída pois está vinculada a um ou mais colaboradores.")
            return self.get(request, *args, **kwargs)


class VinculoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Vinculo
    permission_required = 'controle_de_telefone.view_vinculo'
    template_name = 'controle_de_telefone/vinculo_list.html'
    context_object_name = 'vinculos'
    paginate_by = 10 # Paginação é essencial para listas longas

    def get_queryset(self):
        """
        Otimiza a consulta e adiciona funcionalidade de busca.
        A busca funciona pelo nome completo ou matrícula do funcionário.
        """
        filial_id = self.request.session.get('active_filial_id')
        if not filial_id:
            return Vinculo.objects.none()

        # A consulta original já era bem otimizada com select_related!
        queryset = Vinculo.objects.filter(funcionario__filial_id=filial_id).select_related(
            'funcionario', 'aparelho__modelo__marca', 'linha__plano__operadora'
        )

        # Lógica de Busca
        search_query = self.request.GET.get('q', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(funcionario__nome_completo__icontains=search_query) |
                Q(funcionario__matricula__icontains=search_query)
            )
        
        return queryset

    def get_context_data(self, **kwargs):
        """ Passa o termo de busca de volta para o template. """
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context


class VinculoDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Vinculo
    permission_required = 'controle_de_telefone.view_vinculo'
    template_name = 'controle_de_telefone/vinculo_detail.html'

    def get_queryset(self):
        """ Garante que o usuário só possa ver vínculos da sua filial e otimiza a consulta. """
        filial_id = self.request.session.get('active_filial_id')
        return Vinculo.objects.filter(funcionario__filial_id=filial_id).select_related(
            'funcionario', 'aparelho__modelo__marca', 'linha__plano__operadora'
        )


class VinculoCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = Vinculo
    form_class = VinculoForm
    permission_required = 'controle_de_telefone.add_vinculo'
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:vinculo_list')
    success_message = "Vínculo criado com sucesso!"

    def get_form(self, form_class=None):
        """ Filtra os campos para mostrar apenas itens disponíveis. """
        form = super().get_form(form_class)
        form.fields['aparelho'].queryset = Aparelho.objects.filter(status='disponivel')
        form.fields['linha'].queryset = LinhaTelefonica.objects.filter(status='disponivel')
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Criar Novo Vínculo'
        context['voltar_url'] = self.success_url
        return context


class VinculoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Vinculo
    form_class = VinculoForm
    permission_required = 'controle_de_telefone.change_vinculo'
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:vinculo_list')
    success_message = "Vínculo atualizado com sucesso!"

    def get_queryset(self):
        filial_id = self.request.session.get('active_filial_id')
        return Vinculo.objects.filter(funcionario__filial_id=filial_id)
    
    def get_form(self, form_class=None):
        """
        Filtra os campos para mostrar itens disponíveis E o item atualmente vinculado.
        """
        form = super().get_form(form_class)
        
        # Aparelho: mostra disponíveis OU o que já está neste vínculo
        if self.object.aparelho:
            form.fields['aparelho'].queryset = Aparelho.objects.filter(
                Q(status='disponivel') | Q(pk=self.object.aparelho.pk)
            )
        else:
             form.fields['aparelho'].queryset = Aparelho.objects.filter(status='disponivel')

        # Linha: mostra disponíveis OU a que já está neste vínculo
        if self.object.linha:
            form.fields['linha'].queryset = LinhaTelefonica.objects.filter(
                Q(status='disponivel') | Q(pk=self.object.linha.pk)
            )
        else:
            form.fields['linha'].queryset = LinhaTelefonica.objects.filter(status='disponivel')
            
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Vínculo'
        context['voltar_url'] = self.success_url
        return context


class VinculoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Vinculo
    permission_required = 'controle_de_telefone.delete_vinculo'
    template_name = 'controle_de_telefone/generic_confirm_delete.html'
    success_url = reverse_lazy('controle_de_telefone:vinculo_list')

    def get_queryset(self):
        filial_id = self.request.session.get('active_filial_id')
        return Vinculo.objects.filter(funcionario__filial_id=filial_id)
    
    def form_valid(self, form):
        """ Adiciona mensagem de sucesso na exclusão. """
        messages.success(self.request, "Vínculo excluído com sucesso!")
        return super().form_valid(form)

# --- CRUD para Marca (Novo) ---
class MarcaListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Marca
    permission_required = 'controle_de_telefone.view_marca'
    template_name = 'controle_de_telefone/marca_list.html'
    context_object_name = 'marcas'

class MarcaCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Marca
    form_class = MarcaForm
    permission_required = 'controle_de_telefone.add_marca'
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:marca_list')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastrar Nova Marca'
        context['voltar_url'] = reverse_lazy('controle_de_telefone:marca_list')
        return context

class MarcaUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Marca
    form_class = MarcaForm
    permission_required = 'controle_de_telefone.change_marca'
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:marca_list')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Marca'
        context['voltar_url'] = reverse_lazy('controle_de_telefone:marca_list')
        return context

class MarcaDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Marca
    permission_required = 'controle_de_telefone.delete_marca'
    template_name = 'controle_de_telefone/generic_confirm_delete.html'
    success_url = reverse_lazy('controle_de_telefone:marca_list')


# --- CRUD para Modelo (Novo) ---
class ModeloListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Modelo
    permission_required = 'controle_de_telefone.view_modelo'
    template_name = 'controle_de_telefone/modelo_list.html'
    context_object_name = 'modelos'

class ModeloCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Modelo
    form_class = ModeloForm
    permission_required = 'controle_de_telefone.add_modelo'
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:modelo_list')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastrar Novo Modelo'
        context['voltar_url'] = reverse_lazy('controle_de_telefone:modelo_list')
        return context

class ModeloUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Modelo
    form_class = ModeloForm
    permission_required = 'controle_de_telefone.change_modelo'
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:modelo_list')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Modelo'
        context['voltar_url'] = reverse_lazy('controle_de_telefone:modelo_list')
        return context

class ModeloDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Modelo
    permission_required = 'controle_de_telefone.delete_modelo'
    template_name = 'controle_de_telefone/generic_confirm_delete.html'
    success_url = reverse_lazy('controle_de_telefone:modelo_list')

# Adicione estes imports no topo do seu views.py se eles não estiverem lá
from .models import Operadora, Plano
from .forms import OperadoraForm, PlanoForm

# --- CRUD para Operadora (Novo) ---

class OperadoraListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Operadora
    permission_required = 'controle_de_telefone.view_operadora'
    template_name = 'controle_de_telefone/operadora_list.html'
    context_object_name = 'operadoras'
    paginate_by = 15

class OperadoraDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Operadora
    permission_required = 'controle_de_telefone.view_operadora'
    template_name = 'controle_de_telefone/operadora_detail.html'

class OperadoraCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Operadora
    form_class = OperadoraForm
    permission_required = 'controle_de_telefone.add_operadora'
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:operadora_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastrar Nova Operadora'
        context['voltar_url'] = reverse_lazy('controle_de_telefone:operadora_list')
        return context

class OperadoraUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Operadora
    form_class = OperadoraForm
    permission_required = 'controle_de_telefone.change_operadora'
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:operadora_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Operadora'
        context['voltar_url'] = reverse_lazy('controle_de_telefone:operadora_list')
        return context

class OperadoraDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Operadora
    permission_required = 'controle_de_telefone.delete_operadora'
    template_name = 'controle_de_telefone/generic_confirm_delete.html'
    success_url = reverse_lazy('controle_de_telefone:operadora_list')


# --- CRUD para Plano (Novo) ---

class PlanoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Plano
    permission_required = 'controle_de_telefone.view_plano'
    template_name = 'controle_de_telefone/plano_list.html'
    context_object_name = 'planos'
    paginate_by = 15

class PlanoDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Plano
    permission_required = 'controle_de_telefone.view_plano'
    template_name = 'controle_de_telefone/plano_detail.html'

class PlanoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Plano
    form_class = PlanoForm
    permission_required = 'controle_de_telefone.add_plano'
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:plano_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastrar Novo Plano'
        context['voltar_url'] = reverse_lazy('controle_de_telefone:plano_list')
        return context

class PlanoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Plano
    form_class = PlanoForm
    permission_required = 'controle_de_telefone.change_plano'
    template_name = 'controle_de_telefone/generic_form.html'
    success_url = reverse_lazy('controle_de_telefone:plano_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Plano'
        context['voltar_url'] = reverse_lazy('controle_de_telefone:plano_list')
        return context

class PlanoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Plano
    permission_required = 'controle_de_telefone.delete_plano'
    template_name = 'controle_de_telefone/generic_confirm_delete.html'
    success_url = reverse_lazy('controle_de_telefone:plano_list')

# SUBSTITUA A FUNÇÃO 'dashboard' PELA CLASSE ABAIXO:
class DashboardView(LoginRequiredMixin, TemplateView):
    """
    View para renderizar o painel de controle com dados agregados e gráficos.
    """
    template_name = 'controle_de_telefone/dashboard.html'

    def get_context_data(self, **kwargs):
        # Chama a implementação base primeiro para obter o contexto
        context = super().get_context_data(**kwargs)

        # --- 1. DADOS PARA OS CARDS DE RESUMO ---
        context['total_aparelhos'] = Aparelho.objects.count()
        context['total_linhas'] = LinhaTelefonica.objects.count()
        context['total_vinculos'] = Vinculo.objects.count()
        context['total_marcas'] = Marca.objects.count()
        context['total_operadoras'] = Operadora.objects.count()

        # --- 2. DADOS PARA OS GRÁFICOS ---

        # Gráfico 1: Aparelhos por Marca (Gráfico de Pizza)
        aparelhos_por_marca = Aparelho.objects.values('modelo__marca__nome').annotate(
            total=Count('id')
        ).order_by('-total')

        marcas_labels = [item['modelo__marca__nome'] for item in aparelhos_por_marca]
        marcas_data = [item['total'] for item in aparelhos_por_marca]

       # Gráfico 2: Linhas por Operadora (Gráfico de Barras)
        linhas_por_operadora = LinhaTelefonica.objects.values('plano__operadora__nome').annotate(
            total=Count('id')
        ).order_by('-total')

        # ATENÇÃO: Atualize a chave do dicionário aqui também
        operadoras_labels = [item['plano__operadora__nome'] for item in linhas_por_operadora]
        operadoras_data = [item['total'] for item in linhas_por_operadora]

        # Gráfico 3: Vínculos Ativos vs. Inativos (Exemplo)
        vinculos_status_data = []
        try:
            vinculos_ativos = Vinculo.objects.filter(data_devolucao__isnull=True).count()
            vinculos_inativos = Vinculo.objects.filter(data_devolucao__isnull=False).count()
            vinculos_status_data = [vinculos_ativos, vinculos_inativos]
        except Exception:
            # Lida com o caso do modelo não ter o campo esperado
            pass

        # Adiciona os dados do gráfico ao contexto, convertendo para JSON
        context['marcas_labels_json'] = json.dumps(marcas_labels)
        context['marcas_data_json'] = json.dumps(marcas_data)
        context['operadoras_labels_json'] = json.dumps(operadoras_labels)
        context['operadoras_data_json'] = json.dumps(operadoras_data)
        context['vinculos_status_data_json'] = json.dumps(vinculos_status_data)
        
        return context

@login_required
def download_termo(request, vinculo_id):
    """
    View segura para o download do termo de responsabilidade.
    Verifica se o usuário pertence à filial do vínculo antes de servir o arquivo.
    """
    # Garante que o usuário só pode baixar termos da sua filial ativa
    filial_id = request.session.get('active_filial_id')
    
    vinculo = get_object_or_404(
        Vinculo, 
        pk=vinculo_id, 
        funcionario__filial_id=filial_id
    )
    
    # Verifica se o campo do arquivo não está vazio
    if not vinculo.termo_responsabilidade:
        raise Http404("Nenhum termo de responsabilidade encontrado para este vínculo.")

    # Pega o caminho do arquivo
    file_path = vinculo.termo_responsabilidade.path
    
    # Verifica se o arquivo realmente existe no disco
    if not os.path.exists(file_path):
        raise Http404("Arquivo não encontrado no servidor.")

    # Usa FileResponse, que é otimizado para enviar arquivos
    response = FileResponse(open(file_path, 'rb'), as_attachment=True)
    
    # as_attachment=True define o cabeçalho "Content-Disposition", 
    # forçando o navegador a baixar o arquivo em vez de tentar exibi-lo.
    
    return response
    
    

