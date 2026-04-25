
import ssl
from django.core.mail.backends.smtp import EmailBackend as DjangoEmailBackend


class InsecureEmailBackend(DjangoEmailBackend):
    """
    Backend de email que ignora verificação SSL.
    ⚠️ USAR APENAS EM DESENVOLVIMENTO LOCAL!
    Necessário quando antivírus (AVG/Avast/Kaspersky) intercepta SSL.
    """
    
    @property
    def ssl_context(self):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context
