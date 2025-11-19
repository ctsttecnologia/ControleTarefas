
import uuid
from django.core.signing import Signer
from django.utils.html import mark_safe
from django.db import models
from django.urls import reverse
from django.conf import settings # Melhor prática para referenciar o User model
from django.utils import timezone

from core.managers import FilialManager
from usuario.models import Filial
from datetime import timedelta

# Necessário para a relação genérica
from django.contrib.contenttypes.fields import GenericRelation

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
    descricao_no_certificado = models.TextField(
        "Descrição (para frente do certificado)", 
        blank=True, null=True,
        help_text="Texto que descreve o conteúdo, ex: 'Curso sobre Designado de CIPA...'"
    )
    
    certificado = models.BooleanField("Emite Certificado?", default=True)
    validade_meses = models.PositiveIntegerField("Validade do Certificado (meses)", 
        default=0,
        help_text="Insira 0 se o certificado não tiver validade."
    )
    ativo = models.BooleanField("Ativo", default=True)
    data_cadastro = models.DateTimeField("Data de Cadastro", auto_now_add=True)
    data_atualizacao = models.DateTimeField("Data de Atualização", auto_now=True)
    conteudo_programatico = models.TextField(
        "Conteúdo Programático", 
        blank=True, null=True,
        help_text="Texto que descreve o conteúdo, ex: 'Curso sobre Designado de CIPA...'"
    )
    referencia_normativa = models.CharField(
        "Referência Normativa", 
        max_length=255, 
        blank=True, null=True,
        help_text="Ex: 'conforme NR-5 Portaria nº 08 de 23 de fevereiro de 1.999'"
    )
    grade_curricular = models.TextField(
        "Grade Curricular (para verso)",
        blank=True, null=True,
        help_text="Conteúdo programático detalhado que aparecerá no verso. Use quebras de linha para listar os tópicos."
    )
    
    # Removido null=True para garantir que todo curso tenha uma filial.
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
    data_fim = models.DateTimeField("Data de Fim", null=True, blank=True)
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
    palestrante_cargo = models.CharField(
        "Cargo do Palestrante", 
        max_length=100, 
        blank=True, null=True,
        help_text="Ex: 'Técnica de Segurança do Trabalho'"
    )
    palestrante_registro = models.CharField(
        "Registro Prof. do Palestrante", 
        max_length=50, 
        blank=True, null=True,
        help_text="Ex: 'Registro do MTE SP 0073739'"
    )
    assinaturas_solicitadas = models.BooleanField(
        "Assinaturas Solicitadas",
        default=False, 
        help_text="Marca se os links de assinatura já foram enviados."
    )
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

    
    # --- INTEGRAÇÃO COM A APP 'documentos' ---
    # Adicione esta linha ao seu modelo.
    # 'documentos.Documento' = app_label.ModelName
    
    documentos = GenericRelation(
        'documentos.Documento',
        related_query_name='documento' # <--- O argumento vai aqui
    )

    class Meta:
        db_table = 'treinamento'
        verbose_name = "Treinamento"
        verbose_name_plural = "Treinamentos"
        ordering = ['-data_inicio']
        permissions = [
            ('gerenciar_participantes', 'Pode gerenciar participantes do treinamento'),
            ('alterar_status', 'Pode alterar status do treinamento'),
            ('gerar_certificados', 'Pode gerar certificados de treinamento'),
            ("ver_relatorios", "Pode visualizar o dashboard e relatórios"),
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
    protocolo_validacao = models.UUIDField(
        "Protocolo de Validação",
        default=uuid.uuid4,
        editable=False,
        unique=False,
        null=True,
        db_index=True,
        help_text="ID único para validação do certificado (usado no QR Code)"
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


class GabaritoCertificado(models.Model):
    """
    Armazena o template (gabarito) base para todos os certificados.
    """
    nome = models.CharField("Nome do Gabarito", max_length=100, default="Gabarito Padrão")
    empresa_nome = models.CharField("Nome da Empresa Certificadora", max_length=255, default="CETEST MINAS ENGENHARIA E SERVIÇOS S/A")
    texto_principal = models.TextField(
        "Texto Principal do Certificado",
        default="Certificamos que <strong>{participante_nome}</strong>, portador(a) do documento {participante_documento}, participou do <strong>{nome_curso}</strong> ({conteudo_programatico}), promovido pela {empresa_nome}, {referencia_normativa}, realizado em {local} no período de {data_inicio} a {data_fim}, com carga horária total de <strong>{carga_horaria} ({carga_horaria_extenso}) horas</strong>.",
        help_text="Use os placeholders disponíveis: {participante_nome}, {participante_documento}, {empresa_nome}, {nome_curso}, {conteudo_programatico}, {referencia_normativa}, {data_inicio}, {data_fim}, {carga_horaria}, {carga_horaria_extenso}, {local}"
    )
    imagem_fundo = models.ImageField(
        "Imagem de Fundo (Opcional)", 
        upload_to='certificados/fundos/', 
        null=True, blank=True
    )
    texto_verso = models.TextField(
        "Texto do Verso",
        blank=True, null=True,
        default=(
            "<h3>CONTEÚDO PROGRAMÁTICO</h3>"
            "<div class='grade-curricular'>{grade_curricular}</div>"
            "<hr>"
            "Protocolo de Validação: <strong>{protocolo}</strong><br>"
            "Para verificar a autenticidade deste certificado, aponte a câmera do seu celular para o QR Code."
        ),
        help_text="Texto padrão do verso. Use {grade_curricular}, {protocolo} e {qr_code_tag} (o QR Code será inserido aqui)."
    )
    ativo = models.BooleanField("Ativo", default=True)

    class Meta:
        verbose_name = "Gabarito de Certificado"
        verbose_name_plural = "Gabaritos de Certificado"

    def __str__(self):
        return self.nome

    def renderizar_texto(self, context_dict):
        """
        Substitui os placeholders no texto principal com dados reais.
        """
        return mark_safe(self.texto_principal.format(**context_dict))
    
    def renderizar_verso(self, context_dict):
        """
        Substitui os placeholders no texto do verso com dados reais.
        """
        return mark_safe(self.texto_verso.format(**context_dict))


class Assinatura(models.Model):
    """
    Armazena a coleta de assinatura digital para um participante ou instrutor.
    """
    # Relação: Ou pertence a um participante OU ao responsável de um treinamento
    participante = models.OneToOneField(
        Participante, 
        on_delete=models.CASCADE, 
        related_name='assinatura', 
        null=True, blank=True
    )
    treinamento_responsavel = models.OneToOneField(
        Treinamento, 
        on_delete=models.CASCADE, 
        related_name='assinatura_responsavel',
        null=True, blank=True,
        help_text="Assinatura do Responsável/Instrutor pelo treinamento"
    )
    
    token_acesso = models.CharField(
        "Token de Acesso",
        max_length=100, 
        unique=True, 
        db_index=True,
        default=uuid.uuid4
    )
    assinatura_json = models.TextField("Dados da Assinatura (JSON)", blank=True, null=True)
    data_assinatura = models.DateTimeField("Data da Assinatura", null=True, blank=True)
    
    # Campos para identificar quem assinou (cache)
    nome_assinante = models.CharField(max_length=255, blank=True)
    documento_assinante = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = "Assinatura de Certificado"
        verbose_name_plural = "Assinaturas de Certificado"

    def __str__(self):
        if self.participante:
            return f"Assinatura de {self.participante.funcionario.get_full_name()}"
        if self.treinamento_responsavel:
            return f"Assinatura do Responsável por {self.treinamento_responsavel.nome}"
        return f"Assinatura Pendente ({self.token_acesso})"

    @property
    def esta_assinada(self):
        return self.data_assinatura is not None

    def get_signer(self):
        """ Retorna o nome de quem deve assinar. """
        if self.nome_assinante:
            return self.nome_assinante
        if self.participante:
            return self.participante.funcionario.get_full_name()
        if self.treinamento_responsavel:
            return self.treinamento_responsavel.responsavel.get_full_name()
        return "Desconhecido"