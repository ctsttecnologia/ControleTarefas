
# usuario/tests/test_forms_coverage.py
"""
Testes de cobertura dos branches de segurança e edge cases do forms.py.
Foca nas linhas 144, 293, 308, 368-370, 404-406, 450.
"""

import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError

from departamento_pessoal.models import Funcionario
from usuario.forms import (
    CustomUserChangeForm,
    CustomUserCreationForm,
    GroupCardPermissionsForm,
)
from usuario.models import Filial, Usuario


# =============================================================================
# == FIXTURES
# =============================================================================

@pytest.fixture
def filial_sp(db):
    return Filial.objects.create(nome='São Paulo')


@pytest.fixture
def filial_rj(db):
    return Filial.objects.create(nome='Rio de Janeiro')


@pytest.fixture
def superuser(db):
    return Usuario.objects.create_superuser(
        username='root', email='root@test.com', password='x'
    )


@pytest.fixture
def gerente(db, filial_sp):
    """Usuário não-superuser com acesso apenas à filial SP."""
    user = Usuario.objects.create_user(
        username='gerente', email='g@test.com', password='x'
    )
    user.filiais_permitidas.add(filial_sp)
    return user


@pytest.fixture
def usuario_alvo(db, filial_sp):
    """Usuário comum que será editado nos testes."""
    user = Usuario.objects.create_user(
        username='alvo', email='alvo@test.com', password='x',
        first_name='João', last_name='Alvo',
    )
    user.filiais_permitidas.add(filial_sp)
    return user


# =============================================================================
# == LINHA 144 — CustomUserCreationForm.clean() bloqueia privilégios
# =============================================================================

class TestCreationFormBloqueiaPrivilegios:
    """Non-superuser NÃO pode criar usuário com is_staff/is_superuser."""

    @pytest.mark.django_db
    def test_nao_superuser_enviando_is_staff_via_data_raw_eh_bloqueado(
        self, gerente, filial_sp
    ):
        """
        Mesmo que um atacante forje o POST com is_staff=True, o clean()
        deve barrar (defesa em profundidade — linha 144).
        """
        data = {
            'username': 'novo',
            'first_name': 'Novo',
            'last_name': 'User',
            'email': 'novo@test.com',
            'password1': 'SenhaForte!123',
            'password2': 'SenhaForte!123',
            'filiais_permitidas': [filial_sp.pk],
            'is_staff': True,   # 🚨 tentativa de escalação
        }
        form = CustomUserCreationForm(data=data, request_user=gerente)

        # Simula injeção: força o campo de volta mesmo após o pop do __init__
        form.fields['is_staff'] = type(form.fields.get('is_active'))(required=False)
        form.cleaned_data = {}
        # Forma mais direta: chamar clean com cleaned_data manipulado
        form.is_valid()  # popula cleaned_data normalmente

        # Injeta diretamente cleaned_data para disparar o raise da linha 144
        form.cleaned_data['is_staff'] = True
        with pytest.raises(ValidationError, match='privilégios elevados'):
            form.clean()


# =============================================================================
# == LINHA 293 — CustomUserChangeForm.clean() bloqueia alteração de flag
# =============================================================================

class TestChangeFormBloqueiaAlteracaoDeFlags:
    """Non-superuser não pode ALTERAR is_staff/is_superuser de um usuário."""

    @pytest.mark.django_db
    def test_nao_superuser_tentando_alterar_is_staff_eh_bloqueado(
        self, gerente, usuario_alvo, filial_sp
    ):
        form = CustomUserChangeForm(
            instance=usuario_alvo,
            request_user=gerente,
            filiais_permitidas_qs=Filial.objects.all(),
        )

        # Campos protegidos foram removidos no __init__, mas injetamos
        # direto no cleaned_data para validar a defesa em profundidade (linha 293)
        form.cleaned_data = {
            'is_staff': True,  # antes era False — mudança proibida
            'filiais_permitidas': Filial.objects.filter(pk=filial_sp.pk),
            'filial_ativa': None,
        }

        with pytest.raises(ValidationError, match='alterar privilégios'):
            form.clean()


# =============================================================================
# == LINHA 308 — filial_ativa precisa estar em filiais_permitidas
# =============================================================================

class TestChangeFormValidaFilialAtiva:
    """filial_ativa DEVE estar entre as filiais_permitidas."""

    @pytest.mark.django_db
    def test_filial_ativa_fora_das_permitidas_levanta_erro(
        self, gerente, usuario_alvo, filial_sp, filial_rj
    ):
        form = CustomUserChangeForm(
            instance=usuario_alvo,
            request_user=gerente,
            filiais_permitidas_qs=Filial.objects.all(),
        )
        form.cleaned_data = {
            'filiais_permitidas': Filial.objects.filter(pk=filial_sp.pk),
            'filial_ativa': filial_rj,  # 🚨 RJ não está em [SP]
        }

        with pytest.raises(ValidationError, match='filial ativa deve estar'):
            form.clean()


# =============================================================================
# == LINHAS 368-370 — _sync_funcionario desvincula funcionário anterior
# =============================================================================

# ═══════════════════════════════════════════════════════════════════════
# LINHAS 368-370 — _sync_funcionario desvincula funcionário anterior
# ═══════════════════════════════════════════════════════════════════════

class TestSyncFuncionarioTrocaVinculo:
    """
    Testa _sync_funcionario diretamente com mocks, evitando a complexidade
    de criar Funcionario real (que exige cargo, funcao, departamento, etc.).
    Alvo: linhas 368-370 (desvincular antigo e vincular novo).
    """

    @pytest.mark.django_db
    def test_sync_funcionario_desvincula_antigo_e_vincula_novo(
        self, superuser, usuario_alvo, filial_sp, monkeypatch
    ):
        from unittest.mock import MagicMock

        # Mocks dos dois funcionários
        func_antigo = MagicMock(name='func_antigo')
        func_antigo.usuario = usuario_alvo
        func_antigo.__eq__ = lambda self, other: other is self

        func_novo = MagicMock(name='func_novo')
        func_novo.usuario = None
        func_novo.__eq__ = lambda self, other: other is self

        # Mocka Funcionario.objects.filter(...).first() para retornar func_antigo
        mock_queryset = MagicMock()
        mock_queryset.first.return_value = func_antigo
        monkeypatch.setattr(
            'usuario.forms.Funcionario.objects.filter',
            lambda *a, **kw: mock_queryset,
        )

        # Instancia o form (sem data — vamos chamar só _sync_funcionario)
        form = CustomUserChangeForm(
            instance=usuario_alvo,
            request_user=superuser,
            filiais_permitidas_qs=Filial.objects.all(),
        )
        form.cleaned_data = {'funcionario': func_novo}

        # Ato: chama direto _sync_funcionario
        form._sync_funcionario(usuario_alvo)

        # 🎯 Linhas 368-370: antigo foi desvinculado
        assert func_antigo.usuario is None
        func_antigo.save.assert_called_once_with(update_fields=['usuario'])

        # Novo foi vinculado
        assert func_novo.usuario == usuario_alvo
        func_novo.save.assert_called_once_with(update_fields=['usuario'])

    @pytest.mark.django_db
    def test_sync_funcionario_nada_muda_quando_funcionario_e_o_mesmo(
        self, superuser, usuario_alvo, filial_sp, monkeypatch
    ):
        """Early return: se funcionario_novo == funcionario_atual, não faz nada."""
        from unittest.mock import MagicMock

        func = MagicMock(name='func_mesmo')
        func.usuario = usuario_alvo

        mock_queryset = MagicMock()
        mock_queryset.first.return_value = func
        monkeypatch.setattr(
            'usuario.forms.Funcionario.objects.filter',
            lambda *a, **kw: mock_queryset,
        )

        form = CustomUserChangeForm(
            instance=usuario_alvo,
            request_user=superuser,
            filiais_permitidas_qs=Filial.objects.all(),
        )
        form.cleaned_data = {'funcionario': func}  # mesmo funcionário

        form._sync_funcionario(usuario_alvo)

        # Nada foi salvo (early return)
        func.save.assert_not_called()

    @pytest.mark.django_db
    def test_sync_funcionario_apenas_desvincula_quando_novo_e_none(
        self, superuser, usuario_alvo, filial_sp, monkeypatch
    ):
        """Quando novo=None e existe antigo: só desvincula."""
        from unittest.mock import MagicMock

        func_antigo = MagicMock(name='func_antigo')
        func_antigo.usuario = usuario_alvo

        mock_queryset = MagicMock()
        mock_queryset.first.return_value = func_antigo
        monkeypatch.setattr(
            'usuario.forms.Funcionario.objects.filter',
            lambda *a, **kw: mock_queryset,
        )

        form = CustomUserChangeForm(
            instance=usuario_alvo,
            request_user=superuser,
            filiais_permitidas_qs=Filial.objects.all(),
        )
        form.cleaned_data = {'funcionario': None}  # desvinculando

        form._sync_funcionario(usuario_alvo)

        # Antigo desvinculado
        assert func_antigo.usuario is None
        func_antigo.save.assert_called_once_with(update_fields=['usuario'])


# ═══════════════════════════════════════════════════════════════════════
# LINHAS 404-406 — clean_cards_visiveis valida whitelist
# ═══════════════════════════════════════════════════════════════════════

class TestGroupCardPermissionsFormValidaIds:
    """IDs fora da whitelist CARD_CHOICES devem ser rejeitados."""

    @pytest.mark.django_db
    def test_clean_cards_visiveis_rejeita_id_fora_da_whitelist(self):
        """
        Chama clean_cards_visiveis diretamente para alcançar linhas 404-406.
        (Via data= o MultipleChoiceField barra antes, no validator de choices.)
        """
        grupo = Group.objects.create(name='TesteCards')
        form = GroupCardPermissionsForm(instance=None)
        form.cleaned_data = {
            'cards_visiveis': ['id_inexistente_xyz', 'outro_fake'],
        }

        with pytest.raises(ValidationError, match='inválidos'):
            form.clean_cards_visiveis()

    @pytest.mark.django_db
    def test_clean_cards_visiveis_aceita_ids_validos(self):
        """IDs válidos passam sem erro."""
        from usuario.forms import CARD_CHOICES

        form = GroupCardPermissionsForm(instance=None)
        # Pega o primeiro card válido (se houver)
        if CARD_CHOICES:
            valid_id = CARD_CHOICES[0][0]
            form.cleaned_data = {'cards_visiveis': [valid_id]}
            resultado = form.clean_cards_visiveis()
            assert valid_id in resultado

    @pytest.mark.django_db
    def test_cards_visiveis_vazio_e_valido(self):
        grupo = Group.objects.create(name='TesteCardsVazio')
        form = GroupCardPermissionsForm(data={
            'group': grupo.pk,
            'cards_visiveis': [],
        })
        assert form.is_valid(), form.errors

# Testes de cobertura para forms.py, focando em branches de segurança e validação.
# Alvo: linhas 144, 293, 308, 368-370,
# pytest usuario/tests/test_forms_coverage.py -v --cov=usuario.forms --cov-report=term-missing
