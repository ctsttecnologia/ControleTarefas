
import os
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import User
from uuid import uuid4
from phonenumber_field.modelfields import PhoneNumberField
from django.db import models
from django.urls import reverse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from departamento_pessoal.models import Funcionario
from usuario.models import Filial
from core.managers import FilialManager
from notifications.models import Notificacao
from encrypted_model_fields.fields import EncryptedCharField


# ==============================================================================
# Modelos Base e Funções Utilitárias
# ==============================================================================

class BaseModel(models.Model):
    """
    Um modelo base abstrato que fornece campos de data de criação
    e atualização automáticos.
    """
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        abstract = True
        ordering = ['-criado_em']


def termo_upload_path(instance, filename):
    """
    Gera um caminho seguro e não adivinhável para o termo.
    """
    ext = filename.split('.')[-1]
    return os.path.join('termos', f'{uuid4().hex}.{ext}')


# ==============================================================================
# Modelos de Configuração (Marca, Modelo, Operadora, Plano)
# ==============================================================================

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


# ==============================================================================
# Modelos Principais (Aparelho, Linha, Vinculo)
# ==============================================================================

class Aparelho(BaseModel):
    STATUS_CHOICES = (
        ('disponivel', 'Disponível'),
        ('em_uso', 'Em Uso'),
        ('manutencao', 'Em Manutenção'),
        ('descartado', 'Descartado'),
    )

    APARELHO_TIPO_CHOICES = (
        ('smartphone', 'Smartphone'),
        ('tablet', 'Tablet'),
        ('radio_ht', 'Rádio HT'),
        ('notebook', 'Notebook'),
        ('outro', 'Outro'),
    )
    tipo_de_aparelho = models.CharField(max_length=30, choices=APARELHO_TIPO_CHOICES, default='smartphone', verbose_name="Tipo de Aparelho")
    modelo = models.ForeignKey(Modelo, on_delete=models.PROTECT, related_name="aparelhos")
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name="aparelhos")

    # encrypted_imei = models.CharField(max_length=255, blank=True, null=True, verbose_name="IMEI Criptografado", editable=False)
    numero_serie = models.CharField(max_length=100, unique=True, blank=True, null=True, verbose_name="Número de Série")
    data_aquisicao = models.DateField(blank=True, null=True, verbose_name="Data de Aquisição")
    valor_aquisicao = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Valor de Aquisição")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='disponivel', verbose_name="Status")
    observacoes = models.TextField(blank=True, null=True, verbose_name="Observações")
    acessorios = models.TextField(blank=True, null=True, verbose_name="Acessórios Incluídos")
    imei = EncryptedCharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name="IMEI"
    )

    class Meta:
        verbose_name = "Aparelho Telefônico"
        verbose_name_plural = "Aparelhos Telefônicos"
        ordering = ['modelo__marca__nome', 'modelo__nome']

    def __str__(self):
        return f"{self.modelo} (IMEI: {self.imei or 'N/A'})"


class LinhaTelefonica(BaseModel):
    STATUS_CHOICES = (
        ('disponivel', 'Disponível'),
        ('ativa', 'Ativa (Em Uso)'),
        ('bloqueada', 'Bloqueada'),
        ('cancelada', 'Cancelada'),
    )
    plano = models.ForeignKey(Plano, on_delete=models.PROTECT, related_name="linhas")
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name="linhas")
    numero = PhoneNumberField(unique=True, verbose_name="Número da Linha")
    data_ativacao = models.DateField(verbose_name="Data de Ativação")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='disponivel')

    def __str__(self):
        return str(self.numero)


class Vinculo(BaseModel):
    STATUS_CHOICES = (
        ('ativo', 'Ativo'),
        ('finalizado', 'Finalizado'),
    )
    funcionario = models.ForeignKey(Funcionario, on_delete=models.PROTECT)
    aparelho = models.ForeignKey(Aparelho, on_delete=models.PROTECT, related_name="vinculos", blank=True, null=True, verbose_name="Aparelho")
    linha = models.ForeignKey(LinhaTelefonica, on_delete=models.PROTECT, related_name="vinculos", blank=True, null=True, verbose_name="Linha Telefônica")
    data_entrega = models.DateField(verbose_name="Data de Entrega", blank=True, null=False)
    data_devolucao = models.DateField(blank=True, null=True, verbose_name="Data de Devolução")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ativo')
    termo_gerado = models.FileField(upload_to='termos_gerados/', null=True, blank=True, verbose_name="Termo de Responsabilidade Gerado")
    assinatura_digital = models.FileField(upload_to='assinaturas/', blank=True, null=True)
    termo_assinado_upload = models.FileField(upload_to='termos_assinados/', blank=True, null=True, verbose_name="Upload do Termo Assinado")
    foi_assinado = models.BooleanField(default=False, verbose_name="Termo Foi Assinado?")
    data_assinatura = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = "Vínculo de Aparelho/Linha"
        verbose_name_plural = "Vínculos de Aparelhos/Linhas"
        ordering = ['-criado_em']
        indexes = [
            models.Index(fields=['funcionario', 'status']),
            models.Index(fields=['aparelho', 'status']),
            models.Index(fields=['linha', 'status']),
        ]

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        original_status = None
        if not is_new:
            original = Vinculo.objects.get(pk=self.pk)
            original_status = original.status

        if self.data_devolucao and self.status == 'ativo':
            self.status = 'finalizado'
        
        super().save(*args, **kwargs)

        if is_new and self.status == 'ativo':
            if self.aparelho:
                self.aparelho.status = 'em_uso'
                self.aparelho.save()
            if self.linha:
                self.linha.status = 'ativa'
                self.linha.save()
        
        elif self.status == 'finalizado' and original_status != 'finalizado':
            if self.aparelho:
                self.aparelho.status = 'disponivel'
                self.aparelho.save()
            if self.linha:
                self.linha.status = 'disponivel'
                self.linha.save()

    def __str__(self):
        return f"{self.funcionario} - {self.aparelho or 'Sem Aparelho'}"
        
    def enviar_notificacao_de_assinatura(self, request):
        """
        Método para criar a notificação no sistema e enviar o e-mail.
        """
        usuario_a_notificar = self.funcionario.usuario
        if not usuario_a_notificar:
            print(f"Funcionário {self.funcionario} não tem um usuário de sistema associado.")
            return

        url_assinatura = request.build_absolute_uri(
            reverse('controle_de_telefone:vinculo_assinar', args=[self.pk])
        )

        Notificacao.objects.create(
            usuario=usuario_a_notificar,
            mensagem=f"Lembrete: Assinar Termo de Responsabilidade para o aparelho {self.aparelho}.",
            url_destino=url_assinatura
        )

        if usuario_a_notificar.email:
            assunto = "Lembrete: Termo de Responsabilidade Pendente de Assinatura"
            contexto_email = {
                'nome_usuario': usuario_a_notificar.first_name or usuario_a_notificar.username,
                'nome_aparelho': str(self.aparelho),
                'url_assinatura': url_assinatura,
            }
            corpo_html = render_to_string('emails/notificacao_assinatura.html', contexto_email)
            
            send_mail(
                subject=assunto,
                message='',    
                from_email='nao-responda@suaempresa.com',
                recipient_list=[usuario_a_notificar.email],
                html_message=corpo_html
            )


class RecargaCredito(models.Model):
    """
    Modelo para controlar recargas de créditos de celular corporativo.
    Registra quem solicitou, quem utilizará, valores e período de vigência.
    """
    
    class StatusRecarga(models.TextChoices):
        PENDENTE = 'pendente', 'Pendente'
        APROVADA = 'aprovada', 'Aprovada'
        REALIZADA = 'realizada', 'Realizada'
        CANCELADA = 'cancelada', 'Cancelada'
        EXPIRADA = 'expirada', 'Expirada'
    
    class TipoRecarga(models.TextChoices):
        CREDITO = 'credito', 'Crédito Avulso'
        PACOTE_DADOS = 'pacote_dados', 'Pacote de Dados'
        PACOTE_VOZ = 'pacote_voz', 'Pacote de Voz'
        COMBO = 'combo', 'Combo (Dados + Voz)'
    

    filial = models.ForeignKey(
        'usuario.Filial',
        on_delete=models.PROTECT,
        related_name='recargas_credito',
        verbose_name='Filial'
    )
    
    # Vínculo com a linha telefônica
    linha = models.ForeignKey(
        'LinhaTelefonica',
        on_delete=models.PROTECT,
        related_name='recargas',
        verbose_name='Linha Telefônica',
        help_text='Linha que receberá a recarga'
    )
    
    # Responsável pela solicitação (quem autorizou)
    responsavel = models.ForeignKey(
        'departamento_pessoal.Funcionario',
        on_delete=models.PROTECT,
        related_name='recargas_autorizadas',
        verbose_name='Responsável/Solicitante',
        help_text='Funcionário que autorizou a recarga'
    )
    
    # Usuário que utilizará os créditos
    usuario_credito = models.ForeignKey(
        'departamento_pessoal.Funcionario',
        on_delete=models.PROTECT,
        related_name='recargas_utilizadas',
        verbose_name='Usuário dos Créditos',
        help_text='Funcionário que utilizará os créditos'
    )
    
    # Tipo e valores
    tipo_recarga = models.CharField(
        max_length=20,
        choices=TipoRecarga.choices,
        default=TipoRecarga.CREDITO,
        verbose_name='Tipo de Recarga'
    )
    
    valor = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Valor (R$)',
        help_text='Valor da recarga em reais'
    )
    
    # Detalhes do pacote (se aplicável)
    franquia_dados_mb = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Franquia de Dados (MB)',
        help_text='Quantidade de dados em MB (se aplicável)'
    )
    
    minutos_voz = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Minutos de Voz',
        help_text='Quantidade de minutos (se aplicável)'
    )
    
    # Datas
    data_solicitacao = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data da Solicitação'
    )
    
    data_recarga = models.DateField(
        verbose_name='Data da Recarga',
        help_text='Data em que a recarga foi/será realizada'
    )
    
    data_inicio = models.DateField(
        verbose_name='Início da Vigência',
        help_text='Data de início da validade dos créditos'
    )
    
    data_termino = models.DateField(
        verbose_name='Término da Vigência',
        help_text='Data de expiração dos créditos'
    )
    
    # Status e controle
    status = models.CharField(
        max_length=20,
        choices=StatusRecarga.choices,
        default=StatusRecarga.PENDENTE,
        verbose_name='Status'
    )
    
    # Comprovante
    comprovante = models.FileField(
        upload_to='recargas/comprovantes/%Y/%m/',
        null=True,
        blank=True,
        verbose_name='Comprovante',
        help_text='Comprovante da recarga (PDF ou imagem)'
    )
    
    # Código de transação (da operadora)
    codigo_transacao = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Código da Transação',
        help_text='Código/protocolo da operadora'
    )
    
    # Observações
    observacao = models.TextField(
        blank=True,
        verbose_name='Observações',
        help_text='Informações adicionais sobre a recarga'
    )
    
    # Motivo (justificativa)
    motivo = models.TextField(
        blank=True,
        verbose_name='Motivo/Justificativa',
        help_text='Justificativa para a recarga'
    )
    
    # ══════════════════════════════════════════════════════════════
    # CORREÇÃO: Usar settings.AUTH_USER_MODEL
    # ══════════════════════════════════════════════════════════════
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recargas_criadas',
        verbose_name='Criado por'
    )
    
    atualizado_em = models.DateTimeField(
        auto_now=True,
        verbose_name='Última Atualização'
    )
    
    # Histórico
    historico = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Histórico de Alterações'
    )

    class Meta:
        verbose_name = 'Recarga de Crédito'
        verbose_name_plural = 'Recargas de Crédito'
        ordering = ['-data_solicitacao']
        indexes = [
            models.Index(fields=['filial', 'status']),
            models.Index(fields=['linha']),
            models.Index(fields=['data_recarga']),
            models.Index(fields=['usuario_credito']),
        ]
        permissions = [
            ('aprovar_recarga', 'Pode aprovar recarga de crédito'),
            ('cancelar_recarga', 'Pode cancelar recarga de crédito'),
        ]

    def __str__(self):
        return f"Recarga {self.linha.numero} - {self.data_recarga.strftime('%d/%m/%Y')} - R$ {self.valor}"

    def save(self, *args, **kwargs):
        if self.pk:
            original = RecargaCredito.objects.filter(pk=self.pk).first()
            if original:
                alteracoes = []
                if original.status != self.status:
                    alteracoes.append(f"Status: {original.get_status_display()} → {self.get_status_display()}")
                if original.valor != self.valor:
                    alteracoes.append(f"Valor: R$ {original.valor} → R$ {self.valor}")
                
                if alteracoes:
                    from django.utils import timezone
                    log = {
                        'data': timezone.now().strftime('%d/%m/%Y %H:%M'),
                        'alteracoes': alteracoes
                    }
                    self.historico.append(log)
        
        super().save(*args, **kwargs)

    @property
    def dias_vigencia(self):
        if self.data_inicio and self.data_termino:
            return (self.data_termino - self.data_inicio).days
        return 0
    
    @property
    def is_vigente(self):
        from django.utils import timezone
        hoje = timezone.now().date()
        return self.data_inicio <= hoje <= self.data_termino
    
    @property
    def is_expirada(self):
        from django.utils import timezone
        return self.data_termino < timezone.now().date()
    
    @property
    def franquia_dados_formatada(self):
        if self.franquia_dados_mb:
            if self.franquia_dados_mb >= 1024:
                return f"{self.franquia_dados_mb / 1024:.1f} GB"
            return f"{self.franquia_dados_mb} MB"
        return None
    
    def aprovar(self, user=None):
        self.status = self.StatusRecarga.APROVADA
        self.save()
    
    def realizar(self, codigo_transacao=None, user=None):
        self.status = self.StatusRecarga.REALIZADA
        if codigo_transacao:
            self.codigo_transacao = codigo_transacao
        self.save()
    
    def cancelar(self, motivo_cancelamento=None, user=None):
        self.status = self.StatusRecarga.CANCELADA
        if motivo_cancelamento:
            self.observacao += f"\n[CANCELAMENTO] {motivo_cancelamento}"
        self.save()

