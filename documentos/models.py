from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils import timezone

# Importando a infraestrutura de Filial, conforme seus outros apps
from usuario.models import Filial
from core.managers import FilialManager

def private_document_path(instance, filename):
    """
    Função de upload segura que armazena ficheiros numa pasta privada
    baseada no "dono" do documento (ex: /private_media/documentos/treinamento/42/certificado.pdf)
    """
    app_label = instance.content_type.app_label
    object_id = instance.object_id
    return f'documentos/{app_label}/{object_id}/{filename}'

class Documento(models.Model):
    """
    Modelo centralizado para gestão de documentos com data de vencimento.
    Pode ser anexado a qualquer outro modelo no sistema (Funcionário,
    Treinamento, Equipamento, etc.) usando GenericForeignKey.
    """
    
    class StatusChoices(models.TextChoices):
        VIGENTE = 'VIGENTE', 'Vigente'
        A_VENCER = 'A_VENCER', 'A Vencer' # (Status de aviso, controlado pela task Celery)
        VENCIDO = 'VENCIDO', 'Vencido'     # (Status de vencido, controlado pela task Celery)
        RENOVADO = 'RENOVADO', 'Renovado/Inativo' # (Arquivado após substituição)

    nome = models.CharField("Nome do Documento", max_length=255)
    
    arquivo = models.FileField(
        "Ficheiro",
        upload_to=private_document_path,
        help_text="O ficheiro será armazenado em local seguro."
    )

    data_emissao = models.DateField("Data de Emissão", null=True, blank=True)
    data_vencimento = models.DateField(
        "Data de Vencimento", 
        null=True, 
        blank=True,
        help_text="Deixe em branco se o documento não tiver vencimento."
    )

    status = models.CharField(
        "Status",
        max_length=10, 
        choices=StatusChoices.choices, 
        default=StatusChoices.VIGENTE
    )
    
    # O responsável por este documento (quem será notificado)
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Responsável",
        related_name="documentos_responsaveis"
    )

    # --- Integração com Filial (padrão do seu projeto) ---
    # Este campo é essencial para o FilialManager funcionar.
    # Na sua CreateView, defina este campo:
    # form.instance.filial = self.request.user.filial_ativa
    
    filial = models.ForeignKey(
        Filial, 
        on_delete=models.PROTECT,
        related_name='documentos_filial',
        verbose_name="Filial",
        null=True # Permite null, mas a view deve preenchê-lo
    )

    # Manager customizado para segregação de dados
    objects = FilialManager()
    # --- Fim da Integração com Filial ---

    
    # --- Campos do GenericForeignKey (GFK) ---
    # Permite anexar este documento a QUALQUER outro modelo
    content_type = models.ForeignKey(
        ContentType, 
        on_delete=models.CASCADE,
        verbose_name="Tipo de Objeto"
    )
    
    object_id = models.PositiveIntegerField("ID do Objeto")
    
    content_object = GenericForeignKey(
        'content_type', 
        'object_id'

    )    
    # --- Rastreamento de Renovação ---
    # Se este documento for uma renovação, ele aponta para o doc antigo
    substitui = models.OneToOneField(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="substituto",
        verbose_name="Substitui o Documento"
    )
    # --- Fim do Rastreamento ---

    data_cadastro = models.DateTimeField("Data de Cadastro", auto_now_add=True)
    data_atualizacao = models.DateTimeField("Data de Atualização", auto_now=True)

    class Meta:
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"
        # Ordena pelos vencidos/a vencer mais próximos primeiro
        ordering = ['data_vencimento'] 
        permissions = [
            ("pode_gerenciar_todos_documentos", "Pode gerenciar documentos de todas as filiais"),
            ("pode_validar_documento", "Pode validar um documento enviado"),
        ]

    def __str__(self):
        return self.nome

    def get_absolute_url(self):
        """
        Retorna a URL para a ação principal do documento, que é o download.
        """
        return reverse('documentos:download', kwargs={'pk': self.pk})

    def is_vencido(self):
        """
        Verificação simples se a data de vencimento já passou.
        (A task Celery é quem muda o STATUS, isto é apenas um helper)
        """
        if not self.data_vencimento:
            return False
        return self.data_vencimento < timezone.now().date()


