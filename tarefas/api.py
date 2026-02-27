
# tarefas/api.py

from rest_framework import serializers, viewsets
from .models import Tarefas, Comentario


class ComentarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comentario
        fields = ['id', 'autor', 'texto', 'anexo', 'criado_em']


class TarefaSerializer(serializers.ModelSerializer):
    """Serializer para API REST."""
    comentarios = ComentarioSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    prioridade_display = serializers.CharField(source='get_prioridade_display', read_only=True)
    progresso = serializers.IntegerField(read_only=True)

    class Meta:
        model = Tarefas
        fields = [
            'id', 'titulo', 'descricao', 'status', 'status_display',
            'prioridade', 'prioridade_display', 'prazo', 'data_criacao',
            'recorrente', 'projeto', 'progresso', 'tarefa_pai',
            'usuario', 'responsavel', 'comentarios',
        ]


class TarefaViewSet(viewsets.ModelViewSet):
    queryset = Tarefas.objects.select_related('usuario', 'responsavel', 'filial').all()
    serializer_class = TarefaSerializer

