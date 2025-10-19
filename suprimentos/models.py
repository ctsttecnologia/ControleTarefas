
# suprimentos/models.py

from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
# Importe os modelos Filial e Logradouro de onde eles estiverem
from usuario.models import Filial
from core.managers import FilialManager
from logradouro.models import Logradouro 

class Parceiro(models.Model):
    # Campos unificados de Fornecedor e Fabricante
    razao_social = models.CharField(max_length=255, verbose_name=_("Razão Social"), blank=True)
    nome_fantasia = models.CharField(max_length=255, verbose_name=_("Nome Fantasia / Nome do Fabricante"))
    cnpj = models.CharField(max_length=18, unique=True, null=True, blank=True, verbose_name=_("CNPJ"))
    inscricao_estadual = models.CharField(max_length=20, blank=True, verbose_name=_("Inscrição Estadual"))
    
    # Campos de contato
    contato = models.CharField(max_length=100, blank=True, verbose_name=_("Pessoa de Contato"))
    telefone = models.CharField(max_length=20, blank=True, verbose_name=_("Telefone"))
    celular = models.CharField(max_length=20, blank=True, verbose_name=_("Celular"))
    email = models.EmailField(blank=True, verbose_name=_("E-mail"))
    site = models.URLField(blank=True, verbose_name=_("Site"))
    
    # Endereço (antes era só de Fornecedor)
    endereco = models.ForeignKey(
        Logradouro,
        on_delete=models.PROTECT,
        related_name='parceiros',
        verbose_name=_("Endereço"),
        null=True, blank=True
    )
    
    # Campo de observações (antes era só de Fabricante)
    observacoes = models.TextField(blank=True, verbose_name=_("Observações"))
    
    # Flags para identificar o tipo
    eh_fabricante = models.BooleanField(default=False, verbose_name=_("É Fabricante?"))
    eh_fornecedor = models.BooleanField(default=False, verbose_name=_("É Fornecedor?"))

    # Campos de controle
    ativo = models.BooleanField(default=True, verbose_name=_("Ativo"))
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name='parceiros',
        verbose_name=_("Filial"),
        null=True,
        blank=True
    )
    objects = FilialManager()

    class Meta:
        verbose_name = _("Parceiro")
        verbose_name_plural = _("Parceiros")
        ordering = ['nome_fantasia']
        

    def __str__(self):
        # Usar 'or self.razao_social' garante que se o nome fantasia for vazio, ele mostra a razão social.
        return self.nome_fantasia or self.razao_social

    def get_absolute_url(self):
        return reverse('suprimentos:parceiro_detail', kwargs={'pk': self.pk})
