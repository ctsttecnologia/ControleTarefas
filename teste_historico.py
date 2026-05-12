from tarefas.models import Tarefas, HistoricoTarefa
from django.contrib.auth import get_user_model

User = get_user_model()

# Pega uma tarefa qualquer
t = Tarefas.objects.first()
print(f"\n🎯 Tarefa: '{t.titulo}' (criada por: {t.usuario})")

# Pega 2 usuários DIFERENTES do criador
outros = list(User.objects.exclude(pk=t.usuario.pk)[:2])

if len(outros) < 2:
    print("⚠️ Banco precisa de pelo menos 3 usuários para o teste.")
else:
    ator = outros[0]
    novo = outros[1]
    print(f"👤 Ator (quem adiciona): {ator}")
    print(f"➕ Novo participante: {novo}")

    # Garante que 'novo' NÃO está nos participantes antes do teste
    if t.participantes.filter(pk=novo.pk).exists():
        t.participantes.remove(novo)
        print(f"🧹 Removido {novo} dos participantes (estava lá antes).")

    # 🎯 SIMULA O FLUXO DA VIEW
    t._alterado_por = ator
    t.participantes.add(novo)

    # Verifica resultado
    h = HistoricoTarefa.objects.filter(tarefa=t).order_by('-data_alteracao').first()
    print(f"\n📜 Último registro de histórico:")
    print(f"   Tipo:         {h.tipo_alteracao}")
    print(f"   Descrição:    {h.descricao}")
    print(f"   Alterado por: {h.alterado_por}")
    print(f"   Data:         {h.data_alteracao}")

    if h.alterado_por_id == ator.pk:
        print("\n✅ SUCESSO TOTAL! Bug definitivamente extinto! 🦖💀")
    elif h.alterado_por_id == t.usuario_id:
        print("\n⚠️ Caiu no fallback (criador). Signal não pegou _alterado_por.")
    elif h.alterado_por is None:
        print("\n❌ Histórico ÓRFÃO criado! Algo ainda está errado.")
    else:
        print(f"\n❓ Resultado inesperado: {h.alterado_por}")

    # Cleanup
    t.participantes.remove(novo)
    print("\n🧹 Cleanup: participante removido.")
