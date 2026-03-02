from pgr_gestao.models import RiscoIdentificado, RiscoTreinamentoNecessario, PGRDocumento
from treinamentos.models import TipoCurso

doc = PGRDocumento.objects.get(pk=1)
risco = RiscoIdentificado.objects.filter(pgr_documento=doc).first()

nrs = ['NR-01', 'NR-35', 'NR-10']

for nr in nrs:
    curso = TipoCurso.objects.filter(referencia_normativa=nr).first()
    if curso and risco:
        trein, created = RiscoTreinamentoNecessario.objects.get_or_create(
            risco_identificado=risco,
            tipo_curso=curso,
        )
        status = 'VINCULADO' if created else 'JA EXISTIA'
        print(f'  {status}: {curso.nome} -> {risco.agente}')

print('\nTreinamentos do risco:')
for t in RiscoTreinamentoNecessario.objects.filter(risco_identificado=risco).select_related('tipo_curso'):
    print(f'  - {t.tipo_curso.nome} ({t.tipo_curso.referencia_normativa})')

print('\n=== DONE ===')
