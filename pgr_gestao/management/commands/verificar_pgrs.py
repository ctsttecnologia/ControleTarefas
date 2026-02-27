
"""
Comando para verificar PGRs e Planos de Ação
python manage.py verificar_pgrs
"""
from django.core.management.base import BaseCommand
from pgr_gestao.signals import (
    verificar_pgrs_proximos_vencimento,
    verificar_planos_acao_atrasados
)


class Command(BaseCommand):
    help = 'Verifica PGRs próximos ao vencimento e planos de ação atrasados'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando verificação de PGRs...'))
        
        # Verifica PGRs
        verificar_pgrs_proximos_vencimento()
        
        # Verifica Planos de Ação
        verificar_planos_acao_atrasados()
        
        self.stdout.write(self.style.SUCCESS('✅ Verificação concluída!'))

