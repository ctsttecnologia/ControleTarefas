from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

class EPI(models.Model):
    nome = models.CharField(max_length=100, verbose_name="Nome do EPI")
    descricao = models.TextField(verbose_name="Descrição")
    certificado = models.CharField(max_length=50, verbose_name="Certificado de Aprovação")
    unidade = models.CharField(max_length=20, verbose_name="Unidade de Medida")

    def __str__(self):
        return self.nome

    class Meta:
        db_table = "epi"  # Nome da tabela no banco de dados
        verbose_name = "EPI"
        verbose_name_plural = "EPIs"
        ordering = ['nome']

class FichaEPI(models.Model):
    empregado = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Empregado")
    cargo = models.CharField(max_length=100, verbose_name="Cargo")
    registro = models.CharField(max_length=50, verbose_name="Registro")
    admissao = models.DateField(verbose_name="Data de Admissão")
    demissao = models.DateField(null=True, blank=True, verbose_name="Data de Demissão")
    contrato = models.CharField(max_length=100, verbose_name="Contrato")
    local_data = models.CharField(max_length=100, verbose_name="Local e Data")
    assinatura = models.ImageField(upload_to='assinaturas/', null=True, blank=True, verbose_name="Assinatura Digital")
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    def __str__(self):
        return f"Ficha EPI - {self.empregado.get_full_name()}"

    def get_absolute_url(self):
        return reverse('visualizar_ficha', args=[str(self.id)])

    class Meta:
        db_table = "ficha_epi"  # Nome da tabela no banco de dados
        verbose_name = "Ficha de EPI"
        verbose_name_plural = "Fichas de EPI"
        ordering = ['-criado_em']

class ItemEPI(models.Model):
    ficha = models.ForeignKey(FichaEPI, on_delete=models.CASCADE, related_name='itens', verbose_name="Ficha")
    epi = models.ForeignKey(EPI, on_delete=models.CASCADE, verbose_name="EPI")
    quantidade = models.IntegerField(verbose_name="Quantidade")
    data_recebimento = models.DateField(verbose_name="Data de Recebimento")
    data_devolucao = models.DateField(null=True, blank=True, verbose_name="Data de Devolução")
    recebedor = models.CharField(max_length=100, null=True, blank=True, verbose_name="Recebedor")

    def __str__(self):
        return f"{self.epi.nome} - {self.quantidade}"

    class Meta:
        verbose_name = "Item de EPI"
        verbose_name_plural = "Itens de EPI"
        ordering = ['data_recebimento']


    