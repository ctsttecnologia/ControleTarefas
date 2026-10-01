from django.db import migrations

TABLE = "ferramentas_termoderesponsabilidade"
COLUMN = "token_assinatura"


def _column_exists(schema_editor):
    conn = schema_editor.connection
    with conn.cursor() as cursor:
        cols = [c.name for c in conn.introspection.get_table_description(cursor, TABLE)]
    return COLUMN in cols


def drop_token_assinatura(apps, schema_editor):
    if _column_exists(schema_editor):
        schema_editor.execute(
            f"ALTER TABLE {schema_editor.quote_name(TABLE)} "
            f"DROP COLUMN {schema_editor.quote_name(COLUMN)};"
        )


def restore_token_assinatura(apps, schema_editor):
    if not _column_exists(schema_editor):
        schema_editor.execute(
            f"ALTER TABLE {schema_editor.quote_name(TABLE)} "
            f"ADD COLUMN {schema_editor.quote_name(COLUMN)} CHAR(32) NOT NULL UNIQUE;"
        )


class Migration(migrations.Migration):

    dependencies = [
        ('ferramentas', '0004_alter_termoderesponsabilidade_options'),
    ]

    operations = [
        migrations.RunPython(drop_token_assinatura, restore_token_assinatura),
    ]


