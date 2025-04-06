from django import forms
from .models import TipoTreinamento, Treinamento
from django.core.exceptions import ValidationError
from django.utils import timezone

class TipoTreinamentoForm(forms.ModelForm):
    class Meta:
        model = TipoTreinamento
        fields = '__all__'
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 3}),
        }

class TreinamentoForm(forms.ModelForm):
    class Meta:
        model = Treinamento
        fields = '__all__'
        widgets = {
            'data_inicio': forms.DateInput(attrs={'type': 'date'}),
            'data_vencimento': forms.DateInput(attrs={'type': 'date'}),
            'descricao': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        data_inicio = cleaned_data.get('data_inicio')
        data_vencimento = cleaned_data.get('data_vencimento')
        
        if data_inicio and data_vencimento:
            if data_inicio > data_vencimento:
                raise ValidationError("A data de vencimento não pode ser anterior à data de início.")
            
            if data_inicio < timezone.now().date():
                raise ValidationError("Não é possível cadastrar treinamentos com data retroativa.")
        
        return cleaned_data
        