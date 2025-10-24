# gestao_riscos/models.py
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.conf import settings
from core.managers import FilialManager
from usuario.models import Filial
from departamento_pessoal.models import Cargo, Funcionario

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
        ('PENDENTE', 'Pendente'), ('CONCLUIDA', 'Concluída'),
        ('CANCELADA', 'Cancelada'),
    ]
    
    equipamento = models.ForeignKey(
        'seguranca_trabalho.Equipamento', 
        on_delete=models.CASCADE, 
        related_name='inspecoes'
    )
    data_agendada = models.DateField(verbose_name="Data Agendada")
    data_realizacao = models.DateField(verbose_name="Data de Realização", null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    inspetor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='inspecoes_realizadas')
    observacoes = models.TextField(blank=True)
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name='inspecoes', null=True, blank=False)

    # Usando o manager padrão do Django
    objects = FilialManager()

    class Meta:
        verbose_name = "Inspeção"
        verbose_name_plural = "Inspeções"
        ordering = ['-data_agendada']

    def __str__(self):
        return f"Inspeção de {self.equipamento.nome} em {self.data_agendada}"
    
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
    
