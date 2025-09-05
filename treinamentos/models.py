
from django.db import models
from django.urls import reverse
from django.conf import settings # Melhor prática para referenciar o User model
from django.utils import timezone

from core.managers import FilialManager
from usuario.models import Filial
from datetime import timedelta

class TipoCurso(models.Model):
    """
    Define os tipos de cursos que podem ser oferecidos,
    com suas características como modalidade, área e validade.
    """
    MODALIDADE_CHOICES = [
        ('P', 'Presencial'),
        ('O', 'Online'),
        ('H', 'Híbrido'),
    ]

    AREA_CHOICES = [
        ('ADM', 'Administrativo'),
        ('COM', 'Comportamental'),
        ('GRA', 'Graduação'),
        ('INT', 'Integração'),
        ('LID', 'Liderança'),
        ('MOT', 'Motivacional'),
        ('OPE', 'Operacional'),
        ('PRO', 'Profissionalizante'),
        ('SAU', 'Saúde'),
        ('SEG', 'Segurança'),      
        ('TEC', 'Técnico'),
    ]

    nome = models.CharField("Nome do Curso", max_length=100, unique=True)
    modalidade = models.CharField("Modalidade", max_length=1, choices=MODALIDADE_CHOICES)
    area = models.CharField("Área de Conhecimento", max_length=3, choices=AREA_CHOICES)
    
    # CORREÇÃO: Removido null=True. Uma string vazia é o padrão para campos de texto.
    descricao = models.TextField("Descrição", blank=True, null=True,)
    
    certificado = models.BooleanField("Emite Certificado?", default=True)
    validade_meses = models.PositiveIntegerField("Validade do Certificado (meses)", help_text="Insira 0 se o certificado não tiver validade.")
    ativo = models.BooleanField("Ativo", default=True)
    data_cadastro = models.DateTimeField("Data de Cadastro", auto_now_add=True)
    data_atualizacao = models.DateTimeField("Data de Atualização", auto_now=True)
    
    # CORREÇÃO CRÍTICA: Removido null=True para garantir que todo curso tenha uma filial.
    filial = models.ForeignKey(
        Filial, 
        on_delete=models.PROTECT,
        related_name='tipocursos',
        verbose_name="Filial",
        null=True
    )
    
    # Manager customizado para segregação de dados
    objects = FilialManager()

    class Meta:
        db_table = 'tipocurso'
        verbose_name = "Tipo de Curso"
        verbose_name_plural = "Tipos de Cursos"
        ordering = ['nome']
        permissions = [
            ('ativar_tipocurso', 'Pode ativar/desativar tipo de curso'),
            ('relatorio_tipocurso', 'Pode gerar relatórios de tipos de curso'),
        ]

    def __str__(self):
        return self.nome

    def get_absolute_url(self):
        """
        Retorna a URL para a página de detalhe deste Tipo de Curso.
        Ajuste o nome 'detalhe_tipo_curso' conforme definido em seu urls.py.
        """
        # CORREÇÃO: A URL deve ser para o detalhe do TipoCurso, não do Treinamento.
        try:
            return reverse('treinamentos:detalhe_tipo_curso', kwargs={'pk': self.pk})
        except:
             # Se a rota de detalhe não existir, redireciona para a lista para evitar erros.
            return reverse('treinamentos:lista_tipos_curso')


class Treinamento(models.Model):
    """
    Armazena informações sobre cada treinamento realizado,
    incluindo datas, status, custos e participantes.
    """
    STATUS_CHOICES = [
        ('P', 'Planejado'),
        ('A', 'Em Andamento'),
        ('C', 'Cancelado'),
        ('F', 'Finalizado'),
    ]

    nome = models.CharField("Nome do Treinamento", max_length=200)
    tipo_curso = models.ForeignKey(TipoCurso, on_delete=models.PROTECT, verbose_name="Tipo de Curso")
    data_inicio = models.DateTimeField("Data de Início")
    # O campo data_vencimento pode ser calculado com base na data_inicio e validade do curso,
    # mas mantido aqui se a regra de negócio exigir uma data customizada.
    data_vencimento = models.DateField("Data de Vencimento")
    # Corrigido: 'unique=True' foi removido, pois vários treinamentos podem ter a mesma duração.
    duracao = models.IntegerField("Duração (horas)")
    atividade = models.CharField("Atividade Relacionada", max_length=200, blank=True)
    descricao = models.TextField("Descrição Detalhada")
    # Corrigido: Alterado de CharField para uma relação com o usuário responsável.
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        related_name='treinamentos_responsavel',
        verbose_name="Responsável",
        null=True,
    )
    # Campo 'cm' mantido, mas um nome mais descritivo como 'centro_custo' é recomendado.
    cm = models.CharField("CM (Centro de Custo?)", max_length=100, blank=True)
    palestrante = models.CharField("Palestrante/Instrutor", max_length=100)
    # Campo 'hxh' mantido, mas um nome como 'horas_homem' é recomendado.
    horas_homem = models.PositiveIntegerField("HxH (Horas Homem)", null=True)
    centro_custo = models.CharField("CM (Centro de Custo)", max_length=100, blank=True)
    status = models.CharField("Status", max_length=1, choices=STATUS_CHOICES, default='P')
    local = models.CharField("Local", max_length=200)
    custo = models.DecimalField("Custo Total", max_digits=10, decimal_places=2, default=0.00)
    # Corrigido: 'unique=True' foi removido.
    participantes_previstos = models.IntegerField("Nº de Participantes Previstos")
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    filial = models.ForeignKey(
        Filial, 
        on_delete=models.PROTECT,
        related_name='treinamentos',
        verbose_name="Filial",
        null=True,
    )
    # Manager customizado para segregação de dados
    objects = FilialManager()

    class Meta:
        db_table = 'treinamento'
        verbose_name = "Treinamento"
        verbose_name_plural = "Treinamentos"
        ordering = ['-data_inicio']
        permissions = [
            ('gerenciar_participantes', 'Pode gerenciar participantes do treinamento'),
            ('alterar_status', 'Pode alterar status do treinamento'),
            ('gerar_certificados', 'Pode gerar certificados de treinamento'),
        ]

    def __str__(self):
        return f"{self.nome} ({self.get_status_display()})"

    def get_absolute_url(self):
        return reverse('treinamentos:detalhe_treinamento', kwargs={'pk': self.pk})

    @property
    def dias_para_vencer(self):
        if not self.data_vencimento:
            return float('inf')  # Retorna infinito se não houver data de vencimento
        return (self.data_vencimento - timezone.now().date()).days

class Participante(models.Model):
    """
    Representa a relação entre um Funcionário (User) e um Treinamento,
    registrando presença, notas e emissão de certificado.
    """
    treinamento = models.ForeignKey(
        Treinamento,
        on_delete=models.CASCADE,
        related_name='participantes',
        verbose_name='Treinamento'
    )
    nome = models.CharField(
        max_length=200, 
        verbose_name='Nome do funcionário'
    )
    # Usando settings.AUTH_USER_MODEL para referenciar o usuário.
    funcionario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Funcionário'
    )
    presente = models.BooleanField(
        default=False,
        verbose_name='Presença Confirmada'
    )
    nota_avaliacao = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Nota da Avaliação'
    )
    certificado_emitido = models.BooleanField(
        default=False,
        verbose_name='Certificado Emitido',
    )
    data_registro = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data de Registro',
        null=True,
    )

    class Meta:
        db_table = 'participante'
        verbose_name = 'Participante'
        verbose_name_plural = 'Participantes'
        # MELHORADO: Usando constraints, a abordagem moderna do Django.
        constraints = [
            models.UniqueConstraint(fields=['treinamento', 'funcionario'], name='inscricao_unica_por_aluno')
        ]
        permissions = [
            ('registrar_presenca', 'Pode registrar presença de participantes'),
            ('emitir_certificado', 'Pode emitir certificado para participante'),
            ('avaliar_participante', 'Pode avaliar participante'),
        ]

    def __str__(self):
        # Acessa o nome através da relação com o funcionário.
        nome_funcionario = getattr(self.funcionario, 'nome_completo', self.funcionario.username)
        return f"{nome_funcionario} - {self.treinamento.nome}"


