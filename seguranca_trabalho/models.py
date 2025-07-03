
# seguranca_trabalho/models.py (VERSÃO PROFISSIONAL SST)


from datetime import timedelta
from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# --- Modelos de Catálogo e Estrutura ---

#  Nome da classe em CamelCase (Funcao)
class Funcao(models.Model):
    """Representa um cargo ou função na empresa."""
    nome = models.CharField(max_length=100, unique=True, verbose_name=_("Nome da Função"))
    descricao = models.TextField(blank=True, verbose_name=_("Descrição das Atividades"))
    ativo = models.BooleanField(default=True, verbose_name=_("Ativo"))

    class Meta:
        db_table = 'funcao'
        verbose_name = _("Função")
        # Plural correto
        verbose_name_plural = _("Funções")
        ordering = ['nome']

    def __str__(self):
        return self.nome

class Equipamento(models.Model):
   
    nome = models.CharField(max_length=150, verbose_name=_("Nome do Equipamento"))
    certificado_aprovacao = models.CharField(max_length=50, unique=True, verbose_name=_("Certificado de Aprovação (CA)"))
    vida_util_dias = models.PositiveIntegerField(verbose_name=_("Vida Útil (dias)"), help_text=_("Vida útil em dias após a entrega, conforme fabricante."))
    estoque_minimo = models.PositiveIntegerField(default=5, verbose_name=_("Estoque Mínimo"))
    ativo = models.BooleanField(default=True, verbose_name=_("Ativo"))

    class Meta:
        db_table = 'equipamento'
        verbose_name = _("Equipamento (EPI)")
        verbose_name_plural = _("Equipamentos (EPIs)")
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} (CA: {self.certificado_aprovacao})"
    
    # ... (outros métodos e propriedades) ...

class MatrizEPI(models.Model):
    """Define quais EPIs são necessários para cada Função (Matriz de Risco)."""
    # Apontando para o novo nome da classe 'Funcao'
    funcao = models.ForeignKey(Funcao, on_delete=models.CASCADE, related_name='matriz_epis')
    equipamento = models.ForeignKey(Equipamento, on_delete=models.CASCADE, related_name='matriz_funcoes')
    quantidade_padrao = models.PositiveIntegerField(default=1, verbose_name=_("Quantidade Padrão"))

    class Meta:
        db_table = 'matrizepi'
        verbose_name = _("Matriz de EPI por Função")
        verbose_name_plural = _("Matrizes de EPI por Função")
        unique_together = ('funcao', 'equipamento')

    def __str__(self):
        # Usando o nome correto do campo 'funcao'
        return f"{self.funcao.nome} -> {self.equipamento.nome}"

# --- Modelos Operacionais ---

class FichaEPI(models.Model):
    """A ficha principal que agrupa todas as entregas para um colaborador."""
    colaborador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='fichas_epi', verbose_name=_("Colaborador"))
    # Apontando para o novo nome da classe 'Funcao'
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
    """Registra uma entrega (ou devolução) específica de um EPI para um colaborador."""
    ficha = models.ForeignKey(FichaEPI, on_delete=models.PROTECT, related_name='entregas')
    equipamento = models.ForeignKey(Equipamento, on_delete=models.PROTECT)
    quantidade = models.PositiveIntegerField(default=1)
    
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
    """Audita todas as entradas e saídas de estoque de forma atômica."""
    TIPO_MOVIMENTACAO = [('ENTRADA', 'Entrada'), ('SAIDA', 'Saída')]
    
    equipamento = models.ForeignKey(Equipamento, on_delete=models.PROTECT, related_name='movimentacoes_estoque')
    tipo = models.CharField(max_length=7, choices=TIPO_MOVIMENTACAO)
    quantidade = models.PositiveIntegerField()
    data = models.DateTimeField(default=timezone.now)
    responsavel = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    justificativa = models.CharField(max_length=255)
    entrega_associada = models.ForeignKey(EntregaEPI, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'movimentacaoestoque'
        verbose_name = _("Movimentação de Estoque")
        verbose_name_plural = _("Movimentações de Estoque")
        ordering = ['-data']

        