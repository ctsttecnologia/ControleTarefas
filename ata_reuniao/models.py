from django.db import models
from django.core.validators import MinLengthValidator

class Cliente(models.Model):
    nome = models.CharField(max_length=255, validators=[MinLengthValidator(3)])
    cnpj = models.CharField(max_length=18, blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    endereco = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
    
    def __str__(self):
        return self.nome

class Funcionario(models.Model):
    nome = models.CharField(max_length=255, validators=[MinLengthValidator(3)])
    cargo = models.CharField(max_length=100)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField()
    ativo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Funcionário"
        verbose_name_plural = "Funcionários"
    
    def __str__(self):
        return f"{self.nome} ({self.cargo})"

class AtaReuniao(models.Model):
    NATUREZA_CHOICES = [
        ('Administrativa', 'Administrativa'),
        ('Comercial', 'Comercial'),
        ('Técnica', 'Técnica'),
        ('Outro', 'Outro'),
    ]
    
    STATUS_CHOICES = [
        ('Concluído', 'Concluído'),
        ('Andamento', 'Andamento'),
        ('Pendente', 'Pendente'),
        ('Cancelado', 'Cancelado'),
    ]
    
    contrato = models.ForeignKey(
        Cliente,  # Referência direta ao modelo Cliente
        on_delete=models.PROTECT, 
        verbose_name="Contrato"
    )
    coordenador = models.ForeignKey(
        Funcionario,  # Referência direta ao modelo Funcionario
        on_delete=models.PROTECT, 
        related_name='atas_coordenadas',
        verbose_name="Coordenador"
    )
    responsavel = models.ForeignKey(
        Funcionario, 
        on_delete=models.PROTECT, 
        related_name='atas_responsaveis',
        verbose_name="Responsável"
    )
    natureza = models.CharField(
        max_length=20, 
        choices=NATUREZA_CHOICES,
        verbose_name="Natureza"
    )
    acao = models.TextField(verbose_name="Ação/Proposta")
    entrada = models.DateField(verbose_name="Data de Entrada")
    prazo = models.DateField(verbose_name="Prazo", blank=True, null=True)
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES,
        default='Pendente',
        verbose_name="Status"
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ata_reuniao'    
        verbose_name = "Ata de Reunião"
        verbose_name_plural = "Atas de Reunião"
        ordering = ['-entrada']
    
    def __str__(self):
        return f"Ata {self.id} - {self.contrato} ({self.get_status_display()})"