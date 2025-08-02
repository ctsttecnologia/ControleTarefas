# ferramentas/models.py

from django.db import models
from django.conf import settings
from django.urls import reverse
from django.core.files import File
from io import BytesIO
import qrcode
from core.managers import FilialManager # 👈 Importe o manager do app 'core'
from usuario.models import Filial, Usuario

# Não há necessidade de importar Image da PIL diretamente no modelo se o qrcode a utiliza internamente.

class Ferramenta(models.Model):
    class Status(models.TextChoices):
        DISPONIVEL = 'disponivel', 'Disponível'
        EM_USO = 'em_uso', 'Em Uso'
        EM_MANUTENCAO = 'em_manutencao', 'Em Manutenção'
        DESCARTADA = 'descartada', 'Descartada'

    nome = models.CharField(max_length=100, verbose_name="Nome da Ferramenta")
    patrimonio = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="Nº de Patrimônio")
    codigo_identificacao = models.CharField(max_length=50, unique=True, verbose_name="Código de Identificação (Série/QR)")
    fabricante = models.CharField(max_length=50, blank=True, null=True)
    localizacao_padrao = models.CharField(max_length=100, verbose_name="Localização Padrão", help_text="Ex: Armário A, Gaveta 3")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DISPONIVEL)
    data_aquisicao = models.DateField(verbose_name="Data de Aquisição")
    observacoes = models.TextField(blank=True, null=True)
    qr_code = models.ImageField(upload_to='qrcodes/', blank=True, verbose_name="QR Code")
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name='ferramentas', null=True)
    # Manager Padrão
    objects = FilialManager()

    class Meta:
        verbose_name = "Ferramenta"
        verbose_name_plural = "Ferramentas"
        ordering = ['nome']

    def __str__(self):
        # Usar o patrimônio se existir, senão o código de identificação, torna a representação mais robusta.
        identificador = self.patrimonio or self.codigo_identificacao
        return f"{self.nome} ({identificador})"

    def get_absolute_url(self):
        """ Retorna a URL para a página de detalhes desta ferramenta. """
        # O nome da rota 'ferramenta_detail' precisa corresponder ao definido em urls.py
        return reverse('ferramentas:ferramenta_detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        """ Gera o QR Code com base no código de identificação ou patrimônio antes de salvar. """
        # Usa o código de identificação como prioridade para o QR Code, pois é único e obrigatório.
        identifier_for_qr = self.codigo_identificacao or self.patrimonio
        
        if identifier_for_qr and not self.qr_code:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            # Idealmente, o QR Code deve apontar para a URL da própria ferramenta no sistema.
            # Se você tiver o site configurado, pode usar a URL completa.
            # Por enquanto, usaremos o identificador.
            qr_data = f"FERRAMENTA_ID:{identifier_for_qr}"
            qr.add_data(qr_data)
            qr.make(fit=True)

            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            fname = f'qr_code-{identifier_for_qr}.png'
            buffer = BytesIO()
            qr_img.save(buffer, 'PNG')
            
            # save=False é crucial para evitar um loop de salvamento infinito.
            self.qr_code.save(fname, File(buffer), save=False)

        super().save(*args, **kwargs)

class Atividade(models.Model):
    """ Modelo para registrar um histórico de eventos importantes (log de auditoria). """
    class TipoAtividade(models.TextChoices):
        CRIACAO = 'criacao', 'Criação do Registro'
        ALTERACAO = 'alteracao', 'Alteração de Dados'
        RETIRADA = 'retirada', 'Retirada de Ferramenta'
        DEVOLUCAO = 'devolucao', 'Devolução de Ferramenta'
        MANUTENCAO_INICIO = 'manutencao_inicio', 'Início da Manutenção'
        MANUTENCAO_FIM = 'manutencao_fim', 'Fim da Manutenção'

    ferramenta = models.ForeignKey(Ferramenta, on_delete=models.CASCADE, related_name='atividades')
    tipo_atividade = models.CharField(max_length=20, choices=TipoAtividade.choices)
    descricao = models.CharField(max_length=255, help_text="Detalhes do evento.")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Usuário Responsável")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Data e Hora")
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name='atividade', null=True)
    # Manager Padrão
    objects = FilialManager()

    class Meta:
        verbose_name = "Registro de Atividade"
        verbose_name_plural = "Registros de Atividades"
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.get_tipo_atividade_display()} em {self.ferramenta.nome}"

class Movimentacao(models.Model):
    """ Controla o check-out (retirada) e check-in (devolução) de ferramentas. """
    ferramenta = models.ForeignKey(Ferramenta, on_delete=models.PROTECT, related_name="movimentacoes")
    retirado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ferramentas_retiradas", verbose_name="Retirado por (Responsável)")
    data_retirada = models.DateTimeField(auto_now_add=True)
    data_devolucao_prevista = models.DateTimeField(verbose_name="Devolução Prevista")
    condicoes_retirada = models.TextField(verbose_name="Condições na Retirada", help_text="Descreva o estado da ferramenta (arranhões, funcionamento, etc.)")
    assinatura_retirada = models.ImageField(upload_to='assinaturas/%Y/%m/', verbose_name="Assinatura de Retirada")

    data_devolucao = models.DateTimeField(blank=True, null=True, verbose_name="Data de Devolução")
    recebido_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ferramentas_recebidas", blank=True, null=True, verbose_name="Recebido por")
    condicoes_devolucao = models.TextField(blank=True, null=True, verbose_name="Condições na Devolução")
    assinatura_devolucao = models.ImageField(upload_to='assinaturas/%Y/%m/', blank=True, null=True, verbose_name="Assinatura de Devolução")
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name='movimentacao', null=True)
    # Manager Padrão
    objects = FilialManager()

    @property
    def esta_ativa(self):
        """ Propriedade para verificar facilmente se a movimentação está em aberto. """
        return self.data_devolucao is None

    def __str__(self):
        return f"Retirada de '{self.ferramenta.nome}' por {self.retirado_por.get_username()}"

    class Meta:
        verbose_name = "Movimentação"
        verbose_name_plural = "Movimentações"
        ordering = ['-data_retirada']

