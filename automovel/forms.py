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
    class Meta:
        model = Agendamento
        fields = '__all__'
        widgets = {
            'data_hora_agenda': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'descricao': forms.Textarea(attrs={'rows': 3}),
            'ocorrencia': forms.Textarea(attrs={'rows': 3}),
            'assinatura': forms.HiddenInput(),  # Se for um campo oculto que será preenchido via JS
        }

class ChecklistForm(forms.ModelForm):

    foto_frontal = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'accept': 'image/*',
            'capture': 'environment',
            'class': 'd-none',
            'data-target': 'foto_frontal'
        })
    )

    foto_trazeira = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'accept': 'image/*',
            'capture': 'environment',
            'class': 'd-none',
            'data-target': 'foto_trazeira'
        })
    )
    foto_lado_motorista = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'accept': 'image/*',
            'capture': 'environment',
            'class': 'd-none',
            'data-target': 'foto_lado_motorista'
        })
    )
    foto_lado_passageiro = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'accept': 'image/*',
            'capture': 'environment',
            'class': 'd-none',
            'data-target': 'foto_lado_passageiro'
        })
    )

    data_hora = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        initial=timezone.now,
        required=True
    )
    
    class Meta:
        model = Checklist
        fields = '__all__'
        widgets = {
            'agendamento': forms.HiddenInput(),
            'usuario': forms.HiddenInput(),
            'assinatura': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['data_hora'].initial = timezone.now()
        self.fields['usuario'].initial = self.initial.get('usuario')

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        agendamento = cleaned_data.get('agendamento')
        
        # Verifica se já existe checklist de saída para este agendamento
        if tipo == 'retorno':
            saida_exists = Checklist.objects.filter(
                agendamento=agendamento,
                tipo='saida'
            ).exists()
            if not saida_exists:
                raise forms.ValidationError("Não é possível registrar o retorno sem antes ter registrado a saída.")
        
        return cleaned_data

    def clean_assinatura(self):
        assinatura = self.cleaned_data.get('assinatura')
        if not assinatura:
            raise forms.ValidationError("A assinatura digital é obrigatória.")
        return assinatura

class FotoForm(forms.ModelForm):
    class Meta:
        model = Foto
        fields = '__all__'
        exclude = ['data_criacao']

