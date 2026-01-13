
from rest_framework import serializers
from .models import User # ou o seu modelo de usuário

class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'nome_completo', 'email'] # Apenas os campos seguros e necessários
        read_only_fields = ['id', 'nome_completo', 'email']
