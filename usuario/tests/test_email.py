
"""
Script de teste de envio de e-mail via Django.
Execute com: python test_email.py
"""
import os
import django
import sys

# Ajuste 'seu_projeto' para o nome da pasta que contém o settings.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seu_projeto.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings


def testar_envio():
    destinatario = input("📧 Digite o e-mail de destino: ").strip()

    print("\n🔎 Configurações carregadas:")
    print(f"   HOST:     {settings.EMAIL_HOST}")
    print(f"   PORT:     {settings.EMAIL_PORT}")
    print(f"   USE_TLS:  {settings.EMAIL_USE_TLS}")
    print(f"   USE_SSL:  {getattr(settings, 'EMAIL_USE_SSL', False)}")
    print(f"   USER:     {settings.EMAIL_HOST_USER}")
    print(f"   FROM:     {settings.DEFAULT_FROM_EMAIL}")
    print("\n📨 Enviando e-mail de teste...\n")

    try:
        enviados = send_mail(
            subject='✅ Teste de e-mail - CTST Tecnologia',
            message='Se você recebeu este e-mail, a configuração SMTP está funcionando corretamente!',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[destinatario],
            fail_silently=False,
        )
        print(f"✅ Sucesso! {enviados} e-mail(s) enviado(s) para {destinatario}")
    except Exception as e:
        print(f"❌ Erro ao enviar: {type(e).__name__}")
        print(f"   Detalhe: {e}")
        sys.exit(1)


if __name__ == '__main__':
    testar_envio()

