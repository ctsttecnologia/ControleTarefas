from django import forms
from .models import TipoTreinamento, Treinamento, TreinamentoColaborador
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
    
    def clean(self):
        cleaned_data = super().clean()
        data_inicio = cleaned_data.get('data_inicio')
        data_fim = cleaned_data.get('data_fim')

        if not data_inicio or not data_fim:
            return cleaned_data

        # Converter para timezone-aware datetime se necessário
        if isinstance(data_inicio, date) and not isinstance(data_inicio, datetime):
            data_inicio = timezone.make_aware(
                datetime.combine(data_inicio, datetime.min.time())
            )
        if isinstance(data_fim, date) and not isinstance(data_fim, datetime):
            data_fim = timezone.make_aware(
                datetime.combine(data_fim, datetime.min.time())
            )

        # Validações
        if data_inicio > data_fim:
            self.add_error('data_fim', 'A data de término não pode ser anterior à data de início')
        
        if data_inicio < timezone.now():
            self.add_error('data_inicio', 'Não é possível agendar treinamentos para datas passadas')

        return cleaned_data

class TreinamentoColaboradorForm(forms.ModelForm):
    class Meta:
        model = TreinamentoColaborador
        fields = '__all__'
        widgets = {
            'data_realizacao': forms.DateInput(attrs={'type': 'date'}),
            'data_validade': forms.DateInput(attrs={'type': 'date'}),
        }

