from django.db import migrations

TABELA = 'pgr_risco_identificado'
COLUNA = 'codigo_risco_unico'
INDICE = 'uniq_codigo_risco_ativo_por_pgr'


def _existe(schema_editor, sql, params):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchone()[0] > 0


def _coluna_existe(schema_editor):
    return _existe(
        schema_editor,
        """
        SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s AND COLUMN_NAME = %s
        """,
        [TABELA, COLUNA],
    )


def _indice_existe(schema_editor):
    return _existe(
        schema_editor,
        """
        SELECT COUNT(*) FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s AND INDEX_NAME = %s
        """,
        [TABELA, INDICE],
    )


def adicionar_coluna(apps, schema_editor):
    if schema_editor.connection.vendor != 'mysql':
        return
    if _coluna_existe(schema_editor):
        return
    schema_editor.execute(f"""
        ALTER TABLE {TABELA}
            ADD COLUMN {COLUNA} VARCHAR(50)
            GENERATED ALWAYS AS (IF(excluido_em IS NULL, codigo_risco, NULL)) STORED
    """)


def remover_coluna(apps, schema_editor):
    if schema_editor.connection.vendor != 'mysql':
        return
    if _coluna_existe(schema_editor):
        schema_editor.execute(f"ALTER TABLE {TABELA} DROP COLUMN {COLUNA}")


def adicionar_indice(apps, schema_editor):
    if schema_editor.connection.vendor != 'mysql':
        return
    if _indice_existe(schema_editor):
        return
    schema_editor.execute(f"""
        ALTER TABLE {TABELA}
            ADD UNIQUE INDEX {INDICE} (pgr_documento_id, {COLUNA})
    """)


def remover_indice(apps, schema_editor):
    if schema_editor.connection.vendor != 'mysql':
        return
    if _indice_existe(schema_editor):
        schema_editor.execute(f"ALTER TABLE {TABELA} DROP INDEX {INDICE}")


class Migration(migrations.Migration):

    # Obrigatório em MySQL: DDL não é transacional, então não pode rodar
    # dentro do atomic da migração.
    atomic = False

    dependencies = [
        ('pgr_gestao', '0014_riscoidentificado_uniq_ges_codigo_por_pgr'),
    ]

    operations = [
        migrations.RunPython(adicionar_coluna, remover_coluna),
        migrations.RunPython(adicionar_indice, remover_indice),
    ]
