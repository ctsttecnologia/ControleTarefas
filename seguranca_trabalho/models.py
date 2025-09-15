
# seguranca_trabalho/models.py

from datetime import datetime, timedelta
from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from departamento_pessoal.models import Funcionario

from core.managers import FilialManager
from logradouro.models import Logradouro
from usuario.models import Filial

# --- Modelos de Catálogo e Estrutura ---

class Fabricante(models.Model):
    nome = models.CharField(max_length=150, unique=True, verbose_name=_("Nome do Fabricante"))
    cnpj = models.CharField(max_length=18, blank=True, null=True, verbose_name=_("CNPJ"))
    ativo = models.BooleanField(default=True, verbose_name=_("Ativo"))
    filial = models.ForeignKey(
        Filial, 
        on_delete=models.PROTECT,
        related_name='fabricantes', 
        verbose_name="Filial",
        null=True,
       blank=True,
    )

    # Manager customizado para segregação de dados
    objects = FilialManager()
    class Meta:
        verbose_name = _("Fabricante")
        verbose_name_plural = _("Fabricantes")
        ordering = ['nome']

    endereco = models.ForeignKey(
        Logradouro,
        on_delete=models.PROTECT,
        related_name='fabricantes',
        verbose_name="Endereço",
        null=True
    )

    contato = models.CharField(max_length=100, blank=True, verbose_name=_("Contato"))
    telefone = models.CharField(max_length=20, blank=True, verbose_name=_("Telefone"))
    celular = models.CharField(max_length=20, blank=True, verbose_name=_("Celular"))
    email = models.EmailField(blank=True, verbose_name=_("E-mail de Contato"))
    site = models.URLField(blank=True, verbose_name=_("Site"))
    observacoes = models.TextField(blank=True, verbose_name=_("Observações"))

    def __str__(self):
        return self.nome

    def get_absolute_url(self):
        return reverse('seguranca_trabalho:fabricante_detail', kwargs={'pk': self.pk})


class Fornecedor(models.Model):
    razao_social = models.CharField(max_length=255, verbose_name=_("Razão Social"))
    nome_fantasia = models.CharField(max_length=255, blank=True, verbose_name=_("Nome Fantasia"))
    cnpj = models.CharField(max_length=18, unique=True, verbose_name=_("CNPJ"))
    inscricao_estadual = models.CharField(max_length=20, blank=True, verbose_name=_("Inscrição Estadual"))
    contato = models.CharField(max_length=100, blank=True, verbose_name=_("Contato"))
    telefone = models.CharField(max_length=20, blank=True, verbose_name=_("Telefone de Contato"))
    celular = models.CharField(max_length=20, blank=True, verbose_name=_("Celular"))
    email = models.EmailField(blank=True, verbose_name=_("E-mail de Contato"))
    ativo = models.BooleanField(default=True, verbose_name=_("Ativo"))
    endereco = models.ForeignKey(
        Logradouro,
        on_delete=models.PROTECT,
        related_name='fornecedores',
        verbose_name="Endereço",
        null=True
    )
    site = models.URLField(blank=True, verbose_name=_("Site"))
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name='fornecedores',  
        verbose_name=_("Filial"),
        null=True,                  
        blank=True,              
    )
    # Manager customizado para segregação de dados
    objects = FilialManager()

    class Meta:
        verbose_name = _("Fornecedor")
        verbose_name_plural = _("Fornecedores")
        ordering = ['nome_fantasia']

    def __str__(self):
        return self.nome_fantasia or self.razao_social

    def get_absolute_url(self):
        return reverse('seguranca_trabalho:fornecedor_detail', kwargs={'pk': self.pk})


class Funcao(models.Model):
    nome = models.CharField(max_length=100, unique=True, verbose_name=_("Nome da Função"))
    descricao = models.TextField(blank=True, verbose_name=_("Descrição das Atividades"))
    ativo = models.BooleanField(default=True, verbose_name=_("Ativo"))
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name='funcoes',  
        verbose_name=_("Filial"),
        null=True,                  
        blank=False              
    )
    # Manager customizado para segregação de dados
    objects = FilialManager()

    class Meta:
        verbose_name = _("Função")
        verbose_name_plural = _("Funções")
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Equipamento(models.Model):
    nome = models.CharField(max_length=150, verbose_name=_("Descrição EPI"))
    modelo = models.CharField(max_length=100, blank=True, verbose_name=_("Modelo"))
    fabricante = models.ForeignKey(Fabricante, on_delete=models.PROTECT, related_name='equipamentos', null=True, blank=True)
    fornecedor_padrao = models.ForeignKey(Fornecedor, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Fornecedor Padrão"))
    certificado_aprovacao = models.CharField(max_length=50, verbose_name=_("Certificado de Aprovação (CA)"), help_text=_("Deixe em branco se não aplicável."), blank=True)
    data_validade_ca = models.DateField(null=True, blank=True, verbose_name=_("Data de Validade do CA"))
    vida_util_dias = models.PositiveIntegerField(verbose_name=_("Vida Útil (dias)"), help_text=_("Vida útil em dias após a entrega, conforme fabricante."))
    estoque_minimo = models.PositiveIntegerField(default=5, verbose_name=_("Estoque Mínimo"))
    observacoes = models.TextField(blank=True, verbose_name=_("Observações"))
    requer_numero_serie = models.BooleanField(default=False, verbose_name=_("Requer Rastreamento por Nº de Série?"), help_text=_("Marque se cada item individual precisa ser rastreado."))
    foto = models.ImageField(upload_to='epi_fotos/', null=True, blank=True, verbose_name=_("Foto do Equipamento"))
    ativo = models.BooleanField(default=True, verbose_name=_("Ativo"))
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name='equipamentos',  
        verbose_name=_("Filial"),
        null=True,                  
        blank=False              
    )
    # Manager customizado para segregação de dados
    objects = FilialManager()
 
    class Meta:
        verbose_name = _("Equipamento (EPI)")
        verbose_name_plural = _("Equipamentos (EPIs)")
        ordering = ['nome']
        constraints = [
            models.UniqueConstraint(fields=['fabricante', 'modelo', 'certificado_aprovacao'], name='equipamento_unico_constraint')
        ]

    def __str__(self):
        ca_text = f"CA: {self.certificado_aprovacao}" if self.certificado_aprovacao else 'N/A'
        return f"{self.nome} {self.modelo or ''} ({ca_text})"

    def get_absolute_url(self):
        return reverse('seguranca_trabalho:equipamento_detail', args=[self.pk])


class MatrizEPI(models.Model):
    funcao = models.ForeignKey(Funcao, on_delete=models.CASCADE, related_name='matriz_epis')
    equipamento = models.ForeignKey(Equipamento, on_delete=models.CASCADE, related_name='matriz_funcoes')
    quantidade_padrao = models.PositiveIntegerField(default=1, verbose_name=_("Quantidade Padrão"))
    # --- CAMPO ADICIONADO ---
    frequencia_troca_meses = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name=_("Frequência de Troca (Meses)"),
        help_text=_("Deixe em branco para 'Quando Necessário' (QN).")
    )
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name='matrizepis',  
        verbose_name=_("Filial"),
        null=True,                  
        blank=False              
    )
    # Manager customizado para segregação de dados
    objects = FilialManager()
    
    class Meta:
        verbose_name = _("Matriz de EPI por Função")
        verbose_name_plural = _("Matrizes de EPI por Função")
        unique_together = ('funcao', 'equipamento')

    def __str__(self):
        freq = f"({self.frequencia_troca_meses} meses)" if self.frequencia_troca_meses else "(QN)"
        return f"{self.funcao.nome} -> {self.equipamento.nome} {freq}"


# --- Modelos Operacionais ---

class FichaEPI(models.Model):
    funcionario = models.OneToOneField(Funcionario, on_delete=models.PROTECT, related_name='ficha_epi', verbose_name=_("Funcionário"))
    funcao = models.ForeignKey(Funcao, on_delete=models.PROTECT, verbose_name=_("Função na Admissão"))
    data_admissao = models.DateField(editable=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name='fichaepis',  
        verbose_name=_("Filial"),
        null=True,                  
        blank=False              
    )
    # Manager customizado para segregação de dados
    objects = FilialManager()
    
    class Meta:
        verbose_name = _("Ficha de EPI")
        verbose_name_plural = _("Fichas de EPI")
        ordering = ['-funcionario__nome_completo']

    def save(self, *args, **kwargs):
        if not self.pk and self.funcionario:
            self.data_admissao = self.funcionario.data_admissao
            if hasattr(self.funcionario, 'cargo') and self.funcionario.cargo:
                funcao_obj, created = Funcao.objects.get_or_create(nome=self.funcionario.cargo.nome)
                self.funcao = funcao_obj
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Ficha de {self.funcionario.nome_completo}"

    def get_absolute_url(self):
        return reverse('seguranca_trabalho:ficha_detail', args=[self.pk])


class EntregaEPI(models.Model):
    ficha = models.ForeignKey(FichaEPI, on_delete=models.PROTECT, related_name='entregas')
    equipamento = models.ForeignKey(Equipamento, on_delete=models.PROTECT, verbose_name=_("Equipamento"))
    quantidade = models.PositiveIntegerField(default=1, verbose_name=_("Quantidade"))
    lote = models.CharField(max_length=100, blank=True, verbose_name=_("Lote de Fabricação"))
    numero_serie = models.CharField(max_length=100, blank=True, verbose_name=_("Número de Série"))
    data_entrega = models.DateField(null=True, blank=True, verbose_name=_("Data de Recebimento")) 
    assinatura_recebimento = models.TextField(blank=True, null=True, verbose_name=_("Assinatura de Recebimento"))
    assinatura_imagem = models.ImageField(
        verbose_name="Assinatura (Arquivo)", 
        upload_to='assinaturas/%Y/%m/', 
        null=True, 
        blank=True
    )
    data_assinatura = models.DateTimeField(null=True, blank=True, verbose_name=_("Data da Assinatura"))
    data_devolucao = models.DateField(null=True, blank=True, verbose_name=_("Data de Devolução")) 
    recebedor_devolucao = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name=_("Recebedor")
    ) 
    criado_em = models.DateTimeField(default=timezone.now, verbose_name=_("Data do Registro"))
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name='entregaepis',  
        verbose_name=_("Filial"),
        null=True,                  
        blank=False              
    )
    # Manager customizado para segregação de dados
    objects = FilialManager()

    class Meta:
        verbose_name = _("Entrega de EPI")
        verbose_name_plural = _("Entregas de EPI")
        ordering = ['-criado_em']

    @property
    def data_vencimento_uso(self):
        if self.data_entrega and self.equipamento.vida_util_dias:
            return self.data_entrega + timedelta(days=self.equipamento.vida_util_dias)
        return None

    @property
    def status(self):
        if self.data_devolucao:
            return "Devolvido"
        if not self.assinatura_recebimento and not self.assinatura_imagem:
            return "Pendente Assinatura"
        if self.data_vencimento_uso and timezone.now().date() > self.data_vencimento_uso:
            return "Vencido"
        return "Ativo"


class MovimentacaoEstoque(models.Model):
    TIPO_MOVIMENTACAO = [('ENTRADA', 'Entrada'), ('SAIDA', 'Saída'), ('AJUSTE', 'Ajuste')]
    equipamento = models.ForeignKey(Equipamento, on_delete=models.PROTECT, related_name='movimentacoes_estoque')
    tipo = models.CharField(max_length=7, choices=TIPO_MOVIMENTACAO)
    quantidade = models.IntegerField()
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.SET_NULL, null=True, blank=True)
    lote = models.CharField(max_length=100, blank=True, verbose_name=_("Lote"))
    data_validade_fabricante = models.DateField(null=True, blank=True, verbose_name=_("Validade do Produto (Fabricante)"))
    custo_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name=_("Custo Unitário"))
    data = models.DateTimeField(default=timezone.now)
    responsavel = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    justificativa = models.CharField(max_length=255)
    entrega_associada = models.OneToOneField(EntregaEPI, on_delete=models.SET_NULL, null=True, blank=True)
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name='movimentacaoestoques',  
        verbose_name=_("Filial"),
        null=True,                  
        blank=False              
    )
    # Manager customizado para segregação de dados
    objects = FilialManager()

    class Meta:
        verbose_name = _("Movimentação de Estoque")
        verbose_name_plural = _("Movimentações de Estoque")
        ordering = ['-data']

