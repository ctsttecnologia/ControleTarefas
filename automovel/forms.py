from django import forms
from .models import Carro, Agendamento, Checklist, Foto
from django.contrib.auth.models import User
from django.utils import timezone


class CarroForm(forms.ModelForm):
    class Meta:
        model = Carro
        fields = '__all__'
        widgets = {
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }

class AgendamentoForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        # Primeiro, executa o __init__ padrão da classe pai
        super().__init__(*args, **kwargs)

        # Verifica se o formulário está sendo usado para editar um objeto existente
        if self.instance and self.instance.pk:
            # Se sim, desabilita o campo 'data_hora_agenda'
            self.fields['data_hora_agenda'].disabled = True
            # Opcional: Adiciona um texto de ajuda para o usuário
            self.fields['data_hora_agenda'].help_text = "A data de agendamento não pode ser alterada após a criação." 

    class Meta:
        model = Agendamento
        fields = '__all__'
        widgets = {
            'data_hora_agenda': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'data_hora_devolucao': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'descricao': forms.Textarea(attrs={'rows': 3}),
            'ocorrencia': forms.Textarea(attrs={'rows': 3}),
            'assinatura': forms.HiddenInput(),  # Se for um campo oculto que será preenchido via JS
        }

class ChecklistForm(forms.ModelForm):
    """
    Formulário para o Checklist, com validação robusta no backend para
    fotos, quilometragem e regras de negócio específicas.
    """
    # 1. CAMPOS DE FOTO OBRIGATÓRIOS (Mantido como melhor prática)
    # Garante que a validação principal sempre ocorra no servidor.
    foto_frontal = forms.ImageField(
        required=True,
        label="Foto da Parte Frontal",
        error_messages={'required': 'A foto da parte frontal é obrigatória.'}
    )
    foto_trazeira = forms.ImageField(
        required=True,
        label="Foto da Parte Traseira",
        error_messages={'required': 'A foto da parte traseira é obrigatória.'}
    )
    foto_lado_motorista = forms.ImageField(
        required=True,
        label="Foto do Lado do Motorista",
        error_messages={'required': 'A foto do lado do motorista é obrigatória.'}
    )
    foto_lado_passageiro = forms.ImageField(
        required=True,
        label="Foto do Lado do Passageiro",
        error_messages={'required': 'A foto do lado do passageiro é obrigatória.'}
    )

    class Meta:
        model = Checklist
        # Define a ordem explícita dos campos no formulário
        fields = [
            'tipo', 'data_hora', 'km_inicial', 'km_final',
            'revisao_frontal_status', 'foto_frontal',
            'revisao_trazeira_status', 'foto_trazeira',
            'revisao_lado_motorista_status', 'foto_lado_motorista',
            'revisao_lado_passageiro_status', 'foto_lado_passageiro',
            'observacoes_gerais', 'assinatura', 'confirmacao'
        ]
        # Widgets para customizar a aparência dos campos
        widgets = {
            'data_hora': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'observacoes_gerais': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Danos, avarias ou outras observações...'}),
            'assinatura': forms.HiddenInput(),
        }

    # 2. LÓGICA CONDICIONAL CORRIGIDA E CENTRALIZADA NO __init__
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Define o valor inicial para data_hora de forma consistente
        if not self.instance.pk:
            self.fields['data_hora'].initial = timezone.now().strftime('%Y-%m-%dT%H:%M')

        # CORREÇÃO: Esta lógica agora está corretamente indentada dentro do __init__
        # Torna o KM inicial somente leitura se for um checklist de retorno
        if self.initial.get('tipo') == 'retorno':
            self.fields['km_inicial'].widget.attrs['readonly'] = True
            self.fields['km_inicial'].widget.attrs['class'] = 'form-control bg-light' # Estilo visual
            self.fields['km_final'].required = True # Torna o KM final obrigatório no retorno
            self.fields['km_final'].label = "Quilometragem Final (Obrigatório)"

    # 3. VALIDAÇÃO COMPLETA E ROBUSTA NO clean()
    def clean(self):
        cleaned_data = super().clean()
        
        tipo = cleaned_data.get('tipo')
        agendamento = self.initial.get('agendamento') # Pega do initial para garantir que existe

        if tipo == 'retorno':
            # Valida se o checklist de saída existe
            if agendamento:
                saida_exists = Checklist.objects.filter(agendamento=agendamento, tipo='saida').exists()
                if not saida_exists:
                    raise forms.ValidationError("Não é possível registrar o retorno sem antes ter registrado a saída.")
            
            # Valida a quilometragem final
            km_inicial = cleaned_data.get('km_inicial')
            km_final = cleaned_data.get('km_final')

            if not km_final:
                # O 'required=True' no __init__ já ajuda, mas essa é uma validação extra.
                self.add_error('km_final', 'A quilometragem final é obrigatória para o checklist de retorno.')
            elif km_inicial is not None and km_final < km_inicial:
                self.add_error('km_final', 'A quilometragem final não pode ser menor que a inicial.')
        
        return cleaned_data

    # Validação da assinatura (mantida por ser uma boa prática)
    def clean_assinatura(self):
        assinatura = self.cleaned_data.get('assinatura')
        if not assinatura:
            raise forms.ValidationError("A assinatura digital do responsável é obrigatória.")
        return assinatura
    
    
class FotoForm(forms.ModelForm):
    class Meta:
        model = Foto
        fields = '__all__'
        exclude = ['data_criacao']

