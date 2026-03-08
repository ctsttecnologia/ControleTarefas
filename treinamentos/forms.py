
from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from django.apps import apps
from django.conf import settings
from .models import Participante, Treinamento, TipoCurso

class TipoCursoForm(forms.ModelForm):
    class Meta:
        model = TipoCurso
        fields = [
            'nome',
            'area',
            'modalidade',
            'validade_meses',
            'descricao_no_certificado',
            'referencia_normativa',
            'grade_curricular',
            'certificado',
            'ativo'
        ]
        widgets = {
            'descricao_no_certificado': forms.Textarea(attrs={'rows': 3}),
            'grade_curricular': forms.Textarea(attrs={'rows': 10}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ✅ Remove "Online" das opções — cursos online usam o fluxo EAD
        self.fields['modalidade'].choices = [
            (k, v) for k, v in TipoCurso.MODALIDADE_CHOICES if k != 'O'
        ]


class TreinamentoForm(forms.ModelForm):
    class Meta:
        model = Treinamento
        # Mude de 'exclude' para 'fields'
        fields = [
            'tipo_curso', 
            'responsavel', 
            'nome', 
            'local', 
            'data_inicio', 
            'data_vencimento', 
            'duracao',  
            'descricao',
            'status', 
            'custo',
            'palestrante', 
            'horas_homem',
            'centro_custo',
            'participantes_previstos',
            'atividade', 
            'cm',
            
        ]
        widgets = {
            'data_inicio': forms.DateTimeInput(
                format='%Y-%m-%dT%H:%M',
                attrs={'type': 'datetime-local'}
            ),
            'data_vencimento': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'type': 'date'}
            ),
            'descricao': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # ✅ Só mostra tipos Presencial (P) e Híbrido (H) — Online usa o fluxo EAD
        self.fields['tipo_curso'].queryset = TipoCurso.objects.filter(
            ativo=True,
        ).exclude(modalidade='O')

        User = apps.get_model(settings.AUTH_USER_MODEL)
        self.fields['responsavel'].queryset = User.objects.filter(is_active=True)

        if self.instance and self.instance.pk:
            self.fields['data_inicio'].disabled = True
            self.fields['data_vencimento'].disabled = True

class BaseParticipanteFormSet(BaseInlineFormSet):
    """ Adiciona validação para evitar participantes duplicados. """
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        participantes = []
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                funcionario = form.cleaned_data.get('funcionario')
                if not funcionario:
                    continue
                
                if funcionario in participantes:
                    # Este erro será um 'non_form_error' porque não pertence a um único campo, mas ao formset como um todo.
                    raise forms.ValidationError('Não é possível adicionar o mesmo participante mais de uma vez.')
                
                participantes.append(funcionario)


ParticipanteFormSet = inlineformset_factory(
    Treinamento,
    Participante,
    fields=('funcionario', 'nota_avaliacao', 'presente', 'certificado_emitido'),
    formset=BaseParticipanteFormSet, # <--- Garanta que 'formset=...' está aqui!
    extra=1,
    can_delete=True
)


