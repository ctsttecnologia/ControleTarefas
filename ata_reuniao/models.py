# ata_reuniao/models.py 


from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone 
from django.conf import settings
from core.managers import FilialManager
from usuario.models import Filial


class AtaReuniao(models.Model):
    """
    Modelo para gerenciar as Atas de Reunião, com foco em ações e responsabilidades.
    """
    class Natureza(models.TextChoices):
        ADMINISTRATIVA = 'Administrativa', _('Administrativa')
        COMERCIAL = 'Comercial', _('Comercial')
        TECNICA = 'Técnica', _('Técnica')
        OUTRO = 'Outro', _('Outro')

    class Status(models.TextChoices):
        CONCLUIDO = 'Concluído', _('Concluído')
        ANDAMENTO = 'Andamento', _('Em Andamento')
        PENDENTE = 'Pendente', _('Pendente')
        CANCELADO = 'Cancelado', _('Cancelado')

    # --- TODOS OS CAMPOS DECLARADOS PRIMEIRO ---
    
    contrato = models.ForeignKey(
        'cliente.Cliente', 
        on_delete=models.PROTECT,
        related_name='atas',
        verbose_name=_("Contrato"),
        null=True,
    )
    coordenador = models.ForeignKey(
        'departamento_pessoal.Funcionario',
        on_delete=models.PROTECT,
        related_name='atas_coordenadas',
        verbose_name=_("Coordenador"),
        null=True,
    )
    responsavel = models.ForeignKey(
        'departamento_pessoal.Funcionario',
        on_delete=models.PROTECT,
        related_name='atas_responsaveis',
        verbose_name=_("Responsável"),
        null=True,
    )
    natureza = models.CharField(
        max_length=20,
        choices=Natureza.choices,
        default=Natureza.TECNICA,
        verbose_name=_("Natureza"),
        null=True,
    )
    titulo = models.CharField(
        max_length=50,
        verbose_name=_("Titulo"),
        help_text=_("Descreva o nome da proposta."),
        null=True,
    )
    acao = models.TextField(
        verbose_name=_("Ação/Proposta"),
        help_text=_("Descreva a ação a ser tomada ou a proposta discutida."),
        null=True,
    )
    entrada = models.DateField(
        verbose_name=_("Data de Entrada"),
        null=True,
    )
    prazo = models.DateField(
        verbose_name=_("Prazo Final"),
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDENTE,
        verbose_name=_("Status"),
        null=True,
    )
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name=_("Criado em"))
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name=_("Atualizado em"))
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name='atareuniao', null=True, blank=False)

    # Manager Padrão
    objects = FilialManager()
    # --- META CLASS DEPOIS DOS CAMPOS ---
    
    class Meta:
        db_table = 'ata_reuniao'
        verbose_name = _("Ata de Reunião")
        verbose_name_plural = _("Atas de Reunião")
        ordering = ['-entrada', '-id']
        get_latest_by = 'entrada'

    # --- MÉTODOS DEPOIS DA META CLASS ---
    
    def __str__(self):
        # Formata a data de entrada para o formato DD/MM/YYYY
        data_str = self.entrada.strftime('%d/%m/%Y') if self.entrada else 'Sem data'
        
        # Combina o ID da Ata, o Título e a Data para uma descrição clara
        return f"Ata ID:{self.id} - {self.contrato} / {self.titulo} / ({data_str})"
    
    @property
    def is_overdue(self):
        """Retorna True se a ata estiver com o prazo vencido e não finalizada."""
        if self.status in [self.Status.CONCLUIDO, self.Status.CANCELADO]:
            return False
        if self.prazo and self.prazo < timezone.now().date():
            return True
        return False

class HistoricoAta(models.Model):
    """
    Armazena um registro de cada comentário ou atualização feita em uma Ata de Reunião.
    """
    ata = models.ForeignKey(
        AtaReuniao, 
        on_delete=models.CASCADE, 
        related_name='historico',
        verbose_name=_("Ata de Reunião")
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_("Usuário")
    )
    timestamp = models.DateTimeField(
        auto_now_add=True, 
        verbose_name=_("Data e Hora")
    )
    comentario = models.TextField(
        verbose_name=_("Comentário")
    )
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name='hitoricoata', null=True, blank=False)

    # Manager Padrão
    objects = FilialManager()    

    class Meta:
        db_table = 'historico_ata'
        verbose_name = _("Histórico da Ata")
        verbose_name_plural = _("Históricos da Ata")
        ordering = ['-timestamp'] # Ordena do mais recente para o mais antigo

    def __str__(self):
        return f"Comentário em {self.ata} por {self.usuario} em {self.timestamp.strftime('%d/%m/%Y %H:%M')}"
    

class Comentario(models.Model):
    ata_reuniao = models.ForeignKey(
        'AtaReuniao', 
        on_delete=models.CASCADE,
        related_name='comentarios'
    )
    autor = models.ForeignKey(
        'usuario.Usuario', 
        on_delete=models.CASCADE,
        related_name='comentarios_ata'
    )
    # Adicione este campo:
    comentario = models.TextField() 
    
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f'Comentário de {self.autor.username} em {self.ata_reuniao.titulo}'
    

    