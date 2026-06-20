
# usuario/tests/test_models.py
"""Testes dos modelos do app usuario: Filial, Usuario, GroupCardPermissions."""

import pytest
from django.contrib.auth.models import Group
from usuario.models import Filial, GroupCardPermissions, Usuario

from core.constants import (
    GRUPO_ADMINISTRADOR, GRUPO_GERENTE, GRUPO_COORDENADOR,
    GRUPO_TECNICO, GRUPO_ASSISTENTE, GRUPO_USUARIO_COMUM,
    GRUPO_GESTAO_QUALIDADE, GRUPO_SST_SEGURANCA, GRUPO_DEPARTAMENTO_PESSOAL,
)


@pytest.mark.django_db
class TestPropriedadesPerfil:

    @pytest.mark.parametrize("constante, propriedade", [
        (GRUPO_ADMINISTRADOR,        "is_administrador"),
        (GRUPO_GERENTE,              "is_gerente"),
        (GRUPO_COORDENADOR,          "is_coordenador"),
        (GRUPO_TECNICO,              "is_tecnico"),
        (GRUPO_ASSISTENTE,           "is_assistente"),
        (GRUPO_USUARIO_COMUM,        "is_usuario_comum"),
        (GRUPO_GESTAO_QUALIDADE,     "is_da_qualidade"),   # ✅ nome real
        (GRUPO_SST_SEGURANCA,        "is_do_sst"),         # ✅ nome real
        (GRUPO_DEPARTAMENTO_PESSOAL, "is_do_dp"),          # ✅ nome real
        # ❌ linha de GRUPOS_SETOR removida (não é um grupo nem tem propriedade)
    ])
    def test_propriedade_true_quando_no_grupo(self, usuario_comum, constante, propriedade):
        grupo = Group.objects.create(name=constante)
        usuario_comum.groups.add(grupo)
        usuario_comum.refresh_from_db()
        assert getattr(usuario_comum, propriedade) is True

@pytest.mark.django_db
class TestFilialModel:
    """Modelo Filial — unidades/filiais da empresa."""

    def test_str_retorna_nome(self):
        filial = Filial.objects.create(nome='Matriz SP')
        assert str(filial) == 'Matriz SP'

    def test_nome_unico(self):
        Filial.objects.create(nome='Filial Única')
        with pytest.raises(Exception):  # IntegrityError
            Filial.objects.create(nome='Filial Única')


@pytest.mark.django_db
class TestUsuarioModel:
    """Modelo Usuario customizado (AbstractUser + filiais)."""

    def test_str_com_nome_completo(self):
        user = Usuario.objects.create_user(
            username='emerson',
            email='emerson@test.com',
            password='senha123',
            first_name='Emerson',
            last_name='Silva',
        )
        assert str(user) == 'Emerson Silva'

    def test_str_fallback_para_username_quando_sem_nome(self):
        """Quando first/last name estão vazios, __str__ retorna username."""
        user = Usuario.objects.create_user(
            username='semNome',
            email='semnome@test.com',
            password='senha123',
        )
        assert str(user) == 'semNome'

    def test_is_gerente_true_quando_no_grupo(self, usuario_comum):
        grupo = Group.objects.create(name='GERENTE')
        usuario_comum.groups.add(grupo)
        assert usuario_comum.is_gerente is True

    def test_is_gerente_false_quando_fora_do_grupo(self, usuario_comum):
        assert usuario_comum.is_gerente is False

    def test_is_coordenador_true_quando_no_grupo(self, usuario_comum):
        grupo = Group.objects.create(name='COORDENADOR')
        usuario_comum.groups.add(grupo)
        assert usuario_comum.is_coordenador is True

    def test_is_coordenador_false_quando_fora_do_grupo(self, usuario_comum):
        assert usuario_comum.is_coordenador is False

    def test_is_tecnico_true_quando_no_grupo(self, usuario_comum):
        grupo = Group.objects.create(name='TECNICO')
        usuario_comum.groups.add(grupo)
        assert usuario_comum.is_tecnico is True

    def test_is_tecnico_false_quando_fora_do_grupo(self, usuario_comum):
        assert usuario_comum.is_tecnico is False

    def test_is_administrador_true_quando_superuser(self):
        admin = Usuario.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='senha123',
        )
        assert admin.is_administrador is True

    def test_is_administrador_true_quando_no_grupo(self, usuario_comum):
        grupo = Group.objects.create(name='ADMINISTRADOR')
        usuario_comum.groups.add(grupo)
        assert usuario_comum.is_administrador is True

    def test_is_administrador_false_quando_usuario_comum(self, usuario_comum):
        assert usuario_comum.is_administrador is False

    def test_is_tecnico_true(self, usuario_factory):
        user = usuario_factory()
        grupo, _ = Group.objects.get_or_create(name=GRUPO_TECNICO)
        user.groups.add(grupo)
        assert user.is_tecnico is True

    def test_is_tecnico_false_sem_grupo(self, usuario_factory):
        user = usuario_factory()
        assert user.is_tecnico is False


    def test_is_administrador(self, usuario_factory):
        user = usuario_factory()
        grupo, _ = Group.objects.get_or_create(name=GRUPO_ADMINISTRADOR)
        user.groups.add(grupo)
        assert user.is_administrador is True


    def test_is_da_qualidade(self, usuario_factory):
        user = usuario_factory()
        grupo, _ = Group.objects.get_or_create(name=GRUPO_GESTAO_QUALIDADE)
        user.groups.add(grupo)
        assert user.is_da_qualidade is True

@pytest.mark.django_db
class TestGroupCardPermissionsModel:
    """Mapeamento Grupo → cards visíveis no dashboard."""

    def test_str_retorna_nome_do_grupo(self):
        grupo = Group.objects.create(name='Supervisores')
        perm = GroupCardPermissions.objects.create(
            group=grupo,
            cards_visiveis=['tarefas', 'clientes'],
        )
        assert str(perm) == 'Permissões de Cartão para o Grupo: Supervisores'

    def test_cards_visiveis_default_lista_vazia(self):
        grupo = Group.objects.create(name='Novo Grupo')
        perm = GroupCardPermissions.objects.create(group=grupo)
        assert perm.cards_visiveis == []
