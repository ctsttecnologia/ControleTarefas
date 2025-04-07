from django import forms
from .models import Tarefas

class TarefaForm(forms.ModelForm):
    class Meta:
        model = Tarefas
        fields = ['titulo', 'nome', 'descricao', 'status', 'prazo']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            
            'status': forms.Select(attrs={'class': 'form-control'}),
            'prazo': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }