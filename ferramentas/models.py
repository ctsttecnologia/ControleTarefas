
# ferramentas/models.py

from django.db import models
from django.conf import settings
from django.urls import reverse
from django.core.files import File
from django.core.exceptions import ValidationError
from io import BytesIO
import qrcode
from django.db.models import Q
from core.managers import FilialManager 
from usuario.models import Filial, Usuario
from django.utils import timezone
from core.models import BaseModel
from django.conf import settings
import json # Para lidar com o campo 'assinatura_data'
from core.managers import FilialQuerySet, FilialManager
from departamento_pessoal.models import Funcionario
from cliente.models import Cliente
from suprimentos.models import Parceiro 



class FerramentaQuerySet(FilialQuerySet):
        
    # Este método já existia e deve ser mantido:
    def ferramentas_disponiveis_para_mala(self, mala_instance_pk=None):
        sem_mala = Q(mala__isnull=True)
        if mala_instance_pk:
            da_mala_atual = Q(mala__pk=mala_instance_pk)
            return self.filter(sem_mala | da_mala_atual).distinct()
        return self.filter(sem_mala).distinct()


# Crie este novo Manager que herda do seu FilialManager
class FerramentaManager(FilialManager):
    def get_queryset(self):
        # Conecta este manager ao nosso novo QuerySet
        return FerramentaQuerySet(self.model, using=self._db)

    # Este método "empresta" os métodos do QuerySet para o Manager
    
    def __getattr__(self, name):
        # Se o atributo começar com '_', é um atributo interno.
        # Não devemos interferir, então levantamos um AttributeError padrão.
        if name.startswith('_'):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        # Se não for um atributo interno, repassamos a chamada para o QuerySet.
        return getattr(self.get_queryset(), name)

# =============================================================================
# == NOVO MODELO: MALA DE FERRAMENTAS
# =============================================================================
class MalaFerramentas(models.Model):
    """
    Representa um conjunto ou kit de ferramentas que podem ser retiradas juntas.
    Ex: "Mala de Elétrica 01", "Kit de Manutenção Mecânica".
    """
    class Status(models.TextChoices):
        DISPONIVEL = 'disponivel', 'Disponível'
        EM_USO = 'em_uso', 'Em Uso'

    nome = models.CharField(max_length=100, verbose_name="Nome da Mala/Kit")
    codigo_identificacao = models.CharField(max_length=50, unique=True, verbose_name="Código de Identificação")
    localizacao_padrao = models.CharField(max_length=100, verbose_name="Localização Padrão")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DISPONIVEL)
    quantidade = models.IntegerField(default=1, verbose_name="Quantidade (QTDA)")
    qr_code = models.ImageField(upload_to='qrcodes/malas/', blank=True, verbose_name="QR Code da Mala")
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name='malas_ferramentas')

    objects = FilialManager()

    class Meta:
        verbose_name = "Mala de Ferramentas"
        verbose_name_plural = "Malas de Ferramentas"
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} ({self.codigo_identificacao})"

    def get_absolute_url(self):
        # Você precisará criar esta URL e view
        return reverse('ferramentas:mala_detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        """ Gera o QR Code para a mala antes de salvar. """
        if self.codigo_identificacao and not self.qr_code:
            qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
            # O QR Code pode apontar para uma URL específica da mala no sistema
            qr_data = f"MALA_ID:{self.codigo_identificacao}"
            qr.add_data(qr_data)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            fname = f'qr_code_mala-{self.codigo_identificacao}.png'
            buffer = BytesIO()
            qr_img.save(buffer, 'PNG')
            buffer.seek(0)
            
            self.qr_code.save(fname, File(buffer), save=False)

        super().save(*args, **kwargs)


# =============================================================================
# == MODELO FERRAMENTA (MODIFICADO)
# =============================================================================
class Ferramenta(models.Model):
    
    class Status(models.TextChoices):
        DISPONIVEL = 'disponivel', 'Disponível'
        EM_USO = 'em_uso', 'Em Uso'
        EM_MANUTENCAO = 'em_manutencao', 'Em Manutenção'
        DESCARTADA = 'descartada', 'Descartada'

    nome = models.CharField(max_length=100, verbose_name="Nome da Ferramenta")
    patrimonio = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="Nº de Patrimônio")
    codigo_identificacao = models.CharField(max_length=50, unique=True, verbose_name="Código de Identificação (Série/QR)")
    fabricante_marca = models.CharField(max_length=50, blank=True, null=True, verbose_name="Fabricante/Marca")
    modelo = models.CharField(max_length=50, blank=True, null=True, verbose_name="Modelo")
    serie = models.CharField(max_length=50, blank=True, null=True, verbose_name="Série")
    tamanho_polegadas = models.CharField(max_length=20, blank=True, null=True, verbose_name="Tamanho/Polegada")
    quantidade = models.IntegerField(default=0, verbose_name="Quantidade (QTDA)")
    numero_laudo_tecnico = models.CharField(max_length=20, blank=True, null=True)
    localizacao_padrao = models.CharField(max_length=100, verbose_name="Localização Padrão", help_text="Ex: Armário A, Gaveta 3")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DISPONIVEL, verbose_name="Status Interno")
    data_aquisicao = models.DateField(verbose_name="Data de Aquisição")
    data_descarte = models.DateField(blank=True, null=True, verbose_name="Data de Descarte")
    observacoes = models.TextField(blank=True, null=True)
    qr_code = models.ImageField(upload_to='qrcodes/ferramentas/', blank=True, verbose_name="QR Code")
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name='ferramentas', null=True)
    fornecedor = models.ForeignKey(
        Parceiro,  # Referência ao modelo Fornecedor/Parceiro da app suprimentos
        on_delete=models.SET_NULL,  # Não deleta a ferramenta se o fornecedor for deletado
        related_name='ferramentas_fornecidas',  # Permite acessar: fornecedor.ferramentas_fornecidas.all()
        null=True, 
        blank=True, 
        verbose_name="Fornecedor Principal"
    )
    
    # CAMPO ADICIONADO: Relaciona a ferramenta a uma mala específica.
    mala = models.ForeignKey(
        MalaFerramentas, 
        on_delete=models.SET_NULL, 
        related_name='itens', # Para acessar os itens a partir da mala: minha_mala.itens.all()
        null=True, 
        blank=True, 
        verbose_name="Mala de Ferramentas"
    )

    objects = FerramentaManager()

    class Meta:
        verbose_name = "Ferramenta"
        verbose_name_plural = "Ferramentas"
        ordering = ['nome']

    def __str__(self):
        identificador = self.patrimonio or self.codigo_identificacao
        return f"{self.nome} ({identificador})"

    def get_absolute_url(self):
        return reverse('ferramentas:ferramenta_detail', kwargs={'pk': self.pk})
    
    def get_scan_url(self):
        # Retorna a URL relativa para a página de escaneamento
        return reverse('ferramentas:resultado_scan', kwargs={'codigo_identificacao': self.codigo_identificacao})
    
    @property
    def status_efetivo(self):
        # Se a ferramenta estiver descartada, esse é o status final.
        if self.status == self.Status.DESCARTADA:
            return self.Status.DESCARTADA
        
        # Se a ferramenta estiver em manutenção, esse é o status efetivo,
        # independentemente da mala.
        if self.status == self.Status.EM_MANUTENCAO:
            return self.Status.EM_MANUTENCAO

        # Se a ferramenta está associada a uma mala
        if self.mala:
            # Se a mala está em uso, a ferramenta está em uso (efetivamente)
            if self.mala.status == 'em_uso':
                return self.Status.EM_USO
            # Se a mala está disponível, a ferramenta está disponível
            elif self.mala.status == 'disponivel':
                return self.Status.DISPONIVEL
        
        # Se não está em mala ou a mala não tem status 'em_uso' ou 'disponivel',
        # retorna o status direto da ferramenta.
        return self.status
    
    @property
    def esta_disponivel_para_retirada(self):
        # Verifica se o status efetivo permite a retirada
        return self.status_efetivo == self.Status.DISPONIVEL

    @property
    def get_status_efetivo_display(self):
        """ Retorna o texto legível do status efetivo. """
        return dict(self.Status.choices).get(self.status_efetivo)

    @property
    def esta_emprestada(self):
        """ Propriedade booleana para facilitar o uso no template. """
        return self.status_efetivo == Ferramenta.Status.EM_USO
    
    @property
    def termo_ativo(self):
        """
        Se a ferramenta estiver em uma movimentação ativa ligada a um termo,
        retorna esse termo. Caso contrário, retorna None.
        """
        if self.esta_emprestada:
            movimentacao_ativa = self.movimentacoes.filter(data_devolucao__isnull=True).first()
            if movimentacao_ativa and movimentacao_ativa.termo_responsabilidade:
                return movimentacao_ativa.termo_responsabilidade
        return None

    def save(self, *args, **kwargs):
        identifier_for_qr = self.codigo_identificacao or self.patrimonio
        
        if identifier_for_qr and not self.qr_code:
            qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
            # --- MUDANÇA PRINCIPAL AQUI ---
            # Agora o QR Code conterá a URL para a página de scan
            # Precisa configurar seu site para ser acessível externamente 
            # para que isso funcione fora da sua rede local.
            qr_data = f"http://cetestgerenciandotarefas.com.br{self.get_scan_url()}" # Troque SEU_DOMINIO_AQUI pelo seu domínio real

            qr.add_data(qr_data)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")

            fname = f'qr_code-{identifier_for_qr}.png'
            buffer = BytesIO()
            qr_img.save(buffer, 'PNG')
            buffer.seek(0)
            
            self.qr_code.save(fname, File(buffer), save=False)

        super().save(*args, **kwargs)


class Atividade(models.Model):
    # Nenhuma alteração necessária aqui por enquanto, mas você pode querer adicionar
    # logs específicos para ações em malas no futuro.
    class TipoAtividade(models.TextChoices):
        CRIACAO = 'criacao', 'Criação do Registro'
        ALTERACAO = 'alteracao', 'Alteração de Dados'
        RETIRADA = 'retirada', 'Retirada de Ferramenta/Mala'
        DEVOLUCAO = 'devolucao', 'Devolução de Ferramenta/Mala'
        MANUTENCAO_INICIO = 'manutencao_inicio', 'Início da Manutenção'
        MANUTENCAO_FIM = 'manutencao_fim', 'Fim da Manutenção'

  
    # Permitimos que o campo 'ferramenta' seja nulo, pois a atividade pode ser de uma mala.
    ferramenta = models.ForeignKey(
        Ferramenta, 
        on_delete=models.CASCADE, 
        related_name='atividades',
        null=True,  # Permite nulo
        blank=True  # Permite campo em branco
    )
    # Adicionamos o campo 'mala' para registrar atividades da mala de ferramentas.
    mala = models.ForeignKey(
        MalaFerramentas, 
        on_delete=models.CASCADE, 
        related_name='atividades',
        null=True,  # Permite nulo
        blank=True  # Permite campo em branco
    )
    tipo_atividade = models.CharField(max_length=20, choices=TipoAtividade.choices)
    descricao = models.CharField(max_length=255, help_text="Detalhes do evento.")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Usuário Responsável")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Data e Hora")
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name='atividade', null=True)
    
    objects = FilialManager()

    class Meta:
        verbose_name = "Registro de Atividade"
        verbose_name_plural = "Registros de Atividades"
        ordering = ['-timestamp']

    def __str__(self):
        item = self.ferramenta or self.mala
        return f"{self.get_tipo_atividade_display()} em {item}"

# =============================================================================
# == MODELO MOVIMENTAÇÃO (MODIFICADO)
# =============================================================================
class Movimentacao(models.Model):
    
    # Tipo de uso da ferramenta
    TIPOUSO_CHOICES = [
        ('volante', ('VolanteDiária')),
        ('permanete', ('Permanente')),

    ]

    ferramenta = models.ForeignKey(
        Ferramenta, 
        on_delete=models.PROTECT, 
        related_name="movimentacoes",
        null=True,
        blank=True
    )
    
    mala = models.ForeignKey(
        MalaFerramentas,
        on_delete=models.PROTECT,
        related_name="movimentacoes",
        null=True,
        blank=True
    )

    termo_responsabilidade = models.ForeignKey(
        'TermoDeResponsabilidade',  # Usando string para evitar import circular
        on_delete=models.SET_NULL,
        related_name="movimentacoes_geradas",
        null=True,
        blank=True,
        verbose_name="Termo de Responsabilidade Associado"
    )

    retirado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ferramentas_retiradas", verbose_name="Retirado por (Responsável)")
    tipo_uso = models.CharField(max_length=30, choices=TIPOUSO_CHOICES, default='volante', verbose_name="Tipo de Uso")
    data_retirada = models.DateTimeField(auto_now_add=True)
    data_devolucao_prevista = models.DateTimeField(verbose_name="Devolução Prevista")
    condicoes_retirada = models.TextField(verbose_name="Condições na Retirada", help_text="Descreva o estado do item (arranhões, funcionamento, etc.)")
    assinatura_retirada = models.ImageField(upload_to='assinaturas/%Y/%m/', verbose_name="Assinatura de Retirada")
    data_devolucao = models.DateTimeField(blank=True, null=True, verbose_name="Data de Devolução")
    recebido_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ferramentas_recebidas", blank=True, null=True, verbose_name="Recebido por")
    condicoes_devolucao = models.TextField(blank=True, null=True, verbose_name="Condições na Devolução")
    assinatura_devolucao = models.ImageField(upload_to='assinaturas/%Y/%m/', blank=True, null=True, verbose_name="Assinatura de Devolução")
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name='movimentacao', null=True)
    
    objects = FilialManager()
    
    @property
    def item_movimentado(self):
        """ Propriedade para retornar o item (Ferramenta ou Mala) que foi movimentado. """
        return self.ferramenta or self.mala

    @property
    def esta_ativa(self):
        return self.data_devolucao is None

    
    def __str__(self):
        item = self.item_movimentado
        if item:
            return f"Retirada de '{item}' por {self.retirado_por.get_username()}"
        return f"Movimentação #{self.pk}"

    class Meta:
        verbose_name = "Movimentação"
        verbose_name_plural = "Movimentações"
        ordering = ['-data_retirada']

"""Modelo principal do Termo de Responsabilidade."""

class TermoDeResponsabilidade(models.Model):
    """
    Representa o documento principal do Termo de Responsabilidade,
    espelhando o layout do PDF fornecido.
    """
    class TipoUso(models.TextChoices):
        FERRAMENTAL = 'FER', 'Ferramental'
        MALA = 'MAL', 'Mala'

    # CAMPOS DO CABEÇALHO DO PDF
    contrato = models.CharField(max_length=200, verbose_name="Contrato")
    responsavel = models.ForeignKey(
        Funcionario,
        on_delete=models.PROTECT,
        related_name='termos_responsabilidade',
        verbose_name="Responsável"
    )
    separado_por = models.ForeignKey(
        Funcionario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='termos_separados',
        verbose_name="Separado por (Coordenador)"
    )
    data_emissao = models.DateField(default=timezone.now, verbose_name="Data de Emissão")
    data_recebimento = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Data de Recebimento (Assinatura)"
    )
    
    # CAMPOS INTERNOS E DE CONTROLE
    tipo_uso = models.CharField(
        max_length=30,
        choices=TipoUso.choices,
        verbose_name="Tipo de Uso (Ferramental/Mala)"
    )
    assinatura_data = models.TextField(
        null=True,
        blank=True,
        verbose_name="Dados da Assinatura (Base64)"
    )
    movimentado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        verbose_name="Movimentado por"
    )
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name='termos_responsabilidade')

    objects = FilialManager()

    class Meta:
        verbose_name = "Termo de Responsabilidade"
        verbose_name_plural = "Termos de Responsabilidade"

    def __str__(self):
        return f"Termo #{self.pk} - {self.get_tipo_uso_display()} por {self.responsavel}"

    def is_signed(self):
        return bool(self.assinatura_data)


class ItemTermo(models.Model):
    """
    Representa uma linha na tabela de itens do Termo de Responsabilidade.
    """
    termo = models.ForeignKey(
        TermoDeResponsabilidade,
        on_delete=models.CASCADE,
        related_name='itens',
        verbose_name="Termo"
    )
    
    # CAMPOS DA TABELA DO PDF
    quantidade = models.IntegerField(verbose_name="Quantidade (QTDA)")
    unidade = models.CharField(max_length=10, verbose_name="Unidade (UN)")
    item = models.CharField(max_length=255, verbose_name="Item (Descrição)")
    
    # RELAÇÕES INTERNAS PARA LIGAÇÃO COM O ESTOQUE
    ferramenta = models.ForeignKey(
        'Ferramenta',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Ferramenta Associada"
    )
    mala = models.ForeignKey(
        'MalaFerramentas',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Mala Associada"
    )

    class Meta:
        verbose_name = "Item do Termo"
        verbose_name_plural = "Itens do Termo"

    def __str__(self):
        return f"{self.item} ({self.quantidade} {self.unidade})"
    
    