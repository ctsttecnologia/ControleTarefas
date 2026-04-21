
# usuario/tests/test_forms_creation.py
"""
Testes de segurança do CustomUserCreationForm.
"""
import pytest

from usuario.forms import CustomUserCreationForm
from usuario.models import Usuario

pytestmark = pytest.mark.django_db


# =============================================================================
# DADOS BASE VÁLIDOS
# =============================================================================

def _base_data(filial, **overrides):
    data = {
        'username': 'novo_user',
        'first_name': 'Novo',
        'last_name': 'Usuário',
        'email': 'novo@test.com',
        'password1': 'Senha@Forte123',
        'password2': 'Senha@Forte123',
        'filiais_permitidas': [filial.pk],
    }
    data.update(overrides)
    return data


# =============================================================================
# CRIAÇÃO PELO SUPERUSER
# =============================================================================

class TestCreationSuperuser:
    """Superuser pode criar qualquer tipo de usuário."""

    def test_superuser_pode_criar_usuario_comum(self, superuser, filial_a):
        form = CustomUserCreationForm(
            data=_base_data(filial_a),
            request_user=superuser,
        )
        assert form.is_valid(), form.errors
        user = form.save()
        assert user.is_superuser is False
        assert user.is_staff is False
        assert filial_a in user.filiais_permitidas.all()

    def test_superuser_pode_criar_outro_superuser(self, superuser, filial_a):
        data = _base_data(
            filial_a, is_superuser=True, is_staff=True, is_active=True
        )
        form = CustomUserCreationForm(data=data, request_user=superuser)
        assert form.is_valid(), form.errors
        user = form.save()
        assert user.is_superuser is True
        assert user.is_staff is True

    def test_superuser_ve_campos_de_privilegio(self, superuser):
        form = CustomUserCreationForm(request_user=superuser)
        assert 'is_superuser' in form.fields
        assert 'is_staff' in form.fields


# =============================================================================
# CRIAÇÃO POR GERENTE (NÃO-SUPERUSER) — SEGURANÇA
# =============================================================================

class TestCreationGerente:
    """Gerente NÃO pode conceder privilégios elevados."""

    def test_gerente_nao_ve_campos_de_privilegio(self, gerente):
        form = CustomUserCreationForm(request_user=gerente)
        assert 'is_superuser' not in form.fields
        assert 'is_staff' not in form.fields

    def test_gerente_cria_usuario_sem_privilegios(self, gerente, filial_a):
        form = CustomUserCreationForm(
            data=_base_data(filial_a),
            request_user=gerente,
        )
        assert form.is_valid(), form.errors
        user = form.save()
        assert user.is_superuser is False
        assert user.is_staff is False

    def test_gerente_forja_is_superuser_via_post(self, gerente, filial_a):
        """🔒 Mesmo forjando POST, não pode criar superuser."""
        data = _base_data(filial_a, is_superuser='on', is_staff='on')
        form = CustomUserCreationForm(data=data, request_user=gerente)
        # Form deve ignorar os campos removidos → válido mas sem privilégios
        assert form.is_valid(), form.errors
        user = form.save()
        assert user.is_superuser is False
        assert user.is_staff is False

    def test_gerente_so_ve_suas_filiais(self, gerente, filial_a, filial_b):
        """🔒 Queryset de filiais restrito ao escopo do gerente."""
        form = CustomUserCreationForm(request_user=gerente)
        filiais_disponiveis = list(form.fields['filiais_permitidas'].queryset)
        assert filial_a in filiais_disponiveis
        assert filial_b not in filiais_disponiveis

    def test_gerente_nao_pode_atribuir_filial_alheia(self, gerente, filial_a, filial_b):
        """🔒 Tentar atribuir filial fora do escopo → form inválido."""
        data = _base_data(filial_a, filiais_permitidas=[filial_b.pk])
        form = CustomUserCreationForm(data=data, request_user=gerente)
        assert not form.is_valid()
        assert 'filiais_permitidas' in form.errors


# =============================================================================
# VÍNCULO COM FUNCIONÁRIO
# =============================================================================

class TestCreationFuncionario:
    def test_vincular_funcionario_disponivel(
        self, superuser, filial_a, funcionario_disponivel
    ):
        data = _base_data(filial_a, funcionario=funcionario_disponivel.pk)
        form = CustomUserCreationForm(data=data, request_user=superuser)
        assert form.is_valid(), form.errors
        user = form.save()

        funcionario_disponivel.refresh_from_db()
        assert funcionario_disponivel.usuario == user

    def test_queryset_funcionarios_exclui_ja_vinculados(
        self, superuser, funcionario_disponivel, funcionario_vinculado
    ):
        form = CustomUserCreationForm(request_user=superuser)
        disponíveis = list(form.fields['funcionario'].queryset)
        assert funcionario_disponivel in disponíveis
        assert funcionario_vinculado not in disponíveis


# =============================================================================
# VALIDAÇÕES BÁSICAS
# =============================================================================

class TestCreationValidacoes:
    def test_email_obrigatorio(self, superuser, filial_a):
        data = _base_data(filial_a, email='')
        form = CustomUserCreationForm(data=data, request_user=superuser)
        assert not form.is_valid()
        assert 'email' in form.errors

    def test_filial_obrigatoria(self, superuser, filial_a):
        data = _base_data(filial_a)
        data.pop('filiais_permitidas')
        form = CustomUserCreationForm(data=data, request_user=superuser)
        assert not form.is_valid()
        assert 'filiais_permitidas' in form.errors

    def test_senhas_diferentes(self, superuser, filial_a):
        data = _base_data(filial_a, password2='Outra@Senha123')
        form = CustomUserCreationForm(data=data, request_user=superuser)
        assert not form.is_valid()
        assert 'password2' in form.errors
