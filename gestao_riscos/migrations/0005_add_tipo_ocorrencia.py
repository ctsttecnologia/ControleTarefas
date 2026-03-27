
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestao_riscos', '0004_tiporisco'),
    ]

    operations = [
        migrations.AddField(
            model_name='incidente',
            name='tipo_ocorrencia',
            field=models.CharField(
                max_length=30,
                choices=[
                    ('QUASE_ACIDENTE', 'Quase Acidente (Incidente)'),
                    ('CONDICAO_INSEGURA', 'Condição Insegura'),
                    ('ACIDENTE_SEM_AFASTAMENTO', 'Acidente sem Afastamento'),
                    ('ACIDENTE_COM_AFASTAMENTO', 'Acidente com Afastamento'),
                    ('ACIDENTE_TRAJETO', 'Acidente de Trajeto'),
                    ('ACIDENTE_FATAL', 'Acidente Fatal'),
                ],
                default='QUASE_ACIDENTE',
                verbose_name='Tipo de Ocorrência',
            ),
        ),
    ]

