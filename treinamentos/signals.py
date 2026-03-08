
# treinamentos/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import Treinamento, Assinatura


# TODO: Implemente sua própria função de envio de e-mail
# from core.utils import enviar_email_async

def enviar_link_assinatura(email_destinatario, nome_destinatario, link_assinatura):
    """
    Função placeholder para enviar o e-mail.
    Substitua pela sua implementação real (ex: usando Celery).
    """
    assunto = "Coleta de Assinatura para Certificado de Treinamento"
    mensagem = f"""
    Olá, {nome_destinatario},

    O treinamento que você participou (ou pelo qual foi responsável) foi finalizado.
    Por favor, acesse o link abaixo para registrar sua assinatura digital
    para a emissão do certificado:

    {link_assinatura}

    Obrigado.
    """
    print(f"--- SIMULANDO ENVIO DE E-MAIL PARA: {email_destinatario} ---")
    print(f"Link: {link_assinatura}")
    print("--- FIM DA SIMULAÇÃO ---")


@receiver(post_save, sender=Treinamento)
def disparar_coleta_de_assinaturas(sender, instance, created, **kwargs):
    """
    Dispara o envio de links de assinatura quando um treinamento é
    marcado como 'Finalizado' (F).
    """
    if (instance.status == 'F' and
        instance.tipo_curso.certificado and
        not instance.assinaturas_solicitadas):

        print(f"Iniciando coleta de assinaturas para: {instance.nome}")
        base_url = settings.SITE_URL

        # 1. Criar e enviar para o RESPONSÁVEL (Instrutor)
        try:
            responsavel = instance.responsavel
            if responsavel:
                assinatura_resp, created_resp = Assinatura.objects.get_or_create(
                    treinamento_responsavel=instance,
                    defaults={
                        'nome_assinante': responsavel.get_full_name(),
                        'documento_assinante': getattr(responsavel, 'cpf', 'Não informado')
                    }
                )

                if created_resp or not assinatura_resp.esta_assinada:
                    link_resp = base_url + reverse('treinamentos:pagina_assinatura',
                                                   kwargs={'token': assinatura_resp.token_acesso})
                    enviar_link_assinatura(responsavel.email, responsavel.get_full_name(), link_resp)

        except Exception as e:
            print(f"Erro ao gerar assinatura para responsável: {e}")

        # 2. Criar e enviar para todos os PARTICIPANTES PRESENTES
        participantes_presentes = instance.participantes.filter(presente=True)
        for p in participantes_presentes:
            try:
                assinatura_part, created_part = Assinatura.objects.get_or_create(
                    participante=p,
                    defaults={
                        'nome_assinante': p.funcionario.get_full_name(),
                        'documento_assinante': getattr(p.funcionario, 'cpf', 'Não informado')
                    }
                )

                if created_part or not assinatura_part.esta_assinada:
                    link_part = base_url + reverse('treinamentos:pagina_assinatura',
                                                   kwargs={'token': assinatura_part.token_acesso})
                    enviar_link_assinatura(p.funcionario.email, p.funcionario.get_full_name(), link_part)

            except Exception as e:
                print(f"Erro ao gerar assinatura para participante {p.funcionario.email}: {e}")

        # Marca que os links foram enviados para não duplicar
        instance.assinaturas_solicitadas = True
        instance.save(update_fields=['assinaturas_solicitadas'])


# =============================================================================
# SIGNAL: Emissão automática de Certificado EAD ao aprovar
# =============================================================================
from .models import MatriculaEAD, CertificadoEAD


@receiver(post_save, sender=MatriculaEAD)
def emitir_certificado_ead_ao_aprovar(sender, instance, **kwargs):
    """
    Quando a matrícula é marcada como APROVADO, gera automaticamente
    o registro do CertificadoEAD (o PDF é gerado on-demand na view).
    """
    if instance.status != MatriculaEAD.Status.APROVADO:
        return

    # Já tem certificado? Não duplicar
    if CertificadoEAD.objects.filter(matricula=instance).exists():
        return

    try:
        funcionario = instance.funcionario
        curso = instance.curso
        tipo_curso = curso.tipo_curso

        # Calcula validade
        validade = None
        if tipo_curso and tipo_curso.validade_meses:
            validade = (timezone.now() + timedelta(
                days=tipo_curso.validade_meses * 30
            )).date()

        CertificadoEAD.objects.create(
            matricula=instance,
            nome_funcionario=funcionario.nome_completo,
            cpf_funcionario=funcionario.matricula or '',
            nome_curso=curso.titulo,
            nome_tipo_curso=tipo_curso.nome if tipo_curso else curso.titulo,
            carga_horaria_exigida=curso.carga_horaria_total,
            carga_horaria_cumprida=instance.carga_horaria_cumprida_horas,
            nota=instance.nota_final,
            nome_instrutor=curso.instrutor_nome or '',
            data_validade=validade,
            filial=instance.filial,
            emitido_por=instance.matriculado_por,
        )
        print(f"✅ Certificado EAD emitido para {funcionario.nome_completo} - {curso.titulo}")

    except Exception as e:
        print(f"❌ Erro ao emitir certificado EAD: {e}")
        import traceback
        traceback.print_exc()
