
# seguranca_trabalho/models.py (VERSÃO PROFISSIONAL SST)

from datetime import timedelta
from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# --- Modelos de Catálogo e Estrutura ---

class Fabricante(models.Model):
    """Representa a marca/fabricante de um equipamento."""
    nome = models.CharField(max_length=150, unique=True, verbose_name=_("Nome do Fabricante"))
    cnpj = models.CharField(max_length=18, blank=True, null=True, verbose_name=_("CNPJ"))
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = 'fabricante'
        verbose_name = _("Fabricante")
        verbose_name_plural = _("Fabricantes")
        ordering = ['nome']

    def __str__(self):
        return self.nome

class Fornecedor(models.Model):
    """Representa o fornecedor ou revendedor do equipamento."""
    razao_social = models.CharField(max_length=255, verbose_name=_("Razão Social"))
    nome_fantasia = models.CharField(max_length=255, blank=True, verbose_name=_("Nome Fantasia"))
    cnpj = models.CharField(max_length=18, unique=True, verbose_name=_("CNPJ"))
    email = models.EmailField(blank=True, verbose_name=_("E-mail de Contato"))
    telefone = models.CharField(max_length=20, blank=True, verbose_name=_("Telefone de Contato"))
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = 'fornecedor'
        verbose_name = _("Fornecedor")
        verbose_name_plural = _("Fornecedores")
        ordering = ['nome_fantasia']

    def __str__(self):
        return self.nome_fantasia or self.razao_social

class Funcao(models.Model):
    """Representa um cargo ou função na empresa."""
    nome = models.CharField(max_length=100, unique=True, verbose_name=_("Nome da Função"))
    descricao = models.TextField(blank=True, verbose_name=_("Descrição das Atividades"))
    ativo = models.BooleanField(default=True, verbose_name=_("Ativo"))

    class Meta:
        db_table = 'funcao'
        verbose_name = _("Função")
        verbose_name_plural = _("Funções")
        ordering = ['nome']

    def __str__(self):
        return self.nome

class Equipamento(models.Model):
    """Catálogo de tipos de Equipamentos de Proteção Individual (EPIs)."""
    nome = models.CharField(max_length=150, verbose_name=_("Nome do Equipamento"))
    modelo = models.CharField(max_length=100, blank=True, verbose_name=_("Modelo")) # NOVO
    fabricante = models.ForeignKey(Fabricante, on_delete=models.PROTECT, related_name='equipamentos', null=True, blank=True) # NOVO
    fornecedor_padrao = models.ForeignKey(Fornecedor, on_delete=models.SET_NULL, null=True, blank=True, related_name='equipamentos_fornecidos', verbose_name=_("Fornecedor Padrão")) # NOVO

    certificado_aprovacao = models.CharField(max_length=50, verbose_name=_("Certificado de Aprovação (CA)"), help_text=_("Deixe em branco se não aplicável."))
    data_validade_ca = models.DateField(null=True, blank=True, verbose_name=_("Data de Validade do CA")) # NOVO

    vida_util_dias = models.PositiveIntegerField(verbose_name=_("Vida Útil (dias)"), help_text=_("Vida útil em dias após a entrega, conforme fabricante."))
    estoque_minimo = models.PositiveIntegerField(default=5, verbose_name=_("Estoque Mínimo"))
    
    foto = models.ImageField(upload_to='epi_fotos/', null=True, blank=True, verbose_name=_("Foto do Equipamento")) # NOVO
    observacoes = models.TextField(blank=True, verbose_name=_("Observações")) # NOVO
    
    requer_numero_serie = models.BooleanField(default=False, verbose_name=_("Requer Rastreamento por Nº de Série?"), help_text=_("Marque se cada item individual precisa ser rastreado (ex: cinto de segurança).")) # NOVO
    ativo = models.BooleanField(default=True, verbose_name=_("Ativo"))

    class Meta:
        db_table = 'equipamento'
        verbose_name = _("Equipamento (EPI)")
        verbose_name_plural = _("Equipamentos (EPIs)")
        ordering = ['nome']
        unique_together = [['fabricante', 'modelo', 'certificado_aprovacao']] # Garante que o EPI seja único

    def __str__(self):
        return f"{self.nome} {self.modelo or ''} (CA: {self.certificado_aprovacao or 'N/A'})"

class MatrizEPI(models.Model):
    # ... (sem alterações) ...
    funcao = models.ForeignKey(Funcao, on_delete=models.CASCADE, related_name='matriz_epis')
    equipamento = models.ForeignKey(Equipamento, on_delete=models.CASCADE, related_name='matriz_funcoes')
    quantidade_padrao = models.PositiveIntegerField(default=1, verbose_name=_("Quantidade Padrão"))
    class Meta:
        db_table = 'matrizepi'
        verbose_name = _("Matriz de EPI por Função")
        verbose_name_plural = _("Matrizes de EPI por Função")
        unique_together = ('funcao', 'equipamento')
    def __str__(self):
        return f"{self.funcao.nome} -> {self.equipamento.nome}"


# --- Modelos Operacionais ---

class FichaEPI(models.Model):
    # ... (sem alterações) ...
    colaborador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='fichas_epi', verbose_name=_("Colaborador"))
    funcao = models.ForeignKey(Funcao, on_delete=models.PROTECT, verbose_name=_("Função na Ficha"))
    data_admissao = models.DateField(verbose_name=_("Data de Admissão"))
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'fichaepi'
        verbose_name = _("Ficha de EPI")
        verbose_name_plural = _("Fichas de EPI")
        ordering = ['-criado_em']
    def __str__(self):
        return f"Ficha de {self.colaborador.get_full_name()}"
    def get_absolute_url(self):
        return reverse('seguranca_trabalho:ficha_detalhe', args=[self.pk])


class EntregaEPI(models.Model):
    """Registra uma entrega específica de um ou mais EPIs para um colaborador."""
    ficha = models.ForeignKey(FichaEPI, on_delete=models.PROTECT, related_name='entregas')
    equipamento = models.ForeignKey(Equipamento, on_delete=models.PROTECT)
    quantidade = models.PositiveIntegerField(default=1)
    
    # NOVOS campos para rastreabilidade
    lote = models.CharField(max_length=100, blank=True, verbose_name=_("Lote de Fabricação"))
    numero_serie = models.CharField(max_length=100, blank=True, verbose_name=_("Número de Série"), help_text=_("Preencher se o equipamento exigir rastreamento individual."))
    
    data_entrega = models.DateTimeField(default=timezone.now, verbose_name=_("Data de Entrega"))
    assinatura_recebimento = models.TextField(blank=True, verbose_name=_("Assinatura de Recebimento (Base64)"))
    
    data_devolucao = models.DateTimeField(null=True, blank=True, verbose_name=_("Data de Devolução"))
    assinatura_devolucao = models.TextField(blank=True, verbose_name=_("Assinatura de Devolução (Base64)"))

    class Meta:
        verbose_name = _("Entrega de EPI")
        verbose_name_plural = _("Entregas de EPI")
        ordering = ['-data_entrega']
        
    def __str__(self):
        return f"{self.quantidade}x {self.equipamento.nome} para {self.ficha.colaborador.get_full_name()}"

    # ... (propriedades @property 'data_vencimento_uso' e 'status' continuam as mesmas) ...
    @property
    def data_vencimento_uso(self):
        if self.equipamento.vida_util_dias:
            return self.data_entrega + timedelta(days=self.equipamento.vida_util_dias)
        return None
    @property
    def status(self):
        if self.data_devolucao:
            return "Devolvido"
        if self.data_vencimento_uso and timezone.now() > self.data_vencimento_uso:
            return "Vencido"
        if not self.assinatura_recebimento:
            return "Aguardando Assinatura"
        return "Ativo com Colaborador"

class MovimentacaoEstoque(models.Model):
    """Audita todas as entradas e saídas de estoque."""
    TIPO_MOVIMENTACAO = [('ENTRADA', 'Entrada'), ('SAIDA', 'Saída'), ('AJUSTE', 'Ajuste')] # AJUSTE é uma boa adição
    
    equipamento = models.ForeignKey(Equipamento, on_delete=models.PROTECT, related_name='movimentacoes_estoque')
    tipo = models.CharField(max_length=7, choices=TIPO_MOVIMENTACAO)
    quantidade = models.IntegerField() # Usar IntegerField para permitir ajustes negativos
    
    # NOVOS campos para controle de compra e validade
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.SET_NULL, null=True, blank=True)
    lote = models.CharField(max_length=100, blank=True, verbose_name=_("Lote"))
    data_validade_fabricante = models.DateField(null=True, blank=True, verbose_name=_("Validade do Produto (Fabricante)"))
    custo_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name=_("Custo Unitário"))
    
    data = models.DateTimeField(default=timezone.now)
    responsavel = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    justificativa = models.CharField(max_length=255)
    entrega_associada = models.OneToOneField(EntregaEPI, on_delete=models.SET_NULL, null=True, blank=True) # Alterado para OneToOneField

    class Meta:
        db_table = 'movimentacaoestoque'
        verbose_name = _("Movimentação de Estoque")
        verbose_name_plural = _("Movimentações de Estoque")
        ordering = ['-data']
        