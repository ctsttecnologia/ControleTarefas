from django.db import migrations


class Migration(migrations.Migration):
    """
    Migração de dados do app arquivos → documentos.
    Já executada com sucesso. Agora é um no-op seguro,
    pois o app 'arquivos' foi removido.
    """

    dependencies = [
        ('documentos', '0004_documento_cliente_documento_descricao_and_more'),
    ]

    operations = [
        # Dados já migrados — nada a fazer
    ]


