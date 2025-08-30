
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField 
from core.models import BaseModel
from usuario.models import Filial
import os
from uuid import uuid4
from departamento_pessoal.models import Funcionario

from core.encryption import encrypt_data, decrypt_data


class BaseModel(models.Model):
    """
    Um modelo base abstrato que fornece campos de data de criação
    e atualização automáticos.
    """
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        # Isso garante que este modelo não crie sua própria tabela no banco de dados.
        # Ele serve apenas para ser herdado por outros modelos.
        abstract = True
        ordering = ['-criado_em']


class Marca(BaseModel):
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome da Marca")

    class Meta:
        verbose_name = "Marca"
        verbose_name_plural = "Marcas"
        ordering = ['nome']

    def __str__(self):
        return self.nome

class Modelo(BaseModel):
    marca = models.ForeignKey(Marca, on_delete=models.PROTECT, related_name="modelos")
    nome = models.CharField(max_length=150, verbose_name="Nome do Modelo")

    class Meta:
        verbose_name = "Modelo de Aparelho"
        verbose_name_plural = "Modelos de Aparelhos"
        unique_together = ('marca', 'nome')
        ordering = ['marca__nome', 'nome']

    def __str__(self):
        return f"{self.marca.nome} {self.nome}"

class Aparelho(BaseModel):
    STATUS_CHOICES = (
        ('disponivel', 'Disponível'),
        ('em_uso', 'Em Uso'),
        ('manutencao', 'Em Manutenção'),
        ('descartado', 'Descartado'),
    )
    modelo = models.ForeignKey(Modelo, on_delete=models.PROTECT, related_name="aparelhos")
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name="aparelhos")
    
    # 1. Este é o campo REAL no banco de dados.
    # Ele armazena o IMEI criptografado. Não o mostramos no admin.
    encrypted_imei = models.CharField(
        max_length=255, # Aumente o tamanho para acomodar o texto criptografado
        blank=True,
        null=True,
        verbose_name="IMEI Criptografado",
        editable=False # Impede que seja editado diretamente no admin
    )
    
    numero_serie = models.CharField(max_length=100, unique=True, blank=True, null=True, verbose_name="Número de Série")
    data_aquisicao = models.DateField(blank=True, null=True, verbose_name="Data de Aquisição")    
    valor_aquisicao = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Valor de Aquisição")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='disponivel', verbose_name="Status")
    observacoes = models.TextField(blank=True, null=True, verbose_name="Observações")

    class Meta:
        verbose_name = "Aparelho Telefônico"
        verbose_name_plural = "Aparelhos Telefônicos"
        ordering = ['modelo__marca__nome', 'modelo__nome']

    @property
    def imei(self):
        """Este 'getter' descriptografa o dado quando você acessa `aparelho.imei`."""
        return decrypt_data(self.encrypted_imei)

    @imei.setter
    def imei(self, value: str):
        """Este 'setter' criptografa o dado quando você faz `aparelho.imei = 'novo_valor'`."""
        self.encrypted_imei = encrypt_data(value)

    class Meta:
        verbose_name = "Aparelho Telefônico"
        verbose_name_plural = "Aparelhos Telefônicos"
        ordering = ['modelo__marca__nome', 'modelo__nome']

    def __str__(self):
        # Usamos a propriedade 'imei' aqui, então o valor será descriptografado
        return f"{self.modelo} (IMEI: {self.imei or 'N/A'})"


class Operadora(BaseModel):
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome da Operadora")

    class Meta:
        verbose_name = "Operadora"
        verbose_name_plural = "Operadoras"
        ordering = ['nome']

    def __str__(self):
        return self.nome

class Plano(BaseModel):
    operadora = models.ForeignKey(Operadora, on_delete=models.PROTECT, related_name="planos")
    nome = models.CharField(max_length=150, verbose_name="Nome do Plano")
    valor_mensal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor Mensal")
    franquia_dados_gb = models.PositiveIntegerField(verbose_name="Franquia de Dados (GB)")
    
    class Meta:
        verbose_name = "Plano de Telefonia"
        verbose_name_plural = "Planos de Telefonia"
        unique_together = ('operadora', 'nome')
        ordering = ['operadora__nome', 'nome']

    def __str__(self):
        return f"{self.operadora.nome} - {self.nome}"

class LinhaTelefonica(BaseModel):
    STATUS_CHOICES = (
        ('disponivel', 'Disponível'),
        ('ativa', 'Ativa (Em Uso)'),
        ('bloqueada', 'Bloqueada'),
        ('cancelada', 'Cancelada'),
    )
    plano = models.ForeignKey(Plano, on_delete=models.PROTECT, related_name="linhas")
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name="linhas")

    # <--- MUDANÇA: CharField para PhoneNumberField para validação e formatação
    numero = PhoneNumberField(unique=True, verbose_name="Número da Linha")

    
    data_ativacao = models.DateField(verbose_name="Data de Ativação")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='disponivel')
    # ... (Meta sem alterações) ...
    def __str__(self):
        return str(self.numero)

    def termo_upload_path(instance, filename):
        ext = filename.split('.')[-1]
        # <--- MUDANÇA: Salva dentro de SENDFILE_ROOT (private_media)
        return os.path.join('termos', f'{uuid4().hex}.{ext}')

    # ... o resto do arquivo (função termo_upload_path, modelo Vinculo e signals) permanece igual ...
    def termo_upload_path(instance, filename):
        """Gera um caminho seguro e não adivinhável para o termo."""
        ext = filename.split('.')[-1]
        return os.path.join('termos', f'{uuid4().hex}.{ext}')

def termo_upload_path(instance, filename):
    """Gera um caminho seguro e não adivinhável para o termo."""
    ext = filename.split('.')[-1]
    return os.path.join('termos', f'{uuid4().hex}.{ext}')

class Vinculo(BaseModel):
    STATUS_CHOICES = (
        ('ativo', 'Ativo'),
        ('finalizado', 'Finalizado'),
    )
    funcionario = models.ForeignKey(Funcionario, on_delete=models.PROTECT, related_name="vinculos_telefonicos", verbose_name="Colaborador")
    aparelho = models.ForeignKey(Aparelho, on_delete=models.PROTECT, related_name="vinculos", blank=True, null=True, verbose_name="Aparelho")
    linha = models.ForeignKey(LinhaTelefonica, on_delete=models.PROTECT, related_name="vinculos", blank=True, null=True, verbose_name="Linha Telefônica")
    data_entrega = models.DateField(verbose_name="Data de Entrega")
    data_devolucao = models.DateField(blank=True, null=True, verbose_name="Data de Devolução")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ativo')
    termo_responsabilidade = models.FileField(upload_to=termo_upload_path, blank=True, null=True, verbose_name="Termo de Responsabilidade Assinado")
    # ... (Meta e __str__ sem alterações) ...

    def save(self, *args, **kwargs):
        """
        <--- MUDANÇA: A lógica do signal foi movida para cá.
        Isso garante que as atualizações de status ocorram de forma mais previsível
        e dentro da mesma transação do banco de dados.
        """
        # Rastreia o estado original do objeto
        is_new = self._state.adding
        original_status = None
        if not is_new:
            original = Vinculo.objects.get(pk=self.pk)
            original_status = original.status

        # Lógica para finalizar o vínculo se a data de devolução for preenchida
        if self.data_devolucao and self.status == 'ativo':
            self.status = 'finalizado'
        
        super().save(*args, **kwargs) # Salva o vínculo primeiro

        # Se o vínculo foi criado como ATIVO
        if is_new and self.status == 'ativo':
            if self.aparelho:
                self.aparelho.status = 'em_uso'
                self.aparelho.save()
            if self.linha:
                self.linha.status = 'ativa'
                self.linha.save()
        
        # Se o status do vínculo MUDOU para FINALIZADO
        elif self.status == 'finalizado' and original_status != 'finalizado':
            if self.aparelho:
                self.aparelho.status = 'disponivel'
                self.aparelho.save()
            if self.linha:
                self.linha.status = 'disponivel'
                self.linha.save()


