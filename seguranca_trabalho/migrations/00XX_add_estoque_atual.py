# seguranca_trabalho/migrations/00XX_add_estoque_atual.py
from django.db import migrations, models
from django.db.models import Sum


def backfill_estoque(apps, schema_editor):
    Equipamento = apps.get_model('seguranca_trabalho', 'Equipamento')
    MovimentacaoEstoque = apps.get_model('seguranca_trabalho', 'MovimentacaoEstoque')

    for equipamento in Equipamento.objects.all():
        entradas = MovimentacaoEstoque.objects.filter(
            equipamento=equipamento, tipo='ENTRADA'
        ).aggregate(total=Sum('quantidade'))['total'] or 0

        saidas = MovimentacaoEstoque.objects.filter(
            equipamento=equipamento, tipo='SAIDA'
        ).aggregate(total=Sum('quantidade'))['total'] or 0

        saldo = max(entradas - saidas, 0)
        equipamento.estoque_atual = saldo
        equipamento.save(update_fields=['estoque_atual'])


def reverse_backfill(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('seguranca_trabalho', '0014_fichaepi_consentimento_lgpd_em_and_more'),
    ]

    operations = [
        # ── A coluna JÁ EXISTE fisicamente no banco (int NOT NULL).
        #    Sincroniza apenas o STATE do Django, sem tocar no banco. ──
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='equipamento',
                    name='estoque_atual',
                    field=models.IntegerField(
                        default=0,
                        editable=False,
                        verbose_name='Estoque Atual',
                        help_text='Atualizado automaticamente pelas movimentações.',
                    ),
                ),
            ],
            database_operations=[],
        ),
        migrations.RunPython(backfill_estoque, reverse_backfill),
        # ── Esta constraint NÃO existe ainda no banco (confirmado via
        #    SHOW CREATE TABLE) — executa normalmente, sem SeparateDatabaseAndState.
        migrations.AddConstraint(
            model_name='equipamento',
            constraint=models.CheckConstraint(
                condition=models.Q(estoque_atual__gte=0),
                name='equipamento_estoque_atual_nao_negativo',
            ),
        ),
    ]

