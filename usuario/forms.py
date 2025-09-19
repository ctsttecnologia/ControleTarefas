# usuario/forms.py (VERSÃO REFATORADA)

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm
from django.contrib.auth.models import Group, Permission
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.db import transaction
from .models import Usuario, Filial
from departamento_pessoal.models import Funcionario

# =============================================================================
# == FORMULÁRIOS DE USUÁRIO
# =============================================================================

class CustomUserCreationForm(UserCreationForm):
    """
    Formulário para criar um novo usuário, garantindo que os campos de senha
    sejam herdados e renderizados corretamente.
    """
    first_name = forms.CharField(max_length=150, required=True, label="Primeiro Nome")
    last_name = forms.CharField(max_length=150, required=True, label="Último Nome")
    email = forms.EmailField(max_length=254, required=True, help_text="Obrigatório. Usado para notificações e recuperação de senha.")
    
    funcionario = forms.ModelChoiceField(
        queryset=Funcionario.objects.filter(usuario__isnull=True).order_by('nome_completo'),
        required=False,
        label="Vincular Funcionário (Opcional)",
        help_text="Associe a um funcionário existente que ainda não tem um usuário.",
        empty_label="--- Nenhum ---"
    )

    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email', 'funcionario')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # --- BLOCO DE DIAGNÓSTICO DEFINITIVO ---
        print("="*60)
        print("DIAGNÓSTICO DA CLASSE CustomUserCreationForm")
        print(f"A classe pai (super) é: {super().__class__}")
        
        if 'password' in self.fields:
            print("✅ O CAMPO 'password' EXISTE NO FORMULÁRIO.")
        else:
            print("❌ ERRO CRÍTICO: O CAMPO 'password' NÃO EXISTE NO FORMULÁRIO.")
        
        if 'password2' in self.fields:
            print("✅ O CAMPO 'password2' EXISTE NO FORMULÁRIO.")
        else:
            print("❌ ERRO: O CAMPO 'password2' NÃO EXISTE NO FORMULÁRIO.")
        
        print("\nTODOS OS CAMPOS DISPONÍVEIS:", list(self.fields.keys()))
        print("="*60)
        # --- FIM DO BLOCO DE DIAGNÓSTICO ---
        
        # Adicionando estilos (pode manter esta parte)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            else:
                field.widget.attrs.update({'class': 'form-control'})


    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']

        if commit:
            user.save()
            funcionario_selecionado = self.cleaned_data.get('funcionario')
            if funcionario_selecionado:
                funcionario_selecionado.usuario = user
                funcionario_selecionado.save()
        return user

class CustomUserChangeForm(UserChangeForm):
    """
    Formulário para um administrador editar os dados de um usuário existente.
    - Usa o widget FilteredSelectMultiple para uma melhor UX na seleção de grupos e filiais.
    - Remove o campo de senha para evitar alterações acidentais.
    """
    # A senha não é editada aqui diretamente, por isso a removemos
    password = None

    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        widget=FilteredSelectMultiple(verbose_name='Grupos', is_stacked=False),
        required=False
    )
    filiais_permitidas = forms.ModelMultipleChoiceField(
        queryset=Filial.objects.all().order_by('nome'),
        widget=FilteredSelectMultiple(verbose_name='Filiais Permitidas', is_stacked=False),
        required=False
    )
    filial_ativa = forms.ModelChoiceField(
        queryset=Filial.objects.none(),
        required=False,
        label="Filial Ativa",
        help_text="A filial que o usuário usará por padrão. Deve ser uma das Filiais Permitidas."
    )

    class Meta:
        model = Usuario
        fields = (
            'username', 'first_name', 'last_name', 'email',
            'filiais_permitidas', 'filial_ativa',
            'is_active', 'is_staff', 'is_superuser',
            'groups'
        )

    def __init__(self, *args, **kwargs):
        # Recebe o queryset personalizado
        filiais_permitidas_qs = kwargs.pop('filiais_permitidas_qs', None)
        super().__init__(*args, **kwargs)

        if filiais_permitidas_qs is not None:
            self.fields['filial_ativa'].queryset = filiais_permitidas_qs

        # Preenche os campos ManyToMany com os valores iniciais da instância do usuário
        if self.instance.pk:
            self.fields['groups'].initial = self.instance.groups.all()
            self.fields['filiais_permitidas'].initial = self.instance.filiais_permitidas.all()


class CustomPasswordChangeForm(PasswordChangeForm):
    """
    Formulário para o próprio usuário alterar sua senha, com estilo Bootstrap.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control', 'autocomplete': 'new-password'})


# =============================================================================
# == FORMULÁRIOS DE APOIO (GRUPOS E FILIAIS)
# =============================================================================

class GrupoForm(forms.ModelForm):
    """
    Formulário para gerenciar grupos e suas permissões com um widget amigável.
    """
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
        
