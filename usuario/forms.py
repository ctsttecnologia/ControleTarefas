
# usuario/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm
from django.contrib.auth.models import Group
from .models import Usuario



class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Usuario
        # Definimos os campos a serem exibidos no formulário de criação.
        fields = ('username', 'first_name', 'last_name', 'email')

class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = Usuario
        # Exibimos mais campos no formulário de edição.
        fields = ('username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff', 'is_superuser', 'groups')
        # A senha não é editada aqui por segurança.

class CustomPasswordChangeForm(PasswordChangeForm):
    """ Formulário para o próprio usuário alterar sua senha. """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

class GrupoForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name', 'permissions']
        labels = {
            'name': 'Nome do Grupo',
            'permissions': 'Permissões Associadas'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Define o widget para o campo 'permissions' como checkboxes
        self.fields['permissions'].widget = forms.CheckboxSelectMultiple()
        
        # Opcional: Ordena as permissões para melhor visualização no formulário
        self.fields['permissions'].queryset = self.fields['permissions'].queryset.order_by('content_type__app_label', 'name')
