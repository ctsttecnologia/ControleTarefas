
# A importação do UUID é necessária
from django.db import migrations
import uuid

def popular_protocolos(apps, schema_editor):
    """
    Pega todos os participantes que estão com o protocolo nulo
    e gera um novo UUID para cada um.
    """
    Participante = apps.get_model('treinamentos', 'Participante')
    
    # Itera apenas nos que precisam
    participantes_sem_protocolo = Participante.objects.filter(protocolo_validacao__isnull=True)
    
    # Usamos o bulk_update para eficiência
    participantes_para_atualizar = []
    for p in participantes_sem_protocolo:
        p.protocolo_validacao = uuid.uuid4()
        participantes_para_atualizar.append(p)

    if participantes_para_atualizar:
        Participante.objects.bulk_update(participantes_para_atualizar, ['protocolo_validacao'])

class Migration(migrations.Migration):

    dependencies = [
        ('treinamentos', '0005_gabaritocertificado_remove_tipocurso_descricao_and_more'), # O Django preenche isso
    ]

    operations = [
        # Adicione esta linha
        migrations.RunPython(popular_protocolos, migrations.RunPython.noop),
    ]