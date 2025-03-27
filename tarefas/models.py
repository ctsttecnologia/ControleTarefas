from django.db import models
from django.db import models
from django.utils import timezone




class Tarefas(models.Model):
    STATUS_CHOICES = [
            ('pendente', 'Pendente'),
            ('em_andamento', 'Em Andamento'),
            ('concluida', 'Concluída'),
        ]
    titulo = models.CharField(max_length=100, blank=True, null=True, verbose_name="Titulo")
    nome = models.CharField(max_length=40, verbose_name="Nome")
    descricao = models.TextField(verbose_name="Descrição", blank=True, null=True)
    data_inicio = models.DateTimeField(default=timezone.now, verbose_name="Data de Inícil")
    prazo = models.IntegerField(blank=True, null=True, verbose_name="Prazo")
    final = models.DateTimeField(default=timezone.now, verbose_name="Final")
    criado_por = models.CharField(max_length=40, verbose_name="Criado por")
    responsavel = models.CharField(max_length=40, null=True, verbose_name="Responsável")
    participantes = models.CharField(max_length=50, blank=True, null=True, verbose_name="Participantes")
    observadores = models.CharField(max_length=50, blank=True, null=True, verbose_name="Observadores")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente', verbose_name="Status")
    projeto = models.CharField(max_length=40, verbose_name="Projeto")
    data_inicio = models.DateTimeField(default=timezone.now, verbose_name="Data de Inícil")
    modificada_em = models.DateTimeField(default=timezone.now, verbose_name="Modificado em")
    fechado_em = models.DateTimeField(default=timezone.now, verbose_name="Fechado em")
    duracao_prevista = models.IntegerField(blank=True, null=True, verbose_name="Duração")
    controlar_tempo_gasto = models.CharField(max_length=1, blank=True, null=True, verbose_name="Controlar tempo")
    contato_empresa_fornecedor = models.CharField(max_length=40, blank=True, null=True, verbose_name="Contato Empresa/Empresa")
    observador = models.TextField(blank=True, null=True, verbose_name="Observador")
    data_cadastro = models.DateTimeField(default=timezone.now, verbose_name="Data do cadastro")

    def __str__(self):
        return self.titulo


    class Meta:
        verbose_name = "Tarefas"
        verbose_name_plural = "Tarefas"