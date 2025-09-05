# core/forms.py

from django import forms
from usuario.models import Filial

class ChangeFilialForm(forms.Form):
    filial = forms.ModelChoiceField(
        queryset=Filial.objects.none(),
        required=False,
        empty_label="-- Todas as Filiais (Global) --",
        label="Selecione a nova filial",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    # Stores the IDs of selected items as a hidden field (e.g., for bulk actions or filtering)
    selected_ids = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['filial'].queryset = Filial.objects.all()

