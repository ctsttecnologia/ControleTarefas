
"""
Models do PGR - Programa de Gerenciamento de Riscos
Versão Refatorada e Otimizada

ARQUITETURA DE FILIAL:
  ✅ Models com campo `filial` direto → herdam BaseModel + FilialManager
  ✅ Models sem campo `filial` → definem `_filial_lookup` + FilialManager
  ⏭️  Models globais (Filial, User, PGRSecaoTextoPadrao) → sem filtro

TABELA DE LOOKUPS (models sem campo filial):
  ┌────────────────────────────┬──────────────────────────────────────────────────┐
  │ Model                      │ _filial_lookup                                   │
  ├────────────────────────────┼──────────────────────────────────────────────────┤
  │ CronogramaAcaoPGR          │ pgr_documento__filial_id                         │
  │ AvaliacaoQuantitativa      │ risco_identificado__pgr_documento__filial_id     │
  │ PGRDocumentoResponsavel    │ pgr_documento__filial_id                         │
  │ PGRSecaoTexto              │ pgr_documento__filial_id                         │
  │ RiscoEPIRecomendado        │ risco_identificado__pgr_documento__filial_id     │
  │ RiscoMedidaControle        │ risco_identificado__pgr_documento__filial_id     │
  │ RiscoTreinamentoNecessario │ risco_identificado__pgr_documento__filial_id     │
  │ AnexoPlanoAcao             │ plano_acao__risco_identificado__pgr_documento__… │
  │ AcompanhamentoPlanoAcao    │ plano_acao__risco_identificado__pgr_documento__… │
  └────────────────────────────┴──────────────────────────────────────────────────┘
"""

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model
from datetime import date, timedelta

from logradouro.constant import ESTADOS_BRASIL
from core.managers import FilialManager
from usuario.models import Filial
from departamento_pessoal.models import Cargo, Funcionario
from seguranca_trabalho.models import Equipamento, Funcao
from cliente.models import Cliente
from treinamentos.models import TipoCurso

User = get_user_model()


# =============================================================================
# CHOICES GLOBAIS
# =============================================================================

TIPO_EMPRESA_CHOICES = [
    ('contratante', 'Contratante'),
    ('contratada', 'Contratada'),
    ('prestadora', 'Prestadora de Serviços'),
]

CATEGORIA_RISCO_CHOICES = [
    ('fisico', 'Físico'),
    ('quimico', 'Químico'),
    ('biologico', 'Biológico'),
    ('ergonomico', 'Ergonômico'),
    ('acidente', 'Acidente/Mecânico'),
]

PERFIL_EXPOSICAO_CHOICES = [
    ('esporadica', 'Esporádica - 1'),
    ('pouco_frequente', 'Pouco Frequente - 2'),
    ('ocasional', 'Ocasional - 3'),
    ('frequente', 'Frequente - 4'),
    ('continua', 'Contínua - 5'),
]

GRAVIDADE_CHOICES = [
    (1, '1 - Pequeno porte'),
    (2, '2 - Médio porte'),
    (3, '3 - Grande porte'),
    (4, '4 - Muito grande porte'),
    (5, '5 - Catastrófico'),
]

EXPOSICAO_CHOICES = [
    (1, '1 - Raramente (1x por ano)'),
    (2, '2 - Ocasionalmente (1x por mês)'),
    (3, '3 - Frequentemente (1x por semana)'),
    (4, '4 - Constantemente (diariamente)'),
    (5, '5 - Constantemente (continuamente)'),
]

SEVERIDADE_CHOICES = [
    ('A', 'A - Negligenciável'),
    ('B', 'B - Marginal'),
    ('C', 'C - Moderado'),
    ('D', 'D - Muito Grave'),
    ('E', 'E - Crítico'),
]

PROBABILIDADE_CHOICES = [
    (1, '1 - Muito improvável'),
    (2, '2 - Improvável'),
    (3, '3 - Possível'),
    (4, '4 - Provável'),
    (5, '5 - Muito provável'),
]

CLASSIFICACAO_RISCO_CHOICES = [
    ('negligenciavel', 'Negligenciável'),
    ('marginal', 'Marginal'),
    ('moderado', 'Moderado'),
    ('muito_grave', 'Muito Grave'),
    ('critico', 'Crítico'),
]

STATUS_CONTROLE_CHOICES = [
    ('identificado', 'Identificado'),
    ('em_controle', 'Em Controle'),
    ('controlado', 'Controlado'),
    ('eliminado', 'Eliminado'),
]

PRIORIDADE_CHOICES = [
    ('baixa', 'Baixa'),
    ('media', 'Média'),
    ('alta', 'Alta'),
    ('critica', 'Crítica'),
]

METODO_AVALIACAO_CHOICES = [
    ('qualitativo', 'Qualitativo'),
    ('quantitativo', 'Quantitativo'),
    ('semi_quantitativo', 'Semi-Quantitativo'),
]

STATUS_PGR_CHOICES = [
    ('elaboracao', 'Em Elaboração'),
    ('vigente', 'Vigente'),
    ('vencido', 'Vencido'),
    ('em_revisao', 'Em Revisão'),
    ('cancelado', 'Cancelado'),
]

TIPO_ACAO_CHOICES = [
    ('eliminacao', 'Eliminação do Risco'),
    ('substituicao', 'Substituição'),
    ('controle_engenharia', 'Controle de Engenharia'),
    ('controle_administrativo', 'Controle Administrativo'),
    ('epi', 'Equipamento de Proteção Individual'),
    ('treinamento', 'Treinamento'),
    ('sinalizacao', 'Sinalização'),
]

STATUS_CHOICES = [
    ('pendente', 'Pendente'),
    ('em_andamento', 'Em Andamento'),
    ('concluido', 'Concluído'),
    ('atrasado', 'Atrasado'),
    ('cancelado', 'Cancelado'),
]

PERIODICIDADE_CHOICES = [
    ('admissao', 'Admissional'),
    ('continuo', 'Contínuo'),
    ('diario', 'Diário'),
    ('semanal', 'Semanal'),
    ('mensal', 'Mensal'),
    ('trimestral', 'Trimestral'),
    ('semestral', 'Semestral'),
    ('anual', 'Anual'),
    ('bienal', 'Bienal (2 anos)'),
    ('quando_necessario', 'Quando Necessário'),
]

TIPO_RESPONSABILIDADE_CHOICES = [
    ('elaborador', 'Elaborador'),
    ('revisor', 'Revisor'),
    ('aprovador', 'Aprovador'),
    ('coordenador', 'Coordenador'),
]

TIPO_AVALIACAO_CHOICES = [
    ('ruido', 'Ruído'),
    ('calor', 'Calor'),
    ('iluminacao', 'Iluminação'),
    ('agente_quimico', 'Agente Químico'),
    ('vibracao', 'Vibração'),
    ('radiacao', 'Radiação'),
    ('outro', 'Outro'),
]

UNIDADE_MEDIDA_CHOICES = [
    ('dB', 'dB (Decibéis)'),
    ('dB(A)', 'dB(A) (Decibéis ponderados em A)'),
    ('ppm', 'ppm (Partes por Milhão)'),
    ('mg/m³', 'mg/m³ (Miligrama por Metro Cúbico)'),
    ('f/cm³', 'f/cm³ (Fibras por Centímetro Cúbico)'),
    ('mW/cm²', 'mW/cm² (Miliwatt por Centímetro Quadrado)'),
    ('lux', 'Lux (Iluminância)'),
    ('ºC', '°C (Graus Celsius)'),
    ('IBUTG', 'IBUTG (Índice de Bulbo Úmido)'),
    ('m/s²', 'm/s² (Aceleração - Vibração)'),
    ('%', '% (Percentual)'),
    ('Bq', 'Bq (Becquerel - Radiação)'),
    ('mSv', 'mSv (Milisievert - Radiação)'),
    ('UR', 'UR (Umidade Relativa %)'),
    ('m/s', 'm/s (Metros por Segundo - Velocidade do Ar)'),
    ('outro', 'Outro'),
]


# =============================================================================
# ABSTRACT BASE MODEL
# =============================================================================

class BaseModel(models.Model):
    """
    Model abstrato base com campos comuns.
    Todos os models principais herdam daqui.
    Fornece: filial, ativo, criado_em, atualizado_em, criado_por, FilialManager.
    """

    ativo = models.BooleanField('Ativo', default=True)
    filial = models.ForeignKey(
        'usuario.Filial',
        on_delete=models.CASCADE,
        verbose_name='Filial'
    )
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Criado por'
    )

    objects = FilialManager()

    class Meta:
        abstract = True


# =============================================================================
# EMPRESA E LOCAIS
# =============================================================================

class Empresa(BaseModel):
    """Empresa vinculada a um Cliente para gestão do PGR"""

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        verbose_name='Cliente',
        related_name='pgr_empresas',
        related_query_name='pgr_empresa'
    )
    cnpj = models.CharField('CNPJ', max_length=18, blank=True)
    tipo_empresa = models.CharField(
        'Tipo de Empresa', max_length=20,
        choices=TIPO_EMPRESA_CHOICES, default='contratante'
    )
    cnae_especifico = models.CharField(
        'CNAE Específico', max_length=20, blank=True, null=True,
        help_text='Deixe em branco para usar o CNAE do cliente'
    )
    descricao_cnae = models.TextField('Descrição CNAE', blank=True, null=True)
    atividade_principal = models.TextField('Atividade Principal', blank=True, null=True)
    grau_risco = models.IntegerField(
        'Grau de Risco', choices=[(i, str(i)) for i in range(1, 5)],
        blank=True, null=True
    )
    grau_risco_texto = models.CharField('Grau de Risco (Texto)', max_length=100, blank=True, null=True)
    numero_empregados = models.IntegerField('Número de Empregados', blank=True, null=True)
    numero_empregados_texto = models.CharField('Número de Empregados (Texto)', max_length=100, blank=True, null=True)
    jornada_trabalho = models.CharField('Jornada de Trabalho', max_length=100, default='44 horas semanais')

    # Endereço
    endereco = models.CharField('Endereço', max_length=200, blank=True, null=True)
    numero = models.CharField('Número', max_length=10, blank=True, null=True)
    complemento = models.CharField('Complemento', max_length=100, blank=True, null=True)
    bairro = models.CharField('Bairro', max_length=100, blank=True, null=True)
    cidade = models.CharField('Cidade', max_length=100, blank=True, null=True)
    estado = models.CharField('UF', max_length=2, choices=ESTADOS_BRASIL, blank=True, null=True)
    cep = models.CharField('CEP', max_length=9, blank=True, null=True)

    # Contato
    telefone = models.CharField('Telefone', max_length=20, blank=True, null=True)
    email = models.EmailField('E-mail', blank=True, null=True)

    class Meta:
        db_table = 'pgr_empresa'
        verbose_name = 'Empresa PGR'
        verbose_name_plural = 'Empresas PGR'
        unique_together = ['cliente', 'filial']
        ordering = ['cliente__razao_social']

    def __str__(self):
        return f"{self.razao_social} ({self.get_tipo_empresa_display()})"

    @property
    def razao_social(self):
        return self.cliente.razao_social if self.cliente else 'Sem cliente vinculado'

    @property
    def cnae(self):
        return self.cnae_especifico or getattr(self.cliente, 'cnae', '')

    @property
    def endereco_completo(self):
        partes = filter(None, [
            self.endereco,
            f"nº {self.numero}" if self.numero else None,
            self.complemento, self.bairro,
            f"{self.cidade}/{self.estado}" if self.cidade and self.estado else None,
            f"CEP: {self.cep}" if self.cep else None
        ])
        return ', '.join(partes) or 'Endereço não cadastrado'


class LocalPrestacaoServico(BaseModel):
    """Local onde os serviços são executados"""

    empresa = models.ForeignKey(
        Cliente, on_delete=models.CASCADE,
        related_name='locais_prestacao_pgr',
        related_query_name='local_prestacao_pgr',
        verbose_name='Empresa'
    )
    razao_social = models.CharField('Razão Social', max_length=255)
    cnpj = models.CharField('CNPJ', max_length=18, blank=True)
    descricao = models.TextField('Descrição', blank=True)

    # Endereço
    endereco = models.CharField('Endereço', max_length=200, blank=True, null=True)
    numero = models.CharField('Número', max_length=10, blank=True, null=True)
    complemento = models.CharField('Complemento', max_length=100, blank=True, null=True)
    bairro = models.CharField('Bairro', max_length=100, blank=True, null=True)
    cidade = models.CharField('Cidade', max_length=100, blank=True, null=True)
    estado = models.CharField('UF', max_length=2, choices=ESTADOS_BRASIL, blank=True, null=True)
    cep = models.CharField('CEP', max_length=9, blank=True, null=True)

    class Meta:
        db_table = 'pgr_local_prestacao_servico'
        verbose_name = 'Local de Prestação de Serviço'
        verbose_name_plural = 'Locais de Prestação de Serviços'
        ordering = ['razao_social']

    def __str__(self):
        return f"{self.razao_social} - {self.empresa.razao_social}"

    @property
    def endereco_completo(self):
        partes = filter(None, [
            self.endereco,
            f"nº {self.numero}" if self.numero else None,
            self.complemento, self.bairro,
            f"{self.cidade}/{self.estado}" if self.cidade and self.estado else None,
            f"CEP: {self.cep}" if self.cep else None
        ])
        return ', '.join(partes)


class ProfissionalResponsavel(BaseModel):
    """Profissionais responsáveis pela elaboração do PGR"""

    funcionario = models.ForeignKey(
        Funcionario, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='Funcionário',
        related_name='responsabilidades_pgr',
        related_query_name='responsabilidade_pgr'
    )
    nome_completo = models.CharField('Nome Completo', max_length=200)
    funcao = models.CharField('Função/Cargo', max_length=100, help_text='Ex: Engenheiro de Segurança do Trabalho')
    registro_classe = models.CharField('Registro de Classe', max_length=50, help_text='Ex: 92307/D')
    orgao_classe = models.CharField('Órgão de Classe', max_length=50, blank=True, null=True, help_text='Ex: CREA-MG, MTE-SP')
    especialidade = models.CharField('Especialidade', max_length=200, blank=True, null=True)
    telefone = models.CharField('Telefone', max_length=20, blank=True, null=True)
    email = models.EmailField('E-mail', blank=True, null=True)

    class Meta:
        db_table = 'pgr_profissional_responsavel'
        verbose_name = 'Profissional Responsável'
        verbose_name_plural = 'Profissionais Responsáveis'
        ordering = ['nome_completo']

    def __str__(self):
        return f"{self.nome_completo} - {self.funcao}"

    def save(self, *args, **kwargs):
        if self.funcionario and not self.nome_completo:
            self.nome_completo = self.funcionario.nome_completo
            self.email = self.email or getattr(self.funcionario, 'email', None)
            self.telefone = self.telefone or getattr(self.funcionario, 'telefone', None)
        super().save(*args, **kwargs)


class AmbienteTrabalho(BaseModel):
    """Ambientes de trabalho específicos"""

    empresa = models.ForeignKey(
        Cliente, on_delete=models.CASCADE,
        related_name='ambientes_trabalho_pgr',
        related_query_name='ambiente_trabalho_pgr',
        verbose_name='Cliente', default=None
    )
    local_prestacao = models.ForeignKey(
        LocalPrestacaoServico, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='ambientes',
        verbose_name='Local de Prestação'
    )
    codigo = models.CharField('Código', max_length=50, unique=True)
    nome = models.CharField('Nome', max_length=200)
    descricao = models.TextField('Descrição', blank=True)
    caracteristicas = models.TextField(
        'Características', blank=True,
        help_text='Descrição física: alvenaria, piso, iluminação, ventilação'
    )

    class Meta:
        db_table = 'pgr_ambiente_trabalho'
        verbose_name = 'Ambiente de Trabalho'
        verbose_name_plural = 'Ambientes de Trabalho'
        ordering = ['codigo']

    def __str__(self):
        return f"{self.codigo} - {self.nome}"


# =============================================================================
# DOCUMENTO PGR
# =============================================================================

class PGRDocumento(BaseModel):
    """Documento principal do PGR"""

    empresa = models.ForeignKey(
        Cliente, on_delete=models.CASCADE,
        related_name='documentos_pgr',
        related_query_name='documento_pgr',
        verbose_name='Empresa Cliente', default=None
    )
    responsaveis = models.ManyToManyField(
        'ProfissionalResponsavel',
        through='PGRDocumentoResponsavel',
        verbose_name='Responsáveis', blank=True
    )
    local_prestacao = models.ForeignKey(
        LocalPrestacaoServico, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='documentos_pgr',
        verbose_name='Local de Prestação'
    )

    codigo_documento = models.CharField('Código do Documento', max_length=50, unique=True)
    data_elaboracao = models.DateField('Data de Elaboração')
    data_ultima_revisao = models.DateField('Data da Última Revisão', null=True, blank=True)
    data_vencimento = models.DateField('Data de Vencimento')
    status = models.CharField('Status', max_length=20, choices=STATUS_PGR_CHOICES, default='vigente')
    versao_atual = models.PositiveIntegerField('Versão Atual', default=1)
    objetivo = models.TextField('Objetivo do PGR', blank=True, null=True)
    escopo = models.TextField('Escopo', blank=True, null=True)
    metodologia_avaliacao = models.TextField('Metodologia de Avaliação', blank=True, null=True)
    observacoes = models.TextField('Observações', blank=True)

    class Meta:
        db_table = 'pgr_documento'
        verbose_name = 'Documento PGR'
        verbose_name_plural = 'Documentos PGR'
        ordering = ['-data_elaboracao']
        permissions = [
            ('revisar_pgr', 'Pode revisar PGR'),
            ('aprovar_pgr', 'Pode aprovar PGR'),
            ('visualizar_relatorios_pgr', 'Pode visualizar relatórios do PGR'),
        ]

    def __str__(self):
        return f"{self.codigo_documento} - {self.empresa.razao_social}"

    def get_absolute_url(self):
        return reverse('pgr_gestao:documento_detail', kwargs={'pk': self.pk})

    @property
    def dias_para_vencimento(self):
        return (self.data_vencimento - date.today()).days

    @property
    def dias_vencido(self):
        return max(0, -self.dias_para_vencimento)

    @property
    def percentual_conclusao(self):
        itens = [
            bool(self.codigo_documento),
            self.responsaveis.exists(),
            self.revisoes.exists(),
            self.grupos_exposicao.exists(),
            self.riscos_identificados.exists(),
            self.cronograma_acoes.exists(),
            self.dias_vencido == 0,
            self.status == 'vigente'
        ]
        return (sum(itens) / len(itens)) * 100


# =============================================================================
# DOCUMENTO PGR — MODELS FILHOS (sem campo filial, usam _filial_lookup)
# =============================================================================

class PGRDocumentoResponsavel(models.Model):
    """Vincula profissional responsável a documento PGR"""

    pgr_documento = models.ForeignKey(
        PGRDocumento, on_delete=models.CASCADE,
        verbose_name='Documento PGR', related_name='responsavel_info'
    )
    profissional = models.ForeignKey(
        ProfissionalResponsavel, on_delete=models.PROTECT,
        verbose_name='Profissional', related_name='documento_info'
    )
    tipo_responsabilidade = models.CharField(
        'Tipo de Responsabilidade', max_length=20,
        choices=TIPO_RESPONSABILIDADE_CHOICES, default='elaborador'
    )
    data_atribuicao = models.DateField('Data de Atribuição', default=date.today)

    # ── Filtro por filial via FK do pai ──
    _filial_lookup = 'pgr_documento__filial_id'
    objects = FilialManager()

    class Meta:
        db_table = 'pgr_responsavel_documento'
        verbose_name = 'Responsável pelo Documento'
        verbose_name_plural = 'Responsáveis pelo Documento'
        unique_together = ['pgr_documento', 'profissional']

    def __str__(self):
        return f"{self.profissional.nome_completo} - {self.get_tipo_responsabilidade_display()}"


class PGRRevisao(BaseModel):
    """Controle de revisões do PGR"""

    pgr_documento = models.ForeignKey(
        PGRDocumento, on_delete=models.CASCADE,
        related_name='revisoes', verbose_name='Documento PGR'
    )
    numero_revisao = models.PositiveIntegerField('Número da Revisão')
    descricao_revisao = models.TextField('Descrição da Revisão')
    data_realizacao = models.DateField('Data de Realização')
    realizada_por = models.CharField('Realizada Por', max_length=255, blank=True)
    motivo = models.CharField('Motivo', max_length=100, blank=True)
    observacoes = models.TextField('Observações', blank=True)

    class Meta:
        db_table = 'pgr_revisao'
        verbose_name = 'Revisão do PGR'
        verbose_name_plural = 'Revisões do PGR'
        ordering = ['pgr_documento', '-numero_revisao']
        unique_together = ['pgr_documento', 'numero_revisao']

    def __str__(self):
        return f"Revisão {self.numero_revisao:02d} - {self.pgr_documento.codigo_documento}"


# =============================================================================
# SEÇÕES DE TEXTO DO PGR
# =============================================================================

class PGRSecaoTexto(models.Model):
    """Textos editáveis das seções do PGR"""

    SECAO_CHOICES = [
        ('documento_base', '2. Documento Base'),
        ('documento_base_metas', '2. Documento Base - Metas'),
        ('documento_base_objetivo', '2. Documento Base - Objetivo Geral'),
        ('definicoes', '3. Definições'),
        ('estrutura_pgr', '4. Estrutura do PGR'),
        ('estrutura_requisitos', '4. Estrutura - Requisitos Legais'),
        ('estrutura_estrategia', '4. Estrutura - Estratégia e Metodologia'),
        ('estrutura_registro', '4. Estrutura - Forma de Registro'),
        ('estrutura_periodicidade', '4. Estrutura - Periodicidade'),
        ('estrutura_implantacao', '4. Estrutura - Implantação Cronograma'),
        ('estrutura_eficacia', '4. Estrutura - Análise da Eficácia'),
        ('responsabilidades', '5. Definição das Responsabilidades'),
        ('resp_organizacao', '5. Responsabilidades - Da Organização'),
        ('resp_informacao', '5. Responsabilidades - Da Informação'),
        ('resp_procedimentos', '5. Responsabilidades - Procedimentos'),
        ('resp_seguranca', '5. Responsabilidades - Da Segurança do Trabalho'),
        ('resp_cipa', '5. Responsabilidades - CIPA/Designado'),
        ('resp_medicina', '5. Responsabilidades - Da Medicina do Trabalho'),
        ('resp_supervisao', '5. Responsabilidades - Da Supervisão'),
        ('resp_empregados', '5. Responsabilidades - Dos Empregados'),
        ('diretrizes', '6. Diretrizes'),
        ('desenvolvimento', '7. Desenvolvimento do PGR'),
        ('metodologia_avaliacao', '8. Metodologia de Avaliação'),
        ('metodo_ruido', '8. Metodologia - Agente Físico Ruído'),
        ('metodo_calor', '8. Metodologia - Agente Físico Calor'),
        ('metodo_quimico', '8. Metodologia - Agentes Químicos'),
        ('metodo_biologico', '8. Metodologia - Agentes Biológicos'),
        ('metodo_ergonomico', '8. Metodologia - Agentes Ergonômicos'),
        ('metodo_mecanico', '8. Metodologia - Agentes Mecânicos'),
        ('inventario_riscos_intro', '9. Inventário de Riscos - Introdução'),
        ('plano_acao', '10. Plano de Ação'),
        ('medidas_protecao', '11. Medidas de Proteção'),
        ('medidas_epc', '11. Medidas - Proteção Coletiva'),
        ('medidas_administrativas', '11. Medidas - Administrativas'),
        ('medidas_epi', '11. Medidas - EPI'),
        ('medidas_uso_epi', '11. Medidas - Uso, Guarda e Conservação EPI'),
        ('divulgacao', '13. Divulgação do Programa'),
        ('recomendacoes', '14. Recomendações Gerais'),
        ('legislacao', '15. Legislação Complementar'),
        ('custom', 'Seção Personalizada'),
    ]

    pgr_documento = models.ForeignKey(
        PGRDocumento, on_delete=models.CASCADE,
        related_name='secoes_texto', verbose_name='Documento PGR'
    )
    secao = models.CharField('Seção', max_length=50, choices=SECAO_CHOICES)
    titulo_customizado = models.CharField(
        'Título Customizado', max_length=255, blank=True, null=True,
        help_text='Deixe em branco para usar o título padrão da seção'
    )
    conteudo = models.TextField(
        'Conteúdo', blank=True, null=True,
        help_text='Texto da seção. Deixe em branco para usar o texto padrão.'
    )
    ordem = models.PositiveIntegerField('Ordem de Exibição', default=0)
    incluir_no_pdf = models.BooleanField('Incluir no PDF', default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    # ── Filtro por filial via FK do pai ──
    _filial_lookup = 'pgr_documento__filial_id'
    objects = FilialManager()

    class Meta:
        db_table = 'pgr_secao_texto'
        verbose_name = 'Seção de Texto do PGR'
        verbose_name_plural = 'Seções de Texto do PGR'
        ordering = ['pgr_documento', 'ordem', 'secao']
        unique_together = ['pgr_documento', 'secao']

    def __str__(self):
        return f"{self.get_secao_display()} - {self.pgr_documento.codigo_documento}"


class PGRSecaoTextoPadrao(models.Model):
    """
    Textos PADRÃO globais das seções do PGR.
    ⏭️ Model GLOBAL — sem filtro por filial (é template do sistema).
    """

    secao = models.CharField('Seção', max_length=50, choices=PGRSecaoTexto.SECAO_CHOICES, unique=True)
    titulo = models.CharField('Título da Seção', max_length=255)
    conteudo_padrao = models.TextField(
        'Conteúdo Padrão',
        help_text='Texto padrão. Use {empresa} para substituir pelo nome da empresa.'
    )
    ativo = models.BooleanField('Ativo', default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pgr_secao_texto_padrao'
        verbose_name = 'Texto Padrão de Seção'
        verbose_name_plural = 'Textos Padrão de Seções'
        ordering = ['secao']

    def __str__(self):
        return f"{self.get_secao_display()} - {self.titulo}"


# =============================================================================
# GES - GRUPOS DE EXPOSIÇÃO SIMILAR
# =============================================================================

class GESGrupoExposicao(BaseModel):
    """Grupo de Exposição Similar (GES)"""

    pgr_documento = models.ForeignKey(
        PGRDocumento, on_delete=models.CASCADE,
        related_name='grupos_exposicao', verbose_name='Documento PGR'
    )
    codigo = models.CharField('Código do GES', max_length=50)
    nome = models.CharField('Nome do GES', max_length=200)
    ambiente_trabalho = models.ForeignKey(
        AmbienteTrabalho, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='grupos_exposicao',
        verbose_name='Ambiente de Trabalho', default=None
    )
    cargo = models.ForeignKey(
        Cargo, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ges_cargos_pgr', related_query_name='gges_cargos_pgr',
        verbose_name='Cargo'
    )
    funcao = models.ForeignKey(
        Funcao, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='gges_funcoes_pgr', related_query_name='gges_funcoes_pgr',
        verbose_name='Função'
    )
    numero_trabalhadores = models.PositiveIntegerField('Número de Trabalhadores', blank=True, null=True)
    jornada_trabalho = models.CharField('Jornada de Trabalho', max_length=100, default='44 horas semanais')
    horario_trabalho = models.CharField(
        'Horário de Trabalho', max_length=100, blank=True, null=True,
        help_text='Ex: 08:00 às 17:00'
    )
    descricao_atividades = models.TextField('Descrição das Atividades')
    equipamentos_utilizados = models.TextField('Equipamentos Utilizados', blank=True)
    produtos_manipulados = models.TextField('Produtos Manipulados', blank=True)

    class Meta:
        db_table = 'pgr_ges_grupo_exposicao_similar'
        verbose_name = 'GES - Grupo de Exposição Similar'
        verbose_name_plural = 'GES - Grupos de Exposição Similar'
        ordering = ['pgr_documento', 'codigo']
        unique_together = ['pgr_documento', 'codigo']

    def __str__(self):
        status = '' if self.ativo else ' [INATIVO]'
        return f"{self.codigo} - {self.nome}{status}"

    def get_absolute_url(self):
        return reverse('pgr_gestao:ges_detail', kwargs={'pk': self.pk})

    @property
    def total_riscos(self):
        return self.riscos.count()

    @property
    def riscos_criticos(self):
        return self.riscos.filter(classificacao_risco__in=['critico', 'muito_grave']).count()


# =============================================================================
# RISCOS
# =============================================================================

class TipoRisco(BaseModel):
    """Tipos de Riscos Ocupacionais"""

    categoria = models.CharField('Categoria', max_length=20, choices=CATEGORIA_RISCO_CHOICES)
    nome = models.CharField('Nome do Risco', max_length=200)
    descricao = models.TextField('Descrição', blank=True)
    codigo_cor = models.CharField(
        'Código da Cor', max_length=7, default='#808080',
        help_text='Cor no formato hexadecimal (#RRGGBB)'
    )
    nr_referencia = models.CharField('NR de Referência', max_length=50, blank=True, help_text='Ex: NR-15, NR-17')

    class Meta:
        db_table = 'pgr_tipo_risco'
        verbose_name = 'Tipo de Risco'
        verbose_name_plural = 'Tipos de Riscos'
        ordering = ['categoria', 'nome']

    def __str__(self):
        return f"{self.get_categoria_display()} - {self.nome}"


class RiscoIdentificado(BaseModel):
    """Riscos identificados no ambiente de trabalho"""

    pgr_documento = models.ForeignKey(
        PGRDocumento, on_delete=models.CASCADE,
        related_name='riscos_identificados', verbose_name='Documento PGR'
    )
    ges = models.ForeignKey(
        GESGrupoExposicao, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='riscos', verbose_name='GES'
    )
    ambiente_trabalho = models.ForeignKey(
        LocalPrestacaoServico, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='riscos',
        verbose_name='Ambiente de Trabalho', default='ambiente_trabalho'
    )
    cargo = models.ForeignKey(
        Cargo, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='riscos_pgr', related_query_name='risco_pgr',
        verbose_name='Cargo'
    )
    tipo_risco = models.ForeignKey(
        'gestao_riscos.TipoRisco', on_delete=models.PROTECT,
        related_name='riscos_pgr', verbose_name='Tipo de Risco'
    )

    # Identificação
    codigo_risco = models.CharField('Código do Risco', max_length=50, blank=True, null=True)
    agente = models.CharField('Agente de Risco', max_length=255)
    fonte_geradora = models.TextField('Fonte Geradora', blank=True, null=True)
    meio_propagacao = models.CharField('Meio de Propagação', max_length=255, blank=True, null=True)
    perfil_exposicao = models.CharField(
        'Perfil de Exposição', max_length=20,
        choices=PERFIL_EXPOSICAO_CHOICES, default='ocasional'
    )
    possiveis_efeitos_saude = models.TextField('Possíveis Efeitos à Saúde', blank=True)

    # Matriz de Avaliação
    gravidade_g = models.IntegerField(
        'Gravidade (G)', choices=GRAVIDADE_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    exposicao_e = models.IntegerField(
        'Exposição (E)', choices=EXPOSICAO_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    severidade_s = models.CharField('Severidade (S)', max_length=1, choices=SEVERIDADE_CHOICES)
    probabilidade_p = models.IntegerField(
        'Probabilidade (P)', choices=PROBABILIDADE_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    # Resultado
    classificacao_risco = models.CharField(
        'Classificação do Risco', max_length=20, choices=CLASSIFICACAO_RISCO_CHOICES
    )
    prioridade_acao = models.CharField(
        'Prioridade de Ação', max_length=20, choices=PRIORIDADE_CHOICES, default='media'
    )

    # Controle
    status_controle = models.CharField(
        'Status de Controle', max_length=20, choices=STATUS_CONTROLE_CHOICES, default='identificado'
    )
    metodo_avaliacao = models.CharField(
        'Método de Avaliação', max_length=20, choices=METODO_AVALIACAO_CHOICES, default='qualitativo'
    )
    medidas_controle_existentes = models.TextField('Medidas de Controle Existentes', blank=True)
    observacoes = models.TextField('Observações', blank=True)
    data_identificacao = models.DateField('Data de Identificação', default=date.today)

    class Meta:
        db_table = 'pgr_risco_identificado'
        verbose_name = 'Risco Identificado'
        verbose_name_plural = 'Riscos Identificados'
        ordering = ['-prioridade_acao', '-classificacao_risco', '-data_identificacao']
        indexes = [
            models.Index(fields=['pgr_documento', 'classificacao_risco']),
            models.Index(fields=['status_controle']),
            models.Index(fields=['prioridade_acao']),
        ]

    def __str__(self):
        return f"{self.tipo_risco.nome} - {self.agente}"

    def get_absolute_url(self):
        return reverse('pgr_gestao:risco_detail', kwargs={'pk': self.pk})

    @property
    def cor_classificacao(self):
        cores = {
            'negligenciavel': '#28a745',
            'marginal': '#ffc107',
            'moderado': '#fd7e14',
            'muito_grave': '#dc3545',
            'critico': '#6f0000',
        }
        return cores.get(self.classificacao_risco, '#808080')


# =============================================================================
# RISCOS — MODELS FILHOS (sem campo filial, usam _filial_lookup)
# =============================================================================

class AvaliacaoQuantitativa(models.Model):
    """Avaliações quantitativas de exposição"""

    risco_identificado = models.ForeignKey(
        RiscoIdentificado, on_delete=models.CASCADE,
        related_name='avaliacoes_quantitativas', verbose_name='Risco Identificado'
    )
    tipo_avaliacao = models.CharField('Tipo de Avaliação', max_length=50, choices=TIPO_AVALIACAO_CHOICES)
    metodologia_utilizada = models.CharField('Metodologia Utilizada', max_length=255, blank=True)
    data_avaliacao = models.DateField('Data da Avaliação')
    resultado_medido = models.DecimalField('Resultado Medido', max_digits=10, decimal_places=2)
    unidade_medida = models.CharField('Unidade de Medida', max_length=50, choices=UNIDADE_MEDIDA_CHOICES)
    limite_tolerancia_nr = models.CharField('Limite de Tolerância (NR)', max_length=100, blank=True, null=True)
    conforme = models.BooleanField('Conforme', default=True)
    equipamento_utilizado = models.CharField('Equipamento Utilizado', max_length=255, blank=True)
    responsavel_avaliacao = models.CharField('Responsável pela Avaliação', max_length=255, blank=True)
    observacoes = models.TextField('Observações', blank=True)
    laudo_tecnico = models.FileField('Laudo Técnico', upload_to='pgr/laudos/%Y/%m/', blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    # ── Filtro por filial via FK do pai ──
    _filial_lookup = 'risco_identificado__pgr_documento__filial_id'
    objects = FilialManager()

    class Meta:
        db_table = 'pgr_avaliacao_quantitativa'
        verbose_name = 'Avaliação Quantitativa'
        verbose_name_plural = 'Avaliações Quantitativas'
        ordering = ['-data_avaliacao']

    def __str__(self):
        return f"{self.get_tipo_avaliacao_display()} - {self.data_avaliacao}"


class MedidaControle(BaseModel):
    """Medidas de controle de riscos"""

    TIPO_CONTROLE_CHOICES = [
        ('eliminacao', 'Eliminação'),
        ('substituicao', 'Substituição'),
        ('engenharia', 'Controle de Engenharia'),
        ('administrativo', 'Controle Administrativo'),
        ('epi', 'EPI'),
    ]

    tipo_controle = models.CharField('Tipo de Controle', max_length=20, choices=TIPO_CONTROLE_CHOICES)
    descricao = models.TextField('Descrição da Medida')
    prioridade = models.PositiveIntegerField('Prioridade', default=1)
    nr_referencia = models.CharField('NR de Referência', max_length=50, blank=True)
    eficacia_esperada = models.CharField('Eficácia Esperada', max_length=100, blank=True)

    class Meta:
        db_table = 'pgr_medida_controle'
        verbose_name = 'Medida de Controle'
        verbose_name_plural = 'Medidas de Controle'
        ordering = ['prioridade', 'tipo_controle']

    def __str__(self):
        return f"{self.get_tipo_controle_display()} - {self.descricao[:50]}"


class RiscoMedidaControle(models.Model):
    """Relacionamento entre Risco e Medida de Controle"""

    risco_identificado = models.ForeignKey(
        RiscoIdentificado, on_delete=models.CASCADE,
        related_name='medidas_controle', verbose_name='Risco'
    )
    medida_controle = models.ForeignKey(
        MedidaControle, on_delete=models.CASCADE,
        related_name='riscos', verbose_name='Medida de Controle'
    )
    implementada = models.BooleanField('Implementada', default=False)
    data_implementacao = models.DateField('Data de Implementação', blank=True, null=True)
    responsavel_implementacao = models.CharField('Responsável pela Implementação', max_length=255, blank=True)
    observacoes = models.TextField('Observações', blank=True)

    # ── Filtro por filial via FK do pai ──
    _filial_lookup = 'risco_identificado__pgr_documento__filial_id'
    objects = FilialManager()

    class Meta:
        db_table = 'pgr_risco_medida_controle'
        verbose_name = 'Risco x Medida de Controle'
        verbose_name_plural = 'Riscos x Medidas de Controle'
        unique_together = ['risco_identificado', 'medida_controle']

    def __str__(self):
        return f"{self.risco_identificado} - {self.medida_controle}"


# =============================================================================
# PLANOS DE AÇÃO
# =============================================================================

class PlanoAcaoPGR(BaseModel):
    """Planos de ação para controle de riscos"""

    risco_identificado = models.ForeignKey(
        RiscoIdentificado, on_delete=models.CASCADE,
        related_name='planos_acao', verbose_name='Risco Identificado'
    )
    tipo_acao = models.CharField('Tipo de Ação', max_length=30, choices=TIPO_ACAO_CHOICES)
    descricao_acao = models.TextField('Descrição da Ação')
    justificativa = models.TextField('Justificativa', blank=True)
    prioridade = models.CharField('Prioridade', max_length=20, choices=PRIORIDADE_CHOICES, default='media')
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='pendente')
    responsavel = models.CharField('Responsável', max_length=255)
    data_prevista = models.DateField('Data Prevista')
    data_conclusao = models.DateField('Data de Conclusão', blank=True, null=True)
    custo_estimado = models.DecimalField('Custo Estimado (R$)', max_digits=12, decimal_places=2, blank=True, null=True)
    custo_real = models.DecimalField('Custo Real (R$)', max_digits=12, decimal_places=2, blank=True, null=True)
    evidencia = models.FileField('Evidência de Conclusão', upload_to='pgr/evidencias/%Y/%m/', blank=True, null=True)
    evidencia_conclusao = models.TextField('Descrição da Evidência', blank=True)
    recursos_necessarios = models.TextField('Recursos Necessários', blank=True)
    eficacia_acao = models.TextField('Eficácia da Ação', blank=True)
    resultado_obtido = models.TextField('Resultado Obtido', blank=True)
    observacoes = models.TextField('Observações', blank=True)

    class Meta:
        db_table = 'pgr_plano_acao'
        verbose_name = 'Plano de Ação'
        verbose_name_plural = 'Planos de Ação'
        ordering = ['-prioridade', 'data_prevista']
        indexes = [
            models.Index(fields=['status', 'data_prevista']),
            models.Index(fields=['prioridade']),
        ]

    def __str__(self):
        return f"{self.get_tipo_acao_display()} - {self.descricao_acao[:50]}"

    def get_absolute_url(self):
        return reverse('pgr_gestao:plano_acao_detail', kwargs={'pk': self.pk})

    @property
    def esta_atrasado(self):
        if self.status in ['pendente', 'em_andamento']:
            return self.data_prevista < date.today()
        return False

    @property
    def dias_atraso(self):
        """Retorna o número de dias de atraso (0 se não atrasado)."""
        if self.data_prevista and self.status in ['pendente', 'em_andamento']:
            from django.utils import timezone
            delta = (timezone.now().date() - self.data_prevista).days
            return max(delta, 0)
        return 0


# =============================================================================
# PLANOS DE AÇÃO — MODELS FILHOS (sem campo filial, usam _filial_lookup)
# =============================================================================

class AnexoPlanoAcao(models.Model):
    """Anexos do Plano de Ação"""

    plano_acao = models.ForeignKey(
        PlanoAcaoPGR, on_delete=models.CASCADE,
        related_name='anexos', verbose_name='Plano de Ação'
    )
    nome_arquivo = models.CharField('Nome do Arquivo', max_length=255)
    arquivo = models.FileField('Arquivo', upload_to='pgr/planos_acao/anexos/%Y/%m/')
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='Criado por'
    )
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)

    # ── Filtro por filial via FK do pai ──
    _filial_lookup = 'plano_acao__risco_identificado__pgr_documento__filial_id'
    objects = FilialManager()

    class Meta:
        db_table = 'pgr_anexo_plano_acao'
        verbose_name = 'Anexo do Plano de Ação'
        verbose_name_plural = 'Anexos dos Planos de Ação'
        ordering = ['-criado_em']

    def __str__(self):
        return self.nome_arquivo


class AcompanhamentoPlanoAcao(models.Model):
    """Registro de acompanhamento e evolução dos planos de ação"""

    plano_acao = models.ForeignKey(
        PlanoAcaoPGR, on_delete=models.CASCADE,
        verbose_name='Plano de Ação', related_name='acompanhamentos'
    )
    data_acompanhamento = models.DateField('Data do Acompanhamento', default=date.today)
    status_anterior = models.CharField(
        'Status Anterior', max_length=20, choices=STATUS_CHOICES,
        blank=True, null=True
    )
    status_atual = models.CharField('Status Atual', max_length=20, choices=STATUS_CHOICES)
    percentual_conclusao = models.DecimalField(
        'Percentual de Conclusão', max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='0 a 100%'
    )
    descricao = models.TextField('Descrição do Acompanhamento')
    evidencias = models.TextField('Evidências/Comprovações', blank=True, null=True)
    arquivo_evidencia = models.FileField(
        'Arquivo de Evidência', upload_to='pgr/acompanhamentos/%Y/%m/',
        blank=True, null=True
    )
    dificuldades = models.TextField('Dificuldades Encontradas', blank=True, null=True)
    proximos_passos = models.TextField('Próximos Passos', blank=True, null=True)
    responsavel_acompanhamento = models.CharField('Responsável pelo Acompanhamento', max_length=200)
    observacoes = models.TextField('Observações', blank=True, null=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='Criado por',
        related_name='acompanhamentos_plano_criados'
    )
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True)

    # ── Filtro por filial via FK do pai ──
    _filial_lookup = 'plano_acao__risco_identificado__pgr_documento__filial_id'
    objects = FilialManager()

    class Meta:
        db_table = 'pgr_acompanhamento_plano_acao'
        verbose_name = 'Acompanhamento de Plano de Ação'
        verbose_name_plural = 'Acompanhamentos de Planos de Ação'
        ordering = ['-data_acompanhamento', '-criado_em']
        indexes = [
            models.Index(fields=['plano_acao', '-data_acompanhamento']),
        ]

    def __str__(self):
        return f"Acompanhamento de {self.plano_acao.descricao_acao[:30]} - {self.data_acompanhamento.strftime('%d/%m/%Y')}"

    def save(self, *args, **kwargs):
        if not self.pk and self.plano_acao:
            self.status_anterior = self.plano_acao.status
        super().save(*args, **kwargs)
        if self.status_atual and self.plano_acao:
            plano = self.plano_acao
            plano.status = self.status_atual
            if self.status_atual == 'concluido' and not plano.data_conclusao:
                plano.data_conclusao = self.data_acompanhamento
            plano.save(update_fields=['status', 'data_conclusao'])


# =============================================================================
# CRONOGRAMA E COMPLEMENTOS (sem campo filial, usam _filial_lookup)
# =============================================================================

class CronogramaAcaoPGR(models.Model):
    """Cronograma de ações do PGR"""

    pgr_documento = models.ForeignKey(
        PGRDocumento, on_delete=models.CASCADE,
        related_name='cronograma_acoes', verbose_name='Documento PGR'
    )
    numero_item = models.PositiveIntegerField('Número do Item')
    acao_necessaria = models.TextField('Ação Necessária')
    publico_alvo = models.CharField('Público Alvo', max_length=255, default='Todos os colaboradores')
    periodicidade = models.CharField('Periodicidade', max_length=20, choices=PERIODICIDADE_CHOICES)
    responsavel = models.CharField('Responsável', max_length=255, blank=True)
    data_proxima_avaliacao = models.DateField('Próxima Avaliação', blank=True, null=True)
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='pendente')
    data_realizacao = models.DateField('Data de Realização', blank=True, null=True)
    observacoes = models.TextField('Observações', blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    # ── Filtro por filial via FK do pai ──
    _filial_lookup = 'pgr_documento__filial_id'
    objects = FilialManager()

    class Meta:
        db_table = 'pgr_cronograma_acao'
        verbose_name = 'Cronograma de Ação'
        verbose_name_plural = 'Cronograma de Ações'
        ordering = ['pgr_documento', 'numero_item']
        unique_together = ['pgr_documento', 'numero_item']

    def __str__(self):
        return f"{self.numero_item:02d} - {self.acao_necessaria[:50]}"


class RiscoEPIRecomendado(models.Model):
    """EPIs recomendados para cada risco"""

    risco_identificado = models.ForeignKey(
        RiscoIdentificado, on_delete=models.CASCADE,
        related_name='epis_recomendados', verbose_name='Risco'
    )
    equipamento = models.ForeignKey(
        Equipamento, on_delete=models.PROTECT,
        related_name='riscos_recomendados', verbose_name='Equipamento'
    )
    ca_numero = models.CharField('Número do CA', max_length=50, blank=True)
    obrigatorio = models.BooleanField('Obrigatório', default=True)
    observacoes = models.TextField('Observações', blank=True)

    # ── Filtro por filial via FK do pai ──
    _filial_lookup = 'risco_identificado__pgr_documento__filial_id'
    objects = FilialManager()

    class Meta:
        db_table = 'pgr_risco_epi_recomendado'
        verbose_name = 'EPI Recomendado'
        verbose_name_plural = 'EPIs Recomendados'
        unique_together = ['risco_identificado', 'equipamento']

    def __str__(self):
        return f"{self.equipamento.nome} - {self.risco_identificado.agente}"


class RiscoTreinamentoNecessario(models.Model):
    """Treinamentos necessários para cada risco"""

    risco_identificado = models.ForeignKey(
        RiscoIdentificado, on_delete=models.CASCADE,
        related_name='treinamentos_necessarios', verbose_name='Risco'
    )
    tipo_curso = models.ForeignKey(
        'treinamentos.TipoCurso', on_delete=models.PROTECT,
        related_name='riscos_associados', verbose_name='Tipo de Curso'
    )
    periodicidade = models.CharField(
        'Periodicidade', max_length=20, choices=PERIODICIDADE_CHOICES, default='anual'
    )
    carga_horaria = models.PositiveIntegerField('Carga Horária (horas)', blank=True, null=True)
    obrigatorio = models.BooleanField('Obrigatório', default=True)
    observacoes = models.TextField('Observações', blank=True)

    # ── Filtro por filial via FK do pai ──
    _filial_lookup = 'risco_identificado__pgr_documento__filial_id'
    objects = FilialManager()

    class Meta:
        db_table = 'pgr_risco_treinamento_necessario'
        verbose_name = 'Treinamento Necessário'
        verbose_name_plural = 'Treinamentos Necessários'
        unique_together = ['risco_identificado', 'tipo_curso']

    def __str__(self):
        return f"{self.tipo_curso.nome} - {self.risco_identificado.agente}"

