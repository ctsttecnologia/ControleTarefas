
# suprimentos/tests/test_services_helpers.py
import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from django.utils import timezone

from suprimentos.services import (
    criar_equipamento_epi_from_form,
    criar_ferramenta_from_form,
)
from suprimentos.models import Material
from seguranca_trabalho.models import Equipamento
from ferramentas.models import Ferramenta as FerramentaModel


def _fake_form(data: dict):
    """Simula um form já validado (cleaned_data)."""
    form = MagicMock()
    form.cleaned_data = data   # dict real → .get() já funciona sozinho
    return form

@pytest.mark.django_db
class TestCriarEquipamentoEPI:
    def test_cria_epi_e_vincula_ao_material(self, filial, material_factory, parceiro_factory):
        material = material_factory(descricao="Capacete Branco", marca="3M")
        fabricante = parceiro_factory(nome_fantasia="3M")   # ← campo certo
        form = _fake_form({
            "epi_modelo": "CAP-01",
            "epi_fabricante": fabricante,
            "epi_ca": "12345",
            "epi_vida_util_dias": 365,
        })
        equip = criar_equipamento_epi_from_form(material, form, filial)
        assert equip.fabricante == fabricante

        assert isinstance(equip, Equipamento)
        assert equip.nome == "Capacete Branco"
        assert equip.certificado_aprovacao == "12345"
        assert equip.vida_util_dias == 365
        material.refresh_from_db()
        assert material.equipamento_epi_id == equip.id

    def test_epi_sem_modelo_usa_string_vazia(self, filial, material_factory, parceiro_factory):
        material = material_factory(descricao="Luva")
        fabricante = parceiro_factory(nome_fantasia="Danny")
        form = _fake_form({
            "epi_modelo": None,
            "epi_fabricante": fabricante,   # ← objeto Parceiro
            "epi_ca": "999",
            "epi_vida_util_dias": 180,
        })
        equip = criar_equipamento_epi_from_form(material, form, filial)
        assert equip.modelo == ""

@pytest.fixture
def parceiro_factory(db, filial):
    from suprimentos.models import Parceiro
    def _make(nome_fantasia="Fabricante Teste", **kwargs):
        kwargs.setdefault("filial", filial)
        kwargs.setdefault("eh_fabricante", True)
        return Parceiro.objects.create(nome_fantasia=nome_fantasia, **kwargs)
    return _make

@pytest.mark.django_db
class TestCriarFerramenta:
    def test_cria_ferramenta_from_form(self, filial, material_factory):
        material = material_factory(descricao="Furadeira", marca="Bosch")
        form = _fake_form({
            "ferr_codigo": "FER-01",
            "ferr_patrimonio": "PAT-123",
            "ferr_localizacao": "Almoxarifado",
            "ferr_data_aquisicao": datetime.date(2026, 6, 10),
            "ferr_quantidade": 2,
            "ferr_fornecedor": None,
        })
        ferr = criar_ferramenta_from_form(material, form, filial)
        assert ferr.nome == "Furadeira"
        assert ferr.codigo_identificacao == "FER-01"
        assert ferr.patrimonio == "PAT-123"
        assert ferr.fabricante_marca == "Bosch"
        assert ferr.quantidade == 2          # ← era 2, não 5
        assert ferr.status == FerramentaModel.Status.DISPONIVEL
        material.refresh_from_db()
        assert material.ferramenta_ref_id == ferr.id

    def test_ferramenta_sem_codigo_gera_uuid(self, filial, material_factory):
        material = material_factory(descricao="Martelo")  # sem marca
        form = _fake_form({
            "ferr_codigo": "",                      # vazio → gera FERR-xxxx
            "ferr_patrimonio": None,
            "ferr_localizacao": "Depósito",
            "ferr_data_aquisicao": datetime.date(2026, 6, 10),
            "ferr_quantidade": None,
            "ferr_fornecedor": None,
        })
        ferr = criar_ferramenta_from_form(material, form, filial)
        assert ferr.codigo_identificacao.startswith("FERR-")
        assert len(ferr.codigo_identificacao) == 13   # "FERR-" + 8 hex
        assert ferr.patrimonio is None
        assert ferr.quantidade == 0
        assert ferr.fabricante_marca is None          # marca vazia → None


# pytest suprimentos/ --cov=suprimentos --cov-report=term-missing
# pytest suprimentos/ --cov=suprimentos.services --cov-report=html
