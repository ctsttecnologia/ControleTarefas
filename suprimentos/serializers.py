
# suprimentos/serializers.py

from rest_framework import serializers
from .models import (
    Parceiro, Material, Contrato, VerbaContrato,
    Pedido, ItemPedido,
)


# ═══════════════════════════════════════════════
# PARCEIRO
# ═══════════════════════════════════════════════
class ParceiroSerializer(serializers.ModelSerializer):
    filial_nome = serializers.CharField(source='filial.nome', read_only=True)

    class Meta:
        model = Parceiro
        fields = [
            'id', 'razao_social', 'nome_fantasia', 'cnpj',
            'inscricao_estadual', 'contato', 'telefone', 'celular',
            'email', 'site', 'observacoes',
            'eh_fabricante', 'eh_fornecedor', 'ativo',
            'filial', 'filial_nome',
        ]
        read_only_fields = ['id']


class ParceiroResumoSerializer(serializers.ModelSerializer):
    """Versão compacta para selects e autocompletes."""

    class Meta:
        model = Parceiro
        fields = ['id', 'nome_fantasia', 'cnpj', 'eh_fabricante', 'eh_fornecedor']


# ═══════════════════════════════════════════════
# MATERIAL
# ═══════════════════════════════════════════════
class MaterialSerializer(serializers.ModelSerializer):
    classificacao_display = serializers.CharField(
        source='get_classificacao_display', read_only=True,
    )
    tipo_display = serializers.CharField(
        source='get_tipo_display', read_only=True,
    )
    unidade_display = serializers.CharField(
        source='get_unidade_display', read_only=True,
    )
    ncm_codigo = serializers.CharField(
        source='ncm.codigo', read_only=True, default=None,
    )
    grupo_tributario_nome = serializers.CharField(
        source='grupo_tributario.nome', read_only=True, default=None,
    )

    class Meta:
        model = Material
        fields = [
            'id', 'codigo', 'descricao',
            'classificacao', 'classificacao_display',
            'tipo', 'tipo_display',
            'marca', 'unidade', 'unidade_display',
            'valor_unitario', 'ativo',
            'ncm', 'ncm_codigo',
            'grupo_tributario', 'grupo_tributario_nome',
        ]
        read_only_fields = ['id', 'codigo']

# ═══════════════════════════════════════════════
# CONTRATO
# ═══════════════════════════════════════════════
class ContratoSerializer(serializers.ModelSerializer):
    filial_nome = serializers.CharField(source='filial.nome', read_only=True)

    class Meta:
        model = Contrato
        fields = [
            'id', 'cm', 'cliente', 'filial', 'filial_nome', 'ativo',
        ]
        read_only_fields = ['id']


class ContratoResumoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contrato
        fields = ['id', 'cm', 'cliente']


# ═══════════════════════════════════════════════
# VERBA MENSAL
# ═══════════════════════════════════════════════
class VerbaContratoSerializer(serializers.ModelSerializer):
    contrato_cm = serializers.CharField(source='contrato.cm', read_only=True)
    verba_total = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True,
    )
    compra_epi = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True,
    )
    compra_consumo = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True,
    )
    compra_ferramenta = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True,
    )
    compra_total = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True,
    )
    saldo_epi = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True,
    )
    saldo_consumo = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True,
    )
    saldo_ferramenta = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True,
    )
    saldo_total = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True,
    )

    class Meta:
        model = VerbaContrato
        fields = [
            'id', 'contrato', 'contrato_cm', 'ano', 'mes',
            'verba_epi', 'verba_consumo', 'verba_ferramenta', 'verba_total',
            'compra_epi', 'compra_consumo', 'compra_ferramenta', 'compra_total',
            'saldo_epi', 'saldo_consumo', 'saldo_ferramenta', 'saldo_total',
        ]
        read_only_fields = ['id']


# ═══════════════════════════════════════════════
# ITEM PEDIDO
# ═══════════════════════════════════════════════
class ItemPedidoSerializer(serializers.ModelSerializer):
    material_descricao = serializers.CharField(
        source='material.descricao', read_only=True,
    )
    material_classificacao = serializers.CharField(
        source='material.classificacao', read_only=True,
    )
    material_unidade = serializers.CharField(
        source='material.get_unidade_display', read_only=True,
    )

    class Meta:
        model = ItemPedido
        fields = [
            'id', 'pedido', 'material',
            'material_descricao', 'material_classificacao', 'material_unidade',
            'quantidade', 'valor_unitario', 'valor_total', 'observacao',
            'custo_real', 'total_creditos', 'total_impostos',  # ★ NOVO
        ]
        read_only_fields = ['id', 'valor_total', 'custo_real', 'total_creditos', 'total_impostos']


# ═══════════════════════════════════════════════
# PEDIDO
# ═══════════════════════════════════════════════
class PedidoListSerializer(serializers.ModelSerializer):
    """Serializer enxuto para listagem."""
    contrato_cm = serializers.CharField(source='contrato.cm', read_only=True)
    contrato_cliente = serializers.CharField(source='contrato.cliente', read_only=True)
    solicitante_nome = serializers.CharField(
        source='solicitante.get_full_name', read_only=True,
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True,
    )
    valor_total = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True,
    )

    class Meta:
        model = Pedido
        fields = [
            'id', 'numero', 'contrato', 'contrato_cm', 'contrato_cliente',
            'solicitante', 'solicitante_nome',
            'status', 'status_display', 'valor_total',
            'data_pedido', 'data_aprovacao', 'data_entrega', 'data_recebimento',
        ]
        read_only_fields = ['id', 'numero']


class PedidoDetailSerializer(serializers.ModelSerializer):
    """Serializer completo com itens aninhados."""
    contrato_cm = serializers.CharField(source='contrato.cm', read_only=True)
    contrato_cliente = serializers.CharField(source='contrato.cliente', read_only=True)
    solicitante_nome = serializers.CharField(
        source='solicitante.get_full_name', read_only=True,
    )
    aprovador_nome = serializers.SerializerMethodField()
    recebedor_nome = serializers.SerializerMethodField()
    status_display = serializers.CharField(
        source='get_status_display', read_only=True,
    )
    valor_total = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True,
    )
    itens = ItemPedidoSerializer(many=True, read_only=True)
    totais_por_classificacao = serializers.SerializerMethodField()

    class Meta:
        model = Pedido
        fields = [
            'id', 'numero', 'contrato', 'contrato_cm', 'contrato_cliente',
            'solicitante', 'solicitante_nome',
            'aprovador', 'aprovador_nome',
            'recebedor', 'recebedor_nome',
            'filial', 'status', 'status_display', 'valor_total',
            'data_pedido', 'data_aprovacao', 'data_entrega', 'data_recebimento',
            'observacao', 'motivo_reprovacao',
            'itens', 'totais_por_classificacao',
        ]
        read_only_fields = ['id', 'numero']

    def get_aprovador_nome(self, obj):
        return obj.aprovador.get_full_name() if obj.aprovador else None

    def get_recebedor_nome(self, obj):
        return obj.recebedor.get_full_name() if obj.recebedor else None

    def get_totais_por_classificacao(self, obj):
        totais = obj.totais_por_classificacao()
        return {k: str(v) for k, v in totais.items()}

