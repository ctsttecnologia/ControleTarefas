
# api/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model
from tarefas.models import Tarefas, Comentario
from automovel.models import Carro, Carro_agendamento, Carro_checklist
from seguranca_trabalho.models import FichaEPI, EntregaEPI, Equipamento
from ferramentas.models import TermoDeResponsabilidade, ItemTermo, Ferramenta, MalaFerramentas

User = get_user_model()


# ===================== USUÁRIO =====================
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'filial_ativa']


# ===================== TAREFAS =====================
class TarefaListSerializer(serializers.ModelSerializer):
    """Serializer resumido para listagem de tarefas."""
    responsavel_nome = serializers.CharField(source='responsavel.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    prioridade_display = serializers.CharField(source='get_prioridade_display', read_only=True)

    class Meta:
        model = Tarefas
        fields = [
            'id', 'titulo', 'status', 'status_display', 'prioridade', 
            'prioridade_display', 'prazo', 'responsavel_nome', 'progresso', 'atrasada'
        ]


class TarefaDetailSerializer(serializers.ModelSerializer):
    """Serializer completo para detalhes e edição."""
    responsavel_nome = serializers.CharField(source='responsavel.get_full_name', read_only=True)
    usuario_nome = serializers.CharField(source='usuario.get_full_name', read_only=True)

    class Meta:
        model = Tarefas
        fields = '__all__'
        read_only_fields = ['usuario', 'data_criacao', 'data_atualizacao', 'filial']


class ComentarioSerializer(serializers.ModelSerializer):
    autor_nome = serializers.CharField(source='autor.get_full_name', read_only=True)

    class Meta:
        model = Comentario
        fields = ['id', 'texto', 'autor_nome', 'criado_em', 'anexo']
        read_only_fields = ['autor', 'filial']


# ===================== AUTOMÓVEL =====================
class CarroSerializer(serializers.ModelSerializer):
    status_manutencao = serializers.SerializerMethodField()

    class Meta:
        model = Carro
        fields = ['id', 'placa', 'modelo', 'marca', 'cor', 'ano', 'quilometragem', 
                  'disponivel', 'foto', 'status_manutencao']

    def get_status_manutencao(self, obj):
        status = obj.status_manutencao
        return {'key': status[0], 'message': status[1], 'color': status[2]}


class AgendamentoSerializer(serializers.ModelSerializer):
    carro_info = CarroSerializer(source='carro', read_only=True)

    class Meta:
        model = Carro_agendamento
        fields = '__all__'
        read_only_fields = ['usuario', 'filial', 'status']


class ChecklistSerializer(serializers.ModelSerializer):
    """Serializer para criar/visualizar checklists de veículos."""
    
    class Meta:
        model = Carro_checklist
        fields = [
            'id', 'agendamento', 'tipo', 'data_hora',
            'revisao_frontal_status', 'foto_frontal',
            'revisao_trazeira_status', 'foto_trazeira',
            'revisao_lado_motorista_status', 'foto_lado_motorista',
            'revisao_lado_passageiro_status', 'foto_lado_passageiro',
            'observacoes_gerais', 'assinatura', 'confirmacao'
        ]
        read_only_fields = ['usuario', 'filial', 'data_hora']


# ===================== SEGURANÇA DO TRABALHO (Fichas e EPIs) =====================
class EquipamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipamento
        fields = ['id', 'nome', 'modelo', 'certificado_aprovacao', 'foto']


class EntregaEPISerializer(serializers.ModelSerializer):
    equipamento_info = EquipamentoSerializer(source='equipamento', read_only=True)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = EntregaEPI
        fields = [
            'id', 'equipamento', 'equipamento_info', 'quantidade', 'lote',
            'data_entrega', 'assinatura_recebimento', 'data_assinatura', 'status'
        ]
        read_only_fields = ['ficha', 'filial']


class FichaEPISerializer(serializers.ModelSerializer):
    funcionario_nome = serializers.CharField(source='funcionario.nome_completo', read_only=True)
    entregas_pendentes = serializers.SerializerMethodField()

    class Meta:
        model = FichaEPI
        fields = ['id', 'funcionario', 'funcionario_nome', 'entregas_pendentes', 'criado_em']

    def get_entregas_pendentes(self, obj):
        # Retorna entregas que ainda não foram assinadas
        pendentes = obj.entregas.filter(assinatura_recebimento__isnull=True, assinatura_imagem__isnull=True)
        return EntregaEPISerializer(pendentes, many=True).data


# ===================== TERMOS DE RESPONSABILIDADE =====================
class ItemTermoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemTermo
        fields = ['id', 'quantidade', 'unidade', 'item', 'ferramenta', 'mala']


class TermoResponsabilidadeSerializer(serializers.ModelSerializer):
    itens = ItemTermoSerializer(many=True, read_only=True)
    responsavel_nome = serializers.CharField(source='responsavel.nome_completo', read_only=True)
    is_signed = serializers.BooleanField(read_only=True)

    class Meta:
        model = TermoDeResponsabilidade
        fields = [
            'id', 'contrato', 'responsavel', 'responsavel_nome', 'data_emissao',
            'tipo_uso', 'itens', 'is_signed', 'assinatura_data', 'data_recebimento'
        ]
        read_only_fields = ['movimentado_por', 'filial']


# ===================== ASSINATURA =====================
class AssinaturaSerializer(serializers.Serializer):
    """Serializer genérico para receber assinaturas em Base64."""
    assinatura_base64 = serializers.CharField(
        help_text="Imagem da assinatura codificada em Base64."
    )
# api/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model
from tarefas.models import Tarefas, Comentario
from automovel.models import Carro, Carro_agendamento, Carro_checklist
from seguranca_trabalho.models import FichaEPI, EntregaEPI, Equipamento
from ferramentas.models import TermoDeResponsabilidade, ItemTermo

User = get_user_model()


# ===================== USUÁRIO =====================
class UserSerializer(serializers.ModelSerializer):
    filial_ativa_nome = serializers.CharField(source='filial_ativa.nome', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                  'filial_ativa', 'filial_ativa_nome']


# ===================== TAREFAS =====================
class TarefaListSerializer(serializers.ModelSerializer):
    """Serializer resumido para listagem."""
    responsavel_nome = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    prioridade_display = serializers.CharField(source='get_prioridade_display', read_only=True)

    class Meta:
        model = Tarefas
        fields = [
            'id', 'titulo', 'status', 'status_display', 'prioridade', 
            'prioridade_display', 'prazo', 'responsavel_nome', 'progresso', 'atrasada'
        ]

    def get_responsavel_nome(self, obj):
        if obj.responsavel:
            return obj.responsavel.get_full_name() or obj.responsavel.username
        return None


class TarefaDetailSerializer(serializers.ModelSerializer):
    """Serializer completo para detalhes."""
    responsavel_nome = serializers.SerializerMethodField()
    usuario_nome = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    prioridade_display = serializers.CharField(source='get_prioridade_display', read_only=True)

    class Meta:
        model = Tarefas
        fields = [
            'id', 'titulo', 'descricao', 'status', 'status_display',
            'prioridade', 'prioridade_display', 'prazo', 'data_inicio',
            'data_criacao', 'concluida_em', 'responsavel', 'responsavel_nome',
            'usuario', 'usuario_nome', 'projeto', 'progresso', 'atrasada',
            'recorrente', 'frequencia_recorrencia'
        ]
        read_only_fields = ['usuario', 'data_criacao', 'filial', 'progresso', 'atrasada']

    def get_responsavel_nome(self, obj):
        if obj.responsavel:
            return obj.responsavel.get_full_name() or obj.responsavel.username
        return None

    def get_usuario_nome(self, obj):
        if obj.usuario:
            return obj.usuario.get_full_name() or obj.usuario.username
        return None


class ComentarioSerializer(serializers.ModelSerializer):
    autor_nome = serializers.SerializerMethodField()

    class Meta:
        model = Comentario
        fields = ['id', 'texto', 'autor_nome', 'criado_em', 'anexo']
        read_only_fields = ['autor', 'filial', 'criado_em']

    def get_autor_nome(self, obj):
        return obj.autor.get_full_name() or obj.autor.username


# ===================== AUTOMÓVEL =====================
class CarroSerializer(serializers.ModelSerializer):
    status_manutencao_info = serializers.SerializerMethodField()

    class Meta:
        model = Carro
        fields = [
            'id', 'placa', 'modelo', 'marca', 'cor', 'ano', 
            'quilometragem', 'disponivel', 'foto', 'status_manutencao_info'
        ]

    def get_status_manutencao_info(self, obj):
        status = obj.status_manutencao
        return {
            'key': status[0],
            'message': status[1],
            'color': status[2]
        }


class AgendamentoListSerializer(serializers.ModelSerializer):
    carro_placa = serializers.CharField(source='carro.placa', read_only=True)
    carro_modelo = serializers.CharField(source='carro.modelo', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Carro_agendamento
        fields = [
            'id', 'carro', 'carro_placa', 'carro_modelo', 'funcionario',
            'data_hora_agenda', 'data_hora_devolucao', 'status', 'status_display',
            'km_inicial', 'km_final'
        ]


class AgendamentoDetailSerializer(serializers.ModelSerializer):
    carro_info = CarroSerializer(source='carro', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    tem_checklist_saida = serializers.SerializerMethodField()
    tem_checklist_retorno = serializers.SerializerMethodField()

    class Meta:
        model = Carro_agendamento
        fields = [
            'id', 'carro', 'carro_info', 'funcionario', 'responsavel',
            'data_hora_agenda', 'data_hora_devolucao', 'status', 'status_display',
            'cm', 'descricao', 'pedagio', 'abastecimento',
            'km_inicial', 'km_final', 'ocorrencia',
            'tem_checklist_saida', 'tem_checklist_retorno'
        ]
        read_only_fields = ['usuario', 'filial', 'status']

    def get_tem_checklist_saida(self, obj):
        return obj.checklist_saida is not None

    def get_tem_checklist_retorno(self, obj):
        return obj.checklist_retorno is not None


class ChecklistSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)

    class Meta:
        model = Carro_checklist
        fields = [
            'id', 'agendamento', 'tipo', 'tipo_display', 'data_hora',
            'revisao_frontal_status', 'foto_frontal',
            'revisao_trazeira_status', 'foto_trazeira',
            'revisao_lado_motorista_status', 'foto_lado_motorista',
            'revisao_lado_passageiro_status', 'foto_lado_passageiro',
            'observacoes_gerais', 'assinatura', 'confirmacao'
        ]
        read_only_fields = ['usuario', 'filial', 'data_hora']


# ===================== SEGURANÇA DO TRABALHO =====================
class EquipamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipamento
        fields = ['id', 'nome', 'modelo', 'certificado_aprovacao', 'foto', 'vida_util_dias']


class EntregaEPISerializer(serializers.ModelSerializer):
    equipamento_info = EquipamentoSerializer(source='equipamento', read_only=True)
    status = serializers.CharField(read_only=True)
    data_vencimento_uso = serializers.DateField(read_only=True)
    assinado = serializers.SerializerMethodField()

    class Meta:
        model = EntregaEPI
        fields = [
            'id', 'equipamento', 'equipamento_info', 'quantidade', 'lote',
            'numero_serie', 'data_entrega', 'data_vencimento_uso',
            'assinatura_recebimento', 'data_assinatura', 'status', 'assinado'
        ]
        read_only_fields = ['ficha', 'filial']

    def get_assinado(self, obj):
        return bool(obj.assinatura_recebimento or obj.assinatura_imagem)


class FichaEPIListSerializer(serializers.ModelSerializer):
    funcionario_nome = serializers.CharField(source='funcionario.nome_completo', read_only=True)
    funcionario_matricula = serializers.CharField(source='funcionario.matricula', read_only=True)
    total_entregas_pendentes = serializers.SerializerMethodField()

    class Meta:
        model = FichaEPI
        fields = [
            'id', 'funcionario', 'funcionario_nome', 'funcionario_matricula',
            'total_entregas_pendentes', 'criado_em'
        ]

    def get_total_entregas_pendentes(self, obj):
        return obj.entregas.filter(
            assinatura_recebimento__isnull=True,
            assinatura_imagem__isnull=True
        ).count()


class FichaEPIDetailSerializer(serializers.ModelSerializer):
    funcionario_nome = serializers.CharField(source='funcionario.nome_completo', read_only=True)
    entregas = EntregaEPISerializer(many=True, read_only=True)

    class Meta:
        model = FichaEPI
        fields = [
            'id', 'funcionario', 'funcionario_nome', 'criado_em', 
            'atualizado_em', 'entregas'
        ]


# ===================== TERMOS DE RESPONSABILIDADE =====================
class ItemTermoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemTermo
        fields = ['id', 'quantidade', 'unidade', 'item', 'ferramenta', 'mala']


class TermoListSerializer(serializers.ModelSerializer):
    responsavel_nome = serializers.CharField(source='responsavel.nome_completo', read_only=True)
    tipo_uso_display = serializers.CharField(source='get_tipo_uso_display', read_only=True)
    assinado = serializers.SerializerMethodField()

    class Meta:
        model = TermoDeResponsabilidade
        fields = [
            'id', 'contrato', 'responsavel', 'responsavel_nome',
            'data_emissao', 'tipo_uso', 'tipo_uso_display', 'assinado'
        ]

    def get_assinado(self, obj):
        return obj.is_signed()


class TermoDetailSerializer(serializers.ModelSerializer):
    responsavel_nome = serializers.CharField(source='responsavel.nome_completo', read_only=True)
    itens = ItemTermoSerializer(many=True, read_only=True)
    tipo_uso_display = serializers.CharField(source='get_tipo_uso_display', read_only=True)
    assinado = serializers.SerializerMethodField()

    class Meta:
        model = TermoDeResponsabilidade
        fields = [
            'id', 'contrato', 'responsavel', 'responsavel_nome',
            'separado_por', 'data_emissao', 'data_recebimento',
            'tipo_uso', 'tipo_uso_display', 'itens', 'assinado'
        ]

    def get_assinado(self, obj):
        return obj.is_signed()


# ===================== ASSINATURA (Genérico) =====================
class AssinaturaSerializer(serializers.Serializer):
    """Serializer para receber assinaturas em Base64."""
    assinatura_base64 = serializers.CharField(
        help_text="Imagem da assinatura codificada em Base64 (data:image/png;base64,...)."
    )

