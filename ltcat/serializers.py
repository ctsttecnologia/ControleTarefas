
# ltcat/serializers.py — Adicionar/atualizar

from rest_framework import serializers
from ltcat.models import (
    LocalPrestacaoServicoLTCAT, DocumentoLocalPrestacao,
    EmpresaLTCAT, LTCATDocumento
)
from logradouro.models import Logradouro


class LogradouroResumoSerializer(serializers.ModelSerializer):
    endereco_completo = serializers.SerializerMethodField()

    class Meta:
        model = Logradouro
        fields = ['id', 'endereco', 'numero', 'complemento', 'bairro',
                  'cidade', 'estado', 'cep', 'endereco_completo']

    def get_endereco_completo(self, obj):
        partes = filter(None, [
            obj.endereco,
            f"nº {obj.numero}" if obj.numero else None,
            obj.complemento, obj.bairro,
            f"{obj.cidade}/{obj.estado}" if obj.cidade and obj.estado else None,
            f"CEP: {obj.cep}" if obj.cep else None
        ])
        return ', '.join(partes)


class LocalPrestacaoSerializer(serializers.ModelSerializer):
    endereco_completo = serializers.ReadOnlyField()
    cidade_display = serializers.ReadOnlyField()
    logradouro_info = LogradouroResumoSerializer(source='logradouro', read_only=True)

    class Meta:
        model = LocalPrestacaoServicoLTCAT
        fields = [
            'id', 'nome_local', 'razao_social', 'cnpj', 'descricao',
            'logradouro', 'logradouro_info',
            'endereco', 'numero', 'complemento', 'bairro',
            'cidade', 'estado', 'cep',
            'endereco_completo', 'cidade_display'
        ]


class DocumentoLocalPrestacaoSerializer(serializers.ModelSerializer):
    local_prestacao_info = LocalPrestacaoSerializer(source='local_prestacao', read_only=True)

    class Meta:
        model = DocumentoLocalPrestacao
        fields = [
            'id', 'local_prestacao', 'local_prestacao_info',
            'principal', 'observacoes', 'ordem'
        ]


class EmpresaContratadaResumoSerializer(serializers.ModelSerializer):
    razao_social = serializers.ReadOnlyField()
    endereco_completo = serializers.ReadOnlyField()

    class Meta:
        model = EmpresaLTCAT
        fields = [
            'id', 'razao_social', 'cnpj', 'cnae', 'descricao_cnae',
            'grau_risco', 'grau_risco_texto', 'atividade_principal',
            'numero_empregados', 'numero_empregados_texto',
            'jornada_trabalho', 'endereco_completo',
            'telefone', 'email'
        ]


# ── Atualizar o serializer do Documento ──

class LTCATDocumentoSerializer(serializers.ModelSerializer):
    # Empresas
    empresa_contratante_nome = serializers.CharField(source='nome_contratante', read_only=True)
    empresa_contratada_info = EmpresaContratadaResumoSerializer(source='empresa_contratada', read_only=True)

    # Locais (M2M)
    documento_locais = DocumentoLocalPrestacaoSerializer(many=True, read_only=True)
    local_prestacao_principal_info = LocalPrestacaoSerializer(
        source='local_prestacao_principal', read_only=True
    )

    class Meta:
        model = LTCATDocumento
        fields = [
            'id', 'codigo_documento', 'titulo', 'status',
            # Empresas
            'empresa', 'empresa_contratante_nome',
            'empresa_contratada', 'empresa_contratada_info',
            # Locais
            'documento_locais', 'local_prestacao_principal_info',
            # Datas
            'data_elaboracao', 'data_ultima_revisao', 'data_vencimento',
            # Demais
            'versao_atual', 'objetivo', 'condicoes_preliminares',
            'avaliacao_periculosidade_texto', 'referencias_bibliograficas',
            'observacoes',
        ]

