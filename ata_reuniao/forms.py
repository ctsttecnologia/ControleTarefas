# forms.py
from django import forms
from .models import AtaReuniao, Cliente, Funcionario

class AtaReuniaoForm(forms.ModelForm):
    natureza = forms.ChoiceField(
        choices=AtaReuniao.NATUREZA_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    
    class Meta:
        model = AtaReuniao
        fields = '__all__'
        widgets = {
            'contrato': forms.Select(attrs={'class': 'form-control'}),
            'coordenador': forms.Select(attrs={'class': 'form-control'}),
            'responsavel': forms.Select(attrs={'class': 'form-control'}),
            'acao': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'entrada': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'prazo': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['contrato'].queryset = Cliente.objects.all().order_by('nome')
        self.fields['coordenador'].queryset = Funcionario.objects.filter(ativo=True).order_by('nome')
        self.fields['responsavel'].queryset = Funcionario.objects.filter(ativo=True).order_by('nome')



