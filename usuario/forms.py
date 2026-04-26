# usuario/forms.py
"""
Formulários do app Usuário.

Boas práticas aplicadas:
  - Aceita `request_user` em forms sensíveis para aplicar escopo e
    impedir escalação de privilégios.
  - Valida flags (`is_superuser`, `is_staff`) no `clean()`.
  - Remove visualmente campos que o solicitante não pode alterar.
"""

from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.forms import (
    PasswordChangeForm, UserChangeForm, UserCreationForm,
)
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from departamento_pessoal.models import Funcionario
from usuario.cards import CARD_SUMMARY
from usuario.models import Filial, GroupCardPermissions, Usuario


# =============================================================================
# == HELPERS INTERNOS
# =============================================================================

_PROTECTED_FLAGS = ('is_superuser', 'is_staff')
_PROTECTED_M2M = ('user_permissions',)


def _aplicar_bootstrap(fields):
    """Aplica classes Bootstrap aos widgets de form."""
    for field in fields.values():
        widget = field.widget
        if isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
            continue
        if isinstance(widget, FilteredSelectMultiple):
            continue
        if isinstance(widget, forms.Select):
            widget.attrs.setdefault('class', 'form-select')
        else:
            widget.attrs.setdefault('class', 'form-control')


def _scoped_filiais_queryset(request_user):
    """
    Retorna o queryset de Filiais que o solicitante pode atribuir a outros
    usuários. Superusuário vê todas; demais, apenas suas `filiais_permitidas`.
    """
    if request_user is None or request_user.is_superuser:
        return Filial.objects.all().order_by('nome')
    return request_user.filiais_permitidas.all().order_by('nome')


def _scoped_groups_queryset(request_user):
    """
    Retorna o queryset de Grupos que o solicitante pode atribuir.
    Por enquanto todos — mas deixa o hook pronto para restringir no futuro
    (ex: impedir gerente de conceder grupo 'ADMIN').
    """
    if request_user is None or request_user.is_superuser:
        return Group.objects.all().order_by('name')
    # 🔒 Futuro: exclua grupos administrativos aqui se precisar
    return Group.objects.all().order_by('name')


# =============================================================================
# == FORMULÁRIOS DE USUÁRIO
# =============================================================================

class CustomUserCreationForm(UserCreationForm):
    """
    Formulário para criar um novo usuário.
    """
    first_name = forms.CharField(
        max_length=150, required=True, label="Primeiro Nome"
    )
    last_name = forms.CharField(
        max_length=150, required=True, label="Último Nome"
    )
    email = forms.EmailField(
        max_length=254, required=True,
        help_text="Obrigatório. Usado para notificações e recuperação de senha.",
    )

    funcionario = forms.ModelChoiceField(
        queryset=Funcionario.objects.filter(
            usuario__isnull=True
        ).order_by('nome_completo'),
        required=False,
        label="Vincular Funcionário (Opcional)",
        help_text="Associe a um funcionário existente que ainda não tem um usuário.",
        empty_label="--- Nenhum ---",
    )

    filiais_permitidas = forms.ModelMultipleChoiceField(
        queryset=Filial.objects.none(),  # setado no __init__
        widget=FilteredSelectMultiple(verbose_name='Filiais Permitidas', is_stacked=False),
        required=True,
        help_text="O usuário deve pertencer a pelo menos uma filial.",
    )

    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.none(),  # setado no __init__
        widget=FilteredSelectMultiple(verbose_name='Grupos', is_stacked=False),
        required=False,
        label="Grupos",
    )

    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = UserCreationForm.Meta.fields + (
            'first_name', 'last_name', 'email', 'funcionario',
            'filiais_permitidas', 'groups',
            # As flags só serão aceitas se o solicitante for superuser
            'is_active', 'is_staff', 'is_superuser',
        )

    def __init__(self, *args, request_user=None, **kwargs):
        self.request_user = request_user
        super().__init__(*args, **kwargs)

        # Escopo de filiais e grupos
        self.fields['filiais_permitidas'].queryset = _scoped_filiais_queryset(request_user)
        self.fields['groups'].queryset = _scoped_groups_queryset(request_user)

        if request_user and not self.instance.pk:
            if request_user.filial_ativa:
                self.fields['filiais_permitidas'].initial = [request_user.filial_ativa.pk]

        # Remove campos de privilégio para quem não é superuser
        if request_user and not request_user.is_superuser:
            for flag in _PROTECTED_FLAGS:
                self.fields.pop(flag, None)

        _aplicar_bootstrap(self.fields)

    def clean_filiais_permitidas(self):
        filiais = self.cleaned_data.get('filiais_permitidas')
        if not filiais:
            raise ValidationError(
                "Selecione ao menos uma filial para o usuário."
            )
        return filiais

    def clean(self):
        """ Defesa em profundidade: valida flags mesmo se o campo foi removido."""
        cleaned = super().clean()

        if self.request_user and not self.request_user.is_superuser:
            for flag in _PROTECTED_FLAGS:
                if cleaned.get(flag):
                    raise ValidationError(
                        "Você não tem permissão para conceder privilégios elevados."
                    )
        return cleaned

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']

        # 🔒 Garante que não-superuser NUNCA cria superuser/staff
        if self.request_user and not self.request_user.is_superuser:
            user.is_superuser = False
            user.is_staff = False

        if commit:
            user.save()
            # M2M só pode ser salvo após o user existir
            self.save_m2m()

            funcionario = self.cleaned_data.get('funcionario')
            if funcionario:
                funcionario.usuario = user
                funcionario.save(update_fields=['usuario'])

        return user


class CustomUserChangeForm(UserChangeForm):
    """
    Formulário para editar um usuário existente.

    O campo `funcionario` permite:
      - Manter o funcionário já vinculado (se houver)
      - Vincular a um funcionário ainda sem usuário
      - Desvincular (selecionando "--- Nenhum ---")
    """
    password = None

    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.none(),
        widget=FilteredSelectMultiple(verbose_name='Grupos', is_stacked=False),
        required=False,
        label="Grupos",
    )

    user_permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.select_related('content_type').order_by(
            'content_type__app_label', 'codename'
        ),
        widget=FilteredSelectMultiple(verbose_name='Permissões', is_stacked=False),
        required=False,
        label="Permissões do Usuário",
        help_text="Permissões específicas além das herdadas pelos grupos.",
    )

    filiais_permitidas = forms.ModelMultipleChoiceField(
        queryset=Filial.objects.none(),
        widget=FilteredSelectMultiple(verbose_name='Filiais Permitidas', is_stacked=False),
        required=False,
    )

    filial_ativa = forms.ModelChoiceField(
        queryset=Filial.objects.none(),
        required=False,
        label="Filial Ativa",
        help_text="A filial que o usuário usará por padrão. "
                  "Deve ser uma das Filiais Permitidas.",
    )

    # ═══════════════════════════════════════════════════════════════════
    # 🆕 NOVO: Vínculo com funcionário (mantém atual + disponíveis)
    # ═══════════════════════════════════════════════════════════════════
    funcionario = forms.ModelChoiceField(
        queryset=Funcionario.objects.none(),  # setado no __init__
        required=False,
        label="Funcionário Vinculado",
        help_text=(
            "Vincule este usuário a um funcionário do DP. "
            "Selecione '--- Nenhum ---' para desvincular."
        ),
        empty_label="--- Nenhum ---",
    )

    class Meta:
        model = Usuario
        fields = (
            'username', 'first_name', 'last_name', 'email',
            'filiais_permitidas', 'filial_ativa',
            'is_active', 'is_staff', 'is_superuser',
            'groups', 'user_permissions',
            # funcionario NÃO entra aqui — é salvo manualmente em save()
        )

    def __init__(self, *args, request_user=None, filiais_permitidas_qs=None, **kwargs):
        self.request_user = request_user
        super().__init__(*args, **kwargs)

        # Escopo de filiais e grupos
        self.fields['filiais_permitidas'].queryset = _scoped_filiais_queryset(request_user)
        self.fields['groups'].queryset = _scoped_groups_queryset(request_user)

        if filiais_permitidas_qs is not None:
            self.fields['filial_ativa'].queryset = filiais_permitidas_qs

        # ═══════════════════════════════════════════════════════════════
        # 🆕 Queryset inteligente de funcionário
        # ═══════════════════════════════════════════════════════════════
        self._configurar_campo_funcionario()

        # Pré-carrega valores atuais
        if self.instance.pk:
            self.fields['groups'].initial = self.instance.groups.all()
            self.fields['filiais_permitidas'].initial = self.instance.filiais_permitidas.all()
            self.fields['user_permissions'].initial = self.instance.user_permissions.all()

        # 🔒 Remove campos sensíveis se não for superuser
        if request_user and not request_user.is_superuser:
            for campo in _PROTECTED_FLAGS + _PROTECTED_M2M:
                self.fields.pop(campo, None)

        _aplicar_bootstrap(self.fields)

    def _configurar_campo_funcionario(self):
        """
        Queryset do campo funcionário:
          - Funcionários SEM usuário (disponíveis), OU
          - O funcionário JÁ vinculado a este usuário (se houver)

        Também pré-seleciona o funcionário atual no `initial`.
        """
        funcionario_atual = self._get_funcionario_atual()

        # Base: todos sem usuário + o atual (se houver)
        qs = Funcionario.objects.filter(
            Q(usuario__isnull=True) |
            Q(pk=funcionario_atual.pk if funcionario_atual else None)
        ).order_by('nome_completo').distinct()

        self.fields['funcionario'].queryset = qs

        if funcionario_atual:
            self.fields['funcionario'].initial = funcionario_atual

    def _get_funcionario_atual(self):
        """Retorna o funcionário vinculado ao usuário sendo editado (se houver)."""
        if not self.instance.pk:
            return None
        return Funcionario.objects.filter(usuario=self.instance).first()

    def clean(self):
        """🔒 Defesa em profundidade contra escalação de privilégios."""
        cleaned = super().clean()

        if not self.request_user or self.request_user.is_superuser:
            return cleaned

        # Não-superuser não pode alterar flags protegidas
        for flag in _PROTECTED_FLAGS:
            novo_valor = cleaned.get(flag)
            valor_atual = getattr(self.instance, flag, False)
            if novo_valor is not None and novo_valor != valor_atual:
                raise ValidationError(
                    "Você não tem permissão para alterar privilégios do usuário."
                )

        # Filial ativa precisa estar entre as permitidas
        filial_ativa = cleaned.get('filial_ativa')
        filiais_permitidas = cleaned.get('filiais_permitidas')
        if (filial_ativa and filiais_permitidas
                and filial_ativa not in filiais_permitidas):
            raise ValidationError({
                'filial_ativa': "A filial ativa deve estar entre as filiais permitidas."
            })

        return cleaned

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)

        # 🔒 Trava definitiva de privilégios
        if self.request_user and not self.request_user.is_superuser:
            original = self.instance
            for flag in _PROTECTED_FLAGS:
                setattr(user, flag, getattr(original, flag, False))

        if commit:
            user.save()
            self.save_m2m()
            self._sync_funcionario(user)

        return user

    def _sync_funcionario(self, user):
        """
        Sincroniza o vínculo com funcionário:
          - Desvincula o anterior (se mudou)
          - Vincula o novo (se selecionado)
        """
        funcionario_novo = self.cleaned_data.get('funcionario')
        funcionario_atual = Funcionario.objects.filter(usuario=user).first()

        # Nada mudou
        if funcionario_novo == funcionario_atual:
            return

        # Desvincula o atual (se existir)
        if funcionario_atual and funcionario_atual != funcionario_novo:
            funcionario_atual.usuario = None
            funcionario_atual.save(update_fields=['usuario'])

        # Vincula o novo (se selecionado)
        if funcionario_novo:
            funcionario_novo.usuario = user
            funcionario_novo.save(update_fields=['usuario'])


class CustomPasswordChangeForm(PasswordChangeForm):
    """Formulário para o próprio usuário alterar sua senha."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'form-control',
                'autocomplete': 'new-password',
            })


# =============================================================================
# == FORMULÁRIOS DE APOIO (GRUPOS E FILIAIS)
# =============================================================================

class GrupoForm(forms.ModelForm):
    """
    Formulário para gerenciar grupos e suas permissões.
    """
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.select_related('content_type').order_by(
            'content_type__app_label', 'name'
        ),
        widget=FilteredSelectMultiple(verbose_name='Permissões', is_stacked=False),
        required=False,
    )

    class Meta:
        model = Group
        fields = ['name', 'permissions']
        labels = {
            'name': 'Nome do Grupo',
            'permissions': 'Permissões do Grupo',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
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
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: São Paulo',
            }),
        }


# =============================================================================
# == FORMULÁRIOS DE PERMISSÕES DE CARDS
# =============================================================================

# 🔄 Sincronizado automaticamente com usuario/cards.py (fonte única da verdade)
CARD_CHOICES = [(c['id'], c['title']) for c in CARD_SUMMARY]


class GroupCardPermissionsForm(forms.ModelForm):
    """
    Formulário para definir quais cards um grupo pode ver.
    """
    cards_visiveis = forms.MultipleChoiceField(
        choices=CARD_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Cards Visíveis",
    )

    class Meta:
        model = GroupCardPermissions
        fields = '__all__'

    def clean_cards_visiveis(self):
        """🔒 Valida que todos os IDs enviados estão na whitelist."""
        cards = self.cleaned_data.get('cards_visiveis', [])
        valid_ids = {c[0] for c in CARD_CHOICES}
        invalidos = set(cards) - valid_ids
        if invalidos:
            raise ValidationError(
                f"Cards inválidos: {', '.join(invalidos)}"
            )
        return cards


