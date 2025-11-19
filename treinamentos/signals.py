
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
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
    
    # Descomente quando tiver sua função de e-mail:
    # enviar_email_async.delay(
    #     assunto=assunto,
    #     template='emails/template_assinatura.html', # Crie este template
    #     contexto={'nome': nome_destinatario, 'link': link_assinatura},
    #     destinatarios=[email_destinatario]
    # )


@receiver(post_save, sender=Treinamento)
def disparar_coleta_de_assinaturas(sender, instance, created, **kwargs):
    """
    Dispara o envio de links de assinatura quando um treinamento é
    marcado como 'Finalizado' (F).
    """
    # Só executa se:
    # 1. O status for 'Finalizado'
    # 2. O curso emitir certificado
    # 3. Os links ainda NÃO foram solicitados
    if (instance.status == 'F' and 
        instance.tipo_curso.certificado and 
        not instance.assinaturas_solicitadas):
        
        print(f"Iniciando coleta de assinaturas para: {instance.nome}")
        base_url = settings.SITE_URL # Ex: "https_://meusistema.com"

        # 1. Criar e enviar para o RESPONSÁVEL (Instrutor)
        try:
            responsavel = instance.responsavel
            if responsavel:
                assinatura_resp, created_resp = Assinatura.objects.get_or_create(
                    treinamento_responsavel=instance,
                    defaults={
                        'nome_assinante': responsavel.get_full_name(),
                        'documento_assinante': getattr(responsavel, 'cpf', 'Não informado') # Assumindo que seu User tem 'cpf'
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
