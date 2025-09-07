from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm
from django.contrib.auth.models import Group, Permission
from django.contrib.admin.widgets import FilteredSelectMultiple

from departamento_pessoal.models import Funcionario
from .models import Usuario, Filial
from django.db.models import Q


class CustomUserCreationForm(UserCreationForm):
    """
    Um formulário de criação de usuário personalizado que adiciona um campo
    para selecionar um funcionário.
    """
    funcionario = forms.ModelChoiceField(
        queryset=Funcionario.objects.filter(
            Q(usuario__isnull=True)
        ),
        required=False,
        label="Vincular ao Funcionário",
        help_text="Associa este usuário a um funcionário existente que ainda não tem um usuário.",
    )
    
    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = UserCreationForm.Meta.fields + ('email', 'first_name', 'last_name', 'filiais_permitidas')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtra a lista de funcionários para exibir apenas aqueles que não possuem um usuário associado
        self.fields['funcionario'].queryset = Funcionario.objects.filter(usuario__isnull=True)
        
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            
        return user


class CustomUserChangeForm(UserChangeForm):
    """
    Um formulário de alteração de usuário que permite a edição dos
    grupos e filiais permitidas.
    """
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
            'groups', 'filiais_permitidas'
        )
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['groups'].initial = self.instance.groups.all()
            self.fields['filiais_permitidas'].initial = self.instance.filiais_permitidas.all()


class CustomPasswordChangeForm(PasswordChangeForm):
    """ Formulário para o próprio usuário alterar sua senha. """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class GrupoForm(forms.ModelForm):
    """ Formulário para gerenciar grupos e suas permissões. """
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
        if self.instance.pk:
            self.fields['permissions'].initial = self.instance.permissions.all()


class FilialForm(forms.ModelForm):
    class Meta:
        model = Filial
        fields = ['nome']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: São Paulo'}),
        }

