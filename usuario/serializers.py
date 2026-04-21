
from rest_framework import serializers
from .models import Usuario

class UserSimpleSerializer(serializers.ModelSerializer):
    """
    Serializer enxuto para expor dados básicos do usuário em APIs.
    Apenas campos seguros e read-only (previne escalação via PATCH/PUT).
    """
    nome_completo = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = Usuario
        fields = ['id', 'nome_completo', 'email']
        read_only_fields = ['id', 'nome_completo', 'email']
