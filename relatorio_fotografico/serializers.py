# relatorio_fotografico/serializers.py
from rest_framework import serializers
from .models import RelatorioFotografico, FotoRelatorio


class FotoRelatorioSerializer(serializers.ModelSerializer):
    imagem = serializers.ImageField(read_only=True)
    imagem_url = serializers.SerializerMethodField()

    class Meta:
        model = FotoRelatorio
        fields = ['id', 'relatorio', 'imagem', 'imagem_url', 'legenda', 'ordem', 'created_at']
        read_only_fields = ['id', 'created_at', 'imagem_url']

    def get_imagem_url(self, obj):
        request = self.context.get('request')
        if obj.imagem and request:
            return request.build_absolute_uri(obj.imagem.url)
        return obj.imagem.url if obj.imagem else None


class FotoUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = FotoRelatorio
        fields = ['id', 'imagem', 'legenda', 'ordem']


class RelatorioFotograficoSerializer(serializers.ModelSerializer):
    fotos = FotoRelatorioSerializer(many=True, read_only=True)
    total_folhas = serializers.ReadOnlyField()
    responsavel_nome = serializers.SerializerMethodField()
    total_fotos = serializers.SerializerMethodField()

    obra = serializers.CharField(source='obra_contrato', required=False, allow_blank=True)
    assunto = serializers.CharField(required=False, allow_blank=True)
    titulo = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = RelatorioFotografico
        fields = [
            'id', 'titulo', 'obra', 'obra_contrato', 'data', 'assunto',
            'responsavel', 'responsavel_nome', 'filial', 'status',
            'total_folhas', 'total_fotos', 'fotos', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'obra_contrato', 'created_at', 'updated_at',
            'responsavel', 'filial',
        ]

    def get_responsavel_nome(self, obj):
        return obj.responsavel.get_full_name() or obj.responsavel.username

    def get_total_fotos(self, obj):
        return obj.fotos.count()

    def validate(self, attrs):
        # Gera título automático se não enviado (responsavel/filial ficam a cargo da view)
        if not attrs.get('titulo'):
            obra = attrs.get('obra_contrato') or ''
            assunto = attrs.get('assunto') or ''
            data = attrs.get('data')
            partes = [p for p in [obra, assunto, str(data) if data else ''] if p]
            attrs['titulo'] = ' - '.join(partes) or 'Relatório Fotográfico'
        return attrs


class RelatorioFotograficoListSerializer(serializers.ModelSerializer):
    """Versão leve para listagem (sem carregar todas as fotos)."""
    responsavel_nome = serializers.SerializerMethodField()
    total_fotos = serializers.SerializerMethodField()

    class Meta:
        model = RelatorioFotografico
        fields = [
            'id', 'titulo', 'obra_contrato', 'data', 'assunto', 'status',
            'responsavel_nome', 'total_fotos', 'created_at',
        ]

    def get_responsavel_nome(self, obj):
        return obj.responsavel.get_full_name() or obj.responsavel.username

    def get_total_fotos(self, obj):
        return obj.fotos.count()

