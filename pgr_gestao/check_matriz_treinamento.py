
# check_matriz_treinamento.py
from pgr_gestao.models import (
    GESGrupoExposicao, RiscoIdentificado,
    RiscoTreinamentoNecessario, PGRDocumento
)
from treinamentos.models import TipoCurso

doc = PGRDocumento.objects.get(pk=1)

# 1. GES com cargos
print("=== GES (Cargos) ===")
for ges in GESGrupoExposicao.objects.filter(pgr_documento=doc, ativo=True):
    cargo = ges.cargo.nome if ges.cargo else "SEM CARGO"
    funcao = ges.funcao.nome if ges.funcao else "SEM FUNCAO"
    print(f"  {ges.codigo} | Cargo: {cargo} | Funcao: {funcao} | Trab: {ges.numero_trabalhadores}")

# 2. Treinamentos vinculados a riscos
print("\n=== Treinamentos Necessarios (via RiscoTreinamentoNecessario) ===")
riscos = RiscoIdentificado.objects.filter(pgr_documento=doc)
for risco in riscos:
    treinamentos = risco.treinamentos_necessarios.select_related('tipo_curso').all()
    ges_codigo = risco.ges.codigo if risco.ges else "SEM GES"
    if treinamentos.exists():
        for t in treinamentos:
            ref = t.tipo_curso.referencia_normativa or "SEM REF"
            print(f"  GES: {ges_codigo} | Risco: {risco.agente} | Curso: {t.tipo_curso.nome} | Ref: {ref}")
    else:
        print(f"  GES: {ges_codigo} | Risco: {risco.agente} | SEM TREINAMENTOS VINCULADOS")

# 3. TipoCurso com referencia_normativa
print("\n=== TipoCurso com referencia normativa ===")
for tc in TipoCurso.objects.filter(ativo=True).order_by('nome')[:30]:
    ref = tc.referencia_normativa or "-"
    print(f"  {tc.pk} | {tc.nome} | Area: {tc.area} | Ref: {ref}")

