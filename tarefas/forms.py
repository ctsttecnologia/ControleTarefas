from django import forms
from .models import Tarefas, Comentario
from django.contrib.auth.models import User

class TarefaForm(forms.ModelForm):
    class Meta:
        model = Tarefas
        fields = ['titulo', 'descricao', 'status', 'prioridade', 'prazo', 'usuario']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'prioridade': forms.Select(attrs={'class': 'form-control'}),
            'prazo': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'usuario': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['usuario'].queryset = User.objects.all()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['usuario'].queryset = User.objects.all()


class ComentarioForm(forms.ModelForm):
    class Meta:
        model = Comentario
        fields = ['texto']
        widgets = {
            'texto': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Adicione um comentário...'
            }),
        }