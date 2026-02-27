# ata_reuniao/forms.py

from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from .models import Filial, AtaReuniao, HistoricoAta
from cliente.models import Cliente
from departamento_pessoal.models import Funcionario


# ═══════════════════════════════════════════════════════════════════════════════
# MIXIN PARA FILTRO DE FILIAL EM FORMULÁRIOS
# ═══════════════════════════════════════════════════════════════════════════════

class FilialFormMixin:
    """
    Mixin para formulários que precisam filtrar dados pela filial ativa.
    Replica a lógica do FilialAtivaMixin das views.
    """
    
    def get_filial_ativa(self, request):
        """
        Obtém a filial ativa da sessão ou do funcionário.
        Retorna o objeto Filial ou None.
        """
        if not request:
            return None
            
        # 1. Pegar da sessão (seletor do header) - chave: active_filial_id
        filial_id = request.session.get('active_filial_id')
        
        if filial_id:
            try:
                return Filial.objects.get(pk=filial_id)
            except Filial.DoesNotExist:
                pass
        
        # 2. Fallback: filial_ativa do user (se existir)
        user = request.user
        filial_ativa = getattr(user, 'filial_ativa', None)
        if filial_ativa:
            return filial_ativa
            
        # 3. Fallback: filial do funcionário vinculado
        try:
            funcionario = Funcionario.objects.select_related('filial').get(usuario=user)
            return funcionario.filial
        except Funcionario.DoesNotExist:
            pass
        
        # 4. Superusuário sem filial = None (vê tudo)
        return None
    
    def filter_by_filial(self, queryset, filial, filial_field='filial'):
        """
        Aplica filtro de filial ao queryset.
        Se filial for None e usuário for superuser, retorna tudo.
        """
        if filial:
            return queryset.filter(**{filial_field: filial})
        return queryset


# ═══════════════════════════════════════════════════════════════════════════════
# FORMULÁRIO PRINCIPAL DE ATA DE REUNIÃO
# ═══════════════════════════════════════════════════════════════════════════════

class AtaReuniaoForm(FilialFormMixin, forms.ModelForm):
    """
    Formulário para criar/editar Ata de Reunião.
    Filtra os campos de FK (Contrato, Coordenador, Responsável) pela filial ativa.
    """

    comentario = forms.CharField(
        label=_("Adicionar Novo Comentário/Atualização"),
        widget=forms.Textarea(attrs={
            'rows': 3, 
            'placeholder': 'Descreva a atualização ou progresso aqui...'
        }),
        required=False,
        help_text=_("Este comentário será adicionado ao histórico da ata.")
    )

    class Meta:
        model = AtaReuniao
        fields = [
            'titulo', 'contrato', 'coordenador', 'responsavel', 'natureza', 
            'acao', 'entrada', 'prazo', 'status'
        ]
        
        labels = {
            'titulo': _('Título da Ata'),
            'contrato': _('Contrato'),
            'coordenador': _('Coordenador'),
            'responsavel': _('Responsável'),
            'natureza': _('Natureza'),
            'acao': _('Ação ou Proposta Detalhada'),
            'entrada': _('Data de Entrada'),
            'prazo': _('Prazo Final (Opcional)'),
            'status': _('Status'),
        }

        help_texts = {
            'titulo': _('Descreva o nome da proposta.'),
            'acao': _('Descreva os detalhes, decisões e próximos passos definidos na reunião.'),
        }

        widgets = {
            'titulo': forms.TextInput(attrs={
                'placeholder': 'Ex: Reunião de alinhamento do Projeto X'
            }),
            'acao': forms.Textarea(attrs={'rows': 3}),
            'entrada': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'type': 'date'}
            ),
            'prazo': forms.DateInput(
                format='%Y-%m-%d', 
                attrs={'type': 'date'}
            ),
        }

    def __init__(self, *args, **kwargs):
        # Extrair o request dos kwargs
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # ═══════════════════════════════════════════════════════════════
        # FILTRAR QUERYSETS PELA FILIAL ATIVA
        # ═══════════════════════════════════════════════════════════════
        self._filter_querysets_by_filial()
        
        # Aplicar estilos CSS
        self._apply_styling()

    def _filter_querysets_by_filial(self):
        """
        Filtra os querysets de Contrato, Coordenador e Responsável
        pela filial ativa do usuário.
        """
        filial_ativa = self.get_filial_ativa(self.request)
        
        # ─────────────────────────────────────────────────────────────────
        # CONTRATO (Cliente) - Filtrado por filial
        # ─────────────────────────────────────────────────────────────────
        clientes_qs = Cliente.objects.filter(estatus=True).order_by('nome')
        if filial_ativa:
            clientes_qs = clientes_qs.filter(filial=filial_ativa)
        self.fields['contrato'].queryset = clientes_qs
        
        # ─────────────────────────────────────────────────────────────────
        # COORDENADOR (Funcionário) - Filtrado por filial
        # ─────────────────────────────────────────────────────────────────
        coordenadores_qs = Funcionario.objects.filter(
            status='ATIVO'
        ).select_related('usuario').order_by('nome_completo')
        if filial_ativa:
            coordenadores_qs = coordenadores_qs.filter(filial=filial_ativa)
        self.fields['coordenador'].queryset = coordenadores_qs
        
        # ─────────────────────────────────────────────────────────────────
        # RESPONSÁVEL (Funcionário) - Filtrado por filial
        # ─────────────────────────────────────────────────────────────────
        responsaveis_qs = Funcionario.objects.filter(
            status='ATIVO'
        ).select_related('usuario').order_by('nome_completo')
        if filial_ativa:
            responsaveis_qs = responsaveis_qs.filter(filial=filial_ativa)
        self.fields['responsavel'].queryset = responsaveis_qs

    def _apply_styling(self):
        """Aplica classes CSS e placeholders aos campos do formulário."""
        for field_name, field in self.fields.items():
            # Campos Select
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.update({
                    'class': 'form-select',
                    'data-placeholder': _(f'Selecione {field.label.lower()}') if field.label else ''
                })
            # Campos Checkbox (manter sem form-control)
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            # Demais campos (TextInput, Textarea, DateInput, etc.)
            else:
                current_class = field.widget.attrs.get('class', '')
                if 'form-control' not in current_class:
                    field.widget.attrs.update({
                        'class': f'{current_class} form-control'.strip()
                    })

    def clean_prazo(self):
        """Validação para garantir que a data do prazo não seja no passado."""
        prazo = self.cleaned_data.get('prazo')
        entrada = self.cleaned_data.get('entrada')

        # Permitir prazo no passado apenas em edição (quando já existia)
        if prazo and self.instance.pk is None:  # Apenas na criação
            if prazo < timezone.now().date():
                raise forms.ValidationError(
                    _("A data do prazo não pode ser no passado.")
                )
        
        if prazo and entrada and prazo < entrada:
            raise forms.ValidationError(
                _("O prazo final não pode ser anterior à data de entrada.")
            )
            
        return prazo

    def clean(self):
        """Validações que envolvem múltiplos campos."""
        cleaned_data = super().clean()
        coordenador = cleaned_data.get('coordenador')
        responsavel = cleaned_data.get('responsavel')

        # Exemplo de validação (descomentada se necessário):
        # if coordenador and responsavel and coordenador == responsavel:
        #     self.add_error('responsavel', _('O responsável não pode ser a mesma pessoa que o coordenador.'))
        
        return cleaned_data


# ═══════════════════════════════════════════════════════════════════════════════
# FORMULÁRIO DE TRANSFERÊNCIA DE FILIAL
# ═══════════════════════════════════════════════════════════════════════════════

class TransferenciaFilialForm(forms.Form):
    """
    Formulário para a ação de transferência de filial no admin.
    """
    filial_destino = forms.ModelChoiceField(
        queryset=Filial.objects.all().order_by('nome'),
        label=_("Transferir para a Filial"),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


# ═══════════════════════════════════════════════════════════════════════════════
# FORMULÁRIOS DE HISTÓRICO E COMENTÁRIO
# ═══════════════════════════════════════════════════════════════════════════════

class HistoricoAtaForm(forms.ModelForm):
    """Formulário para adicionar entradas ao histórico da ata."""
    
    class Meta:
        model = HistoricoAta
        fields = ['comentario']
        widgets = {
            'comentario': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Digite seu comentário ou atualização aqui...'
            })
        }
        labels = {
            'comentario': ''  # Oculta o label, pois o contexto já é claro
        }


class ComentarioForm(forms.ModelForm):
    """Formulário simplificado para adicionar comentários ao histórico."""
    
    class Meta:
        model = HistoricoAta
        fields = ['comentario']
        widgets = {
            'comentario': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'Adicione um comentário...'
            }),
        }
        labels = {
            'comentario': _('Comentário')
        }


# ═══════════════════════════════════════════════════════════════════════════════
# FORMULÁRIO DE UPLOAD
# ═══════════════════════════════════════════════════════════════════════════════

class UploadAtaReuniaoForm(forms.Form):
    """
    Formulário para upload do arquivo Excel com as Atas de Reunião.
    """
    file = forms.FileField(
        label=_("Arquivo Excel (.xlsx)"),
        help_text=_("Selecione o arquivo .xlsx contendo os dados das atas de reunião."),
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': '.xlsx'
        })
    )

    def clean_file(self):
        """
        Validação customizada para garantir que o arquivo é do tipo .xlsx.
        """
        uploaded_file = self.cleaned_data.get('file')
        if uploaded_file:
            if not uploaded_file.name.endswith('.xlsx'):
                raise ValidationError(
                    _("Erro: O arquivo deve ser do formato Excel (.xlsx).")
                )
        return uploaded_file

