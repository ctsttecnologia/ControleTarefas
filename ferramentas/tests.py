from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from usuario.models import Filial
from .models import Ferramenta, MalaFerramentas, Movimentacao, Atividade

Usuario = get_user_model()

class FerramentasBaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        """
        cls.filial = Filial.objects.create(nome="CETEST-Matriz", cidade="São Paulo")
        cls.user = Usuario.objects.create_user(
            username='testuser', 
            password='password123',
            nome_completo='Test User',
            filial_ativa=cls.filial
        )
        cls.user.filiais_permitidas.add(cls.filial)

        cls.ferramenta = Ferramenta.objects.create(
            nome="Furadeira de Impacto",
            codigo_identificacao="FUR-001",
            data_aquisicao=timezone.now().date(),
            localizacao_padrao="Armário 1",
            filial=cls.filial
        )

        cls.mala = MalaFerramentas.objects.create(
            nome="Mala de Elétrica 01",
            codigo_identificacao="MALA-ELET-01",
            localizacao_padrao="Sala de Ferramentas",
            filial=cls.filial
        )

class FerramentaModelTest(FerramentasBaseTestCase):
    def test_ferramenta_criacao(self):
        """Testa se a ferramenta foi criada corretamente."""
        self.assertEqual(self.ferramenta.nome, "Furadeira de Impacto")
        self.assertEqual(self.ferramenta.status, Ferramenta.Status.DISPONIVEL)
        self.assertEqual(str(self.ferramenta), "Furadeira de Impacto (FUR-001)")

    def test_qr_code_gerado_no_save(self):
        """Testa se o QR Code é gerado ao salvar uma nova ferramenta sem um."""
        ferramenta_sem_qr = Ferramenta(
            nome="Chave de Fenda",
            codigo_identificacao="CHF-002",
            data_aquisicao=timezone.now().date(),
            localizacao_padrao="Gaveta 2",
            filial=self.filial
        )
        self.assertFalse(ferramenta_sem_qr.qr_code)
        ferramenta_sem_qr.save()
        self.assertTrue(ferramenta_sem_qr.qr_code)
        self.assertIn('qr_code-CHF-002.png', ferramenta_sem_qr.qr_code.name)

    def test_get_absolute_url(self):
        """Testa se a URL absoluta da ferramenta é retornada corretamente."""
        expected_url = reverse('ferramentas:ferramenta_detail', kwargs={'pk': self.ferramenta.pk})
        self.assertEqual(self.ferramenta.get_absolute_url(), expected_url)

class MalaFerramentasModelTest(FerramentasBaseTestCase):
    def test_mala_criacao(self):
        """Testa se a mala de ferramentas foi criada corretamente."""
        self.assertEqual(self.mala.nome, "Mala de Elétrica 01")
        self.assertEqual(self.mala.status, MalaFerramentas.Status.DISPONIVEL)
        self.assertEqual(str(self.mala), "Mala de Elétrica 01 (MALA-ELET-01)")

    def test_qr_code_gerado_no_save_mala(self):
        """Testa se o QR Code é gerado ao salvar uma nova mala."""
        mala_sem_qr = MalaFerramentas(
            nome="Kit Mecânico",
            codigo_identificacao="MALA-MEC-01",
            localizacao_padrao="Bancada 3",
            filial=self.filial
        )
        self.assertFalse(mala_sem_qr.qr_code)
        mala_sem_qr.save()
        self.assertTrue(mala_sem_qr.qr_code)
        self.assertIn('qr_code_mala-MALA-MEC-01.png', mala_sem_qr.qr_code.name)

class MovimentacaoModelTest(FerramentasBaseTestCase):
    def test_clean_sem_item(self):
        """Testa se a validação falha quando nem ferramenta nem mala são fornecidas."""
        mov = Movimentacao(retirado_por=self.user, data_devolucao_prevista=timezone.now())
        with self.assertRaises(ValidationError) as cm:
            mov.clean()
        self.assertIn("A movimentação deve estar associada a uma ferramenta ou a uma mala.", str(cm.exception))

    def test_clean_com_ambos_itens(self):
        """Testa se a validação falha quando ambos ferramenta e mala são fornecidos."""
        mov = Movimentacao(
            ferramenta=self.ferramenta,
            mala=self.mala,
            retirado_por=self.user,
            data_devolucao_prevista=timezone.now()
        )
        with self.assertRaises(ValidationError) as cm:
            mov.clean()
        self.assertIn("A movimentação não pode ser de uma ferramenta e uma mala ao mesmo tempo.", str(cm.exception))

    def test_clean_valido(self):
        """Testa se a validação passa com apenas um item."""
        mov_ferramenta = Movimentacao(ferramenta=self.ferramenta, retirado_por=self.user, data_devolucao_prevista=timezone.now())
        mov_mala = Movimentacao(mala=self.mala, retirado_por=self.user, data_devolucao_prevista=timezone.now())
        
        try:
            mov_ferramenta.clean()
            mov_mala.clean()
        except ValidationError:
            self.fail("A validação `clean()` levantou ValidationError inesperadamente.")

    def test_item_movimentado_property(self):
        """Testa a propriedade `item_movimentado`."""
        mov_ferramenta = Movimentacao(ferramenta=self.ferramenta, retirado_por=self.user)
        mov_mala = Movimentacao(mala=self.mala, retirado_por=self.user)
        self.assertEqual(mov_ferramenta.item_movimentado, self.ferramenta)
        self.assertEqual(mov_mala.item_movimentado, self.mala)

class FerramentaViewsTest(FerramentasBaseTestCase):
    def setUp(self):
        """Loga o usuário para os testes de view."""
        self.client.login(username='testuser', password='password123')
        session = self.client.session
        session['active_filial_id'] = self.filial.id
        session.save()

    def test_ferramenta_list_view(self):
        """Testa a view de listagem de ferramentas."""
        url = reverse('ferramentas:ferramenta_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.ferramenta.nome)
        self.assertTemplateUsed(response, 'ferramentas/ferramenta_list.html')

    def test_ferramenta_detail_view(self):
        """Testa a view de detalhes da ferramenta."""
        url = reverse('ferramentas:ferramenta_detail', kwargs={'pk': self.ferramenta.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.ferramenta.nome)
        self.assertContains(response, self.ferramenta.codigo_identificacao)
        self.assertTemplateUsed(response, 'ferramentas/ferramenta_detail.html')

    def test_ferramenta_create_view(self):
        """Testa a criação de uma nova ferramenta via POST."""
        url = reverse('ferramentas:ferramenta_create')
        data = {
            'nome': 'Martelo de Borracha',
            'codigo_identificacao': 'MAR-001',
            'data_aquisicao': '2023-10-27',
            'localizacao_padrao': 'Caixa 3',
            'filial': self.filial.id,
        }
        response = self.client.post(url, data)
        
        # Verifica se a ferramenta foi criada e se o usuário foi redirecionado
        self.assertEqual(response.status_code, 302)
        nova_ferramenta = Ferramenta.objects.get(codigo_identificacao='MAR-001')
        self.assertRedirects(response, nova_ferramenta.get_absolute_url())
        self.assertEqual(nova_ferramenta.nome, 'Martelo de Borracha')
        self.assertEqual(nova_ferramenta.filial, self.filial)

        # Verifica se a atividade de criação foi registrada
        atividade = Atividade.objects.filter(ferramenta=nova_ferramenta, tipo_atividade=Atividade.TipoAtividade.CRIACAO).first()
        self.assertIsNotNone(atividade)
        self.assertEqual(atividade.usuario, self.user)

    def test_ferramenta_update_view(self):
        """Testa a atualização de uma ferramenta."""
        url = reverse('ferramentas:ferramenta_update', kwargs={'pk': self.ferramenta.pk})
        data = {
            'nome': 'Furadeira de Impacto Profissional',
            'codigo_identificacao': self.ferramenta.codigo_identificacao,
            'data_aquisicao': self.ferramenta.data_aquisicao,
            'localizacao_padrao': 'Armário 1 - Prateleira A',
            'filial': self.filial.id,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.ferramenta.refresh_from_db()
        self.assertEqual(self.ferramenta.nome, 'Furadeira de Impacto Profissional')
        self.assertEqual(self.ferramenta.localizacao_padrao, 'Armário 1 - Prateleira A')
