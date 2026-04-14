# ltcat/models.py

"""
Models do LTCAT - Laudo Técnico das Condições Ambientais do Trabalho
Seguindo
"""

import os

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model
from datetime import date
from core.upload import delete_old_file, safe_delete_file
from core.validators import SecureFileValidator, SecureImageValidator
from logradouro.constant import ESTADOS_BRASIL
from core.managers import FilialManager
from usuario.models import Filial
from departamento_pessoal.models import Cargo, Funcionario
from seguranca_trabalho.models import Funcao
from cliente.models import Cliente
from core.mixins import make_upload_path, sanitize_image
from core.magic_utils import get_mime_type

User = get_user_model()


# =============================================================================
# CHOICES GLOBAIS DO LTCAT
# =============================================================================

TIPO_RISCO_CHOICES = [
    ('fisico', 'Físico'),
    ('quimico', 'Químico'),
    ('biologico', 'Biológico'),
    ('ergonomico', 'Ergonômico'),
    ('acidente', 'Acidente/Mecânico'),
]

TIPO_EXPOSICAO_CHOICES = [
    ('continua', 'Contínua'),
    ('intermitente', 'Intermitente'),
    ('esporadico', 'Esporádico'),
    ('frequente', 'Frequente'),
]

TIPO_AVALIACAO_CHOICES = [
    ('qualitativo', 'Qualitativo'),
    ('quantitativo', 'Quantitativo'),
]

STATUS_LTCAT_CHOICES = [
    ('rascunho', 'Rascunho'),
    ('em_elaboracao', 'Em Elaboração'),
    ('em_revisao', 'Em Revisão'),
    ('aprovado', 'Aprovado'),
    ('vigente', 'Vigente'),
    ('vencido', 'Vencido'),
    ('cancelado', 'Cancelado'),
]

TIPO_CONCLUSAO_CHOICES = [
    ('sem_exposicao', 'Sem exposição a agentes nocivos'),
    ('insalubre_minimo', 'Insalubre - Grau Mínimo (10%)'),
    ('insalubre_medio', 'Insalubre - Grau Médio (20%)'),
    ('insalubre_maximo', 'Insalubre - Grau Máximo (40%)'),
    ('periculoso', 'Periculoso (30% salário base)'),
    ('aposentadoria_15', 'Aposentadoria Especial - 15 anos'),
    ('aposentadoria_20', 'Aposentadoria Especial - 20 anos'),
    ('aposentadoria_25', 'Aposentadoria Especial - 25 anos'),
]

CODIGO_GFIP_CHOICES = [
    ('00', '00 - Nunca exposto'),
    ('01', '01 - Exposto e neutralizado'),
    ('02', '02 - Apos. especial 15 anos'),
    ('03', '03 - Apos. especial 20 anos'),
    ('04', '04 - Apos. especial 25 anos'),
    ('05', '05 - Nunca exposto (multi-vínculo)'),
    ('06', '06 - Apos. especial 15 anos (multi-vínculo)'),
    ('07', '07 - Apos. especial 20 anos (multi-vínculo)'),
    ('08', '08 - Apos. especial 25 anos (multi-vínculo)'),
]

TIPO_PERICULOSIDADE_CHOICES = [
    ('explosivos', 'Explosivos (NR-16, Anexo 01)'),
    ('inflamaveis', 'Inflamáveis (NR-16, Anexo 02)'),
    ('violencia', 'Exposição a Roubos/Violência (NR-16, Anexo 03)'),
    ('eletricidade', 'Eletricidade (NR-16, Anexo 04)'),
    ('transito', 'Agentes de Trânsito (NR-16, Anexo 06)'),
    ('radiacao', 'Radiações Ionizantes (NR-16)'),
]

PRIORIDADE_CHOICES = [
    ('baixa', 'Baixa'),
    ('media', 'Média'),
    ('alta', 'Alta'),
]

TIPO_ANEXO_LTCAT_CHOICES = [
    ('info_engenheiro', 'Informações do Engenheiro de Segurança'),
    ('art', 'ART - Anotação de Responsabilidade Técnica'),
    ('laudo_dosimetria', 'Laudos das Dosimetrias Realizadas'),
    ('laudo_quimico', 'Laudos das Avaliações Químicas'),
    ('certificado_calibracao', 'Certificado de Calibração'),
    ('ppp', 'Perfil Profissiográfico Previdenciário'),
    ('foto', 'Registro Fotográfico'),
    ('outro', 'Outro'),
]

TIPO_RESPONSABILIDADE_LTCAT_CHOICES = [
    ('elaborador', 'Elaborador'),
    ('revisor', 'Revisor'),
    ('aprovador', 'Aprovador'),
    ('coordenador', 'Coordenador'),
]

UNIDADE_MEDIDA_LTCAT_CHOICES = [
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
    ('mSv', 'mSv (Milisievert - Radiação)'),
    ('outro', 'Outro'),
]

SECAO_LTCAT_CHOICES = [
    # Seção 2
    ('objetivo', '2. Objetivo'),

    # Seção 3
    ('condicoes_preliminares', '3. Condições Preliminares'),

    # Seção 4
    ('codigos_gfip', '4. Códigos do Sistema SEFIP/GFIP'),
    ('trabalho_permanente', '4. Trabalho Permanente Não Ocasional'),
    ('agentes_nocivos', '4. Agentes Nocivos Constatados no LTCAT'),

    # Seção 5
    ('ppp_finalidade', '5. PPP - Finalidade'),
    ('ppp_impressao', '5. PPP - Condições de Impressão'),
    ('ppp_especificacoes', '5. PPP - Especificações'),

    # Seção 8
    ('avaliacao_periculosidade', '8. Avaliação das Atividades Periculosas'),

    # Seção 11
    ('embasamento_ruido', '11.1. Agente Físico Ruído - NR-15 Anexo 1'),
    ('embasamento_demais', '11.2. Demais Agentes Insalubres'),

    # Seção 12
    ('referencias_bibliograficas', '12. Referências Bibliográficas'),

    # Customizado
    ('custom', 'Seção Personalizada'),
]


# =============================================================================
# ABSTRACT BASE MODEL (igual ao PGR)
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
# EMPRESA E LOCAIS (vinculados ao LTCAT)
# =============================================================================

class EmpresaLTCAT(BaseModel):
    """Empresa vinculada a um Cliente para gestão do LTCAT"""

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        verbose_name='Cliente',
        related_name='ltcat_empresas',
        related_query_name='ltcat_empresa'
    )
    cnpj = models.CharField('CNPJ', max_length=18, blank=True)
    cnae = models.CharField('CNAE', max_length=200, blank=True, null=True)
    descricao_cnae = models.TextField('Descrição CNAE', blank=True, null=True)
    grau_risco = models.CharField('Grau de Risco', max_length=100, blank=True, null=True)
    grau_risco_texto = models.CharField(
        'Grau de Risco (Texto)', max_length=200, blank=True, null=True,
        help_text='Ex: 03 (três) estando trabalhando nas instalações do contratante.'
    )
    atividade_principal = models.TextField('Atividade Principal', blank=True, null=True)
    numero_empregados = models.IntegerField('Número de Empregados', blank=True, null=True)
    numero_empregados_texto = models.CharField(
        'Número de Empregados (Texto)', max_length=200, blank=True, null=True,
        help_text='Ex: 9 (Nove), sendo 8 fixos e 1 coordenador em visitas quinzenais.'
    )
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
        db_table = 'ltcat_empresa'
        verbose_name = 'Empresa LTCAT'
        verbose_name_plural = 'Empresas LTCAT'
        unique_together = ['cliente', 'filial']
        ordering = ['cliente__razao_social']

    def __str__(self):
        return f"{self.razao_social}"

    @property
    def razao_social(self):
        return self.cliente.razao_social if self.cliente else 'Sem cliente vinculado'

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


class LocalPrestacaoServicoLTCAT(BaseModel):
    """
    Local onde os serviços são efetivamente prestados.
    Agora vinculado ao app Logradouro para busca de endereço.
    Um documento LTCAT pode ter VÁRIOS locais (via M2M intermediária).
    """

    empresa = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name='locais_prestacao_ltcat',
        related_query_name='local_prestacao_ltcat',
        verbose_name='Empresa (Cliente)'
    )
    logradouro = models.ForeignKey(
        'logradouro.Logradouro',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='locais_prestacao_ltcat',
        verbose_name='Endereço (Logradouro)',
        help_text='Selecione o endereço cadastrado no sistema de logradouros'
    )
    nome_local = models.CharField(
        'Nome / Identificação do Local', max_length=300,
        help_text='Ex: Unidade Operacional Camaçari, Sede Administrativa, etc.'
    )
    razao_social = models.CharField('Razão Social', max_length=300, blank=True)
    cnpj = models.CharField('CNPJ', max_length=18, blank=True)
    descricao = models.TextField('Descrição', blank=True)

    # Endereço manual (fallback caso não use logradouro)
    endereco = models.CharField('Endereço', max_length=500, blank=True, null=True)
    numero = models.CharField('Número', max_length=10, blank=True, null=True)
    complemento = models.CharField('Complemento', max_length=100, blank=True, null=True)
    bairro = models.CharField('Bairro', max_length=100, blank=True, null=True)
    cidade = models.CharField('Cidade', max_length=100, blank=True, null=True)
    estado = models.CharField('UF', max_length=2, choices=ESTADOS_BRASIL, blank=True, null=True)
    cep = models.CharField('CEP', max_length=10, blank=True, null=True)

    class Meta:
        db_table = 'ltcat_local_prestacao_servico'
        verbose_name = 'Local de Prestação de Serviço LTCAT'
        verbose_name_plural = 'Locais de Prestação de Serviço LTCAT'
        ordering = ['nome_local']

    def __str__(self):
        cidade = self.cidade_display
        return f"{self.nome_local} - {cidade}" if cidade else self.nome_local

    @property
    def cidade_display(self):
        """Retorna cidade/UF do logradouro ou do campo manual"""
        if self.logradouro:
            return f"{self.logradouro.cidade}/{self.logradouro.estado}"
        if self.cidade and self.estado:
            return f"{self.cidade}/{self.estado}"
        return ''

    @property
    def endereco_completo(self):
        """Monta endereço completo priorizando o Logradouro vinculado"""
        if self.logradouro:
            log = self.logradouro
            partes = filter(None, [
                log.endereco,
                f"nº {log.numero}" if log.numero else None,
                log.complemento,
                log.bairro,
                f"{log.cidade}/{log.estado}" if log.cidade and log.estado else None,
                f"CEP: {log.cep}" if log.cep else None
            ])
            return ', '.join(partes) or 'Endereço não cadastrado'

        # Fallback: campos manuais
        partes = filter(None, [
            self.endereco,
            f"nº {self.numero}" if self.numero else None,
            self.complemento,
            self.bairro,
            f"{self.cidade}/{self.estado}" if self.cidade and self.estado else None,
            f"CEP: {self.cep}" if self.cep else None
        ])
        return ', '.join(partes) or 'Endereço não cadastrado'


class ProfissionalResponsavelLTCAT(BaseModel):
    """Profissionais responsáveis pela elaboração do LTCAT"""

    funcionario = models.ForeignKey(
        Funcionario, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='Funcionário',
        related_name='responsabilidades_ltcat',
        related_query_name='responsabilidade_ltcat'
    )
    nome_completo = models.CharField('Nome Completo', max_length=200)
    funcao = models.CharField(
        'Função/Cargo', max_length=200,
        help_text='Ex: Engenheiro Mecânico e de Segurança do Trabalho'
    )
    registro_classe = models.CharField(
        'Registro de Classe', max_length=100,
        help_text='Ex: CREA-MG 92307/D'
    )
    orgao_classe = models.CharField(
        'Órgão de Classe', max_length=50, blank=True, null=True,
        help_text='Ex: CREA-MG, CRM-SP, MTE-SP'
    )
    especialidade = models.CharField('Especialidade', max_length=200, blank=True, null=True)
    telefone = models.CharField('Telefone', max_length=20, blank=True, null=True)
    email = models.EmailField('E-mail', blank=True, null=True)
    assinatura_imagem = models.ImageField(
        'Assinatura Digital',
        upload_to=make_upload_path('ltcat_assinatura'),  # UUID + path seguro
        blank=True,
        null=True,
        help_text='Imagem da assinatura digital (JPG, PNG, WEBP — máx. 2MB)',
        validators=[SecureImageValidator('ltcat_assinatura')],  # Validação completa
    )

    class Meta:
        db_table = 'ltcat_profissional_responsavel'
        verbose_name = 'Profissional Responsável LTCAT'
        verbose_name_plural = 'Profissionais Responsáveis LTCAT'
        ordering = ['nome_completo']

    def __str__(self):
        return f"{self.nome_completo} - {self.funcao}"

    def save(self, *args, **kwargs):
        delete_old_file(self, 'assinatura_imagem')           # ← adicionar

        if self.funcionario and not self.nome_completo:
            self.nome_completo = self.funcionario.nome_completo
            self.email    = self.email    or getattr(self.funcionario, 'email',    None)
            self.telefone = self.telefone or getattr(self.funcionario, 'telefone', None)

        if self.assinatura_imagem and hasattr(self.assinatura_imagem.file, 'seek'):
            try:
                from core.mixins import _sanitize_image
                self.assinatura_imagem = _sanitize_image(self.assinatura_imagem)
            except Exception:
                pass

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        safe_delete_file(self, 'assinatura_imagem')
        super().delete(*args, **kwargs)
# =============================================================================
# DOCUMENTO LTCAT (Principal)
# =============================================================================

class LTCATDocumento(BaseModel):
    """Documento principal — Laudo Técnico das Condições Ambientais do Trabalho"""

    # ── Empresa CONTRATANTE (Cliente) ──
    empresa = models.ForeignKey(
        Cliente, on_delete=models.CASCADE,
        related_name='documentos_ltcat',
        related_query_name='documento_ltcat',
        verbose_name='Empresa Contratante (Cliente)',
        default=None
    )

    # ── Empresa CONTRATADA (CETEST)
    empresa_contratada = models.ForeignKey(
        'EmpresaLTCAT', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='documentos_ltcat_contratada',
        verbose_name='Empresa Contratada (CETEST)',
        help_text='Empresa que elabora o LTCAT (ex: CETEST)'
    )

    # ── Locais de Prestação (MÚLTIPLOS)
    locais_prestacao = models.ManyToManyField(
        LocalPrestacaoServicoLTCAT,
        through='DocumentoLocalPrestacao',
        verbose_name='Locais de Prestação',
        blank=True
    )

    responsaveis = models.ManyToManyField(
        'ProfissionalResponsavelLTCAT',
        through='LTCATDocumentoResponsavel',
        verbose_name='Responsáveis', blank=True
    )

    # ── Restante dos campos permanece IGUAL ──
    codigo_documento = models.CharField('Código do Documento', max_length=50, unique=True)
    titulo = models.CharField(
        'Título', max_length=300,
        default='LTCAT - Laudo Técnico das Condições Ambientais do Trabalho'
    )
    data_elaboracao = models.DateField('Data de Elaboração')
    data_ultima_revisao = models.DateField('Data da Última Revisão', null=True, blank=True)
    data_vencimento = models.DateField(
        'Data de Vencimento', null=True, blank=True,
        help_text='Deixe em branco para "Sem vencimento"'
    )
    status = models.CharField(
        'Status', max_length=20,
        choices=STATUS_LTCAT_CHOICES, default='rascunho'
    )
    versao_atual = models.PositiveIntegerField('Versão Atual', default=1)
    objetivo = models.TextField('Objetivo', blank=True, null=True)
    condicoes_preliminares = models.TextField(
        'Condições Preliminares', blank=True, null=True,
        default='O trabalho de levantamento de dados foi realizado no local da prestação de serviços.'
    )
    avaliacao_periculosidade_texto = models.TextField(
        'Avaliação Geral de Periculosidade', blank=True, null=True
    )
    referencias_bibliograficas = models.TextField(
        'Referências Bibliográficas', blank=True, null=True
    )
    observacoes = models.TextField('Observações', blank=True)

    class Meta:
        db_table = 'ltcat_documento'
        verbose_name = 'Documento LTCAT'
        verbose_name_plural = 'Documentos LTCAT'
        ordering = ['-data_elaboracao']
        permissions = [
            ('revisar_ltcat', 'Pode revisar LTCAT'),
            ('aprovar_ltcat', 'Pode aprovar LTCAT'),
            ('visualizar_relatorios_ltcat', 'Pode visualizar relatórios do LTCAT'),
        ]

    def __str__(self):
        return f"{self.codigo_documento} - {self.empresa.razao_social}"

    def get_absolute_url(self):
        return reverse('ltcat:documento_detail', kwargs={'pk': self.pk})

    # ── Novas properties ──
    @property
    def local_prestacao_principal(self):
        """Retorna o local marcado como principal (compatibilidade)"""
        vinculo = self.documento_locais.filter(principal=True).select_related('local_prestacao').first()
        if vinculo:
            return vinculo.local_prestacao
        # Fallback: primeiro local
        vinculo = self.documento_locais.select_related('local_prestacao').first()
        return vinculo.local_prestacao if vinculo else None

    @property
    def todos_locais_prestacao(self):
        """Retorna QuerySet ordenado de todos os locais"""
        return self.locais_prestacao.all().order_by(
            '-documentolocalprestacao__principal',
            'documentolocalprestacao__ordem'
        )

    @property
    def nome_contratada(self):
        """Nome da empresa contratada (CETEST)"""
        if self.empresa_contratada:
            return self.empresa_contratada.razao_social
        return 'Não informada'

    @property
    def nome_contratante(self):
        """Nome da empresa contratante (Cliente)"""
        if self.empresa:
            return self.empresa.razao_social
        return 'Não informada'

    # ── Properties existentes (mantidas) ──

    @property
    def is_vencido(self):
        if self.data_vencimento:
            return self.data_vencimento < date.today()
        return False

    @property
    def dias_para_vencimento(self):
        if self.data_vencimento:
            return (self.data_vencimento - date.today()).days
        return None

    @property
    def revisao_atual(self):
        return self.revisoes.order_by('-numero_revisao').first()

    @property
    def percentual_conclusao(self):
        itens = [
            bool(self.codigo_documento),
            self.responsaveis.exists(),
            self.revisoes.exists(),
            self.funcoes.exists(),
            self.funcoes.filter(riscos__isnull=False).exists(),
            self.conclusoes.exists(),
            self.is_vencido is False,
            self.status == 'vigente',
        ]
        return (sum(itens) / len(itens)) * 100


# =============================================================================
# DOCUMENTO LTCAT — MODELS FILHOS (sem campo filial, usam _filial_lookup)
# =============================================================================

class LTCATDocumentoResponsavel(models.Model):
    """Vincula profissional responsável a documento LTCAT"""

    ltcat_documento = models.ForeignKey(
        LTCATDocumento, on_delete=models.CASCADE,
        verbose_name='Documento LTCAT', related_name='responsavel_info'
    )
    profissional = models.ForeignKey(
        ProfissionalResponsavelLTCAT, on_delete=models.PROTECT,
        verbose_name='Profissional', related_name='documento_info'
    )
    tipo_responsabilidade = models.CharField(
        'Tipo de Responsabilidade', max_length=20,
        choices=TIPO_RESPONSABILIDADE_LTCAT_CHOICES, default='elaborador'
    )
    data_atribuicao = models.DateField('Data de Atribuição', default=date.today)

    # ── Filtro por filial via FK do pai ──
    _filial_lookup = 'ltcat_documento__filial_id'
    objects = FilialManager()

    class Meta:
        db_table = 'ltcat_responsavel_documento'
        verbose_name = 'Responsável pelo Documento LTCAT'
        verbose_name_plural = 'Responsáveis pelo Documento LTCAT'
        unique_together = ['ltcat_documento', 'profissional']

    def __str__(self):
        return f"{self.profissional.nome_completo} - {self.get_tipo_responsabilidade_display()}"


class RevisaoLTCAT(models.Model):
    """Controle de revisões do LTCAT (Seção 1)"""

    ltcat_documento = models.ForeignKey(
        LTCATDocumento, on_delete=models.CASCADE,
        related_name='revisoes', verbose_name='Documento LTCAT'
    )
    numero_revisao = models.PositiveIntegerField('Número da Revisão')
    descricao = models.TextField('Descrição da Revisão')
    data_realizada = models.DateField('Data Realizada')
    realizada_por = models.CharField('Realizada Por', max_length=255, blank=True)
    observacoes = models.TextField('Observações', blank=True)
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True)

    # ── Filtro por filial via FK do pai ──
    _filial_lookup = 'ltcat_documento__filial_id'
    objects = FilialManager()

    class Meta:
        db_table = 'ltcat_revisao'
        verbose_name = 'Revisão do LTCAT'
        verbose_name_plural = 'Revisões do LTCAT'
        ordering = ['ltcat_documento', '-numero_revisao']
        unique_together = ['ltcat_documento', 'numero_revisao']

    def __str__(self):
        return f"Rev. {self.numero_revisao:02d} - {self.descricao[:50]}"

class DocumentoLocalPrestacao(models.Model):
    """
    Tabela intermediária M2M: vincula MÚLTIPLOS locais de prestação a um documento LTCAT.
    Permite adicionar informações extras por vínculo (ex: principal, observações).
    """

    ltcat_documento = models.ForeignKey(
        'LTCATDocumento',
        on_delete=models.CASCADE,
        related_name='documento_locais',
        verbose_name='Documento LTCAT'
    )
    local_prestacao = models.ForeignKey(
        LocalPrestacaoServicoLTCAT,
        on_delete=models.CASCADE,
        related_name='documento_vinculos',
        verbose_name='Local de Prestação'
    )
    principal = models.BooleanField(
        'Local Principal?', default=False,
        help_text='Marque se este é o local principal de prestação'
    )
    observacoes = models.TextField('Observações', blank=True)
    ordem = models.PositiveIntegerField('Ordem de Exibição', default=0)
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)

    # ── Filtro por filial via FK do pai ──
    _filial_lookup = 'ltcat_documento__filial_id'
    objects = FilialManager()

    class Meta:
        db_table = 'ltcat_documento_local_prestacao'
        verbose_name = 'Local de Prestação do Documento'
        verbose_name_plural = 'Locais de Prestação do Documento'
        unique_together = ['ltcat_documento', 'local_prestacao']
        ordering = ['-principal', 'ordem', 'local_prestacao__nome_local']

    def __str__(self):
        flag = ' ★' if self.principal else ''
        return f"{self.local_prestacao.nome_local}{flag}"

    def save(self, *args, **kwargs):
        # Se marcar como principal, desmarcar os outros
        if self.principal:
            DocumentoLocalPrestacao.objects.filter(
                ltcat_documento=self.ltcat_documento,
                principal=True
            ).exclude(pk=self.pk).update(principal=False)
        super().save(*args, **kwargs)

# =============================================================================
# SEÇÕES DE TEXTO DO LTCAT
# =============================================================================

class LTCATSecaoTexto(models.Model):
    """Textos editáveis das seções do LTCAT"""

    ltcat_documento = models.ForeignKey(
        LTCATDocumento, on_delete=models.CASCADE,
        related_name='secoes_texto', verbose_name='Documento LTCAT'
    )
    secao = models.CharField('Seção', max_length=50, choices=SECAO_LTCAT_CHOICES)
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
    _filial_lookup = 'ltcat_documento__filial_id'
    objects = FilialManager()

    class Meta:
        db_table = 'ltcat_secao_texto'
        verbose_name = 'Seção de Texto do LTCAT'
        verbose_name_plural = 'Seções de Texto do LTCAT'
        ordering = ['ltcat_documento', 'ordem', 'secao']
        unique_together = ['ltcat_documento', 'secao']

    def __str__(self):
        return f"{self.get_secao_display()} - {self.ltcat_documento.codigo_documento}"


class LTCATSecaoTextoPadrao(models.Model):
    """
    Textos PADRÃO globais das seções do LTCAT.
    Model GLOBAL — sem filtro por filial (é template do sistema).
    """

    secao = models.CharField(
        'Seção', max_length=50,
        choices=SECAO_LTCAT_CHOICES, unique=True
    )
    titulo = models.CharField('Título da Seção', max_length=255)
    conteudo_padrao = models.TextField(
        'Conteúdo Padrão',
        help_text='Texto padrão. Use {empresa} para substituir pelo nome da empresa.'
    )
    ativo = models.BooleanField('Ativo', default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ltcat_secao_texto_padrao'
        verbose_name = 'Texto Padrão de Seção LTCAT'
        verbose_name_plural = 'Textos Padrão de Seções LTCAT'
        ordering = ['secao']

    def __str__(self):
        return f"{self.get_secao_display()} - {self.titulo}"


# =============================================================================
# FUNÇÕES ANALISADAS (Seção 6)
# =============================================================================

class FuncaoAnalisada(models.Model):
    """Funções analisadas no LTCAT (Seção 6)"""

    ltcat_documento = models.ForeignKey(
        LTCATDocumento, on_delete=models.CASCADE,
        related_name='funcoes', verbose_name='Documento LTCAT'
    )
    local_prestacao = models.ForeignKey(
        LocalPrestacaoServicoLTCAT, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='funcoes_analisadas',
        verbose_name='Local de Prestação'
    )
    cargo = models.ForeignKey(
        Cargo, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='funcoes_ltcat',
        related_query_name='funcao_ltcat',
        verbose_name='Cargo'
    )
    funcao_st = models.ForeignKey(
        Funcao, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='funcoes_ltcat',
        related_query_name='funcao_ltcat',
        verbose_name='Função (Seg. Trabalho)'
    )

    nome_funcao = models.CharField('Função', max_length=200)
    cbo = models.CharField('CBO', max_length=20)
    descricao_atividades = models.TextField('Descrição das Atividades')
    ghe = models.CharField(
        'GHE (Grupo Homogêneo de Exposição)', max_length=200, blank=True,
        help_text='Ex: Coordenador, Técnico Mecânico de Refrigeração'
    )
    departamento = models.CharField(
        'Departamento/Setor', max_length=200, blank=True,
        help_text='Ex: Manutenção'
    )
    numero_trabalhadores = models.PositiveIntegerField(
        'Nº de Trabalhadores', blank=True, null=True
    )
    jornada_trabalho = models.CharField(
        'Jornada de Trabalho', max_length=100, blank=True, null=True,
        help_text='Ex: 44 horas semanais'
    )
    ativo = models.BooleanField('Ativo', default=True)
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True)

    # ── Filtro por filial via FK do pai ──
    _filial_lookup = 'ltcat_documento__filial_id'
    objects = FilialManager()

    class Meta:
        db_table = 'ltcat_funcao_analisada'
        verbose_name = 'Função Analisada'
        verbose_name_plural = 'Funções Analisadas'
        ordering = ['nome_funcao']

    def __str__(self):
        return f"{self.nome_funcao} (CBO: {self.cbo})"

    @property
    def total_riscos(self):
        return self.riscos.count()


# =============================================================================
# RECONHECIMENTO DE RISCOS (Seção 7)
# =============================================================================

class ReconhecimentoRisco(models.Model):
    """Reconhecimento de riscos e avaliação dos agentes por GHE (Seção 7)"""

    funcao = models.ForeignKey(
        FuncaoAnalisada, on_delete=models.CASCADE,
        related_name='riscos', verbose_name='Função / GHE'
    )

    # Classificação
    tipo_risco = models.CharField(
        'Tipo de Risco', max_length=15, choices=TIPO_RISCO_CHOICES
    )
    agente = models.CharField('Agente', max_length=300)
    fonte_geradora = models.CharField('Fonte Geradora', max_length=500)
    meio_propagacao = models.CharField(
        'Meio de Propagação', max_length=255, blank=True, null=True
    )

    # Avaliação
    tipo_avaliacao = models.CharField(
        'Tipo de Avaliação', max_length=15,
        choices=TIPO_AVALIACAO_CHOICES, default='qualitativo'
    )
    limite_tolerancia = models.CharField(
        'Limite de Tolerância', max_length=100, blank=True, default='NA'
    )
    resultado_avaliacao = models.CharField(
        'Resultado da Avaliação', max_length=200, blank=True,
        help_text='Ex: 70,92 dB(A), Qualitativo, etc.'
    )
    unidade_medida = models.CharField(
        'Unidade de Medida', max_length=50,
        choices=UNIDADE_MEDIDA_LTCAT_CHOICES, blank=True,
        help_text='Ex: dB(A), mg/m³, etc.'
    )

    # Exposição
    exposicao = models.CharField(
        'Exposição', max_length=15,
        choices=TIPO_EXPOSICAO_CHOICES, default='intermitente'
    )

    # Efeitos
    possiveis_efeitos_saude = models.TextField(
        'Possíveis Efeitos à Saúde', blank=True
    )

    # NR referência
    nr_referencia = models.CharField(
        'NR de Referência', max_length=100, blank=True,
        help_text='Ex: NR-15 Anexo 1, NR-15 Anexo 14'
    )

    observacoes = models.TextField('Observações', blank=True)
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True)

    # ── Filtro por filial via FK do avô ──
    _filial_lookup = 'funcao__ltcat_documento__filial_id'
    objects = FilialManager()

    class Meta:
        db_table = 'ltcat_reconhecimento_risco'
        verbose_name = 'Reconhecimento de Risco'
        verbose_name_plural = 'Reconhecimento de Riscos'
        ordering = ['tipo_risco', 'agente']

    def __str__(self):
        return f"{self.get_tipo_risco_display()} - {self.agente}"

    @property
    def cor_tipo_risco(self):
        cores = {
            'fisico': '#28a745',
            'quimico': '#dc3545',
            'biologico': '#6f42c1',
            'ergonomico': '#fd7e14',
            'acidente': '#007bff',
        }
        return cores.get(self.tipo_risco, '#6c757d')


# =============================================================================
# AVALIAÇÃO DE PERICULOSIDADE (Seção 8)
# =============================================================================

class AvaliacaoPericulosidade(models.Model):
    """Avaliação de periculosidade por tipo NR-16 (Seção 8)"""

    ltcat_documento = models.ForeignKey(
        LTCATDocumento, on_delete=models.CASCADE,
        related_name='avaliacoes_periculosidade', verbose_name='Documento LTCAT'
    )
    tipo = models.CharField(
        'Tipo de Periculosidade', max_length=20,
        choices=TIPO_PERICULOSIDADE_CHOICES
    )
    aplicavel = models.BooleanField('Aplicável?', default=False)
    funcoes_expostas = models.ManyToManyField(
        FuncaoAnalisada, blank=True,
        related_name='periculosidades',
        verbose_name='Funções Expostas'
    )
    descricao = models.TextField(
        'Descrição / Justificativa', blank=True,
        help_text='Ex: As funções avaliadas não lidam com explosivos e não trabalham em área de risco normatizada.'
    )
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True)

    # ── Filtro por filial via FK do pai ──
    _filial_lookup = 'ltcat_documento__filial_id'
    objects = FilialManager()

    class Meta:
        db_table = 'ltcat_avaliacao_periculosidade'
        verbose_name = 'Avaliação de Periculosidade'
        verbose_name_plural = 'Avaliações de Periculosidade'
        unique_together = ['ltcat_documento', 'tipo']

    def __str__(self):
        status = 'Aplicável' if self.aplicavel else 'Não Aplicável'
        return f"{self.get_tipo_display()} - {status}"


# =============================================================================
# CONCLUSÕES FINAIS POR FUNÇÃO (Seção 9)
# =============================================================================

class ConclusaoFuncao(models.Model):
    """Conclusão final por função (Seção 9)"""

    ltcat_documento = models.ForeignKey(
        LTCATDocumento, on_delete=models.CASCADE,
        related_name='conclusoes', verbose_name='Documento LTCAT'
    )
    funcao = models.ForeignKey(
        FuncaoAnalisada, on_delete=models.CASCADE,
        related_name='conclusoes', verbose_name='Função'
    )
    tipo_conclusao = models.CharField(
        'Conclusão', max_length=20, choices=TIPO_CONCLUSAO_CHOICES
    )
    codigo_gfip = models.CharField(
        'Código GFIP/SEFIP', max_length=2,
        choices=CODIGO_GFIP_CHOICES, default='00'
    )

    # Direitos
    faz_jus_insalubridade = models.BooleanField(
        'Faz jus à insalubridade?', default=False
    )
    grau_insalubridade = models.CharField(
        'Grau de Insalubridade', max_length=20, blank=True, null=True,
        choices=[
            ('minimo', 'Mínimo (10%)'),
            ('medio', 'Médio (20%)'),
            ('maximo', 'Máximo (40%)'),
        ]
    )
    faz_jus_periculosidade = models.BooleanField(
        'Faz jus à periculosidade?', default=False
    )
    faz_jus_aposentadoria_especial = models.BooleanField(
        'Faz jus à aposentadoria especial?', default=False
    )
    anos_aposentadoria_especial = models.IntegerField(
        'Anos para Aposentadoria Especial', blank=True, null=True,
        choices=[(15, '15 anos'), (20, '20 anos'), (25, '25 anos')]
    )

    # Fundamentação
    justificativa = models.TextField(
        'Justificativa / Fundamentação', blank=True,
        help_text='Base legal e técnica da conclusão'
    )
    nr_referencia = models.CharField(
        'NR de Referência', max_length=100, blank=True,
        help_text='Ex: NR-15 Anexo 14, NR-16 Anexo 04'
    )
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True)

    # ── Filtro por filial via FK do pai ──
    _filial_lookup = 'ltcat_documento__filial_id'
    objects = FilialManager()

    class Meta:
        db_table = 'ltcat_conclusao_funcao'
        verbose_name = 'Conclusão por Função'
        verbose_name_plural = 'Conclusões por Função'
        unique_together = ['ltcat_documento', 'funcao']

    def __str__(self):
        return f"{self.funcao.nome_funcao} - {self.get_tipo_conclusao_display()}"


# =============================================================================
# RECOMENDAÇÕES TÉCNICAS (Seção 10)
# =============================================================================

class RecomendacaoTecnica(models.Model):
    """Recomendações técnicas do LTCAT (Seção 10)"""

    ltcat_documento = models.ForeignKey(
        LTCATDocumento, on_delete=models.CASCADE,
        related_name='recomendacoes', verbose_name='Documento LTCAT'
    )
    descricao = models.TextField('Descrição da Recomendação')
    prioridade = models.CharField(
        'Prioridade', max_length=5,
        choices=PRIORIDADE_CHOICES, default='media'
    )
    prazo_implementacao = models.DateField(
        'Prazo para Implementação', null=True, blank=True
    )
    implementada = models.BooleanField('Implementada?', default=False)
    data_implementacao = models.DateField(
        'Data da Implementação', null=True, blank=True
    )
    responsavel = models.CharField(
        'Responsável', max_length=255, blank=True
    )
    observacoes = models.TextField('Observações', blank=True)
    ordem = models.PositiveIntegerField('Ordem de Exibição', default=0)
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True)

    # ── Filtro por filial via FK do pai ──
    _filial_lookup = 'ltcat_documento__filial_id'
    objects = FilialManager()

    class Meta:
        db_table = 'ltcat_recomendacao_tecnica'
        verbose_name = 'Recomendação Técnica'
        verbose_name_plural = 'Recomendações Técnicas'
        ordering = ['ordem', 'prioridade']

    def __str__(self):
        return f"[{self.get_prioridade_display()}] {self.descricao[:80]}"


# =============================================================================
# ANEXOS DO LTCAT (Seção 13 / Anexos 1 a 4+)
# =============================================================================

class AnexoLTCAT(models.Model):
    """Documentos anexos ao LTCAT (Anexos 1 a 4+)"""

    ltcat_documento = models.ForeignKey(
        LTCATDocumento, on_delete=models.CASCADE,
        related_name='anexos', verbose_name='Documento LTCAT'
    )
    tipo = models.CharField(
        'Tipo de Anexo', max_length=25,
        choices=TIPO_ANEXO_LTCAT_CHOICES, default='outro'
    )
    numero_romano = models.CharField(
        'Número do Anexo', max_length=10, blank=True,
        help_text='Ex: I, II, III, IV...'
    )
    titulo = models.CharField('Título', max_length=300)
    descricao = models.TextField('Descrição', blank=True)
    arquivo = models.FileField(
        'Arquivo',
        upload_to=make_upload_path('ltcat_anexos'),  # UUID + path seguro
        validators=[SecureFileValidator('ltcat_anexos')],  # Validação completa
        help_text='PDF, DOCX, XLSX, JPG, PNG, WEBP (máx. 50MB)',
    )
    nome_arquivo_original = models.CharField(
        'Nome Original do Arquivo', max_length=500, blank=True
    )
    tamanho_arquivo = models.PositiveIntegerField('Tamanho (bytes)', default=0)
    # Campo novo — MIME type real (opcional mas útil)
    mime_type = models.CharField(
        'Tipo MIME', max_length=100, editable=False, default='',
    )
    incluir_no_pdf = models.BooleanField(
        'Incluir no PDF do LTCAT', default=True,
        help_text='Se marcado, aparecerá listado nos anexos do relatório PDF'
    )
    ordem = models.PositiveIntegerField('Ordem de Exibição', default=0)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='Enviado por'
    )
    criado_em = models.DateTimeField('Enviado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True)

    # ── Filtro por filial via FK do pai ──
    _filial_lookup = 'ltcat_documento__filial_id'
    objects = FilialManager()

    class Meta:
        db_table = 'ltcat_anexo'
        verbose_name = 'Anexo do LTCAT'
        verbose_name_plural = 'Anexos do LTCAT'
        ordering = ['ordem', 'numero_romano', 'criado_em']
        unique_together = ['ltcat_documento', 'numero_romano']

    def __str__(self):
        if self.numero_romano:
            return f"ANEXO {self.numero_romano} – {self.titulo}"
        return self.titulo

    @property
    def titulo_completo(self):
        if self.numero_romano:
            return f"ANEXO {self.numero_romano} – {self.titulo}"
        return self.titulo

    @property
    def extensao(self):
        if self.arquivo and self.arquivo.name:
            return self.arquivo.name.rsplit('.', 1)[-1].upper()
        return ''

    @property
    def tamanho_formatado(self):
        if self.tamanho_arquivo < 1024:
            return f"{self.tamanho_arquivo} B"
        elif self.tamanho_arquivo < 1048576:
            return f"{self.tamanho_arquivo / 1024:.1f} KB"
        else:
            return f"{self.tamanho_arquivo / 1048576:.1f} MB"

    @property
    def icone_tipo(self):
        ext = self.extensao.lower()
        icones = {
            'pdf': 'fa-file-pdf text-danger',
            'doc': 'fa-file-word text-primary',
            'docx': 'fa-file-word text-primary',
            'xls': 'fa-file-excel text-success',
            'xlsx': 'fa-file-excel text-success',
            'jpg': 'fa-file-image text-warning',
            'jpeg': 'fa-file-image text-warning',
            'png': 'fa-file-image text-warning',
            'webp': 'fa-file-image text-warning',
        }
        return icones.get(ext, 'fa-file text-secondary')

    def save(self, *args, **kwargs):
        if self.arquivo:
            if not self.nome_arquivo_original:
                self.nome_arquivo_original = os.path.basename(self.arquivo.name)

            try:
                self.tamanho_arquivo = self.arquivo.size
            except Exception:
                pass

            # ✅ Usa wrapper
            if not self.mime_type:
                try:
                    self.mime_type = get_mime_type(self.arquivo)
                except Exception:
                    self.mime_type = 'application/octet-stream'

            if self.mime_type.startswith('image/') and hasattr(self.arquivo.file, 'seek'):
                try:
                    self.arquivo = sanitize_image(self.arquivo)
                except Exception:
                    pass

        # Auto-numerar (lógica existente mantida)
        if not self.numero_romano:
            existentes = AnexoLTCAT.objects.filter(
                ltcat_documento=self.ltcat_documento
            ).exclude(pk=self.pk).count()
            numeros = [
                'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII',
                'IX', 'X', 'XI', 'XII', 'XIII', 'XIV', 'XV'
            ]
            idx = existentes
            self.numero_romano = numeros[idx] if idx < len(numeros) else str(idx + 1)

        # Auto-ordem (lógica existente mantida)
        if self.ordem == 0 and not self.pk:
            max_ordem = AnexoLTCAT.objects.filter(
                ltcat_documento=self.ltcat_documento
            ).aggregate(models.Max('ordem'))['ordem__max'] or 0
            self.ordem = max_ordem + 1

        # Auto título pelo tipo (lógica existente mantida)
        if not self.titulo and self.tipo != 'outro':
            self.titulo = dict(TIPO_ANEXO_LTCAT_CHOICES).get(self.tipo, '')

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        safe_delete_file(self, 'arquivo')
        super().delete(*args, **kwargs)    


# =============================================================================
# TABELA DE REFERÊNCIA — NR-15 ANEXO 1 (Seção 11.1)
# Model GLOBAL — sem filtro por filial
# =============================================================================

class TabelaRuidoNR15(models.Model):
    """Tabela de referência — Limites NR-15 Anexo 1 (Seção 11.1)"""

    nivel_ruido_db = models.DecimalField(
        'Nível de Ruído dB(A)', max_digits=5, decimal_places=1
    )
    max_exposicao_diaria = models.CharField(
        'Máxima Exposição Diária Permitida', max_length=50
    )

    class Meta:
        db_table = 'ltcat_tabela_ruido_nr15'
        verbose_name = 'Limite de Ruído NR-15'
        verbose_name_plural = 'Limites de Ruído NR-15'
        ordering = ['nivel_ruido_db']

    def __str__(self):
        return f"{self.nivel_ruido_db} dB(A) - {self.max_exposicao_diaria}"

