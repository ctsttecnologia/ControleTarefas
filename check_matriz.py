from pgr_gestao.models import GESGrupoExposicao, RiscoIdentificado, RiscoTreinamentoNecessario, PGRDocumento
from treinamentos.models import TipoCurso

doc = PGRDocumento.objects.get(pk=1)

print('=== GES (Cargos) ===')
for ges in GESGrupoExposicao.objects.filter(pgr_documento=doc, ativo=True):
    cargo = ges.cargo.nome if ges.cargo else 'SEM CARGO'
    print(f'  {ges.codigo} | Cargo: {cargo} | Trab: {ges.numero_trabalhadores}')

print('')
print('=== Treinamentos Necessarios ===')
riscos = RiscoIdentificado.objects.filter(pgr_documento=doc)
for risco in riscos:
    treinamentos = risco.treinamentos_necessarios.select_related('tipo_curso').all()
    ges_codigo = risco.ges.codigo if risco.ges else 'SEM GES'
    if treinamentos.exists():
        for t in treinamentos:
            ref = t.tipo_curso.referencia_normativa or 'SEM REF'
            print(f'  GES: {ges_codigo} | Risco: {risco.agente} | Curso: {t.tipo_curso.nome} | Ref: {ref}')
    else:
        print(f'  GES: {ges_codigo} | Risco: {risco.agente} | SEM TREINAMENTOS')

print('')
print('=== TipoCurso com referencia normativa ===')
for tc in TipoCurso.objects.filter(ativo=True).order_by('nome')[:30]:
    ref = tc.referencia_normativa or '-'
    print(f'  {tc.pk} | {tc.nome} | Area: {tc.area} | Ref: {ref}')
