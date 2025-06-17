
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission 


Usuario = get_user_model()

class UsuarioCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ('username', 'email', 'first_name', 'last_name')  # Ou 'name' se adicionado
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remova 'name' se não existir no modelo
        if 'name' not in self.Meta.fields and 'name' in self.fields:
            del self.fields['name']

class UsuarioChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = Usuario
        fields = '__all__'
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remova 'name' se não existir no modelo
        if 'name' not in self.Meta.fields and 'name' in self.fields:
            del self.fields['name']

class GrupoForm(forms.ModelForm):  # Adicione esta classe
    class Meta:
        model = Group
        fields = '__all__'
        widgets = {
            'permissions': forms.SelectMultiple(attrs={'class': 'select2'})
        }

