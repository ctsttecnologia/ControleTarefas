
# usuario/tests/test_models.py
"""Testes dos modelos do app usuario: Filial, Usuario, GroupCardPermissions."""

import pytest
from django.contrib.auth.models import Group

from usuario.models import Filial, GroupCardPermissions, Usuario


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
        grupo = Group.objects.create(name='Gerente')
        usuario_comum.groups.add(grupo)
        assert usuario_comum.is_gerente is True

    def test_is_gerente_false_quando_fora_do_grupo(self, usuario_comum):
        assert usuario_comum.is_gerente is False

    def test_is_coordenador_true_quando_no_grupo(self, usuario_comum):
        grupo = Group.objects.create(name='Coordenador')
        usuario_comum.groups.add(grupo)
        assert usuario_comum.is_coordenador is True

    def test_is_coordenador_false_quando_fora_do_grupo(self, usuario_comum):
        assert usuario_comum.is_coordenador is False

    def test_is_tecnico_true_quando_no_grupo(self, usuario_comum):
        grupo = Group.objects.create(name='Técnico')
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
        grupo = Group.objects.create(name='Administrador')
        usuario_comum.groups.add(grupo)
        assert usuario_comum.is_administrador is True

    def test_is_administrador_false_quando_usuario_comum(self, usuario_comum):
        assert usuario_comum.is_administrador is False


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
