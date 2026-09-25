
# seguranca_trabalho/management/commands/corrigir_criptografia_assinaturas.py
"""
Corrige assinaturas gravadas em texto puro ANTES da migração para encrypt(),
detectando se o valor já está criptografado (Fernet válido) ou não,
e criptografando apenas o que ainda está em texto puro.

Bypassa o ORM na leitura para evitar BadSignature ao carregar dados
já convertidos para EncryptedTextField.
"""
from django.core.management.base import BaseCommand
from django.db import connection
from django.utils.encoding import force_bytes

from seguranca_trabalho.models import FichaEPI, EntregaEPI


def _fix_field(model, field_name, table_name, stdout):
    field = model._meta.get_field(field_name)

    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT id, {field_name} FROM {table_name} "
            f"WHERE {field_name} IS NOT NULL AND {field_name} != ''"
        )
        rows = cursor.fetchall()

    corrigidos = 0
    ja_criptografados = 0

    for pk, raw_value in rows:
        if raw_value is None:
            continue

        # Tenta decodificar como já criptografado (Fernet válido)
        try:
            field._load(force_bytes(raw_value))
            ja_criptografados += 1
            continue  # já está OK, não faz nada
        except Exception:
            pass  # não é Fernet válido -> está em texto puro, precisa criptografar

        try:
            encrypted_value = field._dump(raw_value)
        except Exception as e:
            stdout.write(f"  ERRO ao criptografar id={pk}: {e}")
            continue

        with connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE {table_name} SET {field_name} = %s WHERE id = %s",
                [encrypted_value, pk],
            )
        corrigidos += 1

    stdout.write(
        f"{table_name}.{field_name}: {corrigidos} corrigidos, "
        f"{ja_criptografados} já estavam criptografados."
    )


class Command(BaseCommand):
    help = "Corrige assinaturas em texto puro, criptografando-as (rodar 1x)."

    def handle(self, *args, **options):
        self.stdout.write("Iniciando correção de criptografia...")

        _fix_field(FichaEPI, 'assinatura_funcionario',
                   'seguranca_trabalho_fichaepi', self.stdout)
        _fix_field(EntregaEPI, 'assinatura_recebimento',
                   'seguranca_trabalho_entregaepi', self.stdout)

        self.stdout.write(self.style.SUCCESS("Concluído."))

