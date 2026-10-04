# ============================================================
#    ferramentas/migrations/00XX_patch_constraints_movimentacao.py
#    Ajuste o número conforme a última migração existente no app.
# ============================================================

from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ('ferramentas', '0007_alter_termoderesponsabilidade_pdf_arquivo'),  
    ]

    operations = [
        migrations.AddConstraint(
            model_name='movimentacao',
            constraint=models.CheckConstraint(
                condition=(
                    Q(ferramenta__isnull=False, mala__isnull=True) |
                    Q(ferramenta__isnull=True, mala__isnull=False)
                ),
                name='mov_ferramenta_xor_mala',
            ),
        ),
        migrations.AddConstraint(
            model_name='movimentacao',
            constraint=models.UniqueConstraint(
                fields=['ferramenta'],
                condition=Q(data_devolucao__isnull=True),
                name='uniq_ferramenta_mov_ativa',
            ),
        ),
        migrations.AddConstraint(
            model_name='movimentacao',
            constraint=models.UniqueConstraint(
                fields=['mala'],
                condition=Q(data_devolucao__isnull=True),
                name='uniq_mala_mov_ativa',
            ),
        ),
        migrations.AddConstraint(
            model_name='itemtermo',
            constraint=models.CheckConstraint(
                condition=(
                    Q(ferramenta__isnull=False, mala__isnull=True) |
                    Q(ferramenta__isnull=True, mala__isnull=False) |
                    Q(ferramenta__isnull=True, mala__isnull=True)
                ),
                name='item_termo_ferramenta_xor_mala',
            ),
        ),
    ]