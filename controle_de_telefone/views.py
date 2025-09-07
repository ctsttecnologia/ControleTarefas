
# controle_de_telefone/views.py
from django.contrib import messages 
import os
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from .models import Aparelho, LinhaTelefonica, Vinculo, Marca, Modelo, Operadora, Plano, enviar_notificacao_de_assinatura
from .forms import AparelhoForm, LinhaTelefonicaForm, VinculoForm, MarcaForm, ModeloForm, OperadoraForm, PlanoForm
from core.mixins import ViewFilialScopedMixin, FilialCreateMixin
from django.views.generic import TemplateView
from django.db.models import Count
import json
from django.db.models import ProtectedError, Q
from django.contrib.messages.views import SuccessMessageMixin
from django.core.files.base import ContentFile
from .pdf_generator import gerar_termo_responsabilidade_pdf 
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from notifications.models import Notificacao


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
    success_message = "Vínculo criado com sucesso! O Termo de Responsabilidade foi gerado."

    def get_form(self, form_class=None):
        """ Filtra os campos para mostrar apenas itens disponíveis. """
        form = super().get_form(form_class)
        # Filtra os aparelhos com status 'disponivel'
        form.fields['aparelho'].queryset = Aparelho.objects.filter(status='disponivel')
        # Filtra as linhas com status 'disponivel'
        form.fields['linha'].queryset = LinhaTelefonica.objects.filter(status='disponivel')
        return form
    
    def get_context_data(self, **kwargs):
        """ Define o título e o botão de voltar da página. """
        context = super().get_context_data(**kwargs)
        context['title'] = 'Criar Novo Vínculo' # 'title' ao invés de 'titulo'
        context['voltar_url'] = self.success_url
        return context

    def form_valid(self, form):
        # Primeiro, chama o método pai para salvar o objeto e obter o self.object
        response = super().form_valid(form)
        
        # Agora o self.object é o vínculo recém-criado
        vinculo = self.object

        # 1. Gerar e salvar o PDF (código que já tínhamos)
        pdf_buffer = gerar_termo_responsabilidade_pdf(vinculo)
        file_name = f"termo_{vinculo.funcionario.id}_{vinculo.id}.pdf"
        vinculo.termo_responsabilidade.save(file_name, ContentFile(pdf_buffer.read()), save=True)
        vinculo.termo_gerado.save(file_name, ContentFile(pdf_buffer.read()), save=True)
        # 2. Criar a notificação no sistema
        # Assumindo que seu modelo Funcionario tem uma relação OneToOne com o User
        usuario_a_notificar = vinculo.funcionario.usuario
        try:
            enviar_notificacao_de_assinatura(self.request, vinculo)
        except Exception as e:
            # Adiciona uma mensagem de erro se a notificação falhar, mas não impede a criação do vínculo
            messages.warning(self.request, f"Vínculo criado, mas ocorreu um erro ao enviar a notificação: {e}")
        # Crie a URL para a qual a notificação irá apontar
        # Ex: a página de edição do vínculo, onde ele pode assinar
        url_assinatura = self.request.build_absolute_uri(
            reverse('controle_de_telefone:vinculo_update', args=[vinculo.pk])
        )

        Notificacao.objects.create(
            usuario=usuario_a_notificar,
            mensagem=f"Um novo Termo de Responsabilidade para o aparelho {vinculo.aparelho} foi gerado para você assinar.",
            url_destino=url_assinatura
        )

        # 3. Enviar a notificação por e-mail
        if usuario_a_notificar.email:
            assunto = "Termo de Responsabilidade Pendente de Assinatura"
            contexto_email = {
                'nome_usuario': usuario_a_notificar.first_name or usuario_a_notificar.username,
                'nome_aparelho': str(vinculo.aparelho),
                'url_assinatura': url_assinatura,
            }
            corpo_html = render_to_string('emails/notificacao_assinatura.html', contexto_email)
            
            send_mail(
                subject=assunto,
                message='', # Django usará o corpo_html
                from_email='seu-email@suaempresa.com.br', # Configure no settings.py
                recipient_list=[usuario_a_notificar.email],
                html_message=corpo_html,
                fail_silently=False # Mude para True em produção
            )

        return response


class VinculoUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Vinculo
    form_class = VinculoForm
    success_url = reverse_lazy('controle_de_telefone:vinculo_list')
    success_message = "Vínculo atualizado com sucesso!"

    def dispatch(self, request, *args, **kwargs):
        """
        Verifica a permissão manualmente. O usuário deve ser o dono do vínculo
        ou ter a permissão 'change_vinculo'.
        """
        vinculo = self.get_object()
        is_owner = request.user == vinculo.funcionario.usuario
        is_manager = request.user.has_perm('controle_de_telefone.change_vinculo')

        if not is_owner and not is_manager:
            return self.handle_no_permission()
        
        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        """
        Retorna um template diferente se o usuário logado for o funcionário
        e o termo estiver pendente de assinatura.
        """
        self.object = self.get_object()
        is_owner = self.request.user == self.object.funcionario.usuario
        is_pending = not self.object.assinatura_digital and not self.object.termo_assinado

        if is_owner and is_pending:
            return ['controle_de_telefone/vinculo_assinatura.html'] # Template para o funcionário assinar
        return ['controle_de_telefone/generic_form.html'] # Template padrão para o gestor editar

    def get_queryset(self):
        """
        Permite que o gestor veja vínculos da sua filial e o funcionário
        veja apenas os seus próprios vínculos.
        """
        user = self.request.user
        if user.has_perm('controle_de_telefone.change_vinculo'):
            filial_id = self.request.session.get('active_filial_id')
            if filial_id:
                return Vinculo.objects.filter(funcionario__filial_id=filial_id)
            return Vinculo.objects.none()
        else:
            return Vinculo.objects.filter(funcionario__usuario=user)

    def get_form(self, form_class=None):
        """
        Customiza os campos do formulário dependendo do usuário.
        - Gestor: Pode editar os aparelhos/linhas disponíveis.
        - Funcionário: Não pode editar nada, apenas assinar.
        """
        form = super().get_form(form_class)
        self.object = self.get_object()
        is_owner = self.request.user == self.object.funcionario.usuario
        is_manager = self.request.user.has_perm('controle_de_telefone.change_vinculo')
        is_pending = not self.object.assinatura_digital and not self.object.termo_assinado

        if is_manager and not (is_owner and is_pending):
            # Lógica para gestores (campos de aparelho/linha disponíveis para troca)
            if self.object.aparelho:
                form.fields['aparelho'].queryset = Aparelho.objects.filter(
                    Q(status='disponivel') | Q(pk=self.object.aparelho.pk)
                )
            else:
                form.fields['aparelho'].queryset = Aparelho.objects.filter(status='disponivel')

            if self.object.linha:
                form.fields['linha'].queryset = LinhaTelefonica.objects.filter(
                    Q(status='disponivel') | Q(pk=self.object.linha.pk)
                )
            else:
                form.fields['linha'].queryset = LinhaTelefonica.objects.filter(status='disponivel')
            
            # Gestor não edita campos de assinatura diretamente
            del form.fields['assinatura_digital']
            del form.fields['termo_assinado']
        
        elif is_owner:
            # Desabilita todos os campos para o funcionário, exceto os de assinatura
            for field_name in ['funcionario', 'aparelho', 'linha', 'data_entrega', 'data_devolucao']:
                if field_name in form.fields:
                    form.fields[field_name].disabled = True

        return form

    def get_context_data(self, **kwargs):
        """
        Adiciona dados extras ao contexto do template.
        """
        context = super().get_context_data(**kwargs)
        self.object = self.get_object()
        is_owner = self.request.user == self.object.funcionario.usuario
        is_pending = not self.object.assinatura_digital and not self.object.termo_assinado

        if is_owner and is_pending:
            context['titulo'] = 'Assinar Termo de Responsabilidade'
            # Adiciona as cláusulas do documento para serem exibidas no template
            context['termo_clauses'] = {
                'clausula_1': "O Celular de propriedade da CETEST MINAS ENGENHARIA E SERVIÇOS S.A ficar a partir desta data sob sua inteira responsabilidade, devendo ser mantido em perfeito estado de conservação e funcionamento, não podendo em qualquer hipótese ser cedido a terceiros sem prévia e escrita concordância da CETEST MINAS ENGENHARIA E SERVIÇOS S.A, obedecendo as cláusulas seguintes:.",
                'clausula_2': "A CETEST MINAS ENGENHARIA E SERVIÇOS S.A NÃO autoriza o portador, ao qual este equipamento se encontra sob responsabilidade por intermédio deste termo, seja em comunicação de voz ou em transmissão de dados, receber e enviar conteúdo considerado inadequado ou ilegal, sob o ponto de vista da ética e da legislação.",
                'clausula_3': "Será de responsabilidade do usuário, signatário deste termo, responder por qualquer forma de comunicação que demonstre atitude de preconceito e racismo, exploração do trabalho escravo, depreciação de entidades públicas e seus servidores, assédio sexual e moral, participação em negócios exclusos aos propósitos desta empresa, descumprimento de legislação e normas reguladoras da competição saudável de mercado.",
                'clausula_4': "Fica aos cuidados do Sr.(a) guarda e conservação do aparelho e respectivos acessórios entregues nesta data, devendo restitu-los sempre que for solicitado pela empresa ou em caso de rescisão do contrato de trabalho, sob pena de responsabilizar-se pelo pagamento de eventuais danos materiais.",
                'clausula_5': "Fica vedado ao Usuário permutar o equipamento, ou qualquer um de seus acessórios, com outro usuário.",
                'clausula_6': "Proibido a troca do e-mail e senha fornecida pela empresa.",
                'clausula_7': "A qualquer momento e sem prévio aviso, a empresa CETEST MINAS ENGENHARIA E SERVIÇOS S.A poderá solicitar a devolução imediata da linha e do aparelho.",
                'clausula_8': "Diante das cláusulas descritas neste termo e da responsabilidade que me foi confiada, declaro que recebi os equipamentos acima descritos em perfeito estado de conservação, bem como autorizo desde já o desconto em minha folha de pagamento, os valores das ligações particulares de meu exclusivo interesse bem como quaisquer outras não relacionadas com o trabalho."
            }
        else:
            context['titulo'] = 'Editar Vínculo'
            
        context['voltar_url'] = self.success_url
        return context

    def form_valid(self, form):
        """
        Valida se pelo menos uma forma de assinatura foi enviada e
        customiza a mensagem de sucesso.
        """
        self.object = self.get_object()
        is_owner = self.request.user == self.object.funcionario.usuario
        is_pending = not self.object.assinatura_digital and not self.object.termo_assinado
        
        if is_owner and is_pending:
            assinatura_digital = form.cleaned_data.get('assinatura_digital')
            termo_assinado = form.cleaned_data.get('termo_assinado')
            if not assinatura_digital and not termo_assinado:
                 form.add_error(None, "Você deve desenhar sua assinatura ou fazer o upload do termo assinado para continuar.")
                 return self.form_invalid(form)
            
            messages.success(self.request, "Termo de Responsabilidade assinado com sucesso!")
        else:
            # Usa a mensagem padrão para outras atualizações
            messages.success(self.request, self.success_message)
            
        return super().form_valid(form)

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

def notificar_assinatura(request, vinculo_id):
    """
    View que é chamada pela URL para reenviar a notificação de um vínculo existente.
    """
    vinculo = get_object_or_404(Vinculo, pk=vinculo_id)
    
    try:
        enviar_notificacao_de_assinatura(request, vinculo)
        messages.success(request, f"Notificação para {vinculo.funcionario.nome_completo} enviada com sucesso!")
    except Exception as e:
        messages.error(request, f"Ocorreu um erro ao enviar a notificação: {e}")

    # Redireciona de volta para a lista de vínculos ou para a página anterior
    return redirect('controle_de_telefone:vinculo_list')    
    

