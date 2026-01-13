
from rest_framework import serializers
from .models import Tarefas, Comentario, HistoricoStatus
from usuario.serializers import UserSimpleSerializer # Supondo que você tenha um serializer simples para o usuário

class TarefaSerializer(serializers.ModelSerializer):
    """
    Serializer principal para a listagem de tarefas.
    Converte os campos de 'choices' para UPPERCASE na leitura (GET)
    e aceita UPPERCASE na escrita (POST/PATCH), convertendo para lowercase.
    """
    
    # 1. CAMPOS PARA LEITURA (Output para o App)
    # Usamos SerializerMethodField para controlar exatamente o que é enviado.
    status = serializers.SerializerMethodField()
    prioridade = serializers.SerializerMethodField()
    
    # Adicionamos os serializers dos relacionamentos para não enviar apenas os IDs
    usuario = UserSimpleSerializer(read_only=True)
    responsavel = UserSimpleSerializer(read_only=True)

    class Meta:
        model = Tarefas
        fields = [
            'id', 
            'titulo', 
            'descricao', 
            'status', 
            'prioridade', 
            'prazo', 
            'data_criacao',
            'recorrente', 
            'projeto',
            'progresso', # A @property do modelo
            'tarefa_pai', # O ID da tarefa pai
            'usuario',
            'responsavel',
        ]

    # --- Métodos para SerializerMethodField (leitura) ---

    def get_status(self, obj):
        # Pega o valor do banco de dados (ex: 'pendente') e envia como 'PENDENTE'
        return obj.status.upper() if obj.status else None

    def get_prioridade(self, obj):
        # Pega o valor do banco de dados (ex: 'alta') e envia como 'ALTA'
        return obj.prioridade.upper() if obj.prioridade else None


    # 2. MÉTODOS PARA ESCRITA (Input vindo do App)
    # Sobrescrevemos create e update para manipular os dados antes de salvar.

    def _convert_to_lowercase(self, data):
        """Função auxiliar para converter os valores de choices para minúsculas."""
        if 'status' in data:
            data['status'] = data['status'].lower()
        if 'prioridade' in data:
            data['prioridade'] = data['prioridade'].lower()
        return data

    def create(self, validated_data):
        """
        Chamado ao criar uma nova tarefa (POST).
        """
        # Converte os dados recebidos em UPPERCASE para lowercase antes de criar no banco
        validated_data = self._convert_to_lowercase(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """
        Chamado ao atualizar uma tarefa existente (PATCH/PUT).
        """
        # Converte os dados recebidos em UPPERCASE para lowercase antes de salvar no banco
        validated_data = self._convert_to_lowercase(validated_data)
        return super().update(instance, validated_data)


class TarefaDetailSerializer(TarefaSerializer):
    """
    Serializer para a visão de detalhes, herda do TarefaSerializer e adiciona mais campos.
    """
    # Adiciona os campos de relacionamentos que não estão na lista
    participantes = UserSimpleSerializer(many=True, read_only=True)
    subtarefas = TarefaSerializer(many=True, read_only=True)
    # Você também precisaria criar serializers para Comentario e HistoricoStatus
    # comentarios = ComentarioSerializer(many=True, read_only=True)
    # historicos = HistoricoStatusSerializer(many=True, read_only=True)

    class Meta(TarefaSerializer.Meta):
        # Herda os 'fields' da classe pai e adiciona os novos
        fields = TarefaSerializer.Meta.fields + [
            'data_inicio',
            'concluida_em',
            'frequencia_recorrencia',
            'data_fim_recorrencia',
            'duracao_prevista',
            'tempo_gasto',
            'participantes',
            'subtarefas',
            # 'comentarios',
            # 'historicos',
        ]

