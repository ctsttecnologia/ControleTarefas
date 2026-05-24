
# core/tests/test_sanitize.py
from datetime import timedelta, timezone
from django.utils import timezone   # ← este precisa estar aqui
from datetime import date  
from io import BytesIO
from api.views import TermoViewSet
from departamento_pessoal.models import Funcionario
from usuario.models import Filial
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, NameObject, TextStringObject
from core.mixins import _sanitize_pdf, _sanitize_image
from ferramentas.models import Ferramenta, MalaFerramentas, Movimentacao


class SanitizePDFTestCase(TestCase):
    """Testa a sanitização de PDFs maliciosos."""

    def _criar_pdf_malicioso(self):
        """Cria PDF com JS + metadados sensíveis em memória."""
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)

        # Injeta JavaScript malicioso
        js_action = DictionaryObject({
            NameObject("/S"): NameObject("/JavaScript"),
            NameObject("/JS"): TextStringObject("app.alert('XSS');"),
        })
        writer._root_object[NameObject("/OpenAction")] = js_action

        # Injeta metadados sensíveis
        writer.add_metadata({
            '/Author': 'Hacker',
            '/Title': 'Malicioso',
            '/Subject': 'Vazamento',
        })

        buffer = BytesIO()
        writer.write(buffer)
        buffer.seek(0)
        return buffer.read()

    def test_remove_open_action(self):
        """Verifica que /OpenAction (gatilho de JS) é removido."""
        conteudo = self._criar_pdf_malicioso()
        uploaded = SimpleUploadedFile('test.pdf', conteudo, 'application/pdf')

        sanitized = _sanitize_pdf(uploaded)
        sanitized.seek(0)

        reader = PdfReader(sanitized)
        root = reader.trailer['/Root']

        self.assertNotIn(NameObject('/OpenAction'), root)

    def test_remove_additional_actions(self):
        """Verifica que /AA é removido."""
        conteudo = self._criar_pdf_malicioso()
        uploaded = SimpleUploadedFile('test.pdf', conteudo, 'application/pdf')

        sanitized = _sanitize_pdf(uploaded)
        sanitized.seek(0)

        reader = PdfReader(sanitized)
        root = reader.trailer['/Root']

        self.assertNotIn(NameObject('/AA'), root)

    def test_remove_embedded_files(self):
        """Verifica que /Names (EmbeddedFiles) é removido."""
        conteudo = self._criar_pdf_malicioso()
        uploaded = SimpleUploadedFile('test.pdf', conteudo, 'application/pdf')

        sanitized = _sanitize_pdf(uploaded)
        sanitized.seek(0)

        reader = PdfReader(sanitized)
        root = reader.trailer['/Root']

        self.assertNotIn(NameObject('/Names'), root)

    def test_remove_acroform(self):
        """Verifica que /AcroForm (XFA exploit) é removido."""
        conteudo = self._criar_pdf_malicioso()
        uploaded = SimpleUploadedFile('test.pdf', conteudo, 'application/pdf')

        sanitized = _sanitize_pdf(uploaded)
        sanitized.seek(0)

        reader = PdfReader(sanitized)
        root = reader.trailer['/Root']

        self.assertNotIn(NameObject('/AcroForm'), root)

    def test_remove_metadados_sensiveis(self):
        """Verifica que metadados sensíveis (Author, Title, Subject) são removidos."""
        conteudo = self._criar_pdf_malicioso()
        uploaded = SimpleUploadedFile('test.pdf', conteudo, 'application/pdf')

        sanitized = _sanitize_pdf(uploaded)
        sanitized.seek(0)

        reader = PdfReader(sanitized)
        metadata = dict(reader.metadata) if reader.metadata else {}

        self.assertNotIn('/Author', metadata)
        self.assertNotIn('/Title', metadata)
        self.assertNotIn('/Subject', metadata)

    def test_preserva_paginas(self):
        """Verifica que o conteúdo (páginas) é preservado."""
        conteudo = self._criar_pdf_malicioso()
        uploaded = SimpleUploadedFile('test.pdf', conteudo, 'application/pdf')

        sanitized = _sanitize_pdf(uploaded)
        sanitized.seek(0)

        reader = PdfReader(sanitized)
        self.assertEqual(len(reader.pages), 1)

    def test_pdf_invalido_retorna_original(self):
        """PDF corrompido deve retornar o arquivo original (não crashar)."""
        conteudo = b'not a real pdf, just garbage'
        uploaded = SimpleUploadedFile('fake.pdf', conteudo, 'application/pdf')

        # Não deve lançar exceção
        sanitized = _sanitize_pdf(uploaded)
        self.assertIsNotNone(sanitized)


class SanitizeImageTestCase(TestCase):
    """Testa a sanitização de imagens."""

    def setUp(self):
        # ... resto do setUp atual ...
        self.filial = Filial.objects.create(
            nome="Filial Teste",
            # demais campos obrigatórios da sua Filial
        )

    def _criar_imagem_com_exif(self):
        """Cria JPEG com metadados EXIF falsos."""
        from PIL import Image

        img = Image.new('RGB', (100, 100), color='red')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        buffer.seek(0)
        return buffer.read()

    def test_sanitiza_jpeg(self):
        """Verifica que JPEG é re-encodado corretamente."""
        conteudo = self._criar_imagem_com_exif()
        uploaded = SimpleUploadedFile('test.jpg', conteudo, 'image/jpeg')

        sanitized = _sanitize_image(uploaded)
        self.assertIsNotNone(sanitized)

    def test_imagem_invalida_retorna_original(self):
        """Arquivo não-imagem deve retornar o original sem crashar."""
        conteudo = b'not a real image'
        uploaded = SimpleUploadedFile('fake.jpg', conteudo, 'image/jpeg')

        sanitized = _sanitize_image(uploaded)
        self.assertIsNotNone(sanitized)
    
    def test_qr_code_nao_gerado_sem_codigo(self):
        """Verifica se o QR code não é gerado sem um código de identificação."""
        mala = MalaFerramentas.objects.create(
            nome="Mala Sem Código",
            localizacao_padrao="Armário D",
            filial=self.filial
        )       
        self.assertFalse(bool(mala.qr_code))


    def test_relacao_termo_movimentacao_mala(self):

        """Testa a associação básica entre movimentação, ferramenta e mala."""
        from datetime import date
        from django.contrib.auth import get_user_model
        User = get_user_model()

        user = User.objects.create_user(
            username="user_mov_teste",
            password="senha123",
        )

        mala = MalaFerramentas.objects.create(
            nome="Mala Teste Sanitize",
            codigo_identificacao="MALA-SAN-001",
            localizacao_padrao="Almoxarifado Teste",
            filial=self.filial,
        )

        ferramenta = Ferramenta.objects.create(
            nome="Ferramenta Teste Sanitize",
            patrimonio="PAT-SAN-001",
            codigo_identificacao="FER-SAN-001",
            localizacao_padrao="Almoxarifado Teste",
            data_aquisicao=date.today(),
            filial=self.filial,
            mala=mala,
        )

        movimentacao = Movimentacao.objects.create(
            ferramenta=ferramenta,
            retirado_por=user,
            tipo_uso=Movimentacao.TipoUso.VOLANTE,
            data_devolucao_prevista=timezone.now() + timedelta(days=7),
            condicoes_retirada="Em perfeito estado para teste.",
        )

        self.assertEqual(movimentacao.retirado_por, user)
        self.assertEqual(movimentacao.ferramenta, ferramenta)
        self.assertEqual(movimentacao.ferramenta.mala, mala)


# Comando para rodar os testes:#
# python manage.py test core.tests.test_sanitize -v 2

# Para rodar um teste específico: Classe#
# python manage.py test core.tests.test_sanitize.SanitizePDFTestCase -v 2

# Para rodar um teste específico: Método#
# python manage.py test core.tests.test_sanitize.SanitizePDFTestCase.test_remove_open_action -v 2

# Mantém DB de teste entre execuções (--keepdb)
# python manage.py test notifications --settings=gerenciandoTarefas.settings_test --keepdb -v 2

# Em paralelo (usa todos os cores da CPU)
# python manage.py test notifications --settings=gerenciandoTarefas.settings_test --parallel -v 2

# python manage.py test --settings=gerenciandoTarefas.settings_test -v 2
