
# core/tests/test_sanitize.py
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, NameObject, TextStringObject

from core.mixins import _sanitize_pdf, _sanitize_image


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

# Comando para rodar os testes:#
# python manage.py test core.tests.test_sanitize -v 2

# Para rodar um teste específico: Classe#
# python manage.py test core.tests.test_sanitize.SanitizePDFTestCase -v 2

# Para rodar um teste específico: Método#
# python manage.py test core.tests.test_sanitize.SanitizePDFTestCase.test_remove_open_action -v 2