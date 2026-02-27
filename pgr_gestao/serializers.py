
"""
Serializers para API REST do PGR
"""
from rest_framework import serializers
from .models import (
    PGRDocumento, PGRDocumentoResponsavel, PGRRevisao,
    GESGrupoExposicaoSimilar, CronogramaAcaoPGR
)

class PGRDocumentoSerializer(serializers.ModelSerializer):
    empresa_nome = serializers.CharField(source='empresa.razao_social', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    dias_vencimento = serializers.IntegerField(source='dias_para_vencimento', read_only=True)
    esta_vencido = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = PGRDocumento
        fields = '__all__'
        read_only_fields = ('data_cadastro', 'data_atualizacao')


class PGRRevisaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PGRRevisao
        fields = '__all__'
        read_only_fields = ('data_cadastro', 'data_atualizacao')


class PGRDocumentoResponsavelSerializer(serializers.ModelSerializer):
    profissional_nome = serializers.CharField(source='profissional.nome_completo', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_responsabilidade_display', read_only=True)
    
    class Meta:
        model = PGRDocumentoResponsavel
        fields = '__all__'
        read_only_fields = ('data_cadastro', 'data_atualizacao')


class GESGrupoExposicaoSimilarSerializer(serializers.ModelSerializer):
    ambiente_nome = serializers.CharField(source='ambiente_trabalho.nome', read_only=True)
    departamento_nome = serializers.CharField(source='departamento.nome', read_only=True)
    cargo_nome = serializers.CharField(source='cargo.nome', read_only=True)
    
    class Meta:
        model = GESGrupoExposicaoSimilar
        fields = '__all__'
        read_only_fields = ('data_cadastro', 'data_atualizacao')


class CronogramaAcaoPGRSerializer(serializers.ModelSerializer):
    periodicidade_display = serializers.CharField(source='get_periodicidade_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = CronogramaAcaoPGR
        fields = '__all__'
        read_only_fields = ('data_cadastro', 'data_atualizacao')

