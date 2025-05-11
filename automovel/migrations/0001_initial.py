# automovel/migrations/0001_initial.py
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        # Remova qualquer dependência que possa causar o ciclo
        # Mantenha apenas dependências essenciais
    ]

    operations = [
        migrations.CreateModel(
            name='Carro',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('placa', models.CharField(max_length=10, unique=True)),
                ('modelo', models.CharField(max_length=50)),
                ('marca', models.CharField(max_length=50)),
                ('cor', models.CharField(max_length=30)),
                ('ano', models.PositiveIntegerField()),
                ('renavan', models.CharField(max_length=20, unique=True)),
                ('data_ultima_manutencao', models.DateField(blank=True, null=True)),
                ('data_proxima_manutencao', models.DateField(blank=True, null=True)),
                ('ativo', models.BooleanField(default=True)),
                ('observacoes', models.TextField(blank=True, null=True)),
                ('disponivel', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='Agendamento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('funcionario', models.CharField(max_length=100)),
                ('data_hora_agenda', models.DateTimeField()),
                ('data_hora_devolucao', models.DateTimeField(blank=True, null=True)),
                ('cm', models.CharField(max_length=20)),
                ('descricao', models.TextField()),
                ('pedagio', models.BooleanField(default=False)),
                ('abastecimento', models.BooleanField(default=False)),
                ('km_inicial', models.PositiveIntegerField()),
                ('km_final', models.PositiveIntegerField(blank=True, null=True)),
                ('foto_principal', models.ImageField(blank=True, null=True, upload_to='agendamentos/')),
                ('assinatura', models.TextField(blank=True)),
                ('responsavel', models.CharField(max_length=100)),
                ('ocorrencia', models.TextField(blank=True, null=True)),
                ('status', models.CharField(choices=[('agendado', 'Agendado'), ('em_andamento', 'Em Andamento'), ('finalizado', 'Finalizado'), ('cancelado', 'Cancelado')], default='agendado', max_length=20)),
                ('cancelar_agenda', models.BooleanField(default=False)),
                ('motivo_cancelamento', models.TextField(blank=True, null=True)),
                ('carro', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='automovel.carro')),
            ],
        ),
        migrations.CreateModel(
            name='Checklist_form',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(max_length=10)),
                ('data_criacao', models.DateTimeField(auto_now_add=True)),
                ('km_inicial', models.PositiveIntegerField()),
                ('km_final', models.PositiveIntegerField(blank=True, null=True)),
                ('revisao_frontal_status', models.CharField(choices=[('ok', 'OK'), ('danificado', 'Danificado'), ('nao_aplicavel', 'Não Aplicável')], max_length=15)),
                ('foto_frontal', models.ImageField(upload_to='checklists/')),
                ('revisao_trazeira_status', models.CharField(choices=[('ok', 'OK'), ('danificado', 'Danificado'), ('nao_aplicavel', 'Não Aplicável')], max_length=15)),
                ('foto_trazeira', models.ImageField(upload_to='checklists/')),
                ('revisao_lado_motorista_status', models.CharField(choices=[('ok', 'OK'), ('danificado', 'Danificado'), ('nao_aplicavel', 'Não Aplicável')], max_length=15)),
                ('foto_lado_motorista', models.ImageField(upload_to='checklists/')),
                ('revisao_lado_passageiro_status', models.CharField(choices=[('ok', 'OK'), ('danificado', 'Danificado'), ('nao_aplicavel', 'Não Aplicável')], max_length=15)),
                ('foto_lado_passageiro', models.ImageField(upload_to='checklists/')),
                ('observacoes_gerais', models.TextField(blank=True, null=True)),
                ('anexo_ocorrencia', models.TextField(blank=True, null=True)),
                ('assinatura', models.TextField()),
                ('confirmacao', models.BooleanField(default=False)),
                ('agendamento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='automovel.agendamento')),
            ],
        ),
        migrations.CreateModel(
            name='Foto',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('imagem', models.ImageField(upload_to='fotos/')),
                ('data_criacao', models.DateTimeField(auto_now_add=True)),
                ('observacao', models.TextField(blank=True, null=True)),
                ('agendamento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='automovel.agendamento')),
            ],
        ),
    ]