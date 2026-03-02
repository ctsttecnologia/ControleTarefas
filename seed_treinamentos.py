from pgr_gestao.models import GESGrupoExposicao, RiscoIdentificado, RiscoTreinamentoNecessario, PGRDocumento
from treinamentos.models import TipoCurso

doc = PGRDocumento.objects.get(pk=1)

# 1. Criar TipoCurso com referencia normativa (se nao existirem)
cursos_dados = [
    {'nome': 'Treinamento Admissional - Integracao SST', 'referencia_normativa': 'NR-01', 'area': 'SST'},
    {'nome': 'Trabalho em Altura', 'referencia_normativa': 'NR-35', 'area': 'SST'},
    {'nome': 'Seguranca em Instalacoes Eletricas', 'referencia_normativa': 'NR-10', 'area': 'SST'},
    {'nome': 'Espacos Confinados', 'referencia_normativa': 'NR-33', 'area': 'SST'},
    {'nome': 'Prevencao e Combate a Incendio', 'referencia_normativa': 'NR-23', 'area': 'SST'},
    {'nome': 'Operacao de Empilhadeira', 'referencia_normativa': 'NR-11', 'area': 'SST'},
]

cursos_criados = {}
for dados in cursos_dados:
    curso, created = TipoCurso.objects.get_or_create(
        referencia_normativa=dados['referencia_normativa'],
        defaults={'nome': dados['nome'], 'area': dados.get('area', 'SST'), 'ativo': True}
    )
    cursos_criados[dados['referencia_normativa']] = curso
    status = 'CRIADO' if created else 'JA EXISTIA'
    print(f'  {status}: {curso.nome} ({curso.referencia_normativa})')

# 2. Pegar o risco existente do GES-001
risco = RiscoIdentificado.objects.filter(pgr_documento=doc).first()

if risco:
    print(f'\nRisco encontrado: {risco.agente} (GES: {risco.ges.codigo})')
    
    # 3. Vincular treinamentos ao risco
    nrs_para_vincular = ['NR-01', 'NR-35', 'NR-10']
    
    for nr_ref in nrs_para_vincular:
        curso = cursos_criados.get(nr_ref)
        if curso:
            trein, created = RiscoTreinamentoNecessario.objects.get_or_create(
                risco=risco,
                tipo_curso=curso,
            )
            status = 'VINCULADO' if created else 'JA VINCULADO'
            print(f'  {status}: {curso.nome} -> {risco.agente}')
    
    # 4. Verificar resultado
    print(f'\nTotal treinamentos vinculados ao risco:')
    for t in risco.treinamentos_necessarios.select_related('tipo_curso').all():
        print(f'  - {t.tipo_curso.nome} ({t.tipo_curso.referencia_normativa})')
else:
    print('ERRO: Nenhum risco encontrado no documento!')

print('\n=== DONE ===')
