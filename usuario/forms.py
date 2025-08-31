
# usuario/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm
from django.contrib.auth.models import Group, Permission 
from .models import Filial, Usuario
from django.contrib.admin.widgets import FilteredSelectMultiple



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

class CustomUserChangeForm(UserChangeForm):
    # Definimos os campos ManyToMany explicitamente para usar o widget do admin
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        widget=FilteredSelectMultiple(verbose_name='Grupos', is_stacked=False),
        required=False
    )
    filiais_permitidas = forms.ModelMultipleChoiceField(
        queryset=Filial.objects.all(),
        widget=FilteredSelectMultiple(verbose_name='Filiais Permitidas', is_stacked=False),
        required=False
    )

    class Meta(UserChangeForm.Meta):
        model = Usuario
        fields = (
            'username', 'first_name', 'last_name', 'email',
            'is_active', 'is_staff', 'is_superuser',
            'groups', 'filiais_permitidas' # Adicionamos os campos aqui
        )
        # O campo 'user_permissions' pode ser adicionado da mesma forma se você precisar
        # gerenciar permissões individuais, mas o ideal é usar grupos.     

class CustomPasswordChangeForm(PasswordChangeForm):
    """ Formulário para o próprio usuário alterar sua senha. """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

# usuario/forms.py

class GrupoForm(forms.ModelForm):
     # A mesma lógica para o formulário de grupo
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all().order_by('content_type__app_label', 'name'),
        widget=FilteredSelectMultiple(verbose_name='Permissões', is_stacked=False),
        required=False
    )
    class Meta:
        model = Group
        fields = ['name', 'permissions']
        labels = {
            'name': 'Nome do Grupo',
            'permissions': 'Permissões do Grupo'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # AQUI ESTÁ A MUDANÇA: Adicionamos uma classe ao widget
        self.fields['permissions'].widget = forms.CheckboxSelectMultiple(
            attrs={'class': 'permissions-list'}
        )
        
        self.fields['permissions'].queryset = self.fields['permissions'].queryset.order_by('content_type__app_label', 'name')

class FilialForm(forms.ModelForm):
    class Meta:
        model = Filial
        fields = ['nome']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: São Paulo'}),
        }

