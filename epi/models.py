from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _

User = get_user_model()



class EPI(models.Model):
    TIPO_EPI_CHOICES = [
        ('PROT', 'Proteção'),
        ('SEG', 'Segurança'),
        ('HIG', 'Higiene'),
        ('OUT', 'Outros'),
    ]
    
    nome = models.CharField(
        max_length=100,
        verbose_name=_("Nome do EPI"),
        help_text=_("Nome completo do equipamento")
    )
    
    descricao = models.TextField(
        verbose_name=_("Descrição"),
        help_text=_("Descrição detalhada do EPI e sua finalidade")
    )
    
    certificado = models.CharField(
        max_length=50,
        verbose_name=_("Certificado de Aprovação"),
        help_text=_("Número do CA (Certificado de Aprovação)")
    )
    
    unidade = models.CharField(
        max_length=20,
        verbose_name=_("Unidade de Medida"),
        default="UN",
        help_text=_("Unidade de medida (UN, PAR, M, etc)")
    )
    
    tipo = models.CharField(
        max_length=4,
        choices=TIPO_EPI_CHOICES,
        default='PROT',
        verbose_name=_("Tipo de EPI")
    )
    
    vida_util = models.PositiveIntegerField(
        verbose_name=_("Vida Útil (meses)"),
        help_text=_("Tempo de vida útil em meses"),
        default=12
    )
    
    estoque_minimo = models.PositiveIntegerField(
        verbose_name=_("Estoque Mínimo"),
        default=10,
        help_text=_("Quantidade mínima em estoque")
    )
    
    estoque_atual = models.PositiveIntegerField(
        verbose_name=_("Estoque Atual"),
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    ativo = models.BooleanField(
        default=True,
        verbose_name=_("Ativo?")
    )
    
    data_cadastro = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Data de Cadastro")
    )
    
    data_atualizacao = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Última Atualização")
    )

    # Métodos avançados
    def precisa_repor(self):
        """Verifica se o estoque está abaixo do mínimo"""
        return self.estoque_atual < self.estoque_minimo
    
    def consumo_mensal(self):
        """Calcula consumo médio mensal (placeholder)"""
        # Implementação real dependeria de histórico de movimentações
        return 0
    
    def proxima_reposicao(self):
        """Estima quando será necessária nova reposição"""
        if self.consumo_mensal() > 0:
            meses = self.estoque_atual / self.consumo_mensal()
            return f"{meses:.1f} meses"
        return _("Indeterminado")
    
    def __str__(self):
        return f"{self.nome} (CA: {self.certificado})"
    
    class Meta:
        db_table = "epi"
        verbose_name = _("EPI")
        verbose_name_plural = _("EPIs")
        ordering = ['nome']
        indexes = [
            models.Index(fields=['nome'], name='idx_epi_nome'),
            models.Index(fields=['certificado'], name='idx_epi_ca'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['nome', 'certificado'],
                name='unique_epi_nome_certificado'
            ),
        ]

class FichaEPI(models.Model):
    STATUS_CHOICES = [
        ('ATIVO', 'Ativo'),
        ('INATIVO', 'Inativo'),
        ('AFASTADO', 'Afastado'),
    ]
    
    empregado = models.ForeignKey('Empregado', on_delete=models.CASCADE, related_name='fichas_epi')
    empregado = models.ForeignKey(
        User, 
        on_delete=models.PROTECT,
        verbose_name=_("Empregado"),
        related_name='fichas_epi'
    )
    
    cargo = models.CharField(
        max_length=100,
        verbose_name=_("Cargo"),
        help_text=_("Cargo/função do empregado")
    )
    
    registro = models.CharField(
        max_length=50,
        verbose_name=_("Registro"),
        help_text=_("Matrícula ou registro funcional")
    )
    
    admissao = models.DateField(
        verbose_name=_("Data de Admissão")
    )
    
    demissao = models.DateField(
        null=True, 
        blank=True, 
        verbose_name=_("Data de Demissão")
    )
    
    contrato = models.CharField(
        max_length=100,
        verbose_name=_("Contrato"),
        help_text=_("Tipo de contrato de trabalho")
    )
    
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='ATIVO',
        verbose_name=_("Status")
    )
    
    local_data = models.CharField(
        max_length=100,
        verbose_name=_("Local e Data"),
        help_text=_("Local e data de emissão da ficha")
    )
    
    assinatura = models.ImageField(
        upload_to='assinaturas/%Y/%m/',
        null=True, 
        blank=True, 
        verbose_name=_("Assinatura Digital")
    )
    
    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Criado em")
    )
    
    atualizado_em = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Atualizado em")
    )

    # Métodos avançados
    def itens_ativos(self):
        """Retorna itens de EPI ainda não devolvidos"""
        return self.itens.filter(data_devolucao__isnull=True)
    
    def total_itens(self):
        """Retorna total de itens associados"""
        return self.itens.count()
    
    def get_absolute_url(self):
        return reverse('epi:visualizar_ficha', args=[str(self.id)])
    
    def clean(self):
        """Validações personalizadas"""
        super().clean()
        
        if self.demissao and self.demissao < self.admissao:
            raise ValidationError({
                'demissao': _("Data de demissão não pode ser anterior à admissão")
            })
    
    def save(self, *args, **kwargs):
        """Atualiza status se houver data de demissão"""
        if self.demissao:
            self.status = 'INATIVO'
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Ficha EPI - {self.empregado.get_full_name()} ({self.registro})"
    
    class Meta:
        db_table = "ficha_epi"
        verbose_name = _("Ficha de EPI")
        verbose_name_plural = _("Fichas de EPI")
        ordering = ['-criado_em']
        indexes = [
            models.Index(fields=['empregado'], name='idx_ficha_empregado'),
            models.Index(fields=['registro'], name='idx_ficha_registro'),
            models.Index(fields=['status'], name='idx_ficha_status'),
        ]

class ItemEPI(models.Model):
    ficha = models.ForeignKey(
        FichaEPI, 
        on_delete=models.CASCADE, 
        related_name='itens', 
        verbose_name=_("Ficha")
    )
    
    epi = models.ForeignKey(
        EPI, 
        on_delete=models.PROTECT, 
        verbose_name=_("EPI")
    )
    
    quantidade = models.PositiveIntegerField(
        verbose_name=_("Quantidade"),
        default=1,
        validators=[MinValueValidator(1)]
    )
    
    data_recebimento = models.DateField(
        verbose_name=_("Data de Recebimento")
    )
    
    data_devolucao = models.DateField(
        null=True, 
        blank=True, 
        verbose_name=_("Data de Devolução")
    )
    
    data_validade = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Data de Validade"),
        help_text=_("Data de validade do EPI (se aplicável)")
    )
    
    recebedor = models.CharField(
        max_length=100, 
        null=True, 
        blank=True, 
        verbose_name=_("Recebedor"),
        help_text=_("Nome do funcionário que recebeu o EPI")
    )
    
    observacoes = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("Observações")
    )
    
    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Criado em")
    )

    # Métodos avançados
    def esta_entregue(self):
        """Verifica se o item ainda não foi devolvido"""
        return self.data_devolucao is None
    
    def calcular_validade(self):
        """Calcula data de validade baseada na vida útil do EPI"""
        if self.epi.vida_util and self.data_recebimento:
            return self.data_recebimento + timedelta(days=self.epi.vida_util*30)
        return None
    
    def save(self, *args, **kwargs):
        """Calcula validade automaticamente se não definida"""
        if not self.data_validade:
            self.data_validade = self.calcular_validade()
        super().save(*args, **kwargs)
    
    def __str__(self):
        status = "Entregue" if self.esta_entregue() else "Devolvido"
        return f"{self.epi.nome} - {self.quantidade} ({status})"
    
    class Meta:
        db_table = "item_epi"
        verbose_name = _("Item de EPI")
        verbose_name_plural = _("Itens de EPI")
        ordering = ['-data_recebimento']
        indexes = [
            models.Index(fields=['ficha'], name='idx_item_ficha'),
            models.Index(fields=['epi'], name='idx_item_epi'),
        ]

