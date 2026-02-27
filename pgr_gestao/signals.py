
"""
Signals para automações do módulo PGR
IMPORTANTE: Importações de models devem ser feitas dentro das funções
"""
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta, date


# ========================================
# SIGNALS DO DOCUMENTO PGR
# ========================================

@receiver(pre_save, sender='pgr_gestao.PGRDocumento')
def verificar_vencimento_pgr(sender, instance, **kwargs):
    """
    Verifica e atualiza o status do PGR conforme a data de vencimento
    """
    if instance.pk:  # Se está atualizando
        hoje = date.today()
        
        # Verifica se está vencido
        if instance.data_vencimento < hoje and instance.status == 'vigente':
            instance.status = 'vencido'
        
        # Se a data de vencimento foi alterada e está futura, reativa
        elif instance.data_vencimento >= hoje and instance.status == 'vencido':
            instance.status = 'vigente'


@receiver(post_save, sender='pgr_gestao.PGRDocumento')
def notificar_criacao_pgr(sender, instance, created, **kwargs):
    """
    Notifica quando um novo PGR é criado
    """
    if created:
        # Log da criação
        print(f"✅ Novo PGR criado: {instance.codigo_documento}")
        
        # Envia e-mail para responsáveis (se configurado)
        if hasattr(settings, 'EMAIL_NOTIFICACAO_PGR') and settings.EMAIL_NOTIFICACAO_PGR:
            try:
                send_mail(
                    subject=f'Novo PGR Criado: {instance.codigo_documento}',
                    message=f'Um novo Programa de Gerenciamento de Riscos foi criado.\n\n'
                            f'Empresa: {instance.empresa.razao_social}\n'
                            f'Código: {instance.codigo_documento}\n'
                            f'Data de Vencimento: {instance.data_vencimento.strftime("%d/%m/%Y")}',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.EMAIL_NOTIFICACAO_PGR],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"❌ Erro ao enviar e-mail: {e}")


@receiver(post_save, sender='pgr_gestao.PGRDocumento')
def criar_cronograma_padrao(sender, instance, created, **kwargs):
    """
    Cria automaticamente ações padrão no cronograma quando um novo PGR é criado
    """
    if created:
        # Importar aqui para evitar circular import
        from pgr_gestao.models import CronogramaAcaoPGR
        
        acoes_padrao = [
            {
                'numero_item': 1,
                'acao_necessaria': 'Treinamentos normativos',
                'publico_alvo': 'Todos os colaboradores',
                'periodicidade': 'admissao',
                'responsavel': 'RH / Segurança do Trabalho'
            },
            {
                'numero_item': 2,
                'acao_necessaria': 'Investigação e reconhecimento dos riscos ambientais',
                'publico_alvo': 'Todos os colaboradores',
                'periodicidade': 'continuo',
                'responsavel': 'Segurança do Trabalho'
            },
            {
                'numero_item': 3,
                'acao_necessaria': 'Análise qualitativa dos riscos ambientais e registro dos dados',
                'publico_alvo': 'Todos os colaboradores',
                'periodicidade': 'bienal',
                'responsavel': 'Segurança do Trabalho'
            },
            {
                'numero_item': 4,
                'acao_necessaria': 'Análise quantitativa de ruído através de dosimetria por amostragem',
                'publico_alvo': 'Todos os colaboradores',
                'periodicidade': 'quando_necessario',
                'responsavel': 'Empresa especializada'
            },
            {
                'numero_item': 5,
                'acao_necessaria': 'Atualização da planilha de Inventários de Riscos, Perigos, Aspectos e Impactos',
                'publico_alvo': 'Todos os colaboradores',
                'periodicidade': 'bienal',
                'responsavel': 'Segurança do Trabalho'
            },
            {
                'numero_item': 6,
                'acao_necessaria': 'Apresentação do PGR',
                'publico_alvo': 'Todos os colaboradores',
                'periodicidade': 'admissao',
                'responsavel': 'RH / Segurança do Trabalho'
            },
            {
                'numero_item': 7,
                'acao_necessaria': 'PCMSO (Programa de Controle Médico e Saúde Ocupacional), de forma integrada com o PGR',
                'publico_alvo': 'Todos os colaboradores',
                'periodicidade': 'anual',
                'responsavel': 'Medicina do Trabalho'
            },
            {
                'numero_item': 8,
                'acao_necessaria': 'Fiscalizar e cobrar o uso dos equipamentos de segurança nos locais de obrigatoriedade para o uso',
                'publico_alvo': 'Todos os colaboradores',
                'periodicidade': 'continuo',
                'responsavel': 'Supervisores / Liderança'
            },
            {
                'numero_item': 9,
                'acao_necessaria': 'Auditar Fichas de EPI\'s',
                'publico_alvo': 'Todos os colaboradores',
                'periodicidade': 'continuo',
                'responsavel': 'RH / Segurança do Trabalho'
            },
            {
                'numero_item': 10,
                'acao_necessaria': 'Revisar o PGR',
                'publico_alvo': 'Gestão',
                'periodicidade': 'bienal',
                'responsavel': 'Segurança do Trabalho'
            },
        ]
        
        # Calcula data de próxima avaliação (2 anos)
        data_proxima = instance.data_vencimento
        
        for acao in acoes_padrao:
            CronogramaAcaoPGR.objects.create(
                pgr_documento=instance,
                numero_item=acao['numero_item'],
                acao_necessaria=acao['acao_necessaria'],
                publico_alvo=acao['publico_alvo'],
                periodicidade=acao['periodicidade'],
                responsavel=acao['responsavel'],
                data_proxima_avaliacao=data_proxima,
                status='pendente'
            )
        
        print(f"✅ Cronograma padrão criado para PGR {instance.codigo_documento}")


# ========================================
# SIGNALS DE REVISÃO
# ========================================

@receiver(post_save, sender='pgr_gestao.PGRRevisao')
def atualizar_versao_pgr(sender, instance, created, **kwargs):
    """
    Atualiza a versão e data da última revisão do PGR automaticamente
    """
    if created:
        pgr = instance.pgr_documento
        pgr.versao_atual = instance.numero_revisao + 1
        pgr.data_ultima_revisao = instance.data_realizacao
        pgr.save(update_fields=['versao_atual', 'data_ultima_revisao'])
        
        print(f"✅ PGR {pgr.codigo_documento} atualizado para versão {pgr.versao_atual}")


# ========================================
# SIGNALS DE RISCOS IDENTIFICADOS
# ========================================

@receiver(pre_save, sender='pgr_gestao.RiscoIdentificado')
def calcular_classificacao_risco(sender, instance, **kwargs):
    """
    Calcula automaticamente a classificação do risco baseado na metodologia
    """
    if instance.gravidade_g and instance.exposicao_e and instance.severidade_s:
        # Matriz de Severidade (Tabela 4 do documento)
        matriz_severidade = {
            (1, 1): 'A', (1, 2): 'A', (1, 3): 'A', (1, 4): 'B', (1, 5): 'B',
            (2, 1): 'A', (2, 2): 'B', (2, 3): 'B', (2, 4): 'C', (2, 5): 'D',
            (3, 1): 'A', (3, 2): 'B', (3, 3): 'C', (3, 4): 'D', (3, 5): 'D',
            (4, 1): 'B', (4, 2): 'C', (4, 3): 'D', (4, 4): 'E', (4, 5): 'E',
            (5, 1): 'B', (5, 2): 'D', (5, 3): 'D', (5, 4): 'E', (5, 5): 'E',
        }
        
        severidade_calculada = matriz_severidade.get(
            (instance.gravidade_g, instance.exposicao_e), 
            'C'
        )
        
        # Atualiza se não foi definida manualmente
        if not instance.severidade_s or instance.severidade_s == 'C':
            instance.severidade_s = severidade_calculada
        
        # Classificação do Risco (Tabela 5 e 8)
        if instance.probabilidade_p:
            matriz_classificacao = {
                ('A', 1): 'negligenciavel', ('A', 2): 'negligenciavel', ('A', 3): 'negligenciavel', 
                ('A', 4): 'marginal', ('A', 5): 'marginal',
                ('B', 1): 'negligenciavel', ('B', 2): 'negligenciavel', ('B', 3): 'marginal', 
                ('B', 4): 'moderado', ('B', 5): 'moderado',
                ('C', 1): 'negligenciavel', ('C', 2): 'marginal', ('C', 3): 'moderado', 
                ('C', 4): 'moderado', ('C', 5): 'muito_grave',
                ('D', 1): 'marginal', ('D', 2): 'moderado', ('D', 3): 'moderado', 
                ('D', 4): 'muito_grave', ('D', 5): 'muito_grave',
                ('E', 1): 'marginal', ('E', 2): 'moderado', ('E', 3): 'muito_grave', 
                ('E', 4): 'muito_grave', ('E', 5): 'critico',
            }
            
            classificacao = matriz_classificacao.get(
                (instance.severidade_s, instance.probabilidade_p),
                'moderado'
            )
            
            instance.classificacao_risco = classificacao
            
            # Define prioridade baseada na classificação
            if classificacao in ['critico', 'muito_grave']:
                instance.prioridade_acao = 'critica'
            elif classificacao == 'moderado':
                instance.prioridade_acao = 'alta'
            elif classificacao == 'marginal':
                instance.prioridade_acao = 'media'
            else:
                instance.prioridade_acao = 'baixa'


@receiver(post_save, sender='pgr_gestao.RiscoIdentificado')
def criar_plano_acao_automatico(sender, instance, created, **kwargs):
    """
    Cria automaticamente um plano de ação para riscos críticos e muito graves
    """
    if created and instance.classificacao_risco in ['critico', 'muito_grave']:
        # Importar aqui
        from pgr_gestao.models import PlanoAcaoPGR
        
        # Verifica se já não existe plano de ação
        if not instance.planos_acao.exists():
            # Define prazo baseado na criticidade
            if instance.classificacao_risco == 'critico':
                prazo = date.today() + timedelta(days=15)  # 15 dias
            else:
                prazo = date.today() + timedelta(days=30)  # 30 dias
            
            PlanoAcaoPGR.objects.create(
                risco_identificado=instance,
                tipo_acao='controle_engenharia',
                descricao_acao=f'Implementar medidas de controle para o risco: {instance.agente}',
                prioridade='critica' if instance.classificacao_risco == 'critico' else 'alta',
                data_prevista=prazo,
                responsavel='Coordenador de Segurança',
                status='pendente',
                criado_por=instance.criado_por if hasattr(instance, 'criado_por') else None
            )
            
            print(f"⚠️ Plano de ação automático criado para risco crítico: {instance.agente}")


@receiver(post_save, sender='pgr_gestao.RiscoIdentificado')
def notificar_risco_critico(sender, instance, created, **kwargs):
    """
    Notifica sobre identificação de risco crítico
    """
    if created and instance.classificacao_risco in ['critico', 'muito_grave']:
        print(f"🚨 ALERTA: Risco {instance.classificacao_risco.upper()} identificado!")
        print(f"   Agente: {instance.agente}")
        print(f"   GES: {instance.ges.nome if instance.ges else 'N/A'}")
        print(f"   PGR: {instance.pgr_documento.codigo_documento}")
        
        # Envio de e-mail para gestores (se configurado)
        if hasattr(settings, 'EMAIL_ALERTA_RISCO_CRITICO'):
            try:
                send_mail(
                    subject=f'🚨 ALERTA: Risco {instance.get_classificacao_risco_display().upper()} Identificado',
                    message=f'Um risco {instance.get_classificacao_risco_display()} foi identificado.\n\n'
                            f'Agente: {instance.agente}\n'
                            f'Fonte Geradora: {instance.fonte_geradora}\n'
                            f'GES: {instance.ges.nome if instance.ges else "N/A"}\n'
                            f'Possíveis Efeitos: {instance.possiveis_efeitos_saude}\n\n'
                            f'Ação necessária imediatamente!',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.EMAIL_ALERTA_RISCO_CRITICO],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"❌ Erro ao enviar alerta: {e}")


# ========================================
# SIGNALS DE PLANOS DE AÇÃO
# ========================================

@receiver(pre_save, sender='pgr_gestao.PlanoAcaoPGR')
def verificar_status_plano(sender, instance, **kwargs):
    """
    Verifica e atualiza status do plano automaticamente
    """
    if instance.pk:  # Se está atualizando
        # Se foi concluído, registra a data
        if instance.status == 'concluido' and not instance.data_conclusao:
            instance.data_conclusao = date.today()
        
        # Se voltou para pendente/em andamento, limpa data de conclusão
        elif instance.status in ['pendente', 'em_andamento'] and instance.data_conclusao:
            instance.data_conclusao = None


@receiver(post_save, sender='pgr_gestao.PlanoAcaoPGR')
def atualizar_status_risco(sender, instance, created, **kwargs):
    """
    Atualiza o status do risco quando o plano é concluído
    """
    if not created and instance.status == 'concluido':
        risco = instance.risco_identificado
        
        # Verifica se todos os planos do risco estão concluídos
        planos_pendentes = risco.planos_acao.exclude(status='concluido').count()
        
        if planos_pendentes == 0:
            risco.status_controle = 'controlado'
            risco.save(update_fields=['status_controle'])
            print(f"✅ Risco {risco.agente} marcado como CONTROLADO")


@receiver(post_save, sender='pgr_gestao.PlanoAcaoPGR')
def notificar_plano_atrasado(sender, instance, **kwargs):
    """
    Notifica quando um plano de ação está atrasado
    """
    if hasattr(instance, 'esta_atrasado') and instance.esta_atrasado and instance.status in ['pendente', 'em_andamento']:
        print(f"⏰ ATENÇÃO: Plano de ação ATRASADO!")
        print(f"   Descrição: {instance.descricao_acao[:50]}...")
        print(f"   Responsável: {instance.responsavel}")
        print(f"   Previsto para: {instance.data_prevista.strftime('%d/%m/%Y')}")


# ========================================
# SIGNALS DE AVALIAÇÕES QUANTITATIVAS
# ========================================

@receiver(post_save, sender='pgr_gestao.AvaliacaoQuantitativa')
def atualizar_metodo_avaliacao_risco(sender, instance, created, **kwargs):
    """
    Atualiza o método de avaliação do risco para quantitativo
    """
    if created:
        risco = instance.risco_identificado
        if risco.metodo_avaliacao != 'quantitativo':
            risco.metodo_avaliacao = 'quantitativo'
            risco.save(update_fields=['metodo_avaliacao'])


@receiver(post_save, sender='pgr_gestao.AvaliacaoQuantitativa')
def alertar_avaliacao_nao_conforme(sender, instance, created, **kwargs):
    """
    Alerta quando uma avaliação está não conforme
    """
    if instance.conforme == False:
        print(f"⚠️ AVALIAÇÃO NÃO CONFORME detectada!")
        print(f"   Tipo: {instance.get_tipo_avaliacao_display()}")
        print(f"   Resultado: {instance.resultado_medido} {instance.unidade_medida}")
        print(f"   Limite: {instance.limite_tolerancia_nr}")
        print(f"   Risco: {instance.risco_identificado.agente}")


# ========================================
# SIGNALS DE GES
# ========================================

@receiver(post_save, sender='pgr_gestao.GESGrupoExposicao')
def gerar_codigo_ges_automatico(sender, instance, created, **kwargs):
    """
    Gera código automático para GES se não fornecido
    """
    if created and not instance.codigo:
        # Conta quantos GES existem no documento
        total_ges = instance.pgr_documento.grupos_exposicao.count()
        
        # Gera código no formato GES-001, GES-002, etc.
        instance.codigo = f"GES-{total_ges:03d}"
        instance.save(update_fields=['codigo'])


# ========================================
# TASK PERIÓDICA (Para usar com Celery/Django-Q)
# ========================================

def verificar_pgrs_proximos_vencimento():
    """
    Tarefa periódica para verificar PGRs próximos ao vencimento
    Deve ser executada diariamente
    """
    from django.db.models import Q
    from pgr_gestao.models import PGRDocumento
    
    hoje = date.today()
    data_alerta_30 = hoje + timedelta(days=30)
    data_alerta_15 = hoje + timedelta(days=15)
    
    # PGRs que vencem em 30 dias
    pgrs_30_dias = PGRDocumento.objects.filter(
        Q(data_vencimento__lte=data_alerta_30) & Q(data_vencimento__gt=hoje),
        status='vigente'
    )
    
    for pgr in pgrs_30_dias:
        dias = (pgr.data_vencimento - hoje).days
        print(f"⚠️ PGR {pgr.codigo_documento} vence em {dias} dias!")
    
    # PGRs que vencem em 15 dias (alerta crítico)
    pgrs_15_dias = PGRDocumento.objects.filter(
        Q(data_vencimento__lte=data_alerta_15) & Q(data_vencimento__gt=hoje),
        status='vigente'
    )
    
    for pgr in pgrs_15_dias:
        dias = (pgr.data_vencimento - hoje).days
        print(f"🚨 URGENTE: PGR {pgr.codigo_documento} vence em {dias} dias!")


def verificar_planos_acao_atrasados():
    """
    Tarefa periódica para verificar planos de ação atrasados
    Deve ser executada diariamente
    """
    from pgr_gestao.models import PlanoAcaoPGR
    
    hoje = date.today()
    
    planos_atrasados = PlanoAcaoPGR.objects.filter(
        status__in=['pendente', 'em_andamento'],
        data_prevista__lt=hoje
    ).select_related('risco_identificado', 'risco_identificado__pgr_documento')
    
    for plano in planos_atrasados:
        dias_atraso = (hoje - plano.data_prevista).days
        print(f"⏰ Plano ATRASADO há {dias_atraso} dias!")
        print(f"   Responsável: {plano.responsavel}")
        print(f"   Descrição: {plano.descricao_acao[:50]}...")


