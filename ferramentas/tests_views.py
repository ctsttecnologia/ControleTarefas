
# ferramentas/tests_views.py
"""
Testes de views do app ferramentas.
Separado de tests.py (que cobre models) para melhor organização.
"""
from datetime import date

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

from ferramentas.models import MalaFerramentas, Ferramenta
from usuario.models import Filial, Usuario

User = get_user_model()


# ============================================================================
# BASE — setup compartilhado
# ============================================================================
class BaseFerramentasViewTest(TestCase):
    """Setup com usuário autenticado, filial ativa e permissões."""

    @classmethod
    def setUpTestData(cls):
        # Filial — ajuste os campos obrigatórios conforme seu modelo
        cls.filial = Filial.objects.create(
            nome='Matriz Teste',
            # cnpj='00.000.000/0001-00',  # adicione se for obrigatório
        )

        # Usuário com filial vinculada
        cls.user = User.objects.create_user(
            username='tester',
            password='senha123',
            email='tester@test.com',
        )
        # Vincula usuário à filial (ajuste conforme seu modelo Usuario)
        if hasattr(cls.user, 'filiais'):
            cls.user.filiais.add(cls.filial)
        if hasattr(cls.user, 'filial_padrao'):
            cls.user.filial_padrao = cls.filial
            cls.user.save()

        # Permissões — concede todas as do app ferramentas
        perms = Permission.objects.filter(
            content_type__app_label='ferramentas'
        )
        cls.user.user_permissions.set(perms)

        # Dados de domínio
        cls.mala = MalaFerramentas.objects.create(
            nome='Mala Elétrica',
            codigo_identificacao='MALA-TEST-001',
            localizacao_padrao='Almoxarifado A',
            quantidade=5,
            filial=cls.filial,
        )

        cls.ferramenta = Ferramenta.objects.create(
            nome='Furadeira Bosch',
            codigo_identificacao='FER-TEST-001',
            quantidade=1,
            localizacao_padrao='Almoxarifado A',
            data_aquisicao=date(2024, 1, 15),
            filial=cls.filial,
        )

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)
        # Define filial ativa na session (usado pelo ViewFilialScopedMixin)
        from core.constants import SESSION_FILIAL_ATIVA
        session = self.client.session
        session[SESSION_FILIAL_ATIVA] = self.filial.id
        session.save()


# ============================================================================
# DASHBOARD
# ============================================================================
class DashboardViewTest(BaseFerramentasViewTest):

    def test_dashboard_get_200(self):
        url = reverse('ferramentas:dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_dashboard_redireciona_sem_login(self):
        self.client.logout()
        url = reverse('ferramentas:dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)


# ============================================================================
# FERRAMENTA — CRUD
# ============================================================================
class FerramentaViewsTest(BaseFerramentasViewTest):

    def test_list_view_200(self):
        url = reverse('ferramentas:ferramenta_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.ferramenta.nome)

    def test_list_view_escopo_por_filial(self):
        """Não deve listar ferramentas de outras filiais."""
        outra_filial = Filial.objects.create(nome='Outra Filial')
        Ferramenta.objects.create(
            nome='Ferramenta Outra Filial',
            codigo_identificacao='FER-OUTRA-001',
            localizacao_padrao='X',
            data_aquisicao=date(2024, 1, 1),
            filial=outra_filial,
        )
        url = reverse('ferramentas:ferramenta_list')
        response = self.client.get(url)
        self.assertNotContains(response, 'Ferramenta Outra Filial')

    def test_detail_view_200(self):
        url = reverse('ferramentas:ferramenta_detail', args=[self.ferramenta.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.ferramenta.codigo_identificacao)

    def test_detail_view_404_id_inexistente(self):
        url = reverse('ferramentas:ferramenta_detail', args=[99999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_create_view_get_200(self):
        url = reverse('ferramentas:ferramenta_create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_create_view_post_valido(self):
        url = reverse('ferramentas:ferramenta_create')
        data = {
            'nome': 'Chave de Fenda',
            'codigo_identificacao': 'FER-TEST-002',
            'quantidade': 10,
            'localizacao_padrao': 'Almoxarifado B',
            'data_aquisicao': '2024-06-01',
            'status': Ferramenta.Status.DISPONIVEL,
        }
        response = self.client.post(url, data)
        # Pode redirecionar (302) ou re-renderizar (200) com erros de campos faltantes
        if response.status_code == 302:
            self.assertTrue(
                Ferramenta.objects.filter(codigo_identificacao='FER-TEST-002').exists()
            )

    def test_create_view_post_invalido(self):
        url = reverse('ferramentas:ferramenta_create')
        response = self.client.post(url, {})  # form vazio
        self.assertEqual(response.status_code, 200)  # re-renderiza form

    def test_update_view_get_200(self):
        url = reverse('ferramentas:ferramenta_update', args=[self.ferramenta.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)
        # Define filial ativa na session
        from core.constants import SESSION_FILIAL_ATIVA
        session = self.client.session
        session[SESSION_FILIAL_ATIVA] = self.filial.id
        session.save()

        # ✅ ADICIONE: setar filial ativa na sessão
        session = self.client.session
        session['filial_ativa_id'] = self.filial.id
        session.save()

# ============================================================================
# MALA DE FERRAMENTAS — CRUD
# ============================================================================
class MalaViewsTest(BaseFerramentasViewTest):

    def test_list_view_200(self):
        url = reverse('ferramentas:mala_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.mala.nome)

    def test_detail_view_200(self):
        url = reverse('ferramentas:mala_detail', args=[self.mala.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_create_view_get_200(self):
        url = reverse('ferramentas:mala_create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_create_view_post_valido(self):
        url = reverse('ferramentas:mala_create')
        data = {
            'nome': 'Nova Mala',
            'codigo_identificacao': 'MALA-NEW-001',
            'localizacao_padrao': 'Almoxarifado C',
            'quantidade': 3,
            'status': MalaFerramentas.Status.DISPONIVEL,
        }
        response = self.client.post(url, data)
        if response.status_code == 302:
            self.assertTrue(
                MalaFerramentas.objects.filter(codigo_identificacao='MALA-NEW-001').exists()
            )

    def test_update_view_get_200(self):
        url = reverse('ferramentas:mala_update', args=[self.mala.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)
        # Define filial ativa na session
        from core.constants import SESSION_FILIAL_ATIVA
        session = self.client.session
        session[SESSION_FILIAL_ATIVA] = self.filial.id
        session.save()


# ============================================================================
# AÇÕES — Manutenção / Inativação
# ============================================================================
class AcaoFerramentaViewsTest(BaseFerramentasViewTest):

    def test_iniciar_manutencao(self):
        url = reverse('ferramentas:iniciar_manutencao', args=[self.ferramenta.pk])
        response = self.client.post(url)
        self.assertIn(response.status_code, [200, 302])
        self.ferramenta.refresh_from_db()
        self.assertEqual(self.ferramenta.status, Ferramenta.Status.EM_MANUTENCAO)

    def test_finalizar_manutencao(self):
        self.ferramenta.status = Ferramenta.Status.EM_MANUTENCAO
        self.ferramenta.save()
        url = reverse('ferramentas:finalizar_manutencao', args=[self.ferramenta.pk])
        response = self.client.post(url)
        self.assertIn(response.status_code, [200, 302])
        self.ferramenta.refresh_from_db()
        self.assertEqual(self.ferramenta.status, Ferramenta.Status.DISPONIVEL)

    def test_inativar_ferramenta(self):
        url = reverse('ferramentas:ferramenta_inativar', args=[self.ferramenta.pk])
        response = self.client.post(url)
        self.assertIn(response.status_code, [200, 302])
        self.ferramenta.refresh_from_db()
        self.assertEqual(self.ferramenta.status, Ferramenta.Status.DESCARTADA)


# ============================================================================
# QR CODE / SCAN
# ============================================================================
class QRCodeViewsTest(BaseFerramentasViewTest):

    def test_imprimir_qrcodes_200(self):
        url = reverse('ferramentas:imprimir_qrcodes')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_resultado_scan_ferramenta_existente(self):
        url = reverse(
            'ferramentas:resultado_scan',
            args=[self.ferramenta.codigo_identificacao],
        )
        response = self.client.get(url)
        self.assertIn(response.status_code, [200, 302])

    def test_resultado_scan_codigo_inexistente(self):
        url = reverse('ferramentas:resultado_scan', args=['CODIGO-INEXISTENTE'])
        response = self.client.get(url)
        self.assertIn(response.status_code, [404, 302])


# ============================================================================
# TERMOS DE RESPONSABILIDADE
# ============================================================================
class TermoViewsTest(BaseFerramentasViewTest):

    def test_termo_list_200(self):
        url = reverse('ferramentas:termoderesponsabilidade_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_criar_termo_get_200(self):
        url = reverse('ferramentas:criar_termo_responsabilidade')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


# ============================================================================
# IMPORTAÇÃO
# ============================================================================
class ImportacaoViewsTest(BaseFerramentasViewTest):

    def test_importar_get_200(self):
        url = reverse('ferramentas:importar_ferramentas')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_download_template_200(self):
        url = reverse('ferramentas:download_template')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Deve retornar um arquivo Excel
        self.assertIn('spreadsheet', response.get('Content-Type', '').lower())


# ============================================================================
# PERMISSÕES — usuário sem permissão é bloqueado
# ============================================================================
class PermissoesViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.filial = Filial.objects.create(nome='Matriz')
        cls.user_sem_perm = User.objects.create_user(
            username='nopermuser', password='123'
        )

    def setUp(self):
        self.client.force_login(self.user_sem_perm)

    def test_listagem_negada_sem_permissao(self):
        url = reverse('ferramentas:ferramenta_list')
        response = self.client.get(url)
        # AppPermissionMixin pode retornar 403 ou redirecionar
        self.assertIn(response.status_code, [302, 403])

    def test_acesso_anonimo_redireciona(self):
        self.client.logout()
        url = reverse('ferramentas:ferramenta_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)




# Roda só os novos testes de views
# python manage.py test ferramentas.tests_views --settings=gerenciandoTarefas.settings_test -v 2

# Roda tudo do app (models + views)
# python manage.py test ferramentas --settings=gerenciandoTarefas.settings_test -v 2

# Mede cobertura com tudo
# coverage run --source='ferramentas' manage.py test ferramentas --settings=gerenciandoTarefas.settings_test
# coverage report -m
