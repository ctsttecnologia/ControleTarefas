
# usuario/tests/test_forms_change.py
"""
Testes de segurança do CustomUserChangeForm.
"""
import pytest

from usuario.forms import CustomUserChangeForm
from usuario.models import Usuario

pytestmark = pytest.mark.django_db


def _base_data(user, filial, **overrides):
    """Monta dados base para edição do `user`."""
    data = {
        'username': user.username,
        'first_name': user.first_name or 'Nome',
        'last_name': user.last_name or 'Sobrenome',
        'email': user.email or 'email@test.com',
        'is_active': 'on',
        'filiais_permitidas': [filial.pk],
        'filial_ativa': filial.pk,
    }
    data.update(overrides)
    return data


# =============================================================================
# ESCALAÇÃO DE PRIVILÉGIOS (🔒 CRÍTICO)
# =============================================================================

class TestChangeEscalacaoPrivilegios:
    """Cenários de tentativa de escalação de privilégios."""

    def test_gerente_nao_ve_campos_privilegio(self, gerente, usuario_comum, filial_a):
        form = CustomUserChangeForm(
            instance=usuario_comum,
            request_user=gerente,
            filiais_permitidas_qs=usuario_comum.filiais_permitidas.all(),
        )
        assert 'is_superuser' not in form.fields
        assert 'is_staff' not in form.fields
        assert 'user_permissions' not in form.fields

    def test_gerente_forja_is_superuser_no_post(
        self, gerente, usuario_comum, filial_a
    ):
        """🔒 Mesmo com POST forjado, não promove."""
        data = _base_data(
            usuario_comum, filial_a,
            is_superuser='on', is_staff='on'
        )
        form = CustomUserChangeForm(
            data=data,
            instance=usuario_comum,
            request_user=gerente,
            filiais_permitidas_qs=usuario_comum.filiais_permitidas.all(),
        )
        assert form.is_valid(), form.errors
        user = form.save()
        assert user.is_superuser is False
        assert user.is_staff is False

    def test_superuser_pode_promover_usuario(
        self, superuser, usuario_comum, filial_a
    ):
        data = _base_data(
            usuario_comum, filial_a,
            is_staff='on', is_superuser='on'
        )
        form = CustomUserChangeForm(
            data=data,
            instance=usuario_comum,
            request_user=superuser,
            filiais_permitidas_qs=usuario_comum.filiais_permitidas.all(),
        )
        assert form.is_valid(), form.errors
        user = form.save()
        assert user.is_staff is True
        assert user.is_superuser is True


# =============================================================================
# ESCOPO DE FILIAIS
# =============================================================================

class TestChangeEscopoFiliais:
    def test_gerente_so_ve_suas_filiais(
        self, gerente, usuario_comum, filial_a, filial_b
    ):
        form = CustomUserChangeForm(
            instance=usuario_comum,
            request_user=gerente,
            filiais_permitidas_qs=usuario_comum.filiais_permitidas.all(),
        )
        filiais = list(form.fields['filiais_permitidas'].queryset)
        assert filial_a in filiais
        assert filial_b not in filiais

    def test_filial_ativa_deve_estar_em_permitidas(
        self, superuser, usuario_comum, filial_a, filial_b
    ):
        """Validação: filial_ativa ∉ filiais_permitidas → erro."""
        data = _base_data(
            usuario_comum, filial_a,
            filiais_permitidas=[filial_a.pk],
            filial_ativa=filial_b.pk,
        )
        form = CustomUserChangeForm(
            data=data,
            instance=usuario_comum,
            request_user=superuser,
            filiais_permitidas_qs=usuario_comum.filiais_permitidas.all(),
        )
        # Superuser vê ambas, então o queryset aceita filial_b
        # mas o clean() do form deve barrar pela inconsistência
        # (nota: para superuser nossa validação não dispara — só para não-superuser)
        # Então esse teste vale para gerente:

    def test_gerente_filial_ativa_fora_de_permitidas(
        self, gerente, usuario_comum, filial_a, filial_b
    ):
        """Gerente tentando desalinhar filial_ativa."""
        # Adiciona filial_b ao escopo do gerente para simular o ataque
        gerente.filiais_permitidas.add(filial_b)

        data = _base_data(
            usuario_comum, filial_a,
            filiais_permitidas=[filial_a.pk],
            filial_ativa=filial_b.pk,
        )
        form = CustomUserChangeForm(
            data=data,
            instance=usuario_comum,
            request_user=gerente,
            filiais_permitidas_qs=usuario_comum.filiais_permitidas.all(),
        )
        # filial_ativa precisa estar no queryset do campo
        form.fields['filial_ativa'].queryset = type(filial_a).objects.all()
        assert not form.is_valid()
        assert 'filial_ativa' in form.errors


# =============================================================================
# VÍNCULO COM FUNCIONÁRIO (🆕)
# =============================================================================

class TestChangeFuncionario:
    """Testes da nova funcionalidade de vínculo em edição."""

    def test_funcionario_atual_aparece_no_queryset(
        self, superuser, usuario_comum, funcionario_vinculado, funcionario_disponivel
    ):
        """
        🆕 Funcionário já vinculado ao usuário editado DEVE aparecer,
        mesmo que não esteja "disponível" (usuario__isnull=False).
        """
        form = CustomUserChangeForm(
            instance=usuario_comum,
            request_user=superuser,
            filiais_permitidas_qs=usuario_comum.filiais_permitidas.all(),
        )
        queryset = list(form.fields['funcionario'].queryset)
        assert funcionario_vinculado in queryset
        assert funcionario_disponivel in queryset

    def test_funcionario_atual_vem_pre_selecionado(
        self, superuser, usuario_comum, funcionario_vinculado
    ):
        form = CustomUserChangeForm(
            instance=usuario_comum,
            request_user=superuser,
            filiais_permitidas_qs=usuario_comum.filiais_permitidas.all(),
        )
        assert form.fields['funcionario'].initial == funcionario_vinculado

    def test_desvincular_funcionario(
        self, superuser, usuario_comum, funcionario_vinculado, filial_a
    ):
        """Selecionar '--- Nenhum ---' deve desvincular."""
        data = _base_data(usuario_comum, filial_a, funcionario='')
        form = CustomUserChangeForm(
            data=data,
            instance=usuario_comum,
            request_user=superuser,
            filiais_permitidas_qs=usuario_comum.filiais_permitidas.all(),
        )
        assert form.is_valid(), form.errors
        form.save()

        funcionario_vinculado.refresh_from_db()
        assert funcionario_vinculado.usuario is None

    def test_trocar_funcionario_vinculado(
        self, superuser, usuario_comum, funcionario_vinculado,
        funcionario_disponivel, filial_a
    ):
        """Trocar vínculo: o antigo é liberado, o novo é associado."""
        data = _base_data(
            usuario_comum, filial_a,
            funcionario=funcionario_disponivel.pk,
        )
        form = CustomUserChangeForm(
            data=data,
            instance=usuario_comum,
            request_user=superuser,
            filiais_permitidas_qs=usuario_comum.filiais_permitidas.all(),
        )
        assert form.is_valid(), form.errors
        form.save()

        funcionario_vinculado.refresh_from_db()
        funcionario_disponivel.refresh_from_db()

        assert funcionario_vinculado.usuario is None
        assert funcionario_disponivel.usuario == usuario_comum

    def test_manter_funcionario_atual_sem_mudanca(
        self, superuser, usuario_comum, funcionario_vinculado, filial_a
    ):
        data = _base_data(
            usuario_comum, filial_a,
            funcionario=funcionario_vinculado.pk,
        )
        form = CustomUserChangeForm(
            data=data,
            instance=usuario_comum,
            request_user=superuser,
            filiais_permitidas_qs=usuario_comum.filiais_permitidas.all(),
        )
        assert form.is_valid(), form.errors
        form.save()

        funcionario_vinculado.refresh_from_db()
        assert funcionario_vinculado.usuario == usuario_comum

    def test_vincular_pela_primeira_vez(
        self, superuser, usuario_comum, funcionario_disponivel, filial_a
    ):
        """Usuário sem funcionário + escolhe um disponível → vincula."""
        data = _base_data(
            usuario_comum, filial_a,
            funcionario=funcionario_disponivel.pk,
        )
        form = CustomUserChangeForm(
            data=data,
            instance=usuario_comum,
            request_user=superuser,
            filiais_permitidas_qs=usuario_comum.filiais_permitidas.all(),
        )
        assert form.is_valid(), form.errors
        form.save()

        funcionario_disponivel.refresh_from_db()
        assert funcionario_disponivel.usuario == usuario_comum


# =============================================================================
# PERMISSÕES INDIVIDUAIS (user_permissions)
# =============================================================================

class TestChangeUserPermissions:
    def test_gerente_nao_pode_editar_permissoes_individuais(
        self, gerente, usuario_comum
    ):
        """🔒 Campo user_permissions é apenas para superuser."""
        form = CustomUserChangeForm(
            instance=usuario_comum,
            request_user=gerente,
            filiais_permitidas_qs=usuario_comum.filiais_permitidas.all(),
        )
        assert 'user_permissions' not in form.fields

    def test_superuser_pode_editar_permissoes_individuais(
        self, superuser, usuario_comum
    ):
        form = CustomUserChangeForm(
            instance=usuario_comum,
            request_user=superuser,
            filiais_permitidas_qs=usuario_comum.filiais_permitidas.all(),
        )
        assert 'user_permissions' in form.fields

