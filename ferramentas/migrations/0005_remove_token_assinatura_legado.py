from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ferramentas', '0004_alter_termoderesponsabilidade_options'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE ferramentas_termoderesponsabilidade DROP COLUMN token_assinatura;",
            reverse_sql="ALTER TABLE ferramentas_termoderesponsabilidade ADD COLUMN token_assinatura CHAR(32) NOT NULL UNIQUE;",
        ),
    ]

