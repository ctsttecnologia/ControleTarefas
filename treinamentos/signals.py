
# treinamentos/signals.py
# treinamentos/signals.py
import logging
from datetime import timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone

from notifications.services import criar_notificacao
from .models import Assinatura, CertificadoEAD, MatriculaEAD, Treinamento

logger = logging.getLogger(__name__)


def _enviar_link(user, assinatura, treinamento):
    link = settings.SITE_URL + reverse('treinamentos:pagina_assinatura',
                                       kwargs={'token': assinatura.token_acesso})
    criar_notificacao(
        usuario=user, titulo=f'Assine seu certificado: {treinamento.nome[:50]}',
        tipo='sistema', categoria='sistema', prioridade='alta',
        url_destino=link, icone='bi-pen',
    )
    if user.email:
        send_mail(
            'Assinatura de certificado de treinamento',
            f'Olá, {user.get_first_name() if hasattr(user, "get_first_name") else user.first_name}.\n\n'
            f'O treinamento "{treinamento.nome}" foi finalizado. Assine em até '
            f'{Assinatura.VALIDADE_DIAS} dias:\n{link}\n',
            settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True,
        )


@receiver(post_save, sender=Treinamento)
def disparar_coleta_de_assinaturas(sender, instance, **kwargs):
    if instance.status != 'F' or not instance.tipo_curso.certificado or instance.assinaturas_solicitadas:
        return

    def _executar():
        alvos = []
        if instance.responsavel:
            a, _ = Assinatura.objects.get_or_create(
                treinamento_responsavel=instance,
                defaults={'nome_assinante': instance.responsavel.get_full_name()})
            alvos.append((instance.responsavel, a))
        for p in instance.participantes.filter(presente=True).select_related('funcionario'):
            a, _ = Assinatura.objects.get_or_create(
                participante=p, defaults={'nome_assinante': p.funcionario.get_full_name()})
            alvos.append((p.funcionario, a))
        for user, a in alvos:
            if not a.esta_assinada:
                try:
                    _enviar_link(user, a, instance)
                except Exception:
                    logger.exception('Falha ao enviar link de assinatura (user=%s)', user.pk)
        Treinamento.objects.filter(pk=instance.pk).update(assinaturas_solicitadas=True)

    transaction.on_commit(_executar)


@receiver(post_save, sender=MatriculaEAD)
def emitir_certificado_ead_ao_aprovar(sender, instance, **kwargs):
    if instance.status != MatriculaEAD.Status.APROVADO or not instance.pode_emitir_certificado:
        return
    if CertificadoEAD.objects.filter(matricula=instance).exists():
        return
    f, curso = instance.funcionario, instance.curso
    try:
        CertificadoEAD.objects.create(
            matricula=instance,
            nome_funcionario=getattr(f, 'nome_completo', str(f)),
            cpf_funcionario=getattr(f, 'cpf', '') or '',  
            nome_curso=curso.titulo,
            nome_tipo_curso=curso.tipo_curso.nome if curso.tipo_curso else '',
            carga_horaria_exigida=curso.carga_horaria_total,
            carga_horaria_cumprida=instance.carga_horaria_cumprida_horas,
            nota=instance.nota_final,
            nome_instrutor=curso.instrutor_nome or '',
            filial=instance.filial,
            emitido_por=instance.matriculado_por,
        )  # data_validade é calculada no save() do model
        criar_notificacao(
            usuario=f.usuario, titulo=f'🎓 Certificado disponível: {curso.titulo[:50]}',
            categoria='sistema', prioridade='media',
            url_destino=reverse('treinamentos:ead_meus_cursos'), icone='bi-award',
        )
    except Exception:
        logger.exception('Erro ao emitir certificado EAD (matrícula %s)', instance.pk)
