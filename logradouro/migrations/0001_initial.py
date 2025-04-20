# logradouro/migrations/0001_initial.py
from django.db import migrations, models
from django.core.validators import MinValueValidator, RegexValidator

class Migration(migrations.Migration):
    initial = True
    
    dependencies = [
        # Não há dependências de outros apps
    ]
    
    operations = [
        migrations.CreateModel(
            name='Logradouro',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('endereco', models.CharField(max_length=150, verbose_name='Endereço', help_text='Nome da rua, avenida, etc.')),
                ('numero', models.IntegerField(validators=[MinValueValidator(1, message='Número não pode ser menor que 1')], verbose_name='Número')),
                ('cep', models.CharField(max_length=8, validators=[RegexValidator(regex=r'^\d{8}$', message='CEP deve conter exatamente 8 dígitos')], verbose_name='CEP', help_text='Apenas números (8 dígitos)')),
                ('complemento', models.CharField(max_length=50, blank=True, null=True, verbose_name='Complemento')),
                ('bairro', models.CharField(max_length=60, verbose_name='Bairro')),
                ('cidade', models.CharField(max_length=60, verbose_name='Cidade')),
                ('estado', models.CharField(max_length=2, choices=[
                    ('AC', 'Acre'), ('AL', 'Alagoas'), ('AP', 'Amapá'),
                    ('AM', 'Amazonas'), ('BA', 'Bahia'), ('CE', 'Ceará'),
                    ('DF', 'Distrito Federal'), ('ES', 'Espírito Santo'),
                    ('GO', 'Goiás'), ('MA', 'Maranhão'), ('MT', 'Mato Grosso'),
                    ('MS', 'Mato Grosso do Sul'), ('MG', 'Minas Gerais'),
                    ('PA', 'Pará'), ('PB', 'Paraíba'), ('PR', 'Paraná'),
                    ('PE', 'Pernambuco'), ('PI', 'Piauí'), ('RJ', 'Rio de Janeiro'),
                    ('RN', 'Rio Grande do Norte'), ('RS', 'Rio Grande do Sul'),
                    ('RO', 'Rondônia'), ('RR', 'Roraima'), ('SC', 'Santa Catarina'),
                    ('SP', 'São Paulo'), ('SE', 'Sergipe'), ('TO', 'Tocantins')
                ], default='SP', verbose_name='Estado')),
                ('pais', models.CharField(default='Brasil', max_length=30, verbose_name='País')),
                ('ponto_referencia', models.CharField(max_length=100, blank=True, null=True, verbose_name='Ponto de Referência')),
                ('latitude', models.DecimalField(decimal_places=6, max_digits=9, null=True, blank=True, verbose_name='Latitude')),
                ('longitude', models.DecimalField(decimal_places=6, max_digits=9, null=True, blank=True, verbose_name='Longitude')),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')),
                ('data_atualizacao', models.DateTimeField(auto_now=True, verbose_name='Última Atualização')),
            ],
            options={
                'verbose_name': 'Logradouro',
                'verbose_name_plural': 'Logradouros',
                'ordering': ['estado', 'cidade', 'bairro', 'endereco'],
                'indexes': [
                    models.Index(fields=['estado', 'cidade'], name='idx_estado_cidade'),
                    models.Index(fields=['cep'], name='idx_logradouro_cep'),
                ],
                'constraints': [
                    models.UniqueConstraint(fields=['endereco', 'numero', 'complemento', 'cep'], name='unique_endereco_completo'),
                ],
            },
        ),
    ]