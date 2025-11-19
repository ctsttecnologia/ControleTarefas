from django.db import models
from django.contrib.contenttypes.fields import GenericRelation
from django.utils import timezone
from usuario.models import Filial
from core.managers import FilialManager
from documentos.models import Documento  # Importando seu app genérico

class Arquivo(models.Model):
    """
    Modelo gestor que organiza os documentos da empresa.
    Os dados físicos (PDF) e datas críticas ficam no app 'documentos'.
    """
    TIPOS_DOCUMENTO = [
        ('CONTRATO', 'Contrato'),
        ('ALVARA', 'Alvará'),
        ('CERTIDAO', 'Certidão'),
        ('FATURA', 'Fatura/Nota Fiscal'),
        ('RELATORIO', 'Relatório'),
        ('ART', 'ART'),
        ('PGR', 'PGR'),
        ('LAUDO', 'Laudo'),
        ('OUTROS', 'Outros'),
    ]

    STATUS_CHOICES = [
        ('ATIVO', 'Ativo'),
        ('ARQUIVADO', 'Arquivado'),
    ]

    # --- Campos de Identificação e Controle ---
    nome = models.CharField("Nome do Documento", max_length=200)
    tipo = models.CharField("Tipo de Documento", max_length=20, choices=TIPOS_DOCUMENTO, default='OUTROS')
    descricao = models.TextField("Descrição/Observações", blank=True, null=True)
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ATIVO')
    dias_aviso = models.PositiveIntegerField("Avisar dias antes", default=30, help_text="Dias de antecedência para notificar vencimento.")
    cliente = models.ForeignKey(
        'cliente.Cliente',  # <--- Substitua pelo caminho real do seu model Cliente
        on_delete=models.SET_NULL, # Se apagar o cliente, o arquivo fica (sem dono)
        null=True, 
        blank=True, # Opcional: pois existem documentos internos (não de clientes)
        verbose_name="Cliente Relacionado",
        related_name="arquivos" # Permite fazer cliente.arquivos.all()
    )
    # --- Vínculo com Filial (Segurança) ---
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name='arquivos_filial')
    
    # --- Integração com o App Documentos ---
    # A "mágica" que conecta este arquivo ao PDF e à Data de Vencimento
    documentos_anexados = GenericRelation(Documento, related_query_name='arquivo_origem')

    data_cadastro = models.DateTimeField(auto_now_add=True)
    
    objects = FilialManager()

    class Meta:
        verbose_name = "Arquivo"
        verbose_name_plural = "Arquivos"
        ordering = ['-data_cadastro']

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"

    @property
    def documento_vigente(self):
        """Retorna o documento ativo (Vigente ou A Vencer) mais recente anexado."""
        return self.documentos_anexados.order_by('-data_vencimento', '-id').first()

    # Helpers para facilitar o acesso no Template (pegando do documento genérico)
    @property
    def data_vencimento(self):
        doc = self.documento_vigente
        return doc.data_vencimento if doc else None
    
    @property
    def responsavel(self):
        doc = self.documento_vigente
        return doc.responsavel if doc else None

    @property
    def arquivo_url(self):
        doc = self.documento_vigente
        if doc and doc.arquivo:
            return doc.arquivo.url
        return None
