
# management/commands/migrar_solicitacoes_para_itens.py

from dns import transaction

from suprimentos.models import Cotacao, ItemSolicitacao, PedidoCompra, SolicitacaoCompra


@transaction.atomic
def handle(self):
    for sol in SolicitacaoCompra.objects.filter(itens__isnull=True):
        pedido = sol.pedido
        
        # Cria 1 ItemSolicitacao para cada ItemPedido
        for item_ped in pedido.itens.all():
            item_sol = ItemSolicitacao.objects.create(
                solicitacao=sol,
                item_pedido_origem=item_ped,
                material=item_ped.material,
                quantidade=item_ped.quantidade,
                valor_unitario_estimado=item_ped.valor_unitario,
            )
            
            # Se solicitação já tem fornecedor → cria Cotacao "histórica"
            if sol.fornecedor and sol.valor_pedido:
                Cotacao.objects.create(
                    item_solicitacao=item_sol,
                    fornecedor=sol.fornecedor,
                    valor_unitario=item_ped.valor_unitario,
                    observacoes="Cotação migrada do fluxo antigo",
                )
        
        # Se PC já foi emitido → cria PedidoCompra histórico
        if sol.numero_pedido_sienge:
            pc = PedidoCompra.objects.create(
                solicitacao=sol,
                fornecedor=sol.fornecedor,
                numero_pedido=sol.numero_pedido_sienge,
                status='EMITIDO',
                data_emissao=sol.data_criacao_pedido,
                # ... demais campos
            )

