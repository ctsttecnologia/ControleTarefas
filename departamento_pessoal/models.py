

# models.py

from datetime import date
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from core.managers import FilialManager
from usuario.models import Filial
from cliente.models import Cliente


class Departamento(models.Model):
    """
    Representa um departamento dentro de uma filial da empresa.
    Ex: Financeiro, Recursos Humanos, TI.
    """
    registro = models.PositiveIntegerField(default=0, verbose_name=_("Registro de Departamento"))
    nome = models.CharField(
        _("Nome do Departamento"),
        max_length=100,
        unique=True
    )
    centro_custo = models.CharField(
        _("Centro de Custo"),
        max_length=20,
        unique=True,
        blank=True,
        null=True
    )
    ativo = models.BooleanField(
        _("Ativo"),
        default=True
    )
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name='departamentos',  
        verbose_name=_("Filial"),
        null=True,            
        blank=False          
    )
    # Manager customizado para segregação de dados
    objects = FilialManager()
   

    class Meta:
        verbose_name = _("Departamento")
        verbose_name_plural = _("Departamentos")
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Cargo(models.Model):
    """
    Representa um cargo ou função exercida dentro da empresa.
    Ex: Analista Financeiro, Desenvolvedor Pleno.
    """
    nome = models.CharField(
        _("Nome do Cargo"),
        max_length=100,
        unique=True
    )
    descricao = models.TextField(
        _("Descrição Sumária do Cargo"),
        blank=True
    )
    cbo = models.CharField(
        _("CBO"),
        max_length=10,
        blank=True,
        help_text=_("Classificação Brasileira de Ocupações")
    )
    ativo = models.BooleanField(
        _("Ativo"),
        default=True
    )
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name='cargos',  
        verbose_name=_("Filial"),
        null=True,
        blank=False
    )

    # Manager customizado para segregação de dados
    objects = FilialManager()

    class Meta:
        verbose_name = _("Cargo")
        verbose_name_plural = _("Cargos")
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Funcionario(models.Model):
    """
    Modelo central que representa um colaborador da empresa, unindo
    dados pessoais, de contato e de contratação.
    """
    # Choices para campos com opções fixas
    STATUS_CHOICES = [
        ('ATIVO', _('Ativo')),
        ('INATIVO', _('Inativo')),
        ('FERIAS', _('Férias')),
        ('AFASTADO', _('Afastado'))
    ]
    SEXO_CHOICES = [
        ('M', _('Masculino')),
        ('F', _('Feminino')),
        ('O', _('Outro'))
    ]

    # --- Relacionamentos Fundamentais ---
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='funcionario',
        verbose_name=_("Usuário do Sistema"),
        null=True,
        blank=True,
    )
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name='funcionarios',  
        verbose_name=_("Filial"),
        null=True,
        blank=True
    )
    cargo = models.ForeignKey(
        Cargo,
        on_delete=models.PROTECT,
        related_name='funcionarios',
        verbose_name=_("Cargo")
    )
    funcao = models.ForeignKey(
        'seguranca_trabalho.Funcao',
        on_delete=models.SET_NULL,  # Se uma função for deletada, não deleta o funcionário
        null=True,                  # Permite que o campo seja nulo no banco de dados
        blank=True,                 # Permite que o campo seja opcional nos formulários
        verbose_name=_("Função (SST)"),
        help_text=_("Função desempenhada pelo funcionário para fins de SST e Matriz de EPI."),
        related_name='funcionarios_dp', 
        related_query_name='funcionario_dp'
    )
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.PROTECT,
        related_name='funcionarios',
        verbose_name=_("Departamento")
    )
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.SET_NULL, # Permite remover o cliente sem apagar o funcionário
        related_name='funcionarios_alocados',
        verbose_name=_("Cliente/Contrato"),
        null=True,
        blank=True
    )

    # --- Informações Pessoais ---
    nome_completo = models.CharField(_("Nome Completo"), max_length=255)
    data_nascimento = models.DateField(_("Data de Nascimento"), null=True, blank=True)
    sexo = models.CharField(_("Sexo"), max_length=1, choices=SEXO_CHOICES, null=True, blank=True)
    email_pessoal = models.EmailField(_("Email Pessoal"), unique=True, null=True, blank=True)
    telefone = models.CharField(_("Telefone de Contato"), max_length=20, blank=True)

    # --- Informações de Contratação ---
    matricula = models.CharField(_("Matrícula"), max_length=20, unique=True)
    data_admissao = models.DateField(_("Data de Admissão"))
    data_demissao = models.DateField(_("Data de Demissão"), null=True, blank=True)
    salario = models.DecimalField(_("Salário Base"), max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(_("Status"), max_length=10, choices=STATUS_CHOICES, default='ATIVO')
    # --- Metadados ---
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    foto_3x4 = models.ImageField(
        _("Foto 3x4"),
        upload_to='fotos_3x4/', 
        null=True,
        blank=True,
        help_text=_("Faça o upload de uma foto 3x4 do funcionário.")
    )

    # Manager customizado para segregação de dados
    objects = FilialManager()

    class Meta:
        
        verbose_name = _("Funcionário")
        verbose_name_plural = _("Funcionários")
        ordering = ['nome_completo']

    def __str__(self):
        return self.nome_completo

    def get_absolute_url(self):
        """URL canônica para um funcionário específico."""
        return reverse('departamento_pessoal:detalhe_funcionario', kwargs={'pk': self.pk})

    @property
    def idade(self):
        """Calcula a idade do funcionário com base na data de nascimento."""
        if not self.data_nascimento:
            return None
        hoje = date.today()
        # Calcula a diferença de anos e subtrai 1 se o aniversário ainda não ocorreu este ano.
        return hoje.year - self.data_nascimento.year - ((hoje.month, hoje.day) < (self.data_nascimento.month, self.data_nascimento.day))
    
    @property
    def rg_numero(self):
        """Retorna o número do RG do funcionário, se existir."""
        try:
            return self.documentos.get(tipo_documento='RG').numero
        except Documento.DoesNotExist:
            return "N/A"
        
class Documento(models.Model):
    """
    Armazena documentos pessoais e profissionais de funcionários.
    Campos específicos são exibidos condicionalmente conforme o tipo.
    """

    # ── Tipos de documento (completo para DP brasileiro) ──
    TIPO_CHOICES = [
        # Documentos pessoais
        ('CPF', 'CPF'),
        ('RG', 'RG / Carteira de Identidade'),
        ('CNH', 'CNH - Carteira de Habilitação'),
        ('CTPS', 'CTPS - Carteira de Trabalho'),
        ('PIS', 'PIS / PASEP / NIT'),
        ('TITULO', 'Título de Eleitor'),
        ('RESERVISTA', 'Certificado de Reservista'),
        ('CERTIDAO_NASC', 'Certidão de Nascimento'),
        ('CERTIDAO_CAS', 'Certidão de Casamento'),
        ('PASSAPORTE', 'Passaporte'),
        ('RNE', 'RNE / CRNM (Estrangeiro)'),
        # Documentos profissionais
        ('REGISTRO_CLASSE', 'Registro de Classe (CREA, CRM, OAB, etc.)'),
        ('CERTIFICADO', 'Certificado / Diploma'),
        ('ASO', 'ASO - Atestado de Saúde Ocupacional'),
        ('NR', 'Certificado de NR (NR-10, NR-35, etc.)'),
        ('COMPROVANTE_END', 'Comprovante de Endereço'),
        ('COMP_ESCOLAR', 'Comprovante de Escolaridade'),
        ('OUTRO', 'Outro'),
    ]

    # ── Categorias de CNH ──
    CNH_CATEGORIA_CHOICES = [
        ('A', 'A - Motos'),
        ('B', 'B - Carros'),
        ('AB', 'AB - Motos e Carros'),
        ('C', 'C - Caminhões'),
        ('D', 'D - Ônibus'),
        ('E', 'E - Carretas / Articulados'),
        ('AC', 'AC'), ('AD', 'AD'), ('AE', 'AE'),
    ]

    # ── UF para órgão expedidor ──
    UF_CHOICES = [
        ('AC', 'AC'), ('AL', 'AL'), ('AM', 'AM'), ('AP', 'AP'),
        ('BA', 'BA'), ('CE', 'CE'), ('DF', 'DF'), ('ES', 'ES'),
        ('GO', 'GO'), ('MA', 'MA'), ('MG', 'MG'), ('MS', 'MS'),
        ('MT', 'MT'), ('PA', 'PA'), ('PB', 'PB'), ('PE', 'PE'),
        ('PI', 'PI'), ('PR', 'PR'), ('RJ', 'RJ'), ('RN', 'RN'),
        ('RO', 'RO'), ('RR', 'RR'), ('RS', 'RS'), ('SC', 'SC'),
        ('SE', 'SE'), ('SP', 'SP'), ('TO', 'TO'),
    ]

    # ═══════════════════════════════════════════════════════════
    # CAMPOS COMUNS A TODOS OS TIPOS
    # ═══════════════════════════════════════════════════════════
    funcionario = models.ForeignKey(
        'departamento_pessoal.Funcionario',
        on_delete=models.PROTECT,
        verbose_name='Funcionário',
        related_name='documentos_dp',
        related_query_name='documento_dp',
    )
    tipo_documento = models.CharField(
        'Tipo de Documento', max_length=20,
        choices=TIPO_CHOICES,
    )
    numero = models.CharField(
        'Número do Documento', max_length=50,
        blank=True, null=True,
        help_text='Número principal do documento',
    )
    data_emissao = models.DateField(
        'Data de Emissão', blank=True, null=True,
    )
    data_validade = models.DateField(
        'Data de Validade', blank=True, null=True,
        help_text='Deixe em branco se não tem validade',
    )
    orgao_expedidor = models.CharField(
        'Órgão Expedidor', max_length=50,
        blank=True, null=True,
        help_text='Ex: SSP-MG, DETRAN-SP, CREA-MG',
    )
    uf_expedidor = models.CharField(
        'UF do Expedidor', max_length=2,
        choices=UF_CHOICES,
        blank=True, null=True,
    )
    observacoes = models.TextField(
        'Observações', blank=True, null=True,
    )
    anexo = models.FileField(
        'Arquivo Anexado',
        upload_to='documentos_funcionarios/%Y/%m/',
        blank=True, null=True,
        help_text='PDF ou imagem (máx. 10MB)',
    )

    # ═══════════════════════════════════════════════════════════
    # CAMPOS ESPECÍFICOS — RG
    # ═══════════════════════════════════════════════════════════
    rg_nome_pai = models.CharField(
        'Nome do Pai', max_length=200, blank=True, null=True,
    )
    rg_nome_mae = models.CharField(
        'Nome da Mãe', max_length=200, blank=True, null=True,
    )
    rg_naturalidade = models.CharField(
        'Naturalidade', max_length=100, blank=True, null=True,
        help_text='Ex: Belo Horizonte/MG',
    )

    # ═══════════════════════════════════════════════════════════
    # CAMPOS ESPECÍFICOS — CNH
    # ═══════════════════════════════════════════════════════════
    cnh_categoria = models.CharField(
        'Categoria da CNH', max_length=3,
        choices=CNH_CATEGORIA_CHOICES, blank=True, null=True,
    )
    cnh_numero_registro = models.CharField(
        'Nº de Registro CNH', max_length=30, blank=True, null=True,
    )
    cnh_primeira_habilitacao = models.DateField(
        'Data da 1ª Habilitação', blank=True, null=True,
    )
    cnh_observacoes_detran = models.CharField(
        'Observações DETRAN', max_length=200, blank=True, null=True,
        help_text='Ex: Exerce Atividade Remunerada (EAR)',
    )

    # ═══════════════════════════════════════════════════════════
    # CAMPOS ESPECÍFICOS — CTPS
    # ═══════════════════════════════════════════════════════════
    ctps_serie = models.CharField(
        'Série da CTPS', max_length=20, blank=True, null=True,
    )
    ctps_uf = models.CharField(
        'UF da CTPS', max_length=2,
        choices=UF_CHOICES, blank=True, null=True,
    )
    ctps_digital = models.BooleanField(
        'CTPS Digital?', default=False,
        help_text='Marque se a CTPS é digital (sem número físico)',
    )

    # ═══════════════════════════════════════════════════════════
    # CAMPOS ESPECÍFICOS — TÍTULO DE ELEITOR
    # ═══════════════════════════════════════════════════════════
    titulo_zona = models.CharField(
        'Zona Eleitoral', max_length=10, blank=True, null=True,
    )
    titulo_secao = models.CharField(
        'Seção Eleitoral', max_length=10, blank=True, null=True,
    )
    titulo_municipio = models.CharField(
        'Município', max_length=100, blank=True, null=True,
    )

    # ═══════════════════════════════════════════════════════════
    # CAMPOS ESPECÍFICOS — RESERVISTA
    # ═══════════════════════════════════════════════════════════
    reservista_categoria = models.CharField(
        'Categoria Reservista', max_length=10, blank=True, null=True,
    )
    reservista_regiao_militar = models.CharField(
        'Região Militar', max_length=50, blank=True, null=True,
    )

    # ═══════════════════════════════════════════════════════════
    # CAMPOS ESPECÍFICOS — REGISTRO DE CLASSE
    # ═══════════════════════════════════════════════════════════
    registro_orgao = models.CharField(
        'Órgão de Classe', max_length=50, blank=True, null=True,
        help_text='Ex: CREA, CRM, OAB, CRN, COREN',
    )
    registro_especialidade = models.CharField(
        'Especialidade', max_length=200, blank=True, null=True,
        help_text='Ex: Engenharia Mecânica e de Segurança do Trabalho',
    )

    # ═══════════════════════════════════════════════════════════
    # CAMPOS ESPECÍFICOS — ASO
    # ═══════════════════════════════════════════════════════════
    ASO_TIPO_CHOICES = [
        ('admissional', 'Admissional'),
        ('periodico', 'Periódico'),
        ('retorno', 'Retorno ao Trabalho'),
        ('mudanca', 'Mudança de Função'),
        ('demissional', 'Demissional'),
    ]
    aso_tipo_exame = models.CharField(
        'Tipo de Exame ASO', max_length=20,
        choices=ASO_TIPO_CHOICES, blank=True, null=True,
    )
    aso_apto = models.BooleanField(
        'Apto?', default=True, null=True,
        help_text='Resultado: Apto ou Inapto',
    )
    aso_medico_nome = models.CharField(
        'Médico Responsável', max_length=200, blank=True, null=True,
    )
    aso_medico_crm = models.CharField(
        'CRM do Médico', max_length=20, blank=True, null=True,
    )
    aso_proximo_exame = models.DateField(
        'Próximo Exame', blank=True, null=True,
    )

    # ═══════════════════════════════════════════════════════════
    # CAMPOS ESPECÍFICOS — CERTIFICADO NR
    # ═══════════════════════════════════════════════════════════
    nr_numero = models.CharField(
        'Número da NR', max_length=10, blank=True, null=True,
        help_text='Ex: NR-10, NR-35, NR-33',
    )
    nr_carga_horaria = models.PositiveIntegerField(
        'Carga Horária (horas)', blank=True, null=True,
    )
    nr_instituicao = models.CharField(
        'Instituição / Empresa', max_length=200, blank=True, null=True,
    )

    # ═══════════════════════════════════════════════════════════
    # CAMPOS ESPECÍFICOS — CERTIFICADO / DIPLOMA
    # ═══════════════════════════════════════════════════════════
    ESCOLARIDADE_CHOICES = [
        ('fundamental', 'Ensino Fundamental'),
        ('medio', 'Ensino Médio'),
        ('tecnico', 'Curso Técnico'),
        ('graduacao', 'Graduação'),
        ('pos', 'Pós-Graduação / MBA'),
        ('mestrado', 'Mestrado'),
        ('doutorado', 'Doutorado'),
        ('curso_livre', 'Curso Livre / Extensão'),
    ]
    certificado_nivel = models.CharField(
        'Nível/Grau', max_length=20,
        choices=ESCOLARIDADE_CHOICES, blank=True, null=True,
    )
    certificado_curso = models.CharField(
        'Nome do Curso', max_length=200, blank=True, null=True,
    )
    certificado_instituicao = models.CharField(
        'Instituição de Ensino', max_length=200, blank=True, null=True,
    )

    # ═══════════════════════════════════════════════════════════
    # CAMPOS ESPECÍFICOS — PASSAPORTE
    # ═══════════════════════════════════════════════════════════
    passaporte_pais_emissao = models.CharField(
        'País de Emissão', max_length=100,
        blank=True, null=True, default='Brasil',
    )

    # ═══════════════════════════════════════════════════════════
    # CAMPO GENÉRICO — OUTRO
    # ═══════════════════════════════════════════════════════════
    outro_descricao = models.CharField(
        'Descrição do Documento', max_length=200,
        blank=True, null=True,
        help_text='Descreva o tipo de documento quando "Outro"',
    )

    # ═══════════════════════════════════════════════════════════
    # CONTROLE / FILIAL (usa o import do topo: from usuario.models import Filial)
    # ═══════════════════════════════════════════════════════════
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name='documentos_dp_filial',  
        verbose_name='Filial',
        null=True, blank=False,
    )

    _filial_lookup = 'filial_id'
    objects = FilialManager()

    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        db_table = 'departamento_pessoal_documento'
        verbose_name = 'Documento'
        verbose_name_plural = 'Documentos'
        unique_together = ('funcionario', 'tipo_documento', 'numero')
        ordering = ['funcionario__nome_completo', 'tipo_documento']

    def __str__(self):
        return f"{self.get_tipo_documento_display()} — {self.funcionario.nome_completo}"

    @property
    def esta_vencido(self):
        """Retorna True se o documento está vencido."""
        if self.data_validade:
            return self.data_validade < date.today()
        return False

    @property
    def vence_em_30_dias(self):
        """Retorna True se vence nos próximos 30 dias."""
        if self.data_validade:
            from datetime import timedelta
            hoje = date.today()
            return hoje <= self.data_validade <= hoje + timedelta(days=30)
        return False

    @property
    def icone(self):
        """Retorna ícone Bootstrap para o tipo de documento."""
        icones = {
            'CPF': 'bi-person-vcard',
            'RG': 'bi-person-badge',
            'CNH': 'bi-car-front',
            'CTPS': 'bi-briefcase-fill',
            'PIS': 'bi-123',
            'TITULO': 'bi-check2-square',
            'RESERVISTA': 'bi-shield-check',
            'CERTIDAO_NASC': 'bi-file-earmark-person',
            'CERTIDAO_CAS': 'bi-heart',
            'PASSAPORTE': 'bi-globe',
            'RNE': 'bi-globe2',
            'REGISTRO_CLASSE': 'bi-award',
            'CERTIFICADO': 'bi-mortarboard',
            'ASO': 'bi-heart-pulse',
            'NR': 'bi-shield-exclamation',
            'COMPROVANTE_END': 'bi-house',
            'COMP_ESCOLAR': 'bi-book',
            'OUTRO': 'bi-file-earmark-text',
        }
        return icones.get(self.tipo_documento, 'bi-file-earmark')

    @property
    def cor_badge(self):
        """Retorna a cor do badge conforme status de validade."""
        if self.esta_vencido:
            return 'danger'
        if self.vence_em_30_dias:
            return 'warning'
        return 'success'

    def clean(self):
        """Validações condicionais por tipo de documento."""
        from django.core.exceptions import ValidationError
        errors = {}

        # CPF — validação de formato
        if self.tipo_documento == 'CPF' and self.numero:
            cpf = self.numero.replace('.', '').replace('-', '').replace(' ', '')
            if len(cpf) != 11 or not cpf.isdigit():
                errors['numero'] = 'CPF deve ter 11 dígitos numéricos.'

        # CNH — categoria obrigatória
        if self.tipo_documento == 'CNH':
            if not self.cnh_categoria:
                errors['cnh_categoria'] = 'Categoria é obrigatória para CNH.'
            if not self.data_validade:
                errors['data_validade'] = 'Data de validade é obrigatória para CNH.'

        # CTPS — série obrigatória se não digital
        if self.tipo_documento == 'CTPS' and not self.ctps_digital:
            if not self.numero:
                errors['numero'] = 'Número é obrigatório para CTPS física.'
            if not self.ctps_serie:
                errors['ctps_serie'] = 'Série é obrigatória para CTPS física.'

        # ASO — tipo de exame obrigatório
        if self.tipo_documento == 'ASO' and not self.aso_tipo_exame:
            errors['aso_tipo_exame'] = 'Tipo de exame é obrigatório para ASO.'

        # NR — número da NR obrigatório
        if self.tipo_documento == 'NR' and not self.nr_numero:
            errors['nr_numero'] = 'Número da NR é obrigatório.'

        # OUTRO — descrição obrigatória
        if self.tipo_documento == 'OUTRO' and not self.outro_descricao:
            errors['outro_descricao'] = 'Descrição é obrigatória para tipo "Outro".'

        if errors:
            raise ValidationError(errors)
