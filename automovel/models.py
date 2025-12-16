
# automovel/models.py

from django import forms
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from core.managers import FilialManager
from usuario.models import Filial
from datetime import date


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

    @property
    def status_manutencao(self):
        """
        Retorna o status da próxima manutenção.
        Formato: (chave, 'Mensagem para o usuário', 'cor_bootstrap')
        """
        if not self.data_proxima_manutencao:
            return ('indefinido', 'Sem data de próxima manutenção definida', 'secondary')

        hoje = date.today()
        diferenca = self.data_proxima_manutencao - hoje
        dias_restantes = diferenca.days
        
        # 1. Manutenção Vencida
        if dias_restantes < 0:
            return ('vencido', f'Manutenção vencida há {-dias_restantes} dias!', 'danger')
        
        # 2. Alerta de Proximidade (ex: 30 dias ou menos)
        elif 0 <= dias_restantes <= 30:
            if dias_restantes == 0:
                return ('proximo', 'Manutenção vence hoje!', 'warning')
            elif dias_restantes == 1:
                return ('proximo', 'Manutenção vence amanhã!', 'warning')
            else:
                return ('proximo', f'Manutenção vence em {dias_restantes} dias.', 'warning')

        # 3. Manutenção em Dia
        else:
            return ('ok', 'Manutenção em dia', 'success')

    def __str__(self):
        return f"{self.marca} {self.modelo} - {self.placa}"

    class Meta:
        db_table = 'carro'
        verbose_name = "Carro"
        verbose_name_plural = "Carros"
        ordering = ['marca', 'modelo']

class Carro_agendamento(BaseFilialModel):
    STATUS_CHOICES = [
        ('agendado', 'Agendado'),
        ('em_andamento', 'Em Andamento'),
        ('finalizado', 'Finalizado'),
        ('manutencao', 'Em Manutenção'),
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
        db_table = 'carro_agendamento'
        verbose_name = "Agendamento"
        verbose_name_plural = "Agendamentos"
        ordering = ['-data_hora_agenda']

    @property
    def checklist_saida(self):
        return self.checklists.filter(tipo='saida').first()

    @property
    def checklist_retorno(self):
        return self.checklists.filter(tipo='retorno').first()

class Carro_checklist(BaseFilialModel):
    TIPO_CHOICES = [('saida', 'Saída'), ('retorno', 'Retorno'), ('vistoria', 'Vistoria')]
    STATUS_CHOICES = [('ok', 'OK'), ('danificado', 'Danificado'), ('nao_aplicavel', 'Não Aplicável')]

    agendamento = models.ForeignKey(Carro_agendamento, on_delete=models.CASCADE, related_name='checklists')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    data_hora = models.DateTimeField(default=timezone.now, verbose_name="Data/Hora")
    
    revisao_frontal_status = models.CharField(max_length=15, choices=STATUS_CHOICES)
    foto_frontal = models.ImageField(upload_to='checklist/frontal/', validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])])
    
    revisao_trazeira_status = models.CharField(max_length=15, choices=STATUS_CHOICES)
    foto_trazeira = models.ImageField(upload_to='checklist/trazeira/', validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])])
    
    revisao_lado_motorista_status = models.CharField(max_length=15, choices=STATUS_CHOICES)
    foto_lado_motorista = models.ImageField(upload_to='checklist/lado_motorista/', validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])])
    
    revisao_lado_passageiro_status = models.CharField(max_length=15, choices=STATUS_CHOICES)
    foto_lado_passageiro = models.ImageField(upload_to='checklist/lado_passageiro/', validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])])
    
    observacoes_gerais = models.TextField(blank=True, null=True)
    assinatura = models.TextField(blank=True, null=True, verbose_name="Assinatura Digital")
    confirmacao = models.BooleanField(default=False)


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
        db_table = 'carro_checklist'
        verbose_name = "Checklist"
        verbose_name_plural = "Checklists"
        ordering = ['-data_hora']
        unique_together = ('agendamento', 'tipo')

class Carro_foto(BaseFilialModel):
    agendamento = models.ForeignKey(Carro_agendamento, on_delete=models.CASCADE, related_name='fotos_agendamento')
    imagem = models.ImageField(upload_to='fotos/')
    data_criacao = models.DateTimeField(default=timezone.now)
    observacao = models.TextField(blank=True, null=True)
    # Removido 'filial' e 'objects'
    # 4. CORREÇÃO DE related_name: alterado o related_name de 'fotos' em agendamento
    # para 'fotos_agendamento' para evitar conflito com o que BaseFilialModel gera.

    def __str__(self):
        return f"Foto #{self.id} - {self.agendamento}"

    class Meta:
        db_table = 'carro_foto'
        verbose_name = "Foto"
        verbose_name_plural = "Fotos"
        ordering = ['-data_criacao']
        unique_together = ('agendamento', 'imagem')
        
class Carro_rastreamento(BaseFilialModel):
    agendamento = models.ForeignKey(Carro_agendamento, on_delete=models.CASCADE, related_name='rastreamentos')
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    velocidade = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    data_hora = models.DateTimeField(default=timezone.now)
    endereco_aproximado = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'carro_rastreamento'
        verbose_name = "Rastreamento"
        verbose_name_plural = "Rastreamentos"
        ordering = ['-data_hora']

class Carro_manutencao(BaseFilialModel):
    TIPO_CHOICES = [
        ('preventiva', 'Preventiva'),
        ('corretiva', 'Corretiva'),
        ('pneu', 'Troca de Pneus'),
        ('oleo', 'Troca de Óleo'),
        ('freio', 'Sistema de Freio'),
        ('outros', 'Outros'),
    ]
    
    carro = models.ForeignKey(Carro, on_delete=models.CASCADE, related_name='manutencoes')
    data_manutencao = models.DateField()
    data_agendamento = models.DateTimeField(default=timezone.now)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    descricao = models.TextField()
    custo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    concluida = models.BooleanField(default=False)
    observacoes = models.TextField(blank=True, null=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        db_table = 'carro_manutencao'
        verbose_name = "Manutenção"
        verbose_name_plural = "Manutenções"
        ordering = ['-data_manutencao']

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        
        # Atualizar datas de manutenção do carro se esta for concluída
        if self.concluida and self.carro:
            self.carro.data_ultima_manutencao = self.data_manutencao
            # Calcular próxima manutenção (ex: 6 meses depois)
            from dateutil.relativedelta import relativedelta
            self.carro.data_proxima_manutencao = self.data_manutencao + relativedelta(months=+6)
            self.carro.save(update_fields=['data_ultima_manutencao', 'data_proxima_manutencao'])

    def __str__(self):
        return f"Manutenção {self.get_tipo_display()} - {self.carro.placa} - {self.data_manutencao}"
    
class ManutencaoForm(forms.ModelForm):
    class Meta:
        model = Carro_manutencao
        fields = ['data_manutencao', 'tipo', 'descricao', 'custo', 'concluida', 'observacoes']
        widgets = {
            'data_manutencao': forms.DateInput(attrs={'type': 'date'}),
            'descricao': forms.Textarea(attrs={'rows': 3}),
            'observacoes': forms.Textarea(attrs={'rows': 2}),
        }
    
    def clean_data_manutencao(self):
        data_manutencao = self.cleaned_data.get('data_manutencao')
        if data_manutencao and data_manutencao < timezone.now().date():
            raise forms.ValidationError("A data da manutenção não pode ser no passado.")
        return data_manutencao
    

    