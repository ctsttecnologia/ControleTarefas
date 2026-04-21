
# usuario/tests/test_serializers.py
"""Testes do UserSimpleSerializer."""

import pytest

from usuario.serializers import UserSimpleSerializer


@pytest.mark.django_db
class TestUserSimpleSerializer:
    """Serializer usado em APIs que expõem dados básicos do usuário."""

    def test_serializa_campos_esperados(self, usuario_comum):
        serializer = UserSimpleSerializer(usuario_comum)
        data = serializer.data

        assert set(data.keys()) == {'id', 'nome_completo', 'email'}
        assert data['id'] == usuario_comum.id
        assert data['email'] == usuario_comum.email

    def test_nome_completo_usa_get_full_name(self, usuario_comum):
        """O campo 'nome_completo' deve refletir first_name + last_name."""
        usuario_comum.first_name = 'Emerson'
        usuario_comum.last_name = 'Silva'
        usuario_comum.save()

        data = UserSimpleSerializer(usuario_comum).data
        assert data['nome_completo'] == 'Emerson Silva'

    def test_nome_completo_vazio_quando_sem_first_last_name(self, usuario_comum):
        """Se não houver first/last name, get_full_name retorna string vazia."""
        usuario_comum.first_name = ''
        usuario_comum.last_name = ''
        usuario_comum.save()

        data = UserSimpleSerializer(usuario_comum).data
        assert data['nome_completo'] == ''

    def test_campos_sao_read_only(self):
        """Nenhum campo pode ser escrito via API — previne escalação."""
        serializer = UserSimpleSerializer()
        for field_name in ['id', 'nome_completo', 'email']:
            assert serializer.fields[field_name].read_only is True

    def test_nao_expoe_campos_sensiveis(self, usuario_comum):
        """Garante que password, is_staff, is_superuser NÃO são expostos."""
        data = UserSimpleSerializer(usuario_comum).data
        campos_proibidos = {
            'password', 'is_staff', 'is_superuser',
            'filiais_permitidas', 'filial_ativa', 'groups',
        }
        assert campos_proibidos.isdisjoint(data.keys())

# pytest usuario/tests/test_serializers.py -v --cov=usuario.serializers --cov-report=term-missing
# pytest usuario/ --cov=usuario --cov-report=term-missing

