
# suprimentos/services.py
"""
Serviços de negócio reutilizáveis do app Suprimentos.
Extraídos das views para facilitar testes e manutenção.
"""
import uuid
import logging

from seguranca_trabalho.models import Equipamento
from ferramentas.models import Ferramenta as FerramentaModel

logger = logging.getLogger(__name__)


def criar_equipamento_epi_from_form(material, form, filial):
    """
    Cria um Equipamento EPI no módulo SST vinculado ao Material.

    Args:
        material: instância de Material já salva
        form: MaterialForm com cleaned_data preenchido
        filial: Filial do usuário logado

    Returns:
        Equipamento criado
    """
    equipamento = Equipamento.objects.create(
        nome=material.descricao,
        modelo=form.cleaned_data.get('epi_modelo', '') or '',
        fabricante=form.cleaned_data['epi_fabricante'],
        certificado_aprovacao=form.cleaned_data.get('epi_ca', ''),
        vida_util_dias=form.cleaned_data['epi_vida_util_dias'],
        filial=filial,
    )
    material.equipamento_epi = equipamento
    material.save(update_fields=['equipamento_epi'])
    logger.info(
        f"Equipamento EPI criado: {equipamento.nome} "
        f"(CA: {equipamento.certificado_aprovacao}) para filial {filial}"
    )
    return equipamento


def criar_ferramenta_from_form(material, form, filial):
    """
    Cria uma Ferramenta no módulo Ferramentas vinculada ao Material.

    Args:
        material: instância de Material já salva
        form: MaterialForm com cleaned_data preenchido
        filial: Filial do usuário logado

    Returns:
        Ferramenta criada
    """
    codigo = form.cleaned_data.get('ferr_codigo', '').strip()
    if not codigo:
        codigo = f"FERR-{uuid.uuid4().hex[:8].upper()}"

    ferramenta = FerramentaModel.objects.create(
        nome=material.descricao,
        codigo_identificacao=codigo,
        patrimonio=form.cleaned_data.get('ferr_patrimonio') or None,
        fabricante_marca=material.marca or None,
        localizacao_padrao=form.cleaned_data['ferr_localizacao'],
        data_aquisicao=form.cleaned_data['ferr_data_aquisicao'],
        quantidade=form.cleaned_data.get('ferr_quantidade') or 0,
        fornecedor=form.cleaned_data.get('ferr_fornecedor'),
        filial=filial,
        status=FerramentaModel.Status.DISPONIVEL,
    )
    material.ferramenta_ref = ferramenta
    material.save(update_fields=['ferramenta_ref'])
    logger.info(
        f"Ferramenta criada: {ferramenta.nome} ({codigo}) para filial {filial}"
    )
    return ferramenta

