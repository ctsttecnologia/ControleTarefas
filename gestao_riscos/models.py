# gestao_riscos/models.py
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.conf import settings # Usado para referenciar o modelo de Filial
from core.managers import FilialManager
from usuario.models import Filial

User = get_user_model()

# -----------------------------------------------------------------------------
# MANAGER CUSTOMIZADO PARA FILTRAGEM DE FILIAL
# -----------------------------------------------------------------------------
class FilialScopedManager(models.Manager):
    """
    Manager que adiciona um método para filtrar querysets pela filial do usuário
    armazenada na request.
    """
    def for_request(self, request):
        qs = self.get_queryset()
        # Se o usuário estiver logado e tiver o atributo 'filial'
        if request.user.is_authenticated and hasattr(request.user, 'filial'):
            return qs.filter(filial=request.user.filial)
        # Se não, retorna uma queryset vazia para não vazar dados.
        return qs.none()

# -----------------------------------------------------------------------------
# MODELOS ATUALIZADOS
# -----------------------------------------------------------------------------

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
    
    # --- CAMPO NOVO E ESSENCIAL ---
    # Supondo que você tenha um modelo de Filial em outro app.
    # Se o modelo Filial estiver no mesmo app, mude para 'Filial'.

    descricao = models.CharField(max_length=255, verbose_name="Título do Incidente")
    detalhes = models.TextField(verbose_name="Detalhes da Ocorrência")
    setor = models.CharField(max_length=20, choices=SETORES_CHOICES, verbose_name="Setor")
    tipo_incidente = models.CharField(max_length=20, choices=TIPO_INCIDENTE_CHOICES, verbose_name="Tipo")
    data_ocorrencia = models.DateTimeField(default=timezone.now, verbose_name="Data e Hora da Ocorrência")
    registrado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='incidentes_registrados')
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name='incidentes', null=True, blank=False)

    # Manager Padrão
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
        ('PENDENTE', 'Pendente'),
        ('CONCLUIDA', 'Concluída'),
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

    # Manager Padrão
    objects = FilialManager()

    class Meta:
        verbose_name = "Inspeção"
        verbose_name_plural = "Inspeções"
        ordering = ['-data_agendada']

    def __str__(self):
        return f"Inspeção de {self.equipamento.nome} em {self.data_agendada}"
    
