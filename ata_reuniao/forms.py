# forms.py
# forms.py
from django import forms
from .models import AtaReuniao, Cliente, Funcionario

class AtaReuniaoForm(forms.ModelForm):
    natureza = forms.ChoiceField(
        choices=AtaReuniao.NATUREZA_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    
    status = forms.ChoiceField(
        choices=AtaReuniao.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    
    class Meta:
        model = AtaReuniao
        fields = '__all__'
        widgets = {
            'acao': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'entrada': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'prazo': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'required': False}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtra clientes e funcionários ativos
        self.fields['contrato'].queryset = Cliente.objects.all().order_by('nome')
        self.fields['coordenador'].queryset = Funcionario.objects.filter(ativo=True).order_by('nome')
        self.fields['responsavel'].queryset = Funcionario.objects.filter(ativo=True).order_by('nome')
        
        # Aplica classes consistentes
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            elif not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-control'})

