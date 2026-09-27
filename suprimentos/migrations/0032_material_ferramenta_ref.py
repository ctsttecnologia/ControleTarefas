from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ferramentas', '0001_initial'),
        ('suprimentos', '0031_alter_parceiro_contato_alter_parceiro_telefone'),
    ]

    operations = [
        migrations.AddField(
            model_name='material',
            name='ferramenta_ref',
            field=models.ForeignKey(blank=True, help_text='Para ferramentas: vincule para atualizar quantidade ao receber pedido.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='materiais_vinculados', to='ferramentas.ferramenta', verbose_name='Ferramenta vinculada'),
        ),
    ]
