# gestao_riscos/models.py
from django.db import models
from django.urls import reverse_lazy
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.conf import settings
from core.managers import FilialManager
from usuario.models import Filial
from departamento_pessoal.models import Cargo, Funcionario
from django.utils.translation import gettext_lazy as _
from seguranca_trabalho.models import Equipamento, EntregaEPI

User = get_user_model()


class Incidente(models.Model):
    """Registra qualquer ocorrência ou incidente de segurança."""
    SETORES_CHOICES = [
        ('OPERAÇAO', 'Operação'),
        ('LOGISTICA', 'Logística'),
        ('MANUTENCAO', 'Manutenção'),
        ('ADMINISTRACAO', 'Administração'),
    ]
    TIPO_INCIDENTE_CHOICES = [
        ('QUASE_ACIDENTE', 'Quase Acidente'),
        ('COM_AFASTAMENTO', 'Com Afastamento'),
        ('SEM_AFASTAMENTO', 'Sem Afastamento'),
    ]
    
    descricao = models.CharField(max_length=255, verbose_name="Título do Incidente")
    detalhes = models.TextField(verbose_name="Detalhes da Ocorrência")
    setor = models.CharField(max_length=20, choices=SETORES_CHOICES, verbose_name="Setor")
    tipo_incidente = models.CharField(max_length=20, choices=TIPO_INCIDENTE_CHOICES, verbose_name="Tipo")
    data_ocorrencia = models.DateTimeField(default=timezone.now, verbose_name="Data e Hora da Ocorrência")
    registrado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='incidentes_registrados')
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name='incidentes', null=True, blank=False)

    objects = FilialManager()

    class Meta:
        verbose_name = "Incidente"
        verbose_name_plural = "Incidentes"
        ordering = ['-data_ocorrencia']

    def __str__(self):
        return self.descricao


class Inspecao(models.Model):
    """Agenda e registra inspeções de segurança."""
    STATUS_CHOICES = [
        ('PENDENTE_APROVACAO', _('Pendente de Aprovação')), # NOVO STATUS
        ('PENDENTE', _('Pendente')),
        ('CONCLUIDA', _('Concluída')),
        ('CANCELADA', _('Cancelada')),
    ]
    
    # MODIFICADO: Torna-se opcional, pois pode ser preenchido via entrega_epi
    equipamento = models.ForeignKey(
        'seguranca_trabalho.Equipamento', 
        on_delete=models.SET_NULL, 
        related_name='inspecoes',
        null=True, blank=True # Agora é opcional
    )
    
    # NOVO CAMPO: Vincula a inspeção a um item de EPI específico
    entrega_epi = models.ForeignKey(
        'seguranca_trabalho.EntregaEPI',
        on_delete=models.CASCADE,
        related_name='inspecoes',
        null=True, blank=True,
        verbose_name=_("Item de EPI Específico")
    )
    
    data_agendada = models.DateField(verbose_name="Data Agendada")
    data_realizacao = models.DateField(verbose_name="Data de Realização", null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    
    # MODIFICADO: 'inspetor' -> 'responsavel' e 'blank=True'
    # Isso corrige a inconsistência com seu TecnicoScopeMixin na view do dashboard
    responsavel = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, blank=True, # Tornar opcional
        related_name='inspecoes_realizadas'
    )
    observacoes = models.TextField(blank=True)
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name='inspecoes', null=True, blank=False)

    objects = FilialManager()

    class Meta:
        verbose_name = "Inspeção"
        verbose_name_plural = "Inspeções"
        ordering = ['-data_agendada']

    def __str__(self):
        # Atualiza o __str__ para a nova lógica
        if self.entrega_epi:
            return f"Inspeção de {self.entrega_epi} em {self.data_agendada}"
        if self.equipamento:
            return f"Inspeção de {self.equipamento.nome} em {self.data_agendada}"
        return f"Inspeção (ID: {self.id}) em {self.data_agendada}"
        
    def save(self, *args, **kwargs):
        """
        Sobrescreve o save para auto-popular equipamento e filial 
        se a entrega_epi for fornecida.
        """
        if self.entrega_epi:
            if not self.equipamento_id: # _id para evitar fetch
                self.equipamento = self.entrega_epi.equipamento
            if not self.filial_id:
                self.filial = self.entrega_epi.filial
        
        # Garante que um dos dois campos está preenchido
        if not self.equipamento_id and not self.entrega_epi_id:
            raise ValueError("A inspeção deve estar ligada a um Equipamento ou a uma Entrega de EPI.")
            
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        # Adiciona um URL (será usado no calendário)
        return reverse_lazy('gestao_riscos:inspecao_detalhe', kwargs={'pk': self.pk})
    
class CartaoTag(models.Model):
    """
    Representa um Cartão de Bloqueio (Tag de Perigo) individual para um funcionário.
    """
    funcionario = models.ForeignKey(
        Funcionario,
        on_delete=models.CASCADE,
        related_name='cartoes_tag',
        verbose_name="Funcionário Proprietário"
    )
    cargo = models.ForeignKey(
        Cargo,
        on_delete=models.CASCADE,
        related_name='cartoes_tag',
        verbose_name="Cargo", 
        null=True, 
        blank=True, 
        default=None,
    )
    fone = models.CharField(
        max_length=20,
        default="(11) 3045-9400",
        verbose_name="Telefone de Contato"
    )
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_validade = models.DateField(verbose_name="Data de Validade", null=True, blank=True)
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name='cartoes_tag'
    )

    objects = FilialManager() # Usando o manager padrão

    class Meta:
        verbose_name = "Cartão de Bloqueio (Tag)"
        verbose_name_plural = "Cartões de Bloqueio (Tags)"
        ordering = ['-data_criacao']

    def __str__(self):
        return f"Cartão de {self.funcionario.nome_completo}"
