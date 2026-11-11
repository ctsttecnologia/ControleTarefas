# treinamentos/forms.py
from decimal import Decimal

from django import forms
from django.apps import apps
from django.conf import settings
from django.forms import BaseInlineFormSet, inlineformset_factory

from core.utils import get_filial_ativa
from .models import Participante, TipoCurso, Treinamento
from dateutil.relativedelta import relativedelta


def _bootstrap(fields):
    for f in fields.values():
        w = f.widget
        if isinstance(w, forms.CheckboxInput):
            css = 'form-check-input'
        elif isinstance(w, forms.Select):
            css = 'form-select'
        else:
            css = 'form-control'
        w.attrs.setdefault('class', css)


class TipoCursoForm(forms.ModelForm):
    class Meta:
        model = TipoCurso
        fields = [
            'nome', 'area', 'modalidade', 'validade_meses',
            'descricao_no_certificado', 'referencia_normativa',
            'grade_curricular', 'certificado', 'ativo',
        ]
        widgets = {
            'descricao_no_certificado': forms.Textarea(attrs={'rows': 3}),
            'grade_curricular': forms.Textarea(attrs={'rows': 10}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # "Online" usa o fluxo EAD — mantém se o registro já for 'O'
        atual = getattr(self.instance, 'modalidade', None)
        self.fields['modalidade'].choices = [('', '---------')] + [
            (k, v) for k, v in TipoCurso.MODALIDADE_CHOICES if k != 'O' or k == atual
        ]
        _bootstrap(self.fields)


class TreinamentoForm(forms.ModelForm):
    class Meta:
        model = Treinamento
        fields = ['nome', 'tipo_curso', 'status', 'data_inicio', 'data_fim', 'data_vencimento',
                  'duracao', 'local', 'palestrante', 'palestrante_cargo', 'responsavel',
                  'participantes_previstos', 'custo', 'centro_custo', 'descricao', 'horas_homem']
        widgets = {
            'data_inicio': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'data_fim': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'data_vencimento': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'descricao': forms.Textarea(attrs={'rows': 3}),
        }
        help_texts = {
            'data_vencimento': 'Calculada a partir da validade do tipo de curso. Pode ser alterada.',
            'duracao': 'Em horas. Aparece no certificado.',
        }

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['data_vencimento'].required = False

        tipos = TipoCurso.objects.filter(ativo=True)
        User = apps.get_model(settings.AUTH_USER_MODEL)
        responsaveis = User.objects.filter(is_active=True)

        if request is not None:
            if hasattr(tipos, 'for_request'):
                tipos = tipos.for_request(request)
            filial = get_filial_ativa(request.user, request)
            if filial:
                responsaveis = responsaveis.filter(funcionario__filial=filial)

        self.fields['tipo_curso'].queryset = tipos
        self.fields['responsavel'].queryset = responsaveis.order_by('first_name')
        _bootstrap(self.fields)

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get('tipo_curso')
        inicio = cleaned.get('data_inicio')
        venc = cleaned.get('data_vencimento')

        validade = getattr(tipo, 'validade_meses', None) if tipo else None

        if not venc and validade and inicio:
            cleaned['data_vencimento'] = inicio + relativedelta(months=validade)
        # Sem validade e sem vencimento → permitido (fica "Sem validade")

        if venc and inicio and venc < inicio.date() if hasattr(inicio, 'date') else False:
            self.add_error('data_vencimento', 'Vencimento não pode ser anterior ao início.')

        return cleaned


class ParticipanteForm(forms.ModelForm):
    class Meta:
        model = Participante
        fields = ('funcionario', 'presente', 'nota_avaliacao')
        widgets = {
            'funcionario': forms.Select(attrs={'class': 'form-select form-select-sm js-busca-participante'}),
            'nota_avaliacao': forms.NumberInput(attrs={'min': 0, 'max': 100, 'step': '0.01'}),
        }

    def clean_nota_avaliacao(self):
        n = self.cleaned_data.get('nota_avaliacao')
        if n is not None and not (Decimal('0') <= n <= Decimal('100')):
            raise forms.ValidationError('A nota deve estar entre 0 e 100.')
        return n

    def save(self, commit=True):
        obj = super().save(commit=False)
        if obj.funcionario_id:
            obj.nome = obj.funcionario.get_full_name() or obj.funcionario.username
        if commit:
            obj.save()
        return obj


class BaseParticipanteFormSet(BaseInlineFormSet):
    """Filtra funcionários pela filial (LGPD) e impede duplicados."""

    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)

    def _queryset_funcionarios(self):
        User = apps.get_model(settings.AUTH_USER_MODEL)
        qs = User.objects.filter(is_active=True)
        if self.request is not None:
            filial = get_filial_ativa(self.request.user, self.request)
            qs = qs.filter(funcionario__filial=filial) if filial else qs.none()
        return qs.order_by('first_name', 'last_name')

    def add_fields(self, form, index):
        super().add_fields(form, index)
        form.fields['funcionario'].queryset = self._queryset_funcionarios()

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        vistos = set()
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get('DELETE'):
                continue
            func = form.cleaned_data.get('funcionario')
            if not func:
                continue
            if func.pk in vistos:
                raise forms.ValidationError('Não é possível adicionar o mesmo participante mais de uma vez.')
            vistos.add(func.pk)


ParticipanteFormSet = inlineformset_factory(
    Treinamento, Participante,
    form=ParticipanteForm,
    formset=BaseParticipanteFormSet,
    extra=0,
    can_delete=True,
)
