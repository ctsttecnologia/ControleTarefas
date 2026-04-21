
# usuario/tests/test_forms_cards.py
"""
Testes do GroupCardPermissionsForm.
"""
import pytest

from usuario.forms import CARD_CHOICES, GroupCardPermissionsForm
from usuario.models import GroupCardPermissions

pytestmark = pytest.mark.django_db


class TestCardPermissionsForm:
    def test_cards_validos_aceitos(self, grupo_operador):
        card_ids = [c[0] for c in CARD_CHOICES[:3]]
        form = GroupCardPermissionsForm(data={
            'group': grupo_operador.pk,
            'cards_visiveis': card_ids,
        })
        assert form.is_valid(), form.errors

    def test_card_invalido_rejeitado(self, grupo_operador):
        """🔒 IDs forjados são bloqueados pelo clean()."""
        form = GroupCardPermissionsForm(data={
            'group': grupo_operador.pk,
            'cards_visiveis': ['hacker_card', 'admin_secreto'],
        })
        assert not form.is_valid()
        assert 'cards_visiveis' in form.errors

    def test_card_misto_valido_invalido_rejeita(self, grupo_operador):
        """Basta um inválido para invalidar tudo."""
        card_valido = CARD_CHOICES[0][0]
        form = GroupCardPermissionsForm(data={
            'group': grupo_operador.pk,
            'cards_visiveis': [card_valido, 'card_fake'],
        })
        assert not form.is_valid()

    def test_lista_vazia_aceita(self, grupo_operador):
        """Grupo sem cards selecionados é válido."""
        form = GroupCardPermissionsForm(data={
            'group': grupo_operador.pk,
            'cards_visiveis': [],
        })
        assert form.is_valid(), form.errors

    def test_card_choices_sincronizado_com_cards_module(self):
        """CARD_CHOICES é gerado de cards.py (fonte única da verdade)."""
        from usuario.cards import CARD_SUMMARY
        ids_forms = {c[0] for c in CARD_CHOICES}
        ids_cards = {c['id'] for c in CARD_SUMMARY}
        assert ids_forms == ids_cards

