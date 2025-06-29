
# documents_app/models.py

from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

from .validators import validate_cpf, validate_pis

from logradouro.constant import ESTADOS_BRASIL

# ANÁLISE: O modelo Departamentos está bom, sem grandes alterações necessárias.
class Departamentos(models.Model):
    TIPO_DEPARTAMENTO_CHOICES = [
        ('ADM', 'Administrativo'), ('OPR', 'Operacional'), ('COM', 'Comercial'),
        ('FIN', 'Financeiro'), ('RH', 'Recursos Humanos'), ('PCM', 'Planejamento'),
        ('TST', 'Segurança do Trabalho'), ('DP', 'Departamento Pessoal'),
    ]
    
    nome = models.CharField(max_length=50, unique=True, verbose_name=_('Nome do Departamento'))
    sigla = models.CharField(max_length=10, unique=True, verbose_name=_('Sigla'))
    tipo = models.CharField(max_length=3, choices=TIPO_DEPARTAMENTO_CHOICES, default='ADM')
    centro_custo = models.CharField(max_length=20, unique=True, blank=True, null=True)
    ativo = models.BooleanField(default=True)
    data_criacao = models.DateField(default=timezone.now)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'departamentos'
        verbose_name = _('Departamento')
        verbose_name_plural = _('Departamentos')
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} ({self.sigla})"

# ANÁLISE: O modelo Cbos está bom.
class Cbos(models.Model):
    codigo = models.CharField(max_length=6, unique=True, verbose_name=_('Código CBO'))
    titulo = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    data_atualizacao = models.DateField(auto_now=True)

    class Meta:
        db_table = 'cbos'
        verbose_name = _('CBO')
        verbose_name_plural = _('CBOs')
        ordering = ['codigo']

    def __str__(self):
        return f"{self.codigo} - {self.titulo}"

# ANÁLISE: O modelo Cargos está bom. `on_delete=models.PROTECT` é uma boa prática aqui.
class Cargos(models.Model):
    nome = models.CharField(max_length=50, unique=True, verbose_name=_('Nome do Cargo'))
    cbo = models.ForeignKey(Cbos, on_delete=models.PROTECT, related_name='cargos')
    salario_base = models.DecimalField(max_digits=10, decimal_places=2)
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = 'cargos'
        verbose_name = _('Cargo')
        verbose_name_plural = _('Cargos')
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} (R$ {self.salario_base})"

class Funcionarios(models.Model):
    SEXO_CHOICES = [('M', 'Masculino'), ('F', 'Feminino'), ('O', 'Outro')]
    ESTATUS_CHOICES = [(1, 'Ativo'), (2, 'Afastado'), (3, 'Desligado'), (4, 'Férias')]

    nome = models.CharField(max_length=100)
    telefone = models.CharField(max_length=15, blank=True)
    naturalidade = models.CharField(max_length=30, blank=True)
    data_nascimento = models.DateField()
    email = models.EmailField(unique=True, error_messages={'unique': _("Este email já está em uso.")})
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES)
    estatus = models.IntegerField(choices=ESTATUS_CHOICES, default=1)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    logradouro = models.ForeignKey('logradouro.Logradouro', on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        db_table = 'funcionarios'
        verbose_name = _('Funcionário')
        verbose_name_plural = _('Funcionários')
        ordering = ['nome']

    def __str__(self):
        # OTIMIZAÇÃO: Acessar a property `self.matricula` aqui pode causar recursão.
        # É mais seguro e eficiente acessar diretamente o campo relacionado.
        try:
            matricula = self.admissao.matricula
        except Admissao.DoesNotExist:
            matricula = 'Sem matrícula'
        return f"{self.nome} ({matricula})"

    # CORREÇÃO: Havia duas definições da property `matricula`. A segunda sobrescrevia a primeira.
    # Unifiquei em uma única versão mais robusta.
    @property
    def matricula(self):
        try:
            return self.admissao.matricula
        except Admissao.DoesNotExist:
            return "N/D"

    @property
    def idade(self):
        hoje = timezone.now().date()
        return hoje.year - self.data_nascimento.year - ((hoje.month, hoje.day) < (self.data_nascimento.month, self.data_nascimento.day))
    
    @property
    def telefone_formatado(self):
        tel = self.telefone
        if not tel:
            return "-"
        if len(tel) == 11:
            return f"({tel[:2]}) {tel[2:7]}-{tel[7:]}"
        elif len(tel) == 10:
            return f"({tel[:2]}) {tel[2:6]}-{tel[6:]}"
        return tel

    def save(self, *args, **kwargs):
        # OTIMIZAÇÃO: Limpa a formatação do telefone antes de salvar no banco.
        # Armazenar apenas os dígitos simplifica validações e formatações futuras.
        if self.telefone:
            self.telefone = ''.join(filter(str.isdigit, str(self.telefone)))
        super().save(*args, **kwargs)

class Documentos(models.Model):
    # OTIMIZAÇÃO: Os TIPO_CHOICES aqui parecem ser mais sobre o tipo do documento do que o contrato.
    # Renomeei para maior clareza e adicionei mais opções que parecem estar faltando, com base na lógica do `clean`.
    TIPO_DOCUMENTO_CHOICES = [
        ('CPF', 'CPF'),
        ('RG', 'RG'),
        ('CTPS', 'Carteira de Trabalho (CTPS)'),
        ('PIS', 'PIS/PASEP'),
        ('TIT', 'Título de Eleitor'),
        ('RES', 'Certificado de Reservista'),
        ('OUT', 'Outro'),
    ]

    funcionario = models.ForeignKey('Funcionarios', on_delete=models.CASCADE, related_name='documentos')
    tipo = models.CharField(max_length=4, choices=TIPO_DOCUMENTO_CHOICES, verbose_name='Tipo de Documento')
    
    # ... outros campos gerais que você possa ter como 'nome', 'sigla', 'data_criacao'
    # Se não forem necessários para todos os tipos, podem ser removidos.
    nome = models.CharField(max_length=50, verbose_name='Nome do Documento', blank=True)
    
    # Campos de documentos específicos
    cpf = models.CharField(
        max_length=14, 
        blank=True, 
        null=True, 
        unique=True, 
        verbose_name='CPF',
        validators=[validate_cpf]
    )
    pis = models.CharField(
        max_length=14, 
        blank=True, 
        null=True, 
        unique=True, 
        verbose_name='PIS/PASEP',
        validators=[validate_pis]
    )
    ctps = models.CharField(max_length=20, blank=True, null=True, verbose_name='CTPS (Número/Série)')
    rg = models.CharField(max_length=15, blank=True, null=True, verbose_name='RG')
    uf_emissor_rg = models.CharField(max_length=2, choices=ESTADOS_BRASIL, blank=True, null=True, verbose_name='UF Emissor do RG')
    orgao_emissor_rg = models.CharField(max_length=10, blank=True, null=True, verbose_name='Órgão Emissor do RG')
    reservista = models.CharField(max_length=12, blank=True, null=True, verbose_name='Nº Reservista')
    titulo_eleitor = models.CharField(max_length=15, blank=True, null=True, verbose_name='Título de Eleitor')

    # Anexos
    anexo = models.FileField(upload_to='documentos/%Y/%m/', blank=True, null=True, verbose_name='Anexo')
    
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'documentos'
        verbose_name = 'Documento'
        verbose_name_plural = 'Documentos'
        # Garante que um funcionário não tenha dois documentos do mesmo tipo (ex: dois CPFs).
        unique_together = ('funcionario', 'tipo')
        ordering = ['-data_atualizacao']

    def __str__(self):
        return f"{self.get_tipo_display()} de {self.funcionario.nome}"

    # CORREÇÃO CRÍTICA: Havia duas funções `clean` no seu modelo. A segunda sobrescrevia a primeira.
    # A lógica foi unificada aqui.
    def clean(self):
        # Validação condicional: Garante que o campo numérico correspondente ao tipo de documento seja preenchido.
        if self.tipo == 'CPF' and not self.cpf:
            raise ValidationError({'cpf': 'CPF é obrigatório para este tipo de documento.'})
        if self.tipo == 'PIS' and not self.pis:
            raise ValidationError({'pis': 'PIS é obrigatório para este tipo de documento.'})
        if self.tipo == 'CTPS' and not self.ctps:
            raise ValidationError({'ctps': 'CTPS é obrigatório para este tipo de documento.'})
        if self.tipo == 'RG' and (not self.rg or not self.uf_emissor_rg or not self.orgao_emissor_rg):
            raise ValidationError({
                'rg': 'RG, UF e Órgão Emissor são obrigatórios para este tipo de documento.',
                'uf_emissor_rg': ' ', 'orgao_emissor_rg': ' '
            })
        if self.tipo == 'RES' and not self.reservista:
            raise ValidationError({'reservista': 'Nº de reservista é obrigatório.'})
        if self.tipo == 'TIT' and not self.titulo_eleitor:
            raise ValidationError({'titulo_eleitor': 'Título de eleitor é obrigatório.'})

        # Validação de unicidade do documento principal (se aplicável)
        # O modelo Admissao agora lida com o "documento principal", tornando essa validação aqui desnecessária
        # e simplificando o modelo de Documentos.

class Admissao(models.Model):
    TIPO_CONTRATO_CHOICES = [('CLT', 'Registro CLT'), ('PJ', 'Pessoa Jurídica'), ('EST', 'Estagiário'), ('APR', 'Aprendiz')]
    DIAS_SEMANA_CHOICES = [
        ('SEG', 'Seg'), ('TER', 'Ter'), ('QUA', 'Qua'),
        ('QUI', 'Qui'), ('SEX', 'Sex'), ('SAB', 'Sáb'), ('DOM', 'Dom')
    ]
    
    # RELACIONAMENTO: OneToOneField é perfeito aqui. Um funcionário tem apenas uma admissão.
    funcionario = models.OneToOneField('Funcionarios', on_delete=models.CASCADE, related_name='admissao')
    
    # REMOÇÃO: O campo `documento_principal` foi removido.
    # Ele criava uma dependência circular complexa. É mais simples e robusto
    # gerenciar os documentos através da relação `funcionario.documentos.all()`.

    cargo = models.ForeignKey('Cargos', on_delete=models.PROTECT, related_name='admissoes')
    departamento = models.ForeignKey('Departamentos', on_delete=models.PROTECT, related_name='admissoes')
    matricula = models.CharField(max_length=10, unique=True, blank=True) # Blank=True para permitir geração automática.
    data_admissao = models.DateField(default=timezone.now)
    salario = models.DecimalField(max_digits=10, decimal_places=2)
    tipo_contrato = models.CharField(max_length=3, choices=TIPO_CONTRATO_CHOICES, default='CLT')
    data_demissao = models.DateField(null=True, blank=True)
    hora_entrada = models.TimeField(null=True, blank=True)
    hora_saida = models.TimeField(null=True, blank=True)
    dias_semana = models.CharField(max_length=27, blank=True) # Armazena 'SEG,TER,QUA'

    class Meta:
        db_table = 'admissao'
        verbose_name = 'Admissão'
        verbose_name_plural = 'Admissões'
        ordering = ['-data_admissao']

    def __str__(self):
        return f"{self.matricula} - {self.funcionario.nome}"

    def save(self, *args, **kwargs):
        # Lógica para gerar matrícula automática se não for fornecida
        if not self.matricula:
            # Encontra a última matrícula, convertendo para inteiro para ordenar numericamente.
            last_admission = Admissao.objects.annotate(
                matricula_int=models.functions.Cast('matricula', models.IntegerField())
            ).order_by('-matricula_int').first()
            
            nova_matricula = int(last_admission.matricula) + 1 if last_admission and last_admission.matricula.isdigit() else 1000
            self.matricula = str(nova_matricula)
        
        super().save(*args, **kwargs)

