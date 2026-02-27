
# pgr_gestao/context_processors.py
from django.conf import settings
from django.db.models import Count, Q
from .models import PGRDocumento, RiscoIdentificado, PlanoAcaoPGR

def pgr_context(request):
    """
    Context processor para adicionar variáveis relacionadas ao PGR em todos os templates.
    """
    context = {
        'PGR_APP_NAME': 'PGR - Programa de Gerenciamento de Riscos',
        'PGR_VERSION': '1.0',
        'pgr_active': True,  # Para verificar se está no módulo PGR
    }
def pgr_stats(request):
    """
    Context processor que adiciona estatísticas do PGR aos templates.
    """
    if not request.user.is_authenticated:
        return {}
    
    try:
        # Estatísticas básicas (você pode personalizar conforme seus modelos)
        stats = {
            'total_documentos_pgr': PGRDocumento.objects.count(),
            'total_riscos_identificados': RiscoIdentificado.objects.count(),
            'total_planos_acao': PlanoAcaoPGR.objects.count(),
            'planos_acao_pendentes': PlanoAcaoPGR.objects.filter(
                status__in=['pendente', 'em_andamento']
            ).count(),
        }
    except:
        # Em caso de erro (ex: tabelas não criadas ainda), retorna valores padrão
        stats = {
            'total_documentos_pgr': 0,
            'total_riscos_identificados': 0,
            'total_planos_acao': 0,
            'planos_acao_pendentes': 0,
        }
    
    return {
        'pgr_stats': stats,
        'pgr_module_active': True,
    }
    
    # Adicione outras variáveis conforme necessário
    return context
