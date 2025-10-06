
# automovel/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from core.managers import FilialManager
from usuario.models import Filial

# 1. CLASSE BASE ABSTRATA
# Centraliza a lógica de filial que se repete em todos os modelos.
# Isso resolve o erro de coluna duplicada e limpa o código.
class BaseFilialModel(models.Model):
    """Um modelo abstrato que adiciona o campo 'filial' e o manager padrão."""
    # O related_name com '%(class)s_set' cria um nome reverso único automaticamente
    # Ex: para Carro, será 'carro_set'; para Agendamento, 'agendamento_set'
    filial = models.ForeignKey(
        Filial, 
        on_delete=models.PROTECT, 
        related_name='%(class)s_set'
    )
    objects = FilialManager()

    class Meta:
        abstract = True

# 2. MODELO CARRO ATUALIZADO
class Carro(BaseFilialModel):
    placa = models.CharField(max_length=10, unique=True)
    modelo = models.CharField(max_length=50)
    marca = models.CharField(max_length=50)
    cor = models.CharField(max_length=30)
    ano = models.PositiveIntegerField()
    renavan = models.CharField(max_length=20, unique=True)
    # 2.1 - Adicionado campo de quilometragem para a lógica do Checklist funcionar
    quilometragem = models.PositiveIntegerField(default=0, verbose_name="Quilometragem")
    data_ultima_manutencao = models.DateField(null=True, blank=True)
    data_proxima_manutencao = models.DateField(null=True, blank=True)
    ativo = models.BooleanField(default=True)
    observacoes = models.TextField(blank=True, null=True)
    disponivel = models.BooleanField(default=True)
    foto = models.ImageField(
        upload_to='carros/fotos/', 
        null=True, 
        blank=True, 
        verbose_name="Foto do Carro"
    )
    # 2.2 - Removido 'filial' e 'objects', que agora vêm de BaseFilialModel
    # CORREÇÃO: O default de uma ForeignKey não deve ser uma string como 'CETEST-SP'.
    # Isso deve ser tratado na lógica da sua view ou serializer ao criar um objeto.

    def __str__(self):
        return f"{self.marca} {self.modelo} - {self.placa}"

    class Meta:
        db_table = 'carro'
        verbose_name = "Carro"
        verbose_name_plural = "Carros"
        ordering = ['marca', 'modelo']

class Agendamento(BaseFilialModel):
    STATUS_CHOICES = [
        ('agendado', 'Agendado'),
        ('em_andamento', 'Em Andamento'),
        ('finalizado', 'Finalizado'),
        ('cancelado', 'Cancelado'),
    ]

    funcionario = models.CharField(max_length=100)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    carro = models.ForeignKey(Carro, on_delete=models.PROTECT, related_name='agendamentos')
    data_hora_agenda = models.DateTimeField()
    data_hora_devolucao = models.DateTimeField()
    cm = models.CharField(max_length=4, verbose_name="CM/Contrato")
    descricao = models.TextField()
    pedagio = models.BooleanField(default=False)
    abastecimento = models.BooleanField(default=False)
    km_inicial = models.PositiveIntegerField()
    km_final = models.PositiveIntegerField(null=True, blank=True)
    foto_principal = models.ImageField(upload_to='agendamentos/', null=True, blank=True)
    assinatura = models.TextField(blank=True, null=True, verbose_name="Assinatura Digital")
    responsavel = models.CharField(max_length=100)
    ocorrencia = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='agendado')
    cancelar_agenda = models.BooleanField(default=False)
    motivo_cancelamento = models.TextField(blank=True, null=True)
    # Removido 'filial' e 'objects'

    def __str__(self):
        return f"Agendamento #{self.id} - {self.carro.placa} para {self.funcionario}"

    class Meta:
        db_table = 'agendamento'
        verbose_name = "Agendamento"
        verbose_name_plural = "Agendamentos"
        ordering = ['-data_hora_agenda']

    @property
    def checklist_saida(self):
        return self.checklists.filter(tipo='saida').first()

    @property
    def checklist_retorno(self):
        return self.checklists.filter(tipo='retorno').first()

class Checklist(BaseFilialModel):
    TIPO_CHOICES = [('saida', 'Saída'), ('retorno', 'Retorno'), ('vistoria', 'Vistoria')]
    STATUS_CHOICES = [('ok', 'OK'), ('danificado', 'Danificado'), ('nao_aplicavel', 'Não Aplicável')]

    agendamento = models.ForeignKey(Agendamento, on_delete=models.CASCADE, related_name='checklists')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    data_hora = models.DateTimeField(default=timezone.now, verbose_name="Data/Hora")
    # Removido km_inicial e km_final, pois já existem no agendamento.
    # O ideal é capturá-los na interface e passá-los para o agendamento ao salvar.
    revisao_frontal_status = models.CharField(max_length=15, choices=STATUS_CHOICES)
    foto_frontal = models.ImageField(upload_to='checklist/frontal/', validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])])
    revisao_trazeira_status = models.CharField(max_length=15, choices=STATUS_CHOICES)
    foto_trazeira = models.ImageField(upload_to='checklist/trazeira/', validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])])
    revisao_lado_motorista_status = models.CharField(max_length=15, choices=STATUS_CHOICES)
    foto_lado_motorista = models.ImageField(upload_to='checklist/lado_motorista/', validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])])
    revisao_lado_passageiro_status = models.CharField(max_length=15, choices=STATUS_CHOICES)
    foto_lado_passageiro = models.ImageField(upload_to='checklist/lado_passageiro/', validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])])
    observacoes_gerais = models.TextField(blank=True, null=True)
    anexo_ocorrencia = models.TextField(blank=True, null=True)
    assinatura = models.TextField(blank=True, null=True, verbose_name="Assinatura Digital")
    confirmacao = models.BooleanField(default=False)
    # Removido 'filial' e 'objects'

    # 3. MÉTODO SAVE CORRIGIDO E REATORADO
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)  # Salva o checklist primeiro

        if is_new:
            agendamento = self.agendamento
            
            if self.tipo == 'saida':
                agendamento.status = 'em_andamento'
                agendamento.save(update_fields=['status'])
            
            elif self.tipo == 'retorno':
                carro = agendamento.carro
                agendamento.status = 'finalizado'
                
                # Assume que o KM final é passado para o agendamento no momento do checklist
                if agendamento.km_final:
                    carro.quilometragem = agendamento.km_final
                    carro.save(update_fields=['quilometragem'])
                
                agendamento.save(update_fields=['status'])

    def __str__(self):
        return f"Checklist ({self.get_tipo_display()}) para Agendamento #{self.agendamento.id}"

    class Meta:
        db_table = 'checklist'
        verbose_name = "Checklist"
        verbose_name_plural = "Checklists"
        ordering = ['-data_hora']
        unique_together = ('agendamento', 'tipo')

class Foto(BaseFilialModel):
    agendamento = models.ForeignKey(Agendamento, on_delete=models.CASCADE, related_name='fotos_agendamento')
    imagem = models.ImageField(upload_to='fotos/')
    data_criacao = models.DateTimeField(default=timezone.now)
    observacao = models.TextField(blank=True, null=True)
    # Removido 'filial' e 'objects'
    # 4. CORREÇÃO DE related_name: alterado o related_name de 'fotos' em agendamento
    # para 'fotos_agendamento' para evitar conflito com o que BaseFilialModel gera.

    def __str__(self):
        return f"Foto #{self.id} - {self.agendamento}"

    class Meta:
        db_table = 'foto'
        verbose_name = "Foto"
        verbose_name_plural = "Fotos"
        ordering = ['-data_criacao']
        unique_together = ('agendamento', 'imagem')
        

