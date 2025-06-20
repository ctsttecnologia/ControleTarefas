
from rest_framework import serializers, viewsets
from .models import Tarefas, Comentario

class ComentarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comentario
        fields = '__all__'

class TarefaSerializer(serializers.ModelSerializer):
    comentarios = ComentarioSerializer(many=True, read_only=True)
    
    class Meta:
        model = Tarefas
        fields = '__all__'
        depth = 1

class TarefaViewSet(viewsets.ModelViewSet):
    queryset = Tarefas.objects.all()
    serializer_class = TarefaSerializer

