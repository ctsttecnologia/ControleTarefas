
import logging
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from seguranca_trabalho.models import EntregaEPI
from gestao_riscos.models import Inspecao

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Verifica EPIs rastreáveis na metade da vida útil e propõe inspeções."

    def handle(self, *args, **options):
        self.stdout.write("Iniciando verificação de inspeções automáticas...")
        today = timezone.now().date()
        
        # Horizonte de dias para propor a inspeção (ex: propor com 7 dias de antecedência)
        horizonte_dias = 7
        data_limite = today + timedelta(days=horizonte_dias)

        # 1. Busca EPIs rastreáveis, entregues, não devolvidos e com vida útil definida
        itens_para_verificar = EntregaEPI.objects.filter(
            data_devolucao__isnull=True,            # Item está ativo com o funcionário
            equipamento__requer_numero_serie=True,  # É rastreável
            equipamento__vida_util_dias__gt=0       # Tem vida útil definida
        ).select_related('equipamento', 'filial')

        contador_propostas = 0
        for item in itens_para_verificar:
            vida_util_dias = item.equipamento.vida_util_dias
            if not vida_util_dias:
                continue

            # 2. Calcula a data de meia-vida
            data_meia_vida = item.data_entrega + timedelta(days=(vida_util_dias / 2))

            # 3. Verifica se a data de meia-vida está dentro do nosso horizonte
            if today <= data_meia_vida <= data_limite:
                
                # 4. Verifica se já não existe uma inspeção (proposta ou pendente)
                inspecao_existente = Inspecao.objects.filter(
                    entrega_epi=item,
                    status__in=['PENDENTE_APROVACAO', 'PENDENTE', 'CONCLUIDA']
                ).exists()

                if not inspecao_existente:
                    # 5. Cria a inspeção proposta
                    Inspecao.objects.create(
                        entrega_epi=item,
                        # equipamento e filial serão auto-preenchidos pelo .save()
                        data_agendada=data_meia_vida,
                        status='PENDENTE_APROVACAO',
                        filial=item.filial, # Garantir a filial
                        observacoes=f"Inspeção automática proposta (meia-vida do item N/S: {item.numero_serie or 'N/A'})."
                    )
                    contador_propostas += 1
                    logger.info(f"Proposta de inspeção criada para {item}.")

        self.stdout.write(self.style.SUCCESS(f"Concluído. {contador_propostas} novas inspeções propostas."))
