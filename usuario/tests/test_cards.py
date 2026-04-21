
# usuario/tests/test_cards.py
"""Testes das funções utilitárias de cards do dashboard."""

from usuario.cards import (
    ALL_CARDS,
    CARD_SUMMARY,
    get_all_cards,
    get_card_ids,
)


class TestCardsModule:
    """Funções helper que expõem os cards configurados."""

    def test_get_all_cards_retorna_lista_completa(self):
        cards = get_all_cards()
        assert cards is ALL_CARDS  # mesma referência
        assert isinstance(cards, list)
        assert len(cards) > 0

    def test_get_card_ids_retorna_set_de_ids(self):
        ids = get_card_ids()
        assert isinstance(ids, set)
        assert len(ids) == len(ALL_CARDS)  # sem duplicatas
        # Sanity check — IDs conhecidos precisam estar presentes
        assert {'clientes', 'dp', 'sst', 'main_dashboard'}.issubset(ids)

    def test_todos_cards_tem_campos_obrigatorios(self):
        """Garante integridade estrutural — previne quebra em templates."""
        obrigatorios = {'id', 'title', 'permission', 'icon', 'links'}
        for card in ALL_CARDS:
            assert obrigatorios.issubset(card.keys()), (
                f"Card {card.get('id')} está sem campos obrigatórios"
            )
            assert isinstance(card['links'], list)

    def test_card_summary_espelha_ids_e_titulos(self):
        assert len(CARD_SUMMARY) == len(ALL_CARDS)
        for summary, card in zip(CARD_SUMMARY, ALL_CARDS):
            assert summary == {'id': card['id'], 'title': card['title']}

    def test_nao_ha_ids_duplicados(self):
        """IDs duplicados quebrariam lógica de permissões."""
        ids = [c['id'] for c in ALL_CARDS]
        assert len(ids) == len(set(ids))
