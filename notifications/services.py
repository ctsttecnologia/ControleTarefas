
# notifications/services.py

"""
Serviço central para criação de notificações e envio de e-mails.
Todos os módulos devem usar estas funções.
"""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q         
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from .models import Notificacao

User = get_user_model()
logger = logging.getLogger(__name__)


# =============================================================================
# SERVIÇO DE NOTIFICAÇÕES (SISTEMA / SINO)
# =============================================================================

def criar_notificacao(
    usuario,
    titulo,
    tipo='sistema',
    categoria='sistema',
    prioridade='media',
    mensagem='',
    url_destino=None,
    icone='bi-bell',
    duplicar=False,
):
    """
    Cria uma notificação para um usuário.

    Args:
        usuario: User instance
        titulo: Texto curto do título
        tipo: Tipo da notificação (ver TIPO_CHOICES)
        categoria: Categoria (tarefa, pgr, chat, sistema, suprimentos)
        prioridade: Prioridade visual (baixa, media, alta, critica)
        mensagem: Texto opcional com mais detalhes
        url_destino: URL relativa para redirecionamento
        icone: Classe do Bootstrap Icons
        duplicar: Se False, evita duplicar notificação idêntica não lida
    """
    if not duplicar:
        existe = Notificacao.objects.filter(
            usuario=usuario,
            tipo=tipo,
            titulo=titulo,
            lida=False,
        ).exists()
        if existe:
            return None

    return Notificacao.objects.create(
        usuario=usuario,
        titulo=titulo,
        tipo=tipo,
        categoria=categoria,
        prioridade=prioridade,
        mensagem=mensagem,
        url_destino=url_destino,
        icone=icone,
    )


def criar_notificacao_para_grupo(usuarios, titulo, mensagem='', **kwargs):
    """
    Cria a mesma notificação para múltiplos usuários.
    """
    notificacoes = []
    for usuario in usuarios:
        n = criar_notificacao(usuario, titulo, mensagem=mensagem, **kwargs)
        if n:
            notificacoes.append(n)
    return notificacoes


# =============================================================================
# FUNÇÕES ESPECÍFICAS PARA TAREFAS
# =============================================================================

def notificar_tarefa_atrasada(tarefa):
    """Cria notificação para tarefa atrasada."""
    if not tarefa.responsavel:
        return None

    url = reverse('tarefas:tarefa_detail', kwargs={'pk': tarefa.pk})

    return criar_notificacao(
        usuario=tarefa.responsavel,
        titulo=f'Tarefa atrasada: {tarefa.titulo[:50]}',
        tipo='tarefa_atrasada',
        categoria='tarefa',
        prioridade='alta',
        mensagem=f'O prazo era {tarefa.prazo.strftime("%d/%m/%Y %H:%M") if tarefa.prazo else "N/A"}.',
        url_destino=url,
        icone='bi-exclamation-triangle-fill',
    )


def notificar_tarefa_lembrete(tarefa):
    """Cria notificação de lembrete de tarefa."""
    if not tarefa.responsavel:
        return None

    url = reverse('tarefas:tarefa_detail', kwargs={'pk': tarefa.pk})

    return criar_notificacao(
        usuario=tarefa.responsavel,
        titulo=f'Lembrete: {tarefa.titulo[:50]}',
        tipo='tarefa_lembrete',
        categoria='tarefa',
        prioridade='media',
        mensagem=f'Prazo: {tarefa.prazo.strftime("%d/%m/%Y %H:%M") if tarefa.prazo else "N/A"}.',
        url_destino=url,
        icone='bi-alarm',
    )


def notificar_tarefa_prazo_proximo(tarefa):
    """Cria notificação para tarefa com prazo nas próximas 24h."""
    if not tarefa.responsavel:
        return None

    url = reverse('tarefas:tarefa_detail', kwargs={'pk': tarefa.pk})

    return criar_notificacao(
        usuario=tarefa.responsavel,
        titulo=f'Prazo próximo: {tarefa.titulo[:50]}',
        tipo='tarefa_prazo_proximo',
        categoria='tarefa',
        prioridade='alta',
        mensagem=f'Vence em {tarefa.prazo.strftime("%d/%m/%Y %H:%M") if tarefa.prazo else "N/A"}.',
        url_destino=url,
        icone='bi-clock-history',
    )


def notificar_tarefa_status(tarefa, status_anterior, novo_status, alterado_por=None):
    """
    Cria notificação de mudança de status para criador e responsável.
    Não notifica quem fez a alteração.
    """
    destinatarios = set()
    if tarefa.usuario and tarefa.usuario != alterado_por:
        destinatarios.add(tarefa.usuario)
    if tarefa.responsavel and tarefa.responsavel != alterado_por:
        destinatarios.add(tarefa.responsavel)

    url = reverse('tarefas:tarefa_detail', kwargs={'pk': tarefa.pk})
    resultados = []

    for user in destinatarios:
        n = criar_notificacao(
            usuario=user,
            titulo=f'Status alterado: {tarefa.titulo[:40]}',
            tipo='tarefa_status',
            categoria='tarefa',
            prioridade='baixa',
            mensagem=f'{status_anterior} → {novo_status}',
            url_destino=url,
            icone='bi-arrow-repeat',
            duplicar=True,
        )
        resultados.append(n)

    return resultados


# =============================================================================
# FUNÇÕES ESPECÍFICAS PARA PGR
# =============================================================================

def notificar_pgr_vencimento(pgr_documento, usuario, dias_restantes):
    """Cria notificação de PGR próximo ao vencimento."""
    prioridade = 'critica' if dias_restantes <= 15 else 'alta'
    icone = 'bi-shield-exclamation' if dias_restantes <= 15 else 'bi-shield'

    url = reverse('pgr_gestao:pgr_detail', kwargs={'pk': pgr_documento.pk})

    return criar_notificacao(
        usuario=usuario,
        titulo=f'PGR {pgr_documento.codigo_documento} vence em {dias_restantes} dias',
        tipo='pgr_vencimento',
        categoria='pgr',
        prioridade=prioridade,
        mensagem=f'Vencimento: {pgr_documento.data_vencimento.strftime("%d/%m/%Y")}.',
        url_destino=url,
        icone=icone,
    )


def notificar_pgr_risco_critico(risco, usuario):
    """Cria notificação para risco crítico identificado."""
    url = reverse('pgr_gestao:pgr_detail', kwargs={'pk': risco.pgr_documento.pk})

    return criar_notificacao(
        usuario=usuario,
        titulo=f'Risco crítico: {risco.agente[:40]}',
        tipo='pgr_risco_critico',
        categoria='pgr',
        prioridade='critica',
        mensagem=f'Classificação: {risco.get_classificacao_risco_display()}.',
        url_destino=url,
        icone='bi-radioactive',
    )


def notificar_pgr_plano_atrasado(plano, usuario):
    """Cria notificação para plano de ação atrasado."""
    url = reverse('pgr_gestao:pgr_detail', kwargs={'pk': plano.risco_identificado.pgr_documento.pk})

    return criar_notificacao(
        usuario=usuario,
        titulo=f'Plano de ação atrasado',
        tipo='pgr_plano_atrasado',
        categoria='pgr',
        prioridade='alta',
        mensagem=f'{plano.descricao_acao[:60]}...',
        url_destino=url,
        icone='bi-calendar-x',
    )


# ═════════════════════════════════════════════════════════════════
# FUNÇÕES ESPECÍFICAS PARA SUPRIMENTOS
# ═════════════════════════════════════════════════════════════════

def _obter_gerentes_da_filial(filial):
    """
    Retorna queryset de usuários do grupo 'Gerente' vinculados à filial.
    Inclui superusuários como fallback.
    """
    gerentes = User.objects.filter(
        groups__name='Gerente',
        is_active=True,
    )

    if filial:
        gerentes_filial = gerentes.filter(filiais_permitidas=filial)
        if gerentes_filial.exists():
            return gerentes_filial

        gerentes_filial = gerentes.filter(filial_ativa=filial)
        if gerentes_filial.exists():
            return gerentes_filial

    return (gerentes | User.objects.filter(
        is_superuser=True, is_active=True
    )).distinct()


# ═════════════════════════════════════════════════════════════════
# NOTIFICAÇÕES — PEDIDO DE MATERIAL (Workflow Revisão)
# ═════════════════════════════════════════════════════════════════

def notificar_pedido_pendente(pedido):
    """Notifica gerentes que há um pedido aguardando aprovação."""
    gerentes = User.objects.filter(
        Q(groups__name='Gerente') | Q(is_superuser=True),
        is_active=True,
    ).distinct()

    if pedido.filial:
        gerentes = gerentes.filter(
            Q(filial_ativa=pedido.filial) | Q(is_superuser=True)
        )

    solicitante = pedido.solicitante.get_full_name() or pedido.solicitante.username
    contrato_info = f"{pedido.contrato.cm} — {pedido.contrato.cliente}"
    valor_total = f"R$ {pedido.valor_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

    for gerente in gerentes:
        criar_notificacao(
            usuario=gerente,
            titulo=f'📋 Pedido {pedido.numero} aguardando aprovação',
            tipo='sistema',
            categoria='suprimentos',
            prioridade='alta',
            mensagem=(
                f'{solicitante} criou um pedido para {contrato_info}.\n'
                f'Tipo: {pedido.get_tipo_obra_display()}\n'
                f'Valor: {valor_total}\n'
                f'Data necessária: {pedido.data_necessaria.strftime("%d/%m/%Y") if pedido.data_necessaria else "Não informada"}'
            ),
            url_destino=pedido.get_absolute_url(),
            icone='bi-clipboard-check',
        )

        enviar_email_notificacao(
            assunto=f'[Suprimentos] Pedido {pedido.numero} — Aprovação Pendente',
            template_texto='notifications/emails/pedido_pendente.txt',
            template_html='notifications/emails/pedido_pendente.html',
            contexto={
                'pedido': pedido,
                'solicitante': solicitante,
                'contrato': contrato_info,
                'valor_total': valor_total,
                'gerente': gerente,
                'url': pedido.get_absolute_url(),
            },
            destinatarios=[gerente.email],
        )


def notificar_pedido_revisao(pedido):
    """Notifica solicitante que o pedido foi devolvido para revisão."""
    aprovador = pedido.aprovador.get_full_name() if pedido.aprovador else 'Gerente'

    criar_notificacao(
        usuario=pedido.solicitante,
        titulo=f'🔄 Pedido {pedido.numero} devolvido para revisão',
        tipo='sistema',
        categoria='suprimentos',
        prioridade='alta',
        mensagem=(
            f'{aprovador} devolveu seu pedido para correção.\n'
            f'Motivo: {pedido.motivo_revisao}\n\n'
            f'Corrija os pontos indicados e reenvie para aprovação.'
        ),
        url_destino=pedido.get_absolute_url(),
        icone='bi-arrow-counterclockwise',
    )

    enviar_email_notificacao(
        assunto=f'[Suprimentos] Pedido {pedido.numero} — Devolvido para Revisão',
        template_texto='notifications/emails/pedido_revisao.txt',
        template_html='notifications/emails/pedido_revisao.html',
        contexto={
            'pedido': pedido,
            'aprovador': aprovador,
            'motivo': pedido.motivo_revisao,
            'url': pedido.get_absolute_url(),
        },
        destinatarios=[pedido.solicitante.email],
    )


def notificar_pedido_aprovado(pedido):
    """Notifica solicitante que o pedido foi aprovado."""
    aprovador = pedido.aprovador.get_full_name() if pedido.aprovador else 'Gerente'

    criar_notificacao(
        usuario=pedido.solicitante,
        titulo=f'✅ Pedido {pedido.numero} APROVADO!',
        tipo='sistema',
        categoria='suprimentos',
        prioridade='media',
        mensagem=(
            f'Seu pedido foi aprovado por {aprovador}.\n'
            f'Uma Solicitação de Compra foi gerada automaticamente '
            f'e encaminhada para a equipe de Suprimentos.'
        ),
        url_destino=pedido.get_absolute_url(),
        icone='bi-check-circle-fill',
    )

    enviar_email_notificacao(
        assunto=f'[Suprimentos] Pedido {pedido.numero} — APROVADO ✅',
        template_texto='notifications/emails/pedido_aprovado.txt',
        template_html='notifications/emails/pedido_aprovado.html',
        contexto={
            'pedido': pedido,
            'aprovador': aprovador,
            'url': pedido.get_absolute_url(),
        },
        destinatarios=[pedido.solicitante.email],
    )


def notificar_pedido_reprovado(pedido):
    """Notifica solicitante que o pedido foi reprovado."""
    aprovador = pedido.aprovador.get_full_name() if pedido.aprovador else 'Gerente'

    criar_notificacao(
        usuario=pedido.solicitante,
        titulo=f'❌ Pedido {pedido.numero} REPROVADO',
        tipo='sistema',
        categoria='suprimentos',
        prioridade='alta',
        mensagem=(
            f'Seu pedido foi reprovado por {aprovador}.\n'
            f'Motivo: {pedido.motivo_reprovacao}'
        ),
        url_destino=pedido.get_absolute_url(),
        icone='bi-x-circle-fill',
    )

    enviar_email_notificacao(
        assunto=f'[Suprimentos] Pedido {pedido.numero} — Reprovado',
        template_texto='notifications/emails/pedido_reprovado.txt',
        template_html='notifications/emails/pedido_reprovado.html',
        contexto={
            'pedido': pedido,
            'aprovador': aprovador,
            'motivo': pedido.motivo_reprovacao,
            'url': pedido.get_absolute_url(),
        },
        destinatarios=[pedido.solicitante.email],
    )


def notificar_pedido_entregue(pedido):
    """Notifica solicitante que o pedido foi marcado como entregue."""
    criar_notificacao(
        usuario=pedido.solicitante,
        titulo=f'📦 Pedido {pedido.numero} — ENTREGUE',
        tipo='sistema',
        categoria='suprimentos',
        prioridade='media',
        mensagem=(
            f'Seu pedido foi marcado como entregue.\n'
            f'Data: {pedido.data_entrega.strftime("%d/%m/%Y") if pedido.data_entrega else "Hoje"}\n'
            f'Confirme o recebimento quando possível.'
        ),
        url_destino=pedido.get_absolute_url(),
        icone='bi-box-seam',
    )


def notificar_pedido_recebido(pedido):
    """Notifica gerente que o pedido foi recebido pelo solicitante."""
    if pedido.aprovador:
        recebedor = pedido.recebedor.get_full_name() if pedido.recebedor else 'Solicitante'
        criar_notificacao(
            usuario=pedido.aprovador,
            titulo=f'✅ Pedido {pedido.numero} — Recebimento confirmado',
            tipo='sistema',
            categoria='suprimentos',
            prioridade='baixa',
            mensagem=f'Recebido por {recebedor} em {pedido.data_recebimento.strftime("%d/%m/%Y %H:%M") if pedido.data_recebimento else "agora"}.',
            url_destino=pedido.get_absolute_url(),
            icone='bi-check2-all',
        )


def notificar_pedido_verba_excedida(pedido, erros):
    """Notifica gerentes sobre estouro de verba."""
    gerentes = User.objects.filter(
        Q(groups__name='Gerente') | Q(is_superuser=True),
        is_active=True,
    ).distinct()

    erros_txt = '\n'.join(erros)

    for gerente in gerentes:
        criar_notificacao(
            usuario=gerente,
            titulo=f'⚠️ Pedido {pedido.numero} — Verba Excedida',
            tipo='sistema',
            categoria='suprimentos',
            prioridade='critica',
            mensagem=(
                f'O pedido de {pedido.solicitante.get_full_name()} '
                f'excede o limite de verba:\n{erros_txt}'
            ),
            url_destino=pedido.get_absolute_url(),
            icone='bi-exclamation-triangle-fill',
        )


# ═════════════════════════════════════════════════════════════════
# NOTIFICAÇÕES — SOLICITAÇÃO DE COMPRA (Workflow Suprimentos)
# ═════════════════════════════════════════════════════════════════

def _get_compradores(filial=None):
    """Retorna usuários do grupo Comprador."""
    qs = User.objects.filter(
        Q(groups__name='Comprador') | Q(groups__name='Administrador') | Q(is_superuser=True),
        is_active=True,
    ).distinct()
    if filial:
        qs = qs.filter(Q(filial_ativa=filial) | Q(is_superuser=True))
    return qs


def _get_gerentes(filial=None):
    """Retorna gerentes da filial."""
    qs = User.objects.filter(
        Q(groups__name='Gerente') | Q(is_superuser=True),
        is_active=True,
    ).distinct()
    if filial:
        qs = qs.filter(Q(filial_ativa=filial) | Q(is_superuser=True))
    return qs


def notificar_solicitacao_criada(solicitacao):
    """Notifica compradores que uma nova solicitação foi gerada."""
    compradores = _get_compradores(solicitacao.filial)
    contrato = f"{solicitacao.contrato.cm} — {solicitacao.contrato.cliente}"
    solicitante = solicitacao.solicitante.get_full_name() or solicitacao.solicitante.username

    for comprador in compradores:
        criar_notificacao(
            usuario=comprador,
            titulo=f'🆕 Nova Solicitação {solicitacao.numero} — Fazer Cotação',
            tipo='sistema',
            categoria='suprimentos',
            prioridade='alta',
            mensagem=(
                f'Solicitante: {solicitante}\n'
                f'Contrato: {contrato}\n'
                f'Material: {solicitacao.descricao_material[:100]}...\n'
                f'Qtd: {solicitacao.quantidade} {solicitacao.get_unidade_medida_display()}\n'
                f'Data necessária: {solicitacao.data_necessaria.strftime("%d/%m/%Y") if solicitacao.data_necessaria else "Não informada"}'
            ),
            url_destino=solicitacao.get_absolute_url(),
            icone='bi-cart-plus',
        )

        enviar_email_notificacao(
            assunto=f'[Suprimentos] Nova Solicitação {solicitacao.numero} — Cotação Necessária',
            template_texto='notifications/emails/solicitacao_criada.txt',
            template_html='notifications/emails/solicitacao_criada.html',
            contexto={
                'solicitacao': solicitacao,
                'solicitante': solicitante,
                'contrato': contrato,
                'comprador': comprador,
                'url': solicitacao.get_absolute_url(),
            },
            destinatarios=[comprador.email],
        )


def notificar_cotacao_enviada(solicitacao):
    """Notifica gerentes que a cotação foi feita e precisa ser validada."""
    gerentes = _get_gerentes(solicitacao.filial)
    comprador = solicitacao.comprador.get_full_name() if solicitacao.comprador else 'Comprador'

    for gerente in gerentes:
        criar_notificacao(
            usuario=gerente,
            titulo=f'📊 Cotação enviada — {solicitacao.numero}',
            tipo='sistema',
            categoria='suprimentos',
            prioridade='alta',
            mensagem=(
                f'{comprador} registrou cotação Nº {solicitacao.numero_cotacao}.\n'
                f'CNPJ: {solicitacao.cnpj_compra}\n'
                f'Tipo NF: {solicitacao.get_tipo_nota_fiscal_display()}\n\n'
                f'Valide a cotação para prosseguir.'
            ),
            url_destino=solicitacao.get_absolute_url(),
            icone='bi-graph-up',
        )

        enviar_email_notificacao(
            assunto=f'[Suprimentos] Cotação {solicitacao.numero} — Validação Necessária',
            template_texto='notifications/emails/cotacao_enviada.txt',
            template_html='notifications/emails/cotacao_enviada.html',
            contexto={
                'solicitacao': solicitacao,
                'comprador': comprador,
                'gerente': gerente,
                'url': solicitacao.get_absolute_url(),
            },
            destinatarios=[gerente.email],
        )


def notificar_cotacao_validada(solicitacao):
    """Notifica comprador que a cotação foi validada."""
    if solicitacao.comprador:
        validador = (
            solicitacao.aprovador_cotacao.get_full_name()
            if solicitacao.aprovador_cotacao else 'Gerente'
        )

        criar_notificacao(
            usuario=solicitacao.comprador,
            titulo=f'✅ Cotação validada — {solicitacao.numero}',
            tipo='sistema',
            categoria='suprimentos',
            prioridade='media',
            mensagem=(
                f'Cotação validada por {validador}.\n'
                f'Prossiga criando o Pedido no Sienge.'
            ),
            url_destino=solicitacao.get_absolute_url(),
            icone='bi-check-circle',
        )

        enviar_email_notificacao(
            assunto=f'[Suprimentos] {solicitacao.numero} — Cotação Validada ✅',
            template_texto='notifications/emails/cotacao_validada.txt',
            template_html='notifications/emails/cotacao_validada.html',
            contexto={
                'solicitacao': solicitacao,
                'validador': validador,
                'url': solicitacao.get_absolute_url(),
            },
            destinatarios=[solicitacao.comprador.email],
        )


def notificar_pedido_sienge_criado(solicitacao):
    """Notifica gerentes que o pedido Sienge foi criado."""
    gerentes = _get_gerentes(solicitacao.filial)
    comprador = solicitacao.comprador.get_full_name() if solicitacao.comprador else 'Comprador'
    valor = f"R$ {solicitacao.valor_pedido:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') if solicitacao.valor_pedido else 'N/D'

    for gerente in gerentes:
        criar_notificacao(
            usuario=gerente,
            titulo=f'📦 Pedido Sienge criado — {solicitacao.numero}',
            tipo='sistema',
            categoria='suprimentos',
            prioridade='alta',
            mensagem=(
                f'{comprador} criou o pedido Nº {solicitacao.numero_pedido_sienge}.\n'
                f'Fornecedor: {solicitacao.fornecedor}\n'
                f'Valor: {valor}\n\n'
                f'Aprove o pedido para prosseguir.'
            ),
            url_destino=solicitacao.get_absolute_url(),
            icone='bi-box-seam',
        )

        enviar_email_notificacao(
            assunto=f'[Suprimentos] Pedido Sienge {solicitacao.numero_pedido_sienge} — Aprovação Necessária',
            template_texto='notifications/emails/pedido_sienge_criado.txt',
            template_html='notifications/emails/pedido_sienge_criado.html',
            contexto={
                'solicitacao': solicitacao,
                'comprador': comprador,
                'valor': valor,
                'gerente': gerente,
                'url': solicitacao.get_absolute_url(),
            },
            destinatarios=[gerente.email],
        )


def notificar_pedido_sienge_aprovado(solicitacao):
    """Notifica comprador que o pedido Sienge foi aprovado."""
    if solicitacao.comprador:
        aprovador = (
            solicitacao.aprovador_pedido.get_full_name()
            if solicitacao.aprovador_pedido else 'Gerente'
        )

        criar_notificacao(
            usuario=solicitacao.comprador,
            titulo=f'✅ Pedido aprovado — {solicitacao.numero}',
            tipo='sistema',
            categoria='suprimentos',
            prioridade='media',
            mensagem=(
                f'Pedido Sienge Nº {solicitacao.numero_pedido_sienge} aprovado por {aprovador}.\n'
                f'Envie o pedido ao fornecedor.'
            ),
            url_destino=solicitacao.get_absolute_url(),
            icone='bi-check-circle-fill',
        )

        enviar_email_notificacao(
            assunto=f'[Suprimentos] {solicitacao.numero} — Pedido Aprovado, Enviar ao Fornecedor',
            template_texto='notifications/emails/pedido_sienge_aprovado.txt',
            template_html='notifications/emails/pedido_sienge_aprovado.html',
            contexto={
                'solicitacao': solicitacao,
                'aprovador': aprovador,
                'url': solicitacao.get_absolute_url(),
            },
            destinatarios=[solicitacao.comprador.email],
        )


def notificar_pedido_enviado_fornecedor(solicitacao):
    """Notifica solicitante + gerente que o pedido foi enviado ao fornecedor."""
    comprador = solicitacao.comprador.get_full_name() if solicitacao.comprador else 'Comprador'
    previsao = (
        solicitacao.data_prevista_entrega.strftime("%d/%m/%Y")
        if solicitacao.data_prevista_entrega else 'Não definida'
    )

    criar_notificacao(
        usuario=solicitacao.solicitante,
        titulo=f'🚚 Pedido enviado — {solicitacao.numero}',
        tipo='sistema',
        categoria='suprimentos',
        prioridade='media',
        mensagem=(
            f'Seu material foi pedido ao fornecedor {solicitacao.fornecedor}.\n'
            f'Previsão de entrega: {previsao}'
        ),
        url_destino=solicitacao.get_absolute_url(),
        icone='bi-truck',
    )

    enviar_email_notificacao(
        assunto=f'[Suprimentos] {solicitacao.numero} — Pedido Enviado ao Fornecedor 🚚',
        template_texto='notifications/emails/pedido_enviado_fornecedor.txt',
        template_html='notifications/emails/pedido_enviado_fornecedor.html',
        contexto={
            'solicitacao': solicitacao,
            'comprador': comprador,
            'previsao': previsao,
            'url': solicitacao.get_absolute_url(),
        },
        destinatarios=[solicitacao.solicitante.email],
    )

    if solicitacao.aprovador_inicial:
        criar_notificacao(
            usuario=solicitacao.aprovador_inicial,
            titulo=f'🚚 Pedido enviado — {solicitacao.numero}',
            tipo='sistema',
            categoria='suprimentos',
            prioridade='baixa',
            mensagem=f'Enviado por {comprador}. Previsão: {previsao}.',
            url_destino=solicitacao.get_absolute_url(),
            icone='bi-truck',
        )


def notificar_entrega_registrada(solicitacao):
    """Notifica solicitante + gerente que a entrega foi realizada."""
    data_entrega = (
        solicitacao.data_entrega_efetiva.strftime("%d/%m/%Y")
        if solicitacao.data_entrega_efetiva else 'Hoje'
    )

    criar_notificacao(
        usuario=solicitacao.solicitante,
        titulo=f'📦 Material entregue — {solicitacao.numero}',
        tipo='sistema',
        categoria='suprimentos',
        prioridade='media',
        mensagem=(
            f'Seu material foi entregue em {data_entrega}.\n'
            f'Fornecedor: {solicitacao.fornecedor}'
        ),
        url_destino=solicitacao.get_absolute_url(),
        icone='bi-box-seam',
    )

    enviar_email_notificacao(
        assunto=f'[Suprimentos] {solicitacao.numero} — Material Entregue 📦',
        template_texto='notifications/emails/entrega_registrada.txt',
        template_html='notifications/emails/entrega_registrada.html',
        contexto={
            'solicitacao': solicitacao,
            'data_entrega': data_entrega,
            'url': solicitacao.get_absolute_url(),
        },
        destinatarios=[solicitacao.solicitante.email],
    )


def notificar_solicitacao_concluida(solicitacao):
    """Notifica todos os envolvidos que a solicitação foi concluída."""
    envolvidos = set()
    envolvidos.add(solicitacao.solicitante)
    if solicitacao.aprovador_inicial:
        envolvidos.add(solicitacao.aprovador_inicial)
    if solicitacao.comprador:
        envolvidos.add(solicitacao.comprador)

    valor_fmt = (
        f"R$ {solicitacao.valor_pedido:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        if solicitacao.valor_pedido else 'N/D'
    )

    for user in envolvidos:
        criar_notificacao(
            usuario=user,
            titulo=f'🎉 Solicitação {solicitacao.numero} CONCLUÍDA!',
            tipo='sistema',
            categoria='suprimentos',
            prioridade='media',
            mensagem=(
                f'NF: {solicitacao.numero_nota_fiscal}\n'
                f'Material: {solicitacao.descricao_material[:80]}...\n'
                f'Fornecedor: {solicitacao.fornecedor}\n'
                f'Valor: {valor_fmt}'
            ),
            url_destino=solicitacao.get_absolute_url(),
            icone='bi-trophy',
        )

    enviar_email_notificacao(
        assunto=f'[Suprimentos] {solicitacao.numero} — CONCLUÍDA ✅🎉',
        template_texto='notifications/emails/solicitacao_concluida.txt',
        template_html='notifications/emails/solicitacao_concluida.html',
        contexto={
            'solicitacao': solicitacao,
            'url': solicitacao.get_absolute_url(),
        },
        destinatarios=[solicitacao.solicitante.email],
    )


def notificar_solicitacao_cancelada(solicitacao):
    """Notifica envolvidos sobre cancelamento."""
    envolvidos = set()
    envolvidos.add(solicitacao.solicitante)
    if solicitacao.aprovador_inicial:
        envolvidos.add(solicitacao.aprovador_inicial)
    if solicitacao.comprador:
        envolvidos.add(solicitacao.comprador)

    for user in envolvidos:
        criar_notificacao(
            usuario=user,
            titulo=f'🚫 Solicitação {solicitacao.numero} CANCELADA',
            tipo='sistema',
            categoria='suprimentos',
            prioridade='alta',
            mensagem=f'Motivo: {solicitacao.motivo_cancelamento}',
            url_destino=solicitacao.get_absolute_url(),
            icone='bi-x-octagon-fill',
        )


# =============================================================================
# SERVIÇO DE E-MAIL (CENTRALIZADO)
# =============================================================================

def enviar_email(assunto, template_texto, template_html, contexto, destinatarios):
    """
    Função genérica e centralizada para enviar e-mails (texto e HTML).

    Args:
        assunto (str): O assunto do e-mail.
        template_texto (str): Caminho para o template de texto plano.
        template_html (str): Caminho para o template HTML.
        contexto (dict): Dicionário com dados para o template.
        destinatarios (list): Lista de strings de e-mails dos destinatários.
    """
    destinatarios_validos = [email for email in destinatarios if email]
    if not destinatarios_validos:
        logger.warning(f"Nenhum destinatário válido fornecido para o e-mail: '{assunto}'.")
        return False

    try:
        corpo_texto = render_to_string(template_texto, contexto)
        corpo_html = render_to_string(template_html, contexto)

        email = EmailMultiAlternatives(
            subject=assunto,
            body=corpo_texto,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=destinatarios_validos,
        )
        email.attach_alternative(corpo_html, "text/html")
        email.send()
        logger.info(f"E-mail '{assunto}' enviado com sucesso para {destinatarios_validos}.")
        return True

    except Exception as e:
        logger.error(f"Falha ao enviar e-mail '{assunto}': {e}", exc_info=True)
        return False

# =============================================================================
# FUNÇÕES ESPECÍFICAS PARA PARTICIPANTES DE TAREFAS
# =============================================================================

def _coletar_interessados_tarefa(tarefa, excluir_usuario=None):
    """
    Retorna set de usuários interessados numa tarefa:
    criador + responsável + participantes, excluindo quem disparou a ação.
    """
    interessados = set()

    if tarefa.usuario:
        interessados.add(tarefa.usuario)
    if tarefa.responsavel:
        interessados.add(tarefa.responsavel)

    for p in tarefa.participantes.all():
        interessados.add(p)

    if excluir_usuario:
        interessados.discard(excluir_usuario)

    return interessados


def notificar_tarefa_criada(tarefa, criador):
    """
    Notifica responsável e participantes que foram incluídos numa nova tarefa.
    Também envia e-mail.
    """
    destinatarios = _coletar_interessados_tarefa(tarefa, excluir_usuario=criador)
    if not destinatarios:
        return []

    url = reverse('tarefas:tarefa_detail', kwargs={'pk': tarefa.pk})
    resultados = []

    for user in destinatarios:
        n = criar_notificacao(
            usuario=user,
            titulo=f'Nova tarefa: {tarefa.titulo[:50]}',
            tipo='tarefa_atribuida',
            categoria='tarefa',
            prioridade='media',
            mensagem=(
                f'Você foi incluído na tarefa "{tarefa.titulo}".\n'
                f'Criada por: {criador.get_full_name() or criador.username}\n'
                f'Prazo: {tarefa.prazo.strftime("%d/%m/%Y %H:%M") if tarefa.prazo else "Não definido"}'
            ),
            url_destino=url,
            icone='bi-plus-circle-fill',
            duplicar=True,
        )
        if n:
            resultados.append(n)

    # E-mail
    emails_destinatarios = [u.email for u in destinatarios if u.email]
    if emails_destinatarios:
        enviar_email(
            assunto=f"Nova tarefa: {tarefa.titulo}",
            template_texto='tarefas/emails/email_nova_tarefa.txt',
            template_html='tarefas/emails/email_nova_tarefa.html',
            contexto={
                'tarefa': tarefa,
                'criador': criador,
                'tarefa_url': url,
            },
            destinatarios=emails_destinatarios,
        )

    return resultados


def notificar_tarefa_comentario(tarefa, autor, texto_comentario):
    """
    Notifica responsável, criador e participantes sobre novo comentário.
    Também envia e-mail.
    """
    destinatarios = _coletar_interessados_tarefa(tarefa, excluir_usuario=autor)
    if not destinatarios:
        return []

    url = reverse('tarefas:tarefa_detail', kwargs={'pk': tarefa.pk})
    texto_curto = texto_comentario[:80] + ('...' if len(texto_comentario) > 80 else '')
    resultados = []

    for user in destinatarios:
        n = criar_notificacao(
            usuario=user,
            titulo=f'Comentário em: {tarefa.titulo[:40]}',
            tipo='tarefa_comentario',
            categoria='tarefa',
            prioridade='baixa',
            mensagem=(
                f'{autor.get_full_name() or autor.username}: "{texto_curto}"'
            ),
            url_destino=url,
            icone='bi-chat-dots-fill',
            duplicar=True,
        )
        if n:
            resultados.append(n)

    # E-mail
    emails_destinatarios = [u.email for u in destinatarios if u.email]
    if emails_destinatarios:
        enviar_email(
            assunto=f"Novo comentário em: {tarefa.titulo}",
            template_texto='tarefas/emails/email_tarefa_comentario.txt',
            template_html='tarefas/emails/email_tarefa_comentario.html',
            contexto={
                'tarefa': tarefa,
                'autor': autor,
                'texto_comentario': texto_comentario,
                'tarefa_url': url,
            },
            destinatarios=emails_destinatarios,
        )

    return resultados


def notificar_tarefa_status_participantes(tarefa, status_anterior, novo_status, alterado_por=None):
    """
    Versão expandida do notificar_tarefa_status que inclui PARTICIPANTES
    além de criador e responsável. Também envia e-mail.
    """
    destinatarios = _coletar_interessados_tarefa(tarefa, excluir_usuario=alterado_por)
    if not destinatarios:
        return []

    url = reverse('tarefas:tarefa_detail', kwargs={'pk': tarefa.pk})
    resultados = []

    # Define prioridade conforme status
    if novo_status in ('concluida', 'Concluída'):
        prioridade = 'media'
        icone = 'bi-check-circle-fill'
    elif novo_status in ('cancelada', 'Cancelada'):
        prioridade = 'alta'
        icone = 'bi-x-circle-fill'
    else:
        prioridade = 'baixa'
        icone = 'bi-arrow-repeat'

    for user in destinatarios:
        n = criar_notificacao(
            usuario=user,
            titulo=f'Status alterado: {tarefa.titulo[:40]}',
            tipo='tarefa_status',
            categoria='tarefa',
            prioridade=prioridade,
            mensagem=f'{status_anterior} → {novo_status}',
            url_destino=url,
            icone=icone,
            duplicar=True,
        )
        if n:
            resultados.append(n)

    # E-mail
    emails_destinatarios = [u.email for u in destinatarios if u.email]
    if emails_destinatarios:
        enviar_email(
            assunto=f"Status da tarefa '{tarefa.titulo}' alterado para {novo_status}",
            template_texto='tarefas/emails/email_notificacao_status.txt',
            template_html='tarefas/emails/email_notificacao_status.html',
            contexto={
                'tarefa': tarefa,
                'status_anterior': status_anterior,
                'novo_status': novo_status,
                'alterado_por': alterado_por,
            },
            destinatarios=emails_destinatarios,
        )

    return resultados


def notificar_tarefa_participante_adicionado(tarefa, novos_participantes, adicionado_por=None):
    """
    Notifica novos participantes quando são adicionados a uma tarefa existente.
    """
    url = reverse('tarefas:tarefa_detail', kwargs={'pk': tarefa.pk})
    resultados = []

    for user in novos_participantes:
        if user == adicionado_por:
            continue

        n = criar_notificacao(
            usuario=user,
            titulo=f'Adicionado à tarefa: {tarefa.titulo[:45]}',
            tipo='tarefa_atribuida',
            categoria='tarefa',
            prioridade='media',
            mensagem=(
                f'Você foi adicionado como participante.\n'
                f'Responsável: {tarefa.responsavel.get_full_name() if tarefa.responsavel else "N/A"}\n'
                f'Prazo: {tarefa.prazo.strftime("%d/%m/%Y %H:%M") if tarefa.prazo else "Não definido"}'
            ),
            url_destino=url,
            icone='bi-person-plus-fill',
            duplicar=True,
        )
        if n:
            resultados.append(n)

    # E-mail
    emails = [u.email for u in novos_participantes if u.email and u != adicionado_por]
    if emails:
        enviar_email(
            assunto=f"Você foi adicionado à tarefa: {tarefa.titulo}",
            template_texto='tarefas/emails/email_nova_tarefa.txt',
            template_html='tarefas/emails/email_nova_tarefa.html',
            contexto={
                'tarefa': tarefa,
                'criador': adicionado_por,
                'tarefa_url': url,
            },
            destinatarios=emails,
        )

    return resultados

def notificar_tarefa_comentario(tarefa, autor, texto_comentario):
    """
    Notifica criador, responsável e participantes sobre novo comentário.
    Cria notificação no sino + envia e-mail.
    """
    destinatarios = _coletar_interessados_tarefa(tarefa, excluir_usuario=autor)
    if not destinatarios:
        return []

    url = reverse('tarefas:tarefa_detail', kwargs={'pk': tarefa.pk})
    texto_curto = texto_comentario[:80] + ('...' if len(texto_comentario) > 80 else '')
    resultados = []

    for user in destinatarios:
        n = criar_notificacao(
            usuario=user,
            titulo=f'Comentário em: {tarefa.titulo[:40]}',
            tipo='tarefa_comentario',
            categoria='tarefa',
            prioridade='baixa',
            mensagem=f'{autor.get_full_name() or autor.username}: "{texto_curto}"',
            url_destino=url,
            icone='bi-chat-dots-fill',
            duplicar=True,
        )
        if n:
            resultados.append(n)

    # E-mail — usa novo template email_tarefa_comentario
    emails_dest = [u.email for u in destinatarios if u.email]
    if emails_dest:
        enviar_email(
            assunto=f"Novo comentário em: {tarefa.titulo}",
            template_texto='tarefas/emails/email_tarefa_comentario.txt',
            template_html='tarefas/emails/email_tarefa_comentario.html',
            contexto={
                'tarefa': tarefa,
                'autor': autor,
                'texto_comentario': texto_comentario,
                'tarefa_url': url,
            },
            destinatarios=emails_dest,
        )

    return resultados


def notificar_tarefa_status_participantes(tarefa, status_anterior, novo_status, alterado_por=None):
    """
    Versão expandida: notifica criador, responsável E participantes
    sobre mudança de status. Cria sino + envia e-mail.
    """
    destinatarios = _coletar_interessados_tarefa(tarefa, excluir_usuario=alterado_por)
    if not destinatarios:
        return []

    url = reverse('tarefas:tarefa_detail', kwargs={'pk': tarefa.pk})
    resultados = []

    # Prioridade e ícone conforme o novo status
    if novo_status in ('concluida', 'Concluída'):
        prioridade = 'media'
        icone = 'bi-check-circle-fill'
    elif novo_status in ('cancelada', 'Cancelada'):
        prioridade = 'alta'
        icone = 'bi-x-circle-fill'
    elif novo_status in ('atrasada', 'Atrasada'):
        prioridade = 'alta'
        icone = 'bi-exclamation-triangle-fill'
    else:
        prioridade = 'baixa'
        icone = 'bi-arrow-repeat'

    for user in destinatarios:
        n = criar_notificacao(
            usuario=user,
            titulo=f'Status alterado: {tarefa.titulo[:40]}',
            tipo='tarefa_status',
            categoria='tarefa',
            prioridade=prioridade,
            mensagem=f'{status_anterior} → {novo_status}',
            url_destino=url,
            icone=icone,
            duplicar=True,
        )
        if n:
            resultados.append(n)

    # E-mail — usa template existente email_notificacao_status
    emails_dest = [u.email for u in destinatarios if u.email]
    if emails_dest:
        enviar_email(
            assunto=f"Status da tarefa '{tarefa.titulo}' alterado para {novo_status}",
            template_texto='tarefas/emails/email_notificacao_status.txt',
            template_html='tarefas/emails/email_notificacao_status.html',
            contexto={
                'tarefa': tarefa,
                'status_anterior': status_anterior,
                'novo_status': novo_status,
                'alterado_por': alterado_por,
                'tarefa_url': url,
            },
            destinatarios=emails_dest,
        )

    return resultados


def notificar_tarefa_participante_adicionado(tarefa, novos_participantes, adicionado_por=None):
    """
    Notifica novos participantes quando são adicionados a uma tarefa existente.
    Cria sino + envia e-mail com template específico.
    """
    url = reverse('tarefas:tarefa_detail', kwargs={'pk': tarefa.pk})
    resultados = []

    for user in novos_participantes:
        if user == adicionado_por:
            continue

        n = criar_notificacao(
            usuario=user,
            titulo=f'Adicionado à tarefa: {tarefa.titulo[:45]}',
            tipo='tarefa_atribuida',
            categoria='tarefa',
            prioridade='media',
            mensagem=(
                f'Você foi adicionado como participante.\n'
                f'Responsável: {tarefa.responsavel.get_full_name() if tarefa.responsavel else "N/A"}\n'
                f'Prazo: {tarefa.prazo.strftime("%d/%m/%Y %H:%M") if tarefa.prazo else "Não definido"}'
            ),
            url_destino=url,
            icone='bi-person-plus-fill',
            duplicar=True,
        )
        if n:
            resultados.append(n)

    # E-mail — usa novo template email_tarefa_participante
    emails_dest = [
        u.email for u in novos_participantes
        if u.email and u != adicionado_por
    ]
    if emails_dest:
        enviar_email(
            assunto=f"Você foi adicionado à tarefa: {tarefa.titulo}",
            template_texto='tarefas/emails/email_tarefa_participante.txt',
            template_html='tarefas/emails/email_tarefa_participante.html',
            contexto={
                'tarefa': tarefa,
                'adicionado_por': adicionado_por,
                'tarefa_url': url,
            },
            destinatarios=emails_dest,
        )

    return resultados

# =============================================================================
# FUNÇÕES ESPECÍFICAS PARA DOCUMENTOS (vencimento)
# =============================================================================

def notificar_documento_a_vencer(documento):
    """
    Notifica o responsável que um documento está próximo do vencimento.
    Prioridade aumenta conforme se aproxima do prazo.
    """
    if not documento.responsavel or not documento.data_vencimento:
        return None

    dias_restantes = documento.dias_para_vencer
    if dias_restantes is None:
        return None

    # Escala de prioridade
    if dias_restantes <= 7:
        prioridade = 'critica'
        icone = 'bi-exclamation-triangle-fill'
    elif dias_restantes <= 15:
        prioridade = 'alta'
        icone = 'bi-exclamation-circle-fill'
    else:
        prioridade = 'media'
        icone = 'bi-calendar-event'

    url = reverse('documentos:lista')
    data_venc = documento.data_vencimento.strftime('%d/%m/%Y')

    n = criar_notificacao(
        usuario=documento.responsavel,
        titulo=f'📄 Documento vence em {dias_restantes} dias: {documento.nome[:40]}',
        tipo='sistema',
        categoria='sistema',
        prioridade=prioridade,
        mensagem=(
            f'Tipo: {documento.get_tipo_display()}\n'
            f'Vencimento: {data_venc}\n'
            f'Dias restantes: {dias_restantes}'
        ),
        url_destino=url,
        icone=icone,
    )

    # E-mail (opcional, só para prioridade alta/crítica para não encher a caixa)
    if prioridade in ('alta', 'critica') and documento.responsavel.email:
        enviar_email(
            assunto=f'[Documentos] {documento.nome} vence em {dias_restantes} dias',
            template_texto='documentos/emails/documento_a_vencer.txt',
            template_html='documentos/emails/documento_a_vencer.html',
            contexto={
                'documento': documento,
                'responsavel': documento.responsavel,
                'dias_restantes': dias_restantes,
                'data_vencimento': data_venc,
                'url': url,
            },
            destinatarios=[documento.responsavel.email],
        )

    return n


def notificar_documento_vencido(documento):
    """
    Notifica o responsável que um documento VENCEU.
    Prioridade crítica + e-mail sempre.
    """
    if not documento.responsavel or not documento.data_vencimento:
        return None

    url = reverse('documentos:lista')
    data_venc = documento.data_vencimento.strftime('%d/%m/%Y')
    dias_atraso = (timezone.now().date() - documento.data_vencimento).days

    n = criar_notificacao(
        usuario=documento.responsavel,
        titulo=f'🚨 Documento VENCIDO: {documento.nome[:45]}',
        tipo='sistema',
        categoria='sistema',
        prioridade='critica',
        mensagem=(
            f'Tipo: {documento.get_tipo_display()}\n'
            f'Venceu em: {data_venc}\n'
            f'Dias de atraso: {dias_atraso}\n\n'
            f'Providencie a renovação o quanto antes!'
        ),
        url_destino=url,
        icone='bi-x-octagon-fill',
    )

    if documento.responsavel.email:
        enviar_email(
            assunto=f'[URGENTE] Documento VENCIDO: {documento.nome}',
            template_texto='documentos/emails/documento_vencido.txt',
            template_html='documentos/emails/documento_vencido.html',
            contexto={
                'documento': documento,
                'responsavel': documento.responsavel,
                'dias_atraso': dias_atraso,
                'data_vencimento': data_venc,
                'url': url,
            },
            destinatarios=[documento.responsavel.email],
        )

    return n


# Alias para compatibilidade com imports antigos
enviar_email_tarefa = enviar_email
enviar_email_pgr = enviar_email
enviar_email_chat = enviar_email
enviar_email_sistema = enviar_email
enviar_email_notificacao = enviar_email
