"""
Padroniza nomes dos grupos de permissão.

- Remove acentos, espaços e hífens
- Corrige mojibake (UTF-8 duplo) de GESTÃO e SEGURANÇA
- Preserva todas as associações User ↔ Group (apenas .update no name)
- Idempotente: só renomeia se o nome antigo existir
"""
from django.db import migrations

# (nome_antigo, nome_novo)
RENAMES = [
    ("USUARIO COMUM", "USUARIO_COMUM"),
    ("DEPARTAMENTO PESSOAL", "DEPARTAMENTO_PESSOAL"),
    ("GESTÃƒO-QUALIDADE", "GESTAO_QUALIDADE"),   # mojibake -> limpo
    ("GESTÃO-QUALIDADE", "GESTAO_QUALIDADE"),    # caso já tenha sido corrigido manualmente
    ("SST-SEGURANÃ‡A", "SST_SEGURANCA"),         # mojibake -> limpo
    ("SST-SEGURANÇA", "SST_SEGURANCA"),          # caso já tenha sido corrigido manualmente
    ("DASHBOARD-FULL", "DASHBOARD_FULL"),
]

# Reverter: novo -> antigo (usa o primeiro nome antigo de cada par)
REVERSE_RENAMES = [
    ("USUARIO_COMUM", "USUARIO COMUM"),
    ("DEPARTAMENTO_PESSOAL", "DEPARTAMENTO PESSOAL"),
    ("GESTAO_QUALIDADE", "GESTÃƒO-QUALIDADE"),
    ("SST_SEGURANCA", "SST-SEGURANÃ‡A"),
    ("DASHBOARD_FULL", "DASHBOARD-FULL"),
]


def rename_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for old, new in RENAMES:
        qs = Group.objects.filter(name=old)
        if qs.exists():
            # Se já existir um grupo com o nome novo, não sobrescreve — apenas loga via print
            if Group.objects.filter(name=new).exclude(pk__in=qs.values("pk")).exists():
                print(f"  ⚠️  Grupo '{new}' já existe. Pulando renomeação de '{old}'.")
                continue
            qs.update(name=new)
            print(f"  ✅ Grupo renomeado: '{old}' → '{new}'")


def revert_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for new, old in REVERSE_RENAMES:
        qs = Group.objects.filter(name=new)
        if qs.exists():
            qs.update(name=old)
            print(f"  ↩️  Grupo revertido: '{new}' → '{old}'")


class Migration(migrations.Migration):

    dependencies = [
        # ⚠️ AJUSTE: coloque aqui a última migration do app `usuario`
        ("usuario", "0002_alter_filial_options"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(rename_groups, reverse_code=revert_groups),
    ]
