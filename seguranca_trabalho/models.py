# Modelos para Segurança do Trabalho - Controle de EPIs, Fichas de EPI, Entregas e Movimentações de Estoque
from datetime import date, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.managers import FilialManager
from departamento_pessoal.models import Cargo
from suprimentos.models import PedidoCompra
from usuario.models import Filial


# =====================================================================
# Modelos de Catálogo e Estrutura
# =====================================================================
# NOTA: Os modelos Fabricante e Fornecedor foram REMOVIDOS para completar
# a refatoração para a aplicação 'suprimentos' e o modelo 'Parceiro'.

class Funcao(models.Model):
    registro = models.PositiveIntegerField(default=0, verbose_name=_("Registro da Função"))
    nome = models.CharField(max_length=100, verbose_name=_("Nome da Função"))
    descricao = models.TextField(blank=True, verbose_name=_("Descrição das Atividades"))
    ativo = models.BooleanField(default=True, verbose_name=_("Ativo"))
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name='funcoes',
        verbose_name=_("Filial"),
        null=True,
        blank=False,
    )

    objects = FilialManager()

    class Meta:
        verbose_name = _("Função")
        verbose_name_plural = _("Funções")
        ordering = ['nome']
        constraints = [
            models.UniqueConstraint(fields=['nome', 'filial'], name='unique_funcao_por_filial'),
        ]

    def __str__(self):
        return self.nome


class CargoFuncao(models.Model):
    cargo = models.ForeignKey(
        Cargo,
        on_delete=models.CASCADE,
        related_name='cargo_funcoes',
        verbose_name=_("Cargo"),
    )
    funcao = models.ForeignKey(
        Funcao,
        on_delete=models.CASCADE,
        related_name='funcoes_cargo',
        verbose_name=_("Função"),
    )
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name='cargo_funcoes',
        verbose_name=_("Filial"),
        null=True,
        blank=False,
    )

    objects = FilialManager()

    class Meta:
        verbose_name = _("Cargo e Função Associados")
        verbose_name_plural = _("Cargos e Funções Associados")
        unique_together = ('cargo', 'funcao', 'filial')

    def __str__(self):
        return f"{self.cargo.nome} - {self.funcao.nome}"

    @property
    def cargo_nome(self):
        return self.cargo.nome

    @property
    def funcao_nome(self):
        return self.funcao


class Equipamento(models.Model):
    nome = models.CharField(max_length=150, verbose_name=_("Descrição EPI"))
    modelo = models.CharField(max_length=100, blank=True, verbose_name=_("Modelo"))
    fabricante = models.ForeignKey(
        'suprimentos.Parceiro',
        on_delete=models.PROTECT,
        limit_choices_to={'eh_fabricante': True},
        related_name='equipamentos_fabricados',
        verbose_name=_("Fabricante"),
    )
    certificado_aprovacao = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("Certificado de Aprovação (CA)"),
        help_text=_("Deixe em branco se não aplicável."),
    )
    data_cadastro = models.DateField(
        auto_now_add=True,
        null=True,
        verbose_name=_("Data de Cadastro"),
        help_text=_("Data em que o equipamento foi cadastrado."),
    )
    data_validade_ca = models.DateField(null=True, blank=True, verbose_name=_("Data de Validade do CA"))
    vida_util_dias = models.PositiveIntegerField(
        verbose_name=_("Vida Útil (dias)"),
        help_text=_("Vida útil em dias após a entrega, conforme fabricante."),
    )
    estoque_minimo = models.PositiveIntegerField(default=5, verbose_name=_("Estoque Mínimo"))
    estoque_atual = models.IntegerField(
        default=0,
        editable=False,
        verbose_name=_("Estoque Atual"),
        help_text=_("Atualizado automaticamente pelas movimentações."),
    )
    requer_numero_serie = models.BooleanField(
        default=False,
        verbose_name=_("Requer Rastreamento por Nº de Série?"),
        help_text=_("Marque se cada item individual precisa ser rastreado."),
    )
    foto = models.ImageField(upload_to='epi_fotos/', null=True, blank=True, verbose_name=_("Foto do Equipamento"))
    observacoes = models.TextField(blank=True, verbose_name=_("Observações"))
    ativo = models.BooleanField(default=True, verbose_name=_("Ativo"))
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name='equipamentos',
        verbose_name=_("Filial"),
        null=True,
        blank=False,
    )

    objects = FilialManager()

    class Meta:
        verbose_name = _("Equipamento (EPI)")
        verbose_name_plural = _("Equipamentos (EPIs)")
        ordering = ['nome']
        constraints = [
            models.UniqueConstraint(
                fields=['fabricante', 'modelo', 'certificado_aprovacao'],
                name='equipamento_unico_constraint',
            ),
        ]
        indexes = [
            models.Index(fields=['filial', 'ativo']),
            models.Index(fields=['nome']),
        ]

    def __str__(self):
        ca_text = f"CA: {self.certificado_aprovacao}" if self.certificado_aprovacao else 'N/A'
        return f"{self.nome} {self.modelo or ''} ({ca_text})"

    def get_absolute_url(self):
        return reverse('seguranca_trabalho:equipamento_detail', args=[self.pk])

    @property
    def estoque_critico(self):
        return self.estoque_atual <= self.estoque_minimo

    @property
    def abaixo_do_minimo(self):
        return self.estoque_atual < self.estoque_minimo

    @property
    def estoque_status(self):
        if self.estoque_atual <= 0:
            return 'sem_estoque'
        if self.estoque_atual <= self.estoque_minimo:
            return 'critico'
        return 'ok'


class MatrizEPI(models.Model):
    funcao = models.ForeignKey(Funcao, on_delete=models.CASCADE, related_name='matriz_epis')
    equipamento = models.ForeignKey(Equipamento, on_delete=models.CASCADE, related_name='matriz_funcoes')
    quantidade_padrao = models.PositiveIntegerField(default=1, verbose_name=_("Quantidade Padrão"))
    frequencia_troca_meses = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name=_("Frequência de Troca (Meses)"),
        help_text=_("Deixe em branco para 'Quando Necessário' (QN)."),
    )
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name='matrizepis',
        verbose_name=_("Filial"),
        null=True,
        blank=False,
    )

    objects = FilialManager()

    class Meta:
        verbose_name = _("Matriz de EPI por Função")
        verbose_name_plural = _("Matrizes de EPI por Função")
        unique_together = ('funcao', 'equipamento')

    def __str__(self):
        freq = f"({self.frequencia_troca_meses} meses)" if self.frequencia_troca_meses else "(QN)"
        return f"{self.funcao.nome} -> {self.equipamento.nome} {freq}"


# =====================================================================
# Modelos Operacionais
# =====================================================================

class FichaEPI(models.Model):
    funcionario = models.OneToOneField(
        'departamento_pessoal.Funcionario',
        on_delete=models.PROTECT,
        related_name='ficha_epi',
        verbose_name=_("Funcionário"),
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    assinatura_funcionario = models.TextField(
        blank=True, null=True,
        verbose_name=_("Assinatura do Funcionário"),
        help_text=_("Assinatura digital (base64) do funcionário no termo."),
    )
    data_assinatura_termo = models.DateTimeField(
        blank=True, null=True,
        verbose_name=_("Data da Assinatura do Termo"),
    )
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name='fichaepis',
        verbose_name=_("Filial"),
        null=True,
        blank=False,
    )

    objects = FilialManager()

    class Meta:
        verbose_name = _("Ficha de EPI")
        verbose_name_plural = _("Fichas de EPI")
        ordering = ['funcionario__nome_completo']

    def __str__(self):
        return f"Ficha de {self.funcionario.nome_completo}"

    def get_absolute_url(self):
        return reverse('seguranca_trabalho:ficha_detail', args=[self.pk])

    @property
    def funcao(self):
        if self.funcionario and hasattr(self.funcionario, 'funcao'):
            return self.funcionario.funcao
        return None

    @property
    def data_admissao(self):
        if self.funcionario:
            return self.funcionario.data_admissao
        return None


class EntregaEPI(models.Model):
    ficha = models.ForeignKey(FichaEPI, on_delete=models.PROTECT, related_name='entregas')
    equipamento = models.ForeignKey(Equipamento, on_delete=models.PROTECT, verbose_name=_("Equipamento"))
    quantidade = models.PositiveIntegerField(default=1, verbose_name=_("Quantidade"))
    lote = models.CharField(max_length=100, blank=True, verbose_name=_("Lote de Fabricação"))
    numero_serie = models.CharField(max_length=100, blank=True, verbose_name=_("Número de Série"))
    data_entrega = models.DateField(default=date.today, verbose_name=_("Data de Recebimento"))
    assinatura_recebimento = models.TextField(
        blank=True, null=True,
        verbose_name=_("Assinatura de Recebimento (Base64)"),
    )
    assinatura_imagem = models.ImageField(
        upload_to='assinaturas/%Y/%m/',
        null=True, blank=True,
        verbose_name=_("Assinatura (Arquivo)"),
    )
    data_assinatura = models.DateTimeField(null=True, blank=True, verbose_name=_("Data da Assinatura"))
    data_devolucao = models.DateField(null=True, blank=True, verbose_name=_("Data de Devolução"))
    recebedor_devolucao = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='epis_recebidos',
        verbose_name=_("Recebedor"),
    )
    criado_em = models.DateTimeField(default=timezone.now, verbose_name=_("Data do Registro"))
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name='entregaepis',
        verbose_name=_("Filial"),
        null=True,
        blank=False,
    )

    objects = FilialManager()

    class Meta:
        verbose_name = _("Entrega de EPI")
        verbose_name_plural = _("Entregas de EPI")
        ordering = ['-criado_em']
        permissions = [
            ("assinar_entregaepi", "Pode assinar entrega de EPI"),
        ]
        indexes = [
            models.Index(fields=['ficha', '-criado_em']),
            models.Index(fields=['equipamento', '-data_entrega']),
            models.Index(fields=['filial', '-criado_em']),
        ]

    def __str__(self):
        funcionario = self.ficha.funcionario.nome_completo if self.ficha else "Sem ficha"
        equipamento = self.equipamento.nome if self.equipamento else "Sem equipamento"
        data = self.data_entrega.strftime('%d/%m/%Y') if self.data_entrega else "S/D"
        return f"{equipamento} → {funcionario} ({data})"

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
        vencimento = self.data_vencimento_uso
        if vencimento and timezone.now().date() > vencimento:
            return "Vencido"
        return "Ativo"


class MovimentacaoEstoque(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = 'ENTRADA', _('Entrada')
        SAIDA = 'SAIDA', _('Saída')
        AJUSTE = 'AJUSTE', _('Ajuste')

    # Campos imutáveis após criação
    CAMPOS_IMUTAVEIS = ('equipamento', 'tipo', 'quantidade', 'delta', 'data')

    # Alias retrocompatível — mantém código antigo funcionando
    MOVIMENTACAO = Tipo.choices

    equipamento = models.ForeignKey(
        Equipamento,
        on_delete=models.PROTECT,
        related_name='movimentacoes_estoque',
        verbose_name=_("Equipamento"),
    )
    tipo = models.CharField(max_length=7, choices=Tipo.choices, verbose_name=_("Tipo"))
    quantidade = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name=_("Quantidade"),
    )

    pedido_compra_origem = models.ForeignKey(PedidoCompra, on_delete=models.SET_NULL, null=True, blank=True)
    
    fornecedor = models.ForeignKey(
        'suprimentos.Parceiro',
        on_delete=models.PROTECT,
        limit_choices_to={'eh_fornecedor': True},
        related_name='movimentacoes_por_fornecedor',
        null=True, blank=True,
        verbose_name=_("Fornecedor"),
    )
    lote = models.CharField(max_length=100, blank=True, verbose_name=_("Lote"))
    data_validade_fabricante = models.DateField(
        null=True, blank=True,
        verbose_name=_("Validade do Produto (Fabricante)"),
    )
    custo_unitario = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        verbose_name=_("Custo Unitário"),
    )
    data = models.DateTimeField(default=timezone.now, null=True, blank=True, verbose_name=_("Data"))
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        verbose_name=_("Responsável"),
    )
    justificativa = models.CharField(max_length=255, blank=True, verbose_name=_("Justificativa"))
    entrega_associada = models.ForeignKey(
        'EntregaEPI',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='movimentacoes',
        verbose_name=_("Entrega Associada"),
    )
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name='movimentacaoestoques',
        verbose_name=_("Filial"),
        null=True,
        blank=False,
    )

    objects = FilialManager()

    class Meta:
        verbose_name = _("Movimentação de Estoque")
        verbose_name_plural = _("Movimentações de Estoque")
        ordering = ['-data']
        indexes = [
            models.Index(fields=['equipamento', '-data']),
            models.Index(fields=['filial', '-data']),
            models.Index(fields=['tipo', '-data']),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.equipamento} ({self.quantidade})"

    # ---------------------------------------------------------------
    # Regras de integridade
    # ---------------------------------------------------------------
    def clean(self):
        super().clean()

        # 1) Quantidade precisa ser positiva
        if self.quantidade is None or self.quantidade <= 0:
            raise ValidationError({'quantidade': 'A quantidade deve ser maior que zero.'})

        # 2) Coerência entre tipo e delta
        if self.tipo == 'ENTRADA' and self.delta != self.quantidade:
            raise ValidationError({'delta': 'Para ENTRADA, delta deve ser igual a quantidade.'})
        if self.tipo == 'SAIDA' and self.delta != -self.quantidade:
            raise ValidationError({'delta': 'Para SAIDA, delta deve ser igual a -quantidade.'})

        # 3) Imutabilidade após persistência
        if self.pk:
            original = type(self).objects.filter(pk=self.pk).first()
            if original is not None:
                alterados = [
                    campo for campo in self.CAMPOS_IMUTAVEIS
                    if getattr(original, f'{campo}_id' if campo == 'equipamento' else campo)
                       != getattr(self, f'{campo}_id' if campo == 'equipamento' else campo)
                ]
                if alterados:
                    raise ValidationError(
                        "Movimentação de estoque é imutável. "
                        f"Campos alterados não permitidos: {', '.join(alterados)}. "
                        "Para corrigir, registre uma movimentação de AJUSTE contrária."
                    )

    def save(self, *args, **kwargs):
        # Garante que clean() seja sempre executado, inclusive fora de Forms/Admin
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def delta(self):
        """Variação que esta movimentação aplica ao estoque."""
        if self.tipo == self.Tipo.ENTRADA:
            return self.quantidade
        if self.tipo == self.Tipo.SAIDA:
            return -self.quantidade
        # AJUSTE: trata como entrada (positivo). Se quiser permitir negativo,
        # mude para campo separado de "saldo de ajuste".
        return self.quantidade



        