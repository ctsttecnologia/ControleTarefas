# ata_reuniao/forms.py

from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .models import Filial, AtaReuniao, HistoricoAta
from cliente.models import Cliente
from departamento_pessoal.models import Funcionario



class AtaReuniaoForm(forms.ModelForm):


    comentario = forms.CharField(
        label=_("Adicionar Novo Comentário/Atualização"),
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Descreva a atualização ou progresso aqui...'}),
        required=False, # O comentário é opcional em cada salvamento
        help_text=_("Este comentário será adicionado ao histórico da ata.")
    )

    class Meta:
        model = AtaReuniao
        # 1. Campo 'titulo' adicionado à lista de campos.
        fields = [
            'titulo', 'contrato', 'coordenador', 'responsavel', 'natureza', 
            'acao', 'entrada', 'prazo', 'status'
        ]
        
        # Centraliza a definição de rótulos (labels) para facilitar a manutenção
        labels = {
            'titulo': _('Título da Ata'),
            'acao': _('Ação ou Proposta Detalhada'),
            'prazo': _('Prazo Final (Opcional)'),
        }

        # Centraliza os textos de ajuda
        help_texts = {
            'acao': _('Descreva os detalhes, decisões e próximos passos definidos na reunião.'),
        }

        widgets = {
            # 2. Widget adicionado para o campo 'titulo' com um placeholder.
            'titulo': forms.TextInput(
                attrs={'placeholder': 'Ex: Reunião de alinhamento do Projeto X'}
            ),
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

        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # Define o queryset para os campos de seleção
        # Isso garante que apenas os funcionários ativos sejam exibidos
        self.fields['contrato'].queryset = Cliente.objects.all().order_by('nome')
        self.fields['coordenador'].queryset = Funcionario.objects.filter(status='ATIVO').order_by('nome_completo')
        self.fields['responsavel'].queryset = Funcionario.objects.filter(status='ATIVO').order_by('nome_completo')

        # Aplica as classes CSS do Bootstrap
        self._apply_styling()

    def _apply_styling(self):
        """Aplica classes CSS e placeholders aos campos do formulário."""
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.update({
                    'class': 'form-select',
                    'data-placeholder': _(f'Selecione {field.label.lower()}')
                })
            elif not isinstance(field.widget, forms.CheckboxInput):
                # O método agora aplicará 'form-control' ao novo campo 'titulo' automaticamente
                field.widget.attrs.update({'class': 'form-control'})
    
    def clean_prazo(self):
        """Validação para garantir que a data do prazo não seja no passado."""
        prazo = self.cleaned_data.get('prazo')
        entrada = self.cleaned_data.get('entrada')

        if prazo and prazo < timezone.now().date():
            raise forms.ValidationError(_("A data do prazo não pode ser no passado."))
        
        if prazo and entrada and prazo < entrada:
            raise forms.ValidationError(_("O prazo final não pode ser anterior à data de entrada."))
            
        return prazo

    def clean(self):
        """Validações que envolvem múltiplos campos."""
        cleaned_data = super().clean()
        coordenador = cleaned_data.get('coordenador')
        responsavel = cleaned_data.get('responsavel')

        # Validação para garantir que coordenador e responsável não sejam a mesma pessoa
        #if coordenador and responsavel and coordenador == responsavel:
        #    self.add_error('responsavel', _('O responsável não pode ser a mesma pessoa que o coordenador.'))
        
        # Um método 'clean' DEVE sempre retornar o dicionário cleaned_data.
        return cleaned_data
    
class TransferenciaFilialForm(forms.Form):
    """
    Formulário para a ação de transferência de filial no admin.
    """
    filial_destino = forms.ModelChoiceField(
        queryset=Filial.objects.all().order_by('nome'),
        label="Transferir para a Filial",
        required=True
    )

class HistoricoAtaForm(forms.ModelForm):
    class Meta:
        model = HistoricoAta
        fields = ['comentario']
        widgets = {
            'comentario': forms.Textarea(
                attrs={
                    'rows': 3,
                    'placeholder': 'Digite seu comentário ou atualização aqui...'
                }
            )
        }
        labels = {
            'comentario': ''  # Oculta o label, pois o contexto já é claro
        }


