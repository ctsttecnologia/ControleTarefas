# core/forms.py

from django import forms

from usuario.models import Filial
from core.magic_utils import get_mime_type
from django.conf import settings
from core.validators import SecureFileValidator

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

# ============================================================
#  FORM MIXIN DE UPLOAD SEGURO
# ============================================================

class SecureUploadFormMixin:
    """
    Mixin para forms com upload seguro.

    Uso:
        class LaudoForm(SecureUploadFormMixin, forms.ModelForm):
            UPLOAD_APP = 'ltcat'
            UPLOAD_FIELD = 'file'

            class Meta:
                model = LaudoLTCAT
                fields = ['titulo', 'file']
    """

    UPLOAD_APP = 'default'
    UPLOAD_FIELD = 'file'

    def clean(self):
        cleaned = super().clean()
        file = cleaned.get(self.UPLOAD_FIELD)

        if file and hasattr(file, 'seek'):
            validator = SecureFileValidator(app_name=self.UPLOAD_APP)
            validator(file)

            mime = get_mime_type(file)

            if mime.startswith('image/'):
                from core.mixins import _sanitize_image
                cleaned[self.UPLOAD_FIELD] = _sanitize_image(file)

        return cleaned
    
    def get_upload_config_display(self):
        """Info para exibir no template (formatos aceitos, tamanho max)."""
        config = settings.UPLOAD_CONFIG.get(
            self.UPLOAD_APP,
            settings.UPLOAD_CONFIG.get('default', {}),
        )
        extensions = []
        for exts in config.get('allowed_types', {}).values():
            extensions.extend(exts)

        return {
            'max_size_mb': config.get('max_size_mb', 5),
            'extensions': sorted(set(extensions)),
            'accept': ','.join(sorted(set(extensions))),
        }
