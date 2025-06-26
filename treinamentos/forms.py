
from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from django.apps import apps # Importe 'apps'
from .models import Treinamento, Participante, TipoCurso
from django.conf import settings

class TipoCursoForm(forms.ModelForm):
    class Meta:
        model = TipoCurso
        fields = '__all__'
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 3}),
        }

class TreinamentoForm(forms.ModelForm):
    class Meta:
        model = Treinamento
        fields = '__all__'
        widgets = {
            'data_inicio': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'data_vencimento': forms.DateInput(attrs={'type': 'date'}),
            'descricao': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo_curso'].queryset = TipoCurso.objects.filter(ativo=True)
        # Use apps.get_model para obter o modelo de usuário
        User = apps.get_model(settings.AUTH_USER_MODEL)
        self.fields['responsavel'].queryset = User.objects.filter(is_active=True)

class ParticipanteForm(forms.ModelForm):
    class Meta:
        model = Participante
        fields = ['funcionario', 'presente', 'nota_avaliacao', 'certificado_emitido']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        User = apps.get_model(settings.AUTH_USER_MODEL)
        self.fields['funcionario'].queryset = User.objects.filter(is_active=True)

class BaseParticipanteFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        # if any(self.errors):
        #     return

        # participantes = []
        # for form in self.forms:
        #     if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
        #         funcionario = form.cleaned_data.get('funcionario')
        #         if funcionario in participantes:
        #             form.add_error('funcionario', 'Este funcionário já está na lista.')
        #         participantes.append(funcionario)

# Criação do FormSet
ParticipanteFormSet = inlineformset_factory(
    Treinamento,
    Participante,
    form=ParticipanteForm,
    formset=BaseParticipanteFormSet,
    fields=['funcionario', 'presente', 'nota_avaliacao', 'certificado_emitido'],
    extra=1,
    can_delete=True
)

