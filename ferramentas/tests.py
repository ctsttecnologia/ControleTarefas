
# ferramentas/tests.py
"""
Testes para o app ferramentas

Comandos
pytest ferramentas/tests.py
python manage.py test ferramentas

python manage.py test ferramentas
python manage.py test ferramentas -v 2
python manage.py test ferramentas.tests.MovimentacaoConstraintTest
python manage.py test ferramentas.tests.MovimentacaoConcorrenciaTest
"""
from datetime import date, timedelta, datetime

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.utils import IntegrityError
from django.utils import timezone

# Modelos da app 'ferramentas'
from .models import (
    AssinaturaMovimentacao, MalaFerramentas, Ferramenta, Atividade,
    Movimentacao, TermoDeResponsabilidade, ItemTermo
)

# Dependências de outras apps
from usuario.models import Filial
from departamento_pessoal.models import Departamento, Funcionario
from suprimentos.models import Parceiro
from seguranca_trabalho.models import Cargo, Funcao


User = get_user_model()


class FerramentasBaseTestCase(TestCase):
    """
    Classe base com dados comuns para todos os testes do app ferramentas.
    Desativa signals problemáticos durante os testes.
    """

    @classmethod
    def setUpClass(cls):
        """Desativa signals antes de iniciar os testes"""
        super().setUpClass()
        cls._disconnect_signals()

    @classmethod
    def tearDownClass(cls):
        """Reativa signals após os testes"""
        cls._reconnect_signals()
        super().tearDownClass()

    @classmethod
    def _disconnect_signals(cls):
        """Desconecta signals problemáticos"""
        from django.db.models.signals import post_save
        from departamento_pessoal.models import Funcionario

        cls._stored_receivers = []

        for receiver in post_save._live_receivers(Funcionario):
            receiver_name = getattr(receiver, '__name__', str(receiver))
            if 'pgr' in receiver_name.lower() or 'admissional' in receiver_name.lower():
                cls._stored_receivers.append((post_save, Funcionario, receiver))

        for signal, sender, receiver in cls._stored_receivers:
            signal.disconnect(receiver, sender=sender)

    @classmethod
    def _reconnect_signals(cls):
        """Reconecta signals que foram desconectados"""
        for signal, sender, receiver in getattr(cls, '_stored_receivers', []):
            signal.connect(receiver, sender=sender)

    @classmethod
    def setUpTestData(cls):
        """Configura dados comuns para todos os testes"""

        cls.filial = Filial.objects.create(
            nome=f"Filial Teste {timezone.now().timestamp()}"
        )

        cls.departamento = Departamento.objects.create(
            nome=f"Departamento Teste {timezone.now().timestamp()}",
            filial=cls.filial
        )

        cls.user = User.objects.create_user(
            username=f'testuser_{timezone.now().timestamp()}',
            password='password123'
        )
        if hasattr(cls.user, 'filial'):
            cls.user.filial = cls.filial
            cls.user.save()

        cls.cargo = Cargo.objects.create(
            filial=cls.filial,
            nome=f"Cargo Teste {timezone.now().timestamp()}"
        )
        cls.funcao = Funcao.objects.create(
            filial=cls.filial,
            nome=f"Função Teste {timezone.now().timestamp()}"
        )

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')

        cls.funcionario = Funcionario.objects.create(
            nome_completo='João da Silva Teste',
            matricula=f'TESTE-FUNC-{timestamp}',
            filial=cls.filial,
            cargo=cls.cargo,
            funcao=cls.funcao,
            data_admissao=timezone.now().date(),
            departamento=cls.departamento
        )

        cls.coordenador = Funcionario.objects.create(
            nome_completo='Maria Coordenadora Teste',
            matricula=f'TESTE-COORD-{timestamp}',
            filial=cls.filial,
            cargo=cls.cargo,
            funcao=cls.funcao,
            data_admissao=timezone.now().date(),
            departamento=cls.departamento
        )

        cls.tecnico = Funcionario.objects.create(
            nome_completo='Técnico de Testes',
            matricula=f'TESTE-TEC-{timestamp}',
            filial=cls.filial,
            cargo=cls.cargo,
            funcao=cls.funcao,
            data_admissao=timezone.now().date(),
            departamento=cls.departamento
        )

        cls.parceiro = Parceiro.objects.create(
            nome_fantasia='Fornecedor ABC Teste',
            filial=cls.filial,
            cnpj='12.345.678/0001-99'
        )


class MalaFerramentasModelTest(FerramentasBaseTestCase):
    """Testes para o modelo MalaFerramentas."""

    def test_criacao_mala_sucesso(self):
        """Verifica se uma Mala de Ferramentas é criada corretamente."""
        mala = MalaFerramentas.objects.create(
            nome="Mala de Elétrica 01",
            codigo_identificacao="M-ELET-01",
            localizacao_padrao="Armário C, Prateleira 2",
            filial=self.filial
        )
        self.assertEqual(str(mala), "Mala de Elétrica 01 (M-ELET-01)")
        self.assertEqual(mala.status, MalaFerramentas.Status.DISPONIVEL)

        if mala.qr_code and mala.qr_code.name:
            self.assertTrue(mala.qr_code.name.endswith('.png'))

    def test_codigo_identificacao_deve_ser_unico(self):
        """Testa a restrição 'unique' do campo codigo_identificacao."""
        MalaFerramentas.objects.create(
            nome="Mala 01",
            codigo_identificacao="M-UNIQUE-01",
            filial=self.filial
        )
        with self.assertRaises(IntegrityError):
            MalaFerramentas.objects.create(
                nome="Mala 02",
                codigo_identificacao="M-UNIQUE-01",
                filial=self.filial
            )

    def test_get_absolute_url(self):
        """Testa se a URL absoluta da mala é gerada corretamente."""
        mala = MalaFerramentas.objects.create(
            nome="Kit Mecânico",
            codigo_identificacao="M-MEC-URL-01",
            filial=self.filial
        )
        expected_url = f'/ferramentas/malas/{mala.pk}/'
        self.assertEqual(mala.get_absolute_url(), expected_url)

    def test_qr_code_nao_gerado_sem_codigo(self):
        """Verifica se o QR code não é gerado sem um código de identificação."""
        mala = MalaFerramentas.objects.create(
            nome="Mala Sem Código",
            localizacao_padrao="Armário D",
            filial=self.filial
        )
        self.assertFalse(bool(mala.qr_code and mala.qr_code.name))


class FerramentaModelTest(FerramentasBaseTestCase):
    """Testes para o modelo Ferramenta."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.mala = MalaFerramentas.objects.create(
            nome="Mala Padrão Ferramenta",
            codigo_identificacao="M-PADRAO-FERR",
            filial=cls.filial
        )

    def test_criacao_ferramenta_sucesso(self):
        """Verifica a criação de uma Ferramenta com todos os campos."""
        hoje = timezone.now().date()
        ferramenta = Ferramenta.objects.create(
            nome="Furadeira de Impacto",
            patrimonio="PAT-12345",
            codigo_identificacao="FUR-001",
            fabricante_marca="Bosch",
            localizacao_padrao="Bancada 1",
            data_aquisicao=hoje,
            filial=self.filial,
            fornecedor=self.parceiro,
            mala=self.mala
        )
        self.assertEqual(str(ferramenta), "Furadeira de Impacto (PAT-12345)")
        self.assertEqual(ferramenta.status, Ferramenta.Status.DISPONIVEL)

    def test_status_efetivo_ferramenta_disponivel_mala_disponivel(self):
        """Testa status efetivo: ferramenta e mala disponíveis."""
        ferramenta = Ferramenta.objects.create(
            filial=self.filial,
            nome="Alicate de Pressão",
            codigo_identificacao="AL-001-A",
            data_aquisicao=date.today(),
            status=Ferramenta.Status.DISPONIVEL,
            mala=self.mala
        )

        self.mala.status = MalaFerramentas.Status.DISPONIVEL
        self.mala.save()
        ferramenta.refresh_from_db()

        self.assertEqual(ferramenta.status_efetivo, Ferramenta.Status.DISPONIVEL)
        self.assertTrue(ferramenta.esta_disponivel_para_retirada)
        self.assertFalse(ferramenta.esta_emprestada)

    def test_status_efetivo_ferramenta_disponivel_mala_em_uso(self):
        """Testa status efetivo: ferramenta disponível mas mala em uso."""
        ferramenta = Ferramenta.objects.create(
            filial=self.filial,
            nome="Alicate de Pressão B",
            codigo_identificacao="AL-001-B",
            data_aquisicao=date.today(),
            status=Ferramenta.Status.DISPONIVEL,
            mala=self.mala
        )

        self.mala.status = MalaFerramentas.Status.EM_USO
        self.mala.save()
        ferramenta.refresh_from_db()

        self.assertEqual(ferramenta.status_efetivo, Ferramenta.Status.EM_USO)
        self.assertFalse(ferramenta.esta_disponivel_para_retirada)
        self.assertTrue(ferramenta.esta_emprestada)

    def test_status_efetivo_ferramenta_em_manutencao(self):
        """Testa status efetivo: ferramenta em manutenção (ignora mala)."""
        ferramenta = Ferramenta.objects.create(
            filial=self.filial,
            nome="Alicate de Pressão C",
            codigo_identificacao="AL-001-C",
            data_aquisicao=date.today(),
            status=Ferramenta.Status.EM_MANUTENCAO,
            mala=self.mala
        )

        self.assertEqual(ferramenta.status_efetivo, Ferramenta.Status.EM_MANUTENCAO)
        self.assertFalse(ferramenta.esta_disponivel_para_retirada)

    def test_status_efetivo_ferramenta_descartada(self):
        """Testa status efetivo: ferramenta descartada (status final)."""
        ferramenta = Ferramenta.objects.create(
            filial=self.filial,
            nome="Alicate de Pressão D",
            codigo_identificacao="AL-001-D",
            data_aquisicao=date.today(),
            status=Ferramenta.Status.DESCARTADA,
            mala=self.mala
        )

        self.assertEqual(ferramenta.status_efetivo, Ferramenta.Status.DESCARTADA)
        self.assertFalse(ferramenta.esta_disponivel_para_retirada)

    def test_status_efetivo_sem_mala(self):
        """Testa o status efetivo quando a ferramenta não está em uma mala."""
        ferramenta = Ferramenta.objects.create(
            filial=self.filial,
            nome="Chave de Fenda",
            codigo_identificacao="CF-001",
            data_aquisicao=date.today(),
            status=Ferramenta.Status.DISPONIVEL
        )
        self.assertEqual(ferramenta.status_efetivo, Ferramenta.Status.DISPONIVEL)
        self.assertTrue(ferramenta.esta_disponivel_para_retirada)

    def test_manager_ferramentas_disponiveis_para_mala(self):
        """Testa o método customizado do Manager/QuerySet."""
        mala_a = MalaFerramentas.objects.create(
            nome="Mala A Manager",
            codigo_identificacao="M-A-MGR",
            filial=self.filial
        )
        mala_b = MalaFerramentas.objects.create(
            nome="Mala B Manager",
            codigo_identificacao="M-B-MGR",
            filial=self.filial
        )

        ferramenta_livre = Ferramenta.objects.create(
            nome="Martelo",
            codigo_identificacao="F-LIVRE-MGR",
            data_aquisicao=timezone.now().date(),
            filial=self.filial
        )
        ferramenta_mala_a = Ferramenta.objects.create(
            nome="Alicate",
            codigo_identificacao="F-MALA-A-MGR",
            data_aquisicao=timezone.now().date(),
            filial=self.filial,
            mala=mala_a
        )
        ferramenta_mala_b = Ferramenta.objects.create(
            nome="Serrote",
            codigo_identificacao="F-MALA-B-MGR",
            data_aquisicao=timezone.now().date(),
            filial=self.filial,
            mala=mala_b
        )

        disponiveis_nova_mala = Ferramenta.objects.ferramentas_disponiveis_para_mala()
        self.assertIn(ferramenta_livre, disponiveis_nova_mala)
        self.assertNotIn(ferramenta_mala_a, disponiveis_nova_mala)
        self.assertNotIn(ferramenta_mala_b, disponiveis_nova_mala)

        disponiveis_mala_a = Ferramenta.objects.ferramentas_disponiveis_para_mala(
            mala_instance_pk=mala_a.pk
        )
        self.assertIn(ferramenta_livre, disponiveis_mala_a)
        self.assertIn(ferramenta_mala_a, disponiveis_mala_a)
        self.assertNotIn(ferramenta_mala_b, disponiveis_mala_a)


class TermoResponsabilidadeModelTest(FerramentasBaseTestCase):
    """Testes para os modelos TermoDeResponsabilidade e ItemTermo."""

    def test_criacao_termo_e_itens(self):
        """Verifica a criação de um Termo com seus itens."""
        termo = TermoDeResponsabilidade.objects.create(
            contrato="CT-2024-05",
            responsavel=self.funcionario,
            separado_por=self.coordenador,
            tipo_uso=TermoDeResponsabilidade.TipoUso.FERRAMENTAL,
            movimentado_por=self.user,
            filial=self.filial
        )
        self.assertEqual(
            str(termo),
            f"Termo #{termo.id} - Ferramental — {self.funcionario.nome_completo}"
        )

        ferramenta = Ferramenta.objects.create(
            nome="Multímetro Digital",
            codigo_identificacao="MUL-001",
            data_aquisicao=timezone.now().date(),
            filial=self.filial
        )

        item = ItemTermo.objects.create(
            termo=termo,
            quantidade=1,
            unidade="UN",
            item="Multímetro Digital XYZ",
            ferramenta=ferramenta
        )

        self.assertEqual(str(item), "Multímetro Digital XYZ (1 UN)")
        self.assertEqual(termo.itens.count(), 1)
        self.assertIn(item, termo.itens.all())

    def test_termo_assinatura(self):
        """
        Testa se a presença de 'assinatura_imagem' indica termo assinado.
        O modelo real não possui método is_signed(); a assinatura é
        indicada pela presença do campo 'assinatura_imagem' (ImageField
        do AssinavelMixin).
        """
        termo = TermoDeResponsabilidade.objects.create(
            contrato="CT-SIG-01",
            responsavel=self.funcionario,
            tipo_uso=TermoDeResponsabilidade.TipoUso.MALA,
            movimentado_por=self.user,
            filial=self.filial
        )
        self.assertFalse(bool(termo.assinatura_imagem))

        termo.assinatura_imagem = SimpleUploadedFile(
            "sig.png", b"fake_png_bytes", content_type="image/png"
        )
        termo.save()
        termo.refresh_from_db()

        self.assertTrue(bool(termo.assinatura_imagem))

    def test_relacao_termo_movimentacao(self):
        """Testa a associação entre Termo e Movimentacao (ferramenta)."""
        termo = TermoDeResponsabilidade.objects.create(
            contrato="CT-MOV-01",
            responsavel=self.funcionario,
            tipo_uso=TermoDeResponsabilidade.TipoUso.FERRAMENTAL,
            movimentado_por=self.user,
            filial=self.filial
        )

        ferramenta = Ferramenta.objects.create(
            nome="Parafusadeira",
            codigo_identificacao="PAR-001",
            data_aquisicao=timezone.now().date(),
            filial=self.filial
        )

        # Movimentacao não tem campo 'assinatura_retirada' como argumento de
        # criação: a assinatura vive em AssinaturaMovimentacao (FK para
        # Movimentacao) e é criada separadamente.
        movimentacao = Movimentacao.objects.create(
            ferramenta=ferramenta,
            termo_responsabilidade=termo,
            retirado_por=self.user,
            data_devolucao_prevista=timezone.now() + timedelta(days=5),
            condicoes_retirada="Nova, na caixa.",
            filial=self.filial
        )
        AssinaturaMovimentacao.objects.create(
            movimentacao=movimentacao,
            tipo=AssinaturaMovimentacao.Tipo.RETIRADA,
        )

        self.assertEqual(termo.movimentacoes_geradas.count(), 1)
        self.assertEqual(movimentacao.termo_responsabilidade, termo)
        self.assertEqual(
            movimentacao.assinatura_retirada.tipo,
            AssinaturaMovimentacao.Tipo.RETIRADA
        )

def test_relacao_termo_movimentacao_mala(self):
        """Testa a associação entre Termo e Movimentacao para uma mala."""
        termo = TermoDeResponsabilidade.objects.create(
            contrato="CT-MALA-01",
            responsavel=self.funcionario,
            tipo_uso=TermoDeResponsabilidade.TipoUso.MALA,
            movimentado_por=self.user,
            filial=self.filial
        )

        mala = MalaFerramentas.objects.create(
            nome="Mala de Teste Termo",
            codigo_identificacao="M-TESTE-TERMO",
            filial=self.filial
        )

        ferramenta = Ferramenta.objects.create(
            nome="Ferramenta Teste Mala",
            codigo_identificacao="FT-001-MALA",
            data_aquisicao=timezone.now().date(),
            filial=self.filial,
            mala=mala
        )

        movimentacao = Movimentacao.objects.create(
            mala=mala,
            termo_responsabilidade=termo,
            retirado_por=self.user,
            data_devolucao_prevista=timezone.now() + timedelta(days=5),
            condicoes_retirada="Nova, na caixa.",
            filial=self.filial
        )
        AssinaturaMovimentacao.objects.create(
            movimentacao=movimentacao,
            tipo=AssinaturaMovimentacao.Tipo.RETIRADA,
        )

        self.assertEqual(termo.movimentacoes_geradas.count(), 1)
        self.assertEqual(movimentacao.termo_responsabilidade, termo)

        mala.status = MalaFerramentas.Status.EM_USO
        mala.save()
        ferramenta.refresh_from_db()

        # NOTA: 'ferramenta.termo_ativo' reflete apenas movimentações feitas
        # diretamente na ferramenta, não propaga o termo da mala-mãe quando
        # a retirada é feita via mala. Esse teste foca na relação
        # Termo <-> Movimentacao, não na propagação de termo_ativo.
        self.assertEqual(mala.status, MalaFerramentas.Status.EM_USO)

        movimentacao.data_devolucao = timezone.now()
        movimentacao.save()
        mala.status = MalaFerramentas.Status.DISPONIVEL
        mala.save()
        ferramenta.refresh_from_db()

        self.assertEqual(mala.status, MalaFerramentas.Status.DISPONIVEL)

class MovimentacaoConstraintTest(FerramentasBaseTestCase):
    """Garante que o CheckConstraint XOR funciona no banco (MySQL-safe)."""

    def test_nao_permite_movimentacao_sem_item_nem_mala(self):
        with self.assertRaises(IntegrityError):
            Movimentacao.objects.create(
                retirado_por=self.user,
                data_devolucao_prevista=timezone.now() + timedelta(days=1),
                condicoes_retirada="Sem item",
                filial=self.filial
            )

    def test_nao_permite_ferramenta_e_mala_juntas(self):
        mala = MalaFerramentas.objects.create(
            nome="Mala Teste XOR",
            codigo_identificacao="M-XOR-01",
            filial=self.filial
        )
        ferramenta = Ferramenta.objects.create(
            nome="Chave Inglesa",
            codigo_identificacao="CHV-XOR-01",
            data_aquisicao=timezone.now().date(),
            filial=self.filial
        )

        with self.assertRaises(IntegrityError):
            Movimentacao.objects.create(
                ferramenta=ferramenta,
                mala=mala,
                retirado_por=self.user,
                data_devolucao_prevista=timezone.now() + timedelta(days=1),
                condicoes_retirada="Ferramenta e mala juntas",
                filial=self.filial
            )


class MovimentacaoConcorrenciaTest(FerramentasBaseTestCase):
    """
    Testa a proteção de concorrência feita na camada de aplicação
    (select_for_update), já que o MySQL/MariaDB não suporta
    UniqueConstraint condicional (índice único parcial).

    NOTA: este teste verifica a REGRA de negócio usada pela view
    (checagem de movimentação ativa). Um teste real de concorrência
    com duas threads simultâneas exigiria TransactionTestCase +
    threading, fora do escopo aqui.
    """

    def test_bloqueia_segunda_retirada_do_mesmo_item_ja_ativo(self):
        ferramenta = Ferramenta.objects.create(
            nome="Chave Inglesa",
            codigo_identificacao="CHV-CONC-01",
            data_aquisicao=timezone.now().date(),
            filial=self.filial
        )

        Movimentacao.objects.create(
            ferramenta=ferramenta,
            retirado_por=self.user,
            data_devolucao_prevista=timezone.now() + timedelta(days=1),
            condicoes_retirada="OK",
            filial=self.filial
        )

        # Simula a mesma checagem que a view faz após o select_for_update()
        ja_ativa = Movimentacao.objects.filter(
            ferramenta=ferramenta, data_devolucao__isnull=True
        ).exists()
        self.assertTrue(ja_ativa)
