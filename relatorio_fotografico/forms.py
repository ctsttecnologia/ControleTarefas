
# relatorio_fotografico/forms.py
from django import forms
from django.forms import inlineformset_factory

from .models import RelatorioFotografico, FotoRelatorio


class RelatorioFotograficoForm(forms.ModelForm):
    class Meta:
        model = RelatorioFotografico
        fields = ['titulo', 'obra_contrato', 'data', 'responsavel', 'status', 'assunto']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'obra_contrato': forms.TextInput(attrs={'class': 'form-control'}),
            'data': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'responsavel': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'assunto': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }

class FotoRelatorioForm(forms.ModelForm):
    class Meta:
        model = FotoRelatorio
        fields = ['imagem', 'legenda', 'ordem']
        widgets = {
            'legenda': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'ordem': forms.HiddenInput(),
        }


FotoFormSet = inlineformset_factory(
    RelatorioFotografico, FotoRelatorio, form=FotoRelatorioForm, extra=0, can_delete=True
)


class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultiFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultiFileInput(attrs={
            'multiple': True,
            'accept': 'image/*',
            'capture': 'environment',
            'class': 'form-control',
        }))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class MultiplaFotoUploadForm(forms.Form):
    imagens = MultiFileField(required=False)


    