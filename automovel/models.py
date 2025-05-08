from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Carro(models.Model):
    placa = models.CharField(max_length=10, unique=True)
    modelo = models.CharField(max_length=50)
    marca = models.CharField(max_length=50)
    cor = models.CharField(max_length=30)
    ano = models.PositiveIntegerField()
    renavan = models.CharField(max_length=20, unique=True)
    data_ultima_manutencao = models.DateField(null=True, blank=True)
    data_proxima_manutencao = models.DateField(null=True, blank=True)
    ativo = models.BooleanField(default=True)
    observacoes = models.TextField(blank=True, null=True)
    disponivel = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.marca} {self.modelo} - {self.placa}"
    
    class Meta:
        verbose_name = "Carro"
        verbose_name_plural = "Carros"

class Agendamento(models.Model):
    STATUS_CHOICES = [
        ('agendado', 'Agendado'),
        ('em_andamento', 'Em Andamento'),
        ('finalizado', 'Finalizado'),
        ('cancelado', 'Cancelado'),
    ]
    
    funcionario = models.CharField(max_length=100)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    carro = models.ForeignKey(Carro, on_delete=models.CASCADE)
    data_hora_agenda = models.DateTimeField()
    data_hora_devolucao = models.DateTimeField(null=True, blank=True)
    cm = models.CharField(max_length=20)
    descricao = models.TextField()
    pedagio = models.BooleanField(default=False)
    abastecimento = models.BooleanField(default=False)
    km_inicial = models.PositiveIntegerField()
    km_final = models.PositiveIntegerField(null=True, blank=True)
    foto_principal = models.ImageField(upload_to='agendamentos/', null=True, blank=True)
    assinatura = models.TextField(blank=True)
    responsavel = models.CharField(max_length=100)
    ocorrencia = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='agendado')
    cancelar_agenda = models.BooleanField(default=False)
    motivo_cancelamento = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Agendamento #{self.id} - {self.carro} - {self.funcionario}"
    
    class Meta:
        verbose_name = "Agendamento"
        verbose_name_plural = "Agendamentos"

class Checklist(models.Model):
    STATUS_CHOICES = [
        ('ok', 'OK'),
        ('danificado', 'Danificado'),
        ('nao_aplicavel', 'Não Aplicável'),
    ]
    
    tipo = models.CharField(max_length=10)
    data_criacao = models.DateTimeField(default=timezone.now)
    km_inicial = models.PositiveIntegerField()
    km_final = models.PositiveIntegerField(null=True, blank=True)
    revisao_frontal_status = models.CharField(max_length=15, choices=STATUS_CHOICES)
    foto_frontal = models.ImageField(upload_to='checklists/')
    revisao_trazeira_status = models.CharField(max_length=15, choices=STATUS_CHOICES)
    foto_trazeira = models.ImageField(upload_to='checklists/')
    revisao_lado_motorista_status = models.CharField(max_length=15, choices=STATUS_CHOICES)
    foto_lado_motorista = models.ImageField(upload_to='checklists/')
    revisao_lado_passageiro_status = models.CharField(max_length=15, choices=STATUS_CHOICES)
    foto_lado_passageiro = models.ImageField(upload_to='checklists/')
    observacoes_gerais = models.TextField(blank=True, null=True)
    anexo_ocorrencia = models.TextField(blank=True, null=True)
    assinatura = models.TextField()
    confirmacao = models.BooleanField(default=False)
    agendamento = models.ForeignKey(Agendamento, on_delete=models.CASCADE, related_name='checklists')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"Checklist #{self.id} - {self.agendamento}"
    
    class Meta:
        verbose_name = "Checklist"
        verbose_name_plural = "Checklists"

class Foto(models.Model):
    imagem = models.ImageField(upload_to='fotos/')
    data_criacao = models.DateTimeField(default=timezone.now)
    observacao = models.TextField(blank=True, null=True)
    agendamento = models.ForeignKey(Agendamento, on_delete=models.CASCADE, related_name='fotos')
    
    def __str__(self):
        return f"Foto #{self.id} - {self.agendamento}"
    
    class Meta:
        verbose_name = "Foto"
        verbose_name_plural = "Fotos"

