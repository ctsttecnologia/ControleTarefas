# gestao_riscos/models.py
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

class Incidente(models.Model):
    """Registra qualquer ocorrência ou incidente de segurança."""
    SETORES_CHOICES = [
        ('PRODUCAO_A', 'Produção A'),
        ('PRODUCAO_B', 'Produção B'),
        ('LOGISTICA', 'Logística'),
        ('MANUTENCAO', 'Manutenção'),
        ('ADM', 'Administrativo'),
        ('OUTRO', 'Outro'),
    ]

    CAUSA_CHOICES = [
        ('FALHA_EPI', 'Falha de EPI'),
        ('ATO_INSEGURO', 'Ato Inseguro do Colaborador'),
        ('CONDICAO_INSEGURA', 'Condição Insegura do Ambiente'),
        ('FALHA_EPC', 'Falha de Equipamento Coletivo'),
        ('FALTA_TREINAMENTO', 'Falta de Treinamento'),
        ('OUTRA', 'Outra'),
    ]
    
    
    TIPO_INCIDENTE_CHOICES = [
        ('QUASE_ACIDENTE', 'Quase Acidente'),
        ('COM_AFASTAMENTO', 'Com Afastamento'),
        ('SEM_AFASTAMENTO', 'Sem Afastamento'),
        ('AMBIENTAL', 'Incidente Ambiental'),
    ]

    descricao = models.CharField(max_length=255, verbose_name="Título do Incidente")
    detalhes = models.TextField(verbose_name="Detalhes da Ocorrência")
    setor = models.CharField(max_length=20, choices=SETORES_CHOICES, verbose_name="Setor")
    tipo_incidente = models.CharField(max_length=20, choices=TIPO_INCIDENTE_CHOICES, verbose_name="Tipo")
    data_ocorrencia = models.DateTimeField(default=timezone.now, verbose_name="Data e Hora da Ocorrência")
    registrado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='incidentes_registrados')
    causa_provavel = models.CharField(max_length=30, choices=CAUSA_CHOICES, null=True, blank=True)

    
    class Meta:
        verbose_name = "Incidente"
        verbose_name_plural = "Incidentes"
        ordering = ['-data_ocorrencia']

    def __str__(self):
        return self.descricao


class Inspecao(models.Model):
    """Agenda e registra inspeções de segurança."""
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('EM_ANDAMENTO', 'Em Andamento'),
        ('CONCLUIDA', 'Concluída'),
        ('CANCELADA', 'Cancelada'),
    ]

    equipamento = models.ForeignKey(
       'seguranca_trabalho.equipamento', 
        on_delete=models.CASCADE, 
        related_name='inspecoes'
    )
    data_agendada = models.DateField(verbose_name="Data Agendada")
    data_realizacao = models.DateField(verbose_name="Data de Realização", null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    inspetor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='inspecoes_realizadas')
    observacoes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Inspeção"
        verbose_name_plural = "Inspeções"
        ordering = ['-data_agendada']

    def __str__(self):
        return f"Inspeção de {self.equipamento.nome} em {self.data_agendada}"
    
