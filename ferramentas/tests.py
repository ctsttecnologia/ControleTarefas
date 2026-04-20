# ferramentas/tests.py
"""
Testes para o app ferramentas
"""
from datetime import datetime
from datetime import date, timedelta
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.utils import IntegrityError
from django.utils import timezone


# Modelos da app 'ferramentas'
from .models import (
    MalaFerramentas, Ferramenta, Atividade, 
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
        
        # Desativa signals do PGR para evitar erros
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
        
        # Armazena receivers para reconectar depois
        cls._stored_receivers = []
        
        # Procura e desconecta signals do PGR
        for receiver in post_save._live_receivers(Funcionario):
            receiver_name = getattr(receiver, '__name__', str(receiver))
            if 'pgr' in receiver_name.lower() or 'admissional' in receiver_name.lower():
                cls._stored_receivers.append((post_save, Funcionario, receiver))
        
        # Desconecta os receivers armazenados
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
        
        # 1. Criar uma Filial
        cls.filial = Filial.objects.create(
            nome=f"Filial Teste {timezone.now().timestamp()}"
        )
        
        # 2. Criar um Departamento
        cls.departamento = Departamento.objects.create(
            nome=f"Departamento Teste {timezone.now().timestamp()}",
            filial=cls.filial
        )
        
        # 3. Criar um Usuário
        cls.user = User.objects.create_user(
            username=f'testuser_{timezone.now().timestamp()}',
            password='password123'
        )
        # Associar filial se o modelo User tiver esse campo
        if hasattr(cls.user, 'filial'):
            cls.user.filial = cls.filial
            cls.user.save()
        
        # 4. Criar Cargo e Função
        cls.cargo = Cargo.objects.create(
            filial=cls.filial, 
            nome=f"Cargo Teste {timezone.now().timestamp()}"
        )
        cls.funcao = Funcao.objects.create(
            filial=cls.filial, 
            nome=f"Função Teste {timezone.now().timestamp()}"
        )
        # Use timestamp ou uuid para garantir unicidade
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        # 5. Criar Funcionários
        cls.funcionario = Funcionario.objects.create(
            nome_completo='João da Silva Teste',
            matricula=f'TESTE-FUNC-{timestamp}',   # ← sufixo único
            filial=cls.filial,
            cargo=cls.cargo,
            funcao=cls.funcao,
            data_admissao=timezone.now().date(),
            departamento=cls.departamento
        )

        cls.coordenador = Funcionario.objects.create(
            nome_completo='Maria Coordenadora Teste',
            matricula=f'TESTE-COORD-{timestamp}',  # ← sufixo único
            filial=cls.filial,
            cargo=cls.cargo,
            funcao=cls.funcao,
            data_admissao=timezone.now().date(),
            departamento=cls.departamento
        )
        
        cls.tecnico = Funcionario.objects.create(
            nome_completo='Técnico de Testes',
            filial=cls.filial,
            cargo=cls.cargo,
            funcao=cls.funcao,
            data_admissao=timezone.now().date(),
            departamento=cls.departamento
        )
        
        # 6. Criar um Fornecedor/Parceiro
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
        
        # Verifica QR Code se implementado
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
        # Se não tem código, QR code deve estar vazio
        self.assertFalse(bool(mala.qr_code.name) if mala.qr_code else True)


class FerramentaModelTest(FerramentasBaseTestCase):
    """Testes para o modelo Ferramenta."""

    @classmethod
    def setUpTestData(cls):
        """Configura dados específicos para os testes de Ferramenta."""
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

        # Cenário 1: Ferramentas disponíveis para uma NOVA mala
        disponiveis_nova_mala = Ferramenta.objects.ferramentas_disponiveis_para_mala()
        self.assertIn(ferramenta_livre, disponiveis_nova_mala)
        self.assertNotIn(ferramenta_mala_a, disponiveis_nova_mala)
        self.assertNotIn(ferramenta_mala_b, disponiveis_nova_mala)

        # Cenário 2: Ferramentas disponíveis para EDITAR a Mala A
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
            f"Termo #{termo.pk} - Ferramental por {self.funcionario.nome_completo}"
        )
        self.assertFalse(termo.is_signed())

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

    def test_termo_is_signed(self):
        """Testa a propriedade 'is_signed'."""
        termo = TermoDeResponsabilidade.objects.create(
            contrato="CT-SIG-01",
            responsavel=self.funcionario,
            tipo_uso=TermoDeResponsabilidade.TipoUso.MALA,
            movimentado_por=self.user,
            filial=self.filial
        )
        self.assertFalse(termo.is_signed())

        termo.assinatura_data = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA..."
        termo.save()

        self.assertTrue(termo.is_signed())

    def test_relacao_termo_movimentacao(self):
        """Testa a associação entre Termo e Movimentacao."""
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

        fake_signature = SimpleUploadedFile(
            "sig.png", 
            b"file_content", 
            content_type="image/png"
        )

        movimentacao = Movimentacao.objects.create(
            ferramenta=ferramenta,
            termo_responsabilidade=termo,
            retirado_por=self.user,
            data_devolucao_prevista=timezone.now() + timedelta(days=5),
            condicoes_retirada="Nova, na caixa.",
            assinatura_retirada=fake_signature,
            filial=self.filial
        )
        
        self.assertEqual(termo.movimentacoes_geradas.count(), 1)
        self.assertEqual(movimentacao.termo_responsabilidade, termo)

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

        # Criar uma ferramenta associada à mala
        ferramenta = Ferramenta.objects.create(
            nome="Ferramenta Teste Mala",
            codigo_identificacao="FT-001-MALA",
            data_aquisicao=timezone.now().date(),
            filial=self.filial,
            mala=mala
        )

        fake_signature = SimpleUploadedFile(
            "sig.png", 
            b"file_content", 
            content_type="image/png"
        )

        movimentacao = Movimentacao.objects.create(
            mala=mala,
            termo_responsabilidade=termo,
            retirado_por=self.user,
            data_devolucao_prevista=timezone.now() + timedelta(days=5),
            condicoes_retirada="Nova, na caixa.",
            assinatura_retirada=fake_signature,
            filial=self.filial
        )

        self.assertEqual(termo.movimentacoes_geradas.count(), 1)
        self.assertEqual(movimentacao.termo_responsabilidade, termo)

        # Atualiza status e verifica o termo ativo
        mala.status = MalaFerramentas.Status.EM_USO
        mala.save()
        ferramenta.refresh_from_db()
        
        # Verifica termo_ativo se a propriedade existir
        if hasattr(ferramenta, 'termo_ativo'):
            self.assertEqual(ferramenta.termo_ativo, termo)

        # Simula a devolução
        movimentacao.data_devolucao = timezone.now()
        movimentacao.save()
        mala.status = MalaFerramentas.Status.DISPONIVEL
        mala.save()
        ferramenta.refresh_from_db()
        
        if hasattr(ferramenta, 'termo_ativo'):
            self.assertIsNone(ferramenta.termo_ativo)

