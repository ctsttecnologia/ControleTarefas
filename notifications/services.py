
# notifications/services.py

"""
Serviço central para criação de notificações e envio de e-mails.
Todos os módulos devem usar estas funções.
"""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

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


# =============================================================================
# FUNÇÕES ESPECÍFICAS PARA SUPRIMENTOS
# =============================================================================

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
        # 1º: Tenta por filiais_permitidas (ManyToMany)
        gerentes_filial = gerentes.filter(filiais_permitidas=filial)
        if gerentes_filial.exists():
            return gerentes_filial

        # 2º: Fallback por filial_ativa (FK)
        gerentes_filial = gerentes.filter(filial_ativa=filial)
        if gerentes_filial.exists():
            return gerentes_filial

    # Último fallback: todos os gerentes + superusers
    return (gerentes | User.objects.filter(
        is_superuser=True, is_active=True
    )).distinct()



def notificar_pedido_pendente(pedido):
    """
    RASCUNHO → PENDENTE: Notifica gerentes da filial do contrato.
    """
    url = reverse('suprimentos:pedido_detalhe', kwargs={'pk': pedido.pk})
    filial = pedido.contrato.filial
    gerentes = _obter_gerentes_da_filial(filial)

    valor_str = f'R$ {pedido.valor_total:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

    return criar_notificacao_para_grupo(
        usuarios=gerentes,
        titulo=f'Pedido {pedido.numero} aguarda aprovação',
        tipo='pedido_pendente',
        categoria='suprimentos',
        prioridade='alta',
        mensagem=(
            f'Solicitante: {pedido.solicitante.get_full_name() or pedido.solicitante.username}\n'
            f'Contrato: {pedido.contrato.cm} — {pedido.contrato.cliente}\n'
            f'Valor total: {valor_str}'
        ),
        url_destino=url,
        icone='bi-cart-check',
    )


def notificar_pedido_aprovado(pedido):
    """
    PENDENTE → APROVADO: Notifica o solicitante.
    """
    url = reverse('suprimentos:pedido_detalhe', kwargs={'pk': pedido.pk})

    return criar_notificacao(
        usuario=pedido.solicitante,
        titulo=f'Pedido {pedido.numero} aprovado ✅',
        tipo='pedido_aprovado',
        categoria='suprimentos',
        prioridade='media',
        mensagem=(
            f'Aprovado por: {pedido.aprovador.get_full_name() or pedido.aprovador.username}\n'
            f'Contrato: {pedido.contrato.cm}'
        ),
        url_destino=url,
        icone='bi-check-circle-fill',
        duplicar=True,
    )


def notificar_pedido_reprovado(pedido):
    """
    PENDENTE → REPROVADO: Notifica o solicitante (prioridade alta).
    """
    url = reverse('suprimentos:pedido_detalhe', kwargs={'pk': pedido.pk})

    motivo = pedido.motivo_reprovacao[:100] if pedido.motivo_reprovacao else 'Sem motivo informado'

    return criar_notificacao(
        usuario=pedido.solicitante,
        titulo=f'Pedido {pedido.numero} reprovado ❌',
        tipo='pedido_reprovado',
        categoria='suprimentos',
        prioridade='alta',
        mensagem=(
            f'Reprovado por: {pedido.aprovador.get_full_name() or pedido.aprovador.username}\n'
            f'Motivo: {motivo}'
        ),
        url_destino=url,
        icone='bi-x-circle-fill',
        duplicar=True,
    )


def notificar_pedido_entregue(pedido):
    """
    APROVADO → ENTREGUE: Notifica o solicitante para confirmar recebimento.
    """
    url = reverse('suprimentos:pedido_detalhe', kwargs={'pk': pedido.pk})

    return criar_notificacao(
        usuario=pedido.solicitante,
        titulo=f'Pedido {pedido.numero} entregue 📦',
        tipo='pedido_entregue',
        categoria='suprimentos',
        prioridade='media',
        mensagem=(
            f'Contrato: {pedido.contrato.cm}\n'
            f'Confirme o recebimento dos materiais.'
        ),
        url_destino=url,
        icone='bi-box-seam-fill',
        duplicar=True,
    )


def notificar_pedido_recebido(pedido):
    """
    ENTREGUE → RECEBIDO: Notifica gerentes que o recebimento foi confirmado.
    """
    url = reverse('suprimentos:pedido_detalhe', kwargs={'pk': pedido.pk})
    filial = pedido.contrato.filial
    gerentes = _obter_gerentes_da_filial(filial)

    recebedor_nome = ''
    if pedido.recebedor:
        recebedor_nome = pedido.recebedor.get_full_name() or pedido.recebedor.username

    return criar_notificacao_para_grupo(
        usuarios=gerentes,
        titulo=f'Pedido {pedido.numero} recebido ✅',
        tipo='pedido_recebido',
        categoria='suprimentos',
        prioridade='baixa',
        mensagem=(
            f'Recebido por: {recebedor_nome}\n'
            f'Contrato: {pedido.contrato.cm}\n'
            f'Entrada no estoque processada automaticamente.'
        ),
        url_destino=url,
        icone='bi-clipboard-check-fill',
    )


def notificar_pedido_verba_excedida(pedido, erros_verba):
    """
    Notifica gerentes quando um pedido é enviado excedendo a verba.
    Chamada como alerta (não bloqueia o envio).
    """
    url = reverse('suprimentos:pedido_detalhe', kwargs={'pk': pedido.pk})
    filial = pedido.contrato.filial
    gerentes = _obter_gerentes_da_filial(filial)

    detalhes = '\n'.join(f'⚠ {erro}' for erro in erros_verba)

    return criar_notificacao_para_grupo(
        usuarios=gerentes,
        titulo=f'Pedido {pedido.numero} excede verba!',
        tipo='pedido_verba_excedida',
        categoria='suprimentos',
        prioridade='critica',
        mensagem=(
            f'Solicitante: {pedido.solicitante.get_full_name() or pedido.solicitante.username}\n'
            f'Contrato: {pedido.contrato.cm}\n'
            f'{detalhes}'
        ),
        url_destino=url,
        icone='bi-exclamation-diamond-fill',
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
            template_texto='tarefas/emails/email_tarefa_criada.txt',
            template_html='tarefas/emails/email_tarefa_criada.html',
            contexto={
                'tarefa': tarefa,
                'criador': criador,
                'url': url,
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
                'url': url,
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
            template_texto='tarefas/emails/email_tarefa_criada.txt',
            template_html='tarefas/emails/email_tarefa_criada.html',
            contexto={
                'tarefa': tarefa,
                'criador': adicionado_por,
                'url': url,
            },
            destinatarios=emails,
        )

    return resultados

# ═══════════════════════════════════════════════════════════════════════
# FUNÇÕES PARA PARTICIPANTES DE TAREFAS (sino + e-mail)
# ═══════════════════════════════════════════════════════════════════════

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
    Cria notificação no sino + envia e-mail usando template existente.
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
                f'Criada por: {criador.get_full_name() or criador.username}\n'
                f'Prazo: {tarefa.prazo.strftime("%d/%m/%Y %H:%M") if tarefa.prazo else "Não definido"}'
            ),
            url_destino=url,
            icone='bi-plus-circle-fill',
            duplicar=True,
        )
        if n:
            resultados.append(n)

    # E-mail — usa template existente email_nova_tarefa
    emails_dest = [u.email for u in destinatarios if u.email]
    if emails_dest:
        enviar_email(
            assunto=f"Nova tarefa atribuída: {tarefa.titulo}",
            template_texto='tarefas/emails/email_nova_tarefa.txt',
            template_html='tarefas/emails/email_nova_tarefa.html',
            contexto={
                'tarefa': tarefa,
                'criador': criador,
                'tarefa_url': url,
            },
            destinatarios=emails_dest,
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


# Alias para compatibilidade com imports antigos
enviar_email_tarefa = enviar_email
enviar_email_pgr = enviar_email
enviar_email_chat = enviar_email
enviar_email_sistema = enviar_email
enviar_email_notificacao = enviar_email
