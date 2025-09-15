
from django.db import models
from django.utils.translation import gettext_lazy as _
from logradouro.models import Logradouro
from core.managers import FilialManager
from usuario.models import Filial
from core.validators import (validate_telefone, validate_cnpj, validate_email)


class Cliente(models.Model):

    # Seus campos continuam aqui...
    nome = models.CharField(max_length=100, verbose_name=_('Nome Fantasia'))
    logradouro = models.ForeignKey(Logradouro, on_delete=models.PROTECT, related_name='clientes', verbose_name=_('Endereço'))
    contrato = models.CharField(max_length=4, default='0', verbose_name=_('Número do Contrato (CM)'))
    razao_social = models.CharField(max_length=100, verbose_name=_('Razão Social'))
    unidade = models.PositiveIntegerField(null=True, blank=True, verbose_name=_('Unidade/Filial'))
    cnpj = models.CharField(
        max_length=18,
        unique=True,
        verbose_name=_('CNPJ'),
        help_text=_('Formato: 00.000.000/0000-00'),
        validators=[validate_cnpj]  # O validador é usado aqui
    )
    
    telefone = models.CharField(
        max_length=16,
        blank=True,
        null=True,
        verbose_name=_('Telefone'),
        help_text=_('Formato: (00) 00000-0000 ou (00) 0000-0000'),
        validators=[validate_telefone] # O validador é usado aqui
    )
    email = models.EmailField(
        max_length=100, 
        blank=True, 
        null=True, 
        verbose_name=_('E-mail'),
        validators=[validate_email]
    ) # O validador é usado aqui
    observacoes = models.TextField(blank=True, null=True, verbose_name=_('Observações'))
    inscricao_estadual = models.CharField(max_length=20, blank=True, null=True, verbose_name=_('Inscrição Estadual'))
    inscricao_municipal = models.CharField(max_length=20, blank=True, null=True, verbose_name=_('Inscrição Municipal'))
    data_de_inicio = models.DateField(verbose_name=_('Data de Início'))
    estatus = models.BooleanField(default=True, verbose_name=_('Ativo?'))
    data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name=_('Data de Cadastro'))
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name=_('Última Atualização'))
    data_encerramento = models.DateField(null=True, blank=True, verbose_name=_('Data de Encerramento'))
    # CORREÇÃO: related_name único e campo obrigatório.
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name='Cliente', null=True, blank=False)

    # Manager Padrão
    objects = FilialManager()

    @property
    def cnpj_formatado(self):
        """Retorna CNPJ formatado consistentemente."""
        cnpj_limpo = ''.join(filter(str.isdigit, self.cnpj))
        if len(cnpj_limpo) == 14:
            return f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:]}"
        return self.cnpj

    def __str__(self):
        return self.nome

    class Meta:
        db_table = 'cliente'
        ordering = ['nome']
        verbose_name = _('Cliente')
        verbose_name_plural = _('Clientes')

    