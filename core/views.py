# core/views.py
import mimetypes

from django.conf import settings
from django.db import close_old_connections
from django.shortcuts import redirect, render, get_object_or_404
from django.views import View
from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.http import FileResponse, Http404, HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.apps import apps
from django.views.generic import TemplateView
from usuario.models import Filial
import logging
from django.contrib.auth.decorators import login_required
from django.utils import timezone
import json
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .models import TokenAssinaturaRemota



logger = logging.getLogger(__name__)


class SecureFileDownloadView(LoginRequiredMixin, View):
    """
    View genérica para servir qualquer arquivo de mídia de forma segura.
    Compatível com qualquer storage backend (local, GCS, S3, etc.)
    """

    def get(self, request, app, model, pk, field):
        # 1. Obter o model dinamicamente
        try:
            ModelClass = apps.get_model(app, model)
        except LookupError:
            raise Http404("Recurso não encontrado.")

        # 2. Obter o objeto
        obj = get_object_or_404(ModelClass, pk=pk)

        # 3. Obter o campo de arquivo
        if not hasattr(obj, field):
            raise Http404("Campo não encontrado.")

        file_field = getattr(obj, field)
        if not file_field:
            raise Http404("Nenhum arquivo associado.")

        # 4. Verificar se o arquivo existe no storage
        try:
            exists = file_field.storage.exists(file_field.name)
        except Exception:
            exists = False

        if not exists:
            # ══════════════════════════════════════════════
            # FALLBACK: busca no GCS quando o storage local
            # não encontra o arquivo (dev apontando para produção)
            # ══════════════════════════════════════════════
            if settings.DEBUG:
                try:
                    import importlib
                    gcloud_module = importlib.import_module('storages.backends.gcloud')
                    GoogleCloudStorage = gcloud_module.GoogleCloudStorage

                    bucket_name = getattr(settings, 'GS_BUCKET_NAME', None)
                    credentials = getattr(settings, 'GS_CREDENTIALS', None)

                    if bucket_name:
                        gcs = GoogleCloudStorage(
                            bucket_name=bucket_name,
                            credentials=credentials,  # None = usa ADC
                        )

                        # Tenta caminho direto, depois com prefixo media/
                        for name in [file_field.name, f'media/{file_field.name}']:
                            if gcs.exists(name):
                                return HttpResponseRedirect(gcs.url(name))
                except (ImportError, Exception):
                    pass

            raise Http404("Arquivo não encontrado no servidor.")

        # 5. Extrair o nome do arquivo
        filename = file_field.name.split('/')[-1]

        # 6. Determinar Content-Type
        content_type, _ = mimetypes.guess_type(filename)
        if content_type is None:
            content_type = 'application/octet-stream'

        # 7. Servir o arquivo (compatível com qualquer storage)
        try:
            file_obj = file_field.open('rb')
        except Exception:
            raise Http404("Erro ao acessar o arquivo.")

        response = FileResponse(
            file_obj,
            content_type=content_type,
        )

        # PDFs e imagens abrem inline; outros fazem download
        inline_types = [
            'application/pdf',
            'image/jpeg', 'image/png', 'image/gif',
            'image/webp', 'image/svg+xml',
        ]
        if content_type in inline_types:
            response['Content-Disposition'] = f'inline; filename="{filename}"'
        else:
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response


# ============================================================
# VIEWS DE SELEÇÃO DE FILIAL
# ============================================================

class SelecionarFilialView(UserPassesTestMixin, View):

    def test_func(self):
        return self.request.user.is_authenticated

    def post(self, request, *args, **kwargs):
        filial_id = request.POST.get('filial_id')

        if filial_id:
            try:
                if filial_id == '0':
                    if 'active_filial_id' in request.session:
                        del request.session['active_filial_id']
                    messages.success(request, "Visão alterada para Todas as Filiais.")
                else:
                    filial = Filial.objects.get(pk=filial_id)
                    request.session['active_filial_id'] = filial.id
                    messages.success(request, f"Visão alterada para a filial: {filial.nome}.")

            except (Filial.DoesNotExist, ValueError):
                messages.error(request, "A filial selecionada é inválida ou ocorreu um erro.")
        else:
            messages.warning(request, "Nenhuma filial foi selecionada.")

        return redirect(request.META.get('HTTP_REFERER', 'ferramentas:dashboard'))


class SetFilialView(View):
    def post(self, request, *args, **kwargs):
        filial_id = request.POST.get('filial_id')
        if filial_id:
            request.session['filial_id'] = filial_id

        return redirect(request.META.get('HTTP_REFERER', '/'))


# ============================================================
# VIEWS DE ERRO PERSONALIZADAS
# ============================================================

def error_400_view(request, exception=None):
    if not hasattr(request, 'user'):
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
    return render(request, 'errors/400.html', status=400)


def error_403_view(request, exception=None):
    if not hasattr(request, 'user'):
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
    return render(request, 'errors/403.html', status=403)


def error_404_view(request, exception=None):
    try:
        close_old_connections()
        return render(request, 'errors/404.html', status=404)
    except Exception:
        return HttpResponse(
            '<h1>404 - Página não encontrada</h1>',
            status=404,
            content_type='text/html',
        )


def error_500_view(request):
    try:
        close_old_connections()
        return render(request, 'errors/500.html', status=500)
    except Exception:
        # Fallback absoluto — sem template, sem DB
        return HttpResponse(
            '<h1>500 - Erro interno</h1>'
            '<p>O servidor encontrou um erro. Tente novamente em instantes.</p>',
            status=500,
            content_type='text/html',
        )


def error_503_view(request, exception=None):
    if not hasattr(request, 'user'):
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
    return render(request, 'errors/503.html', status=503)

# ============================================================
#  VIEW MIXIN DE UPLOAD SEGURO
# ============================================================

class SecureUploadViewMixin(LoginRequiredMixin):
    """
    Mixin para views de upload.

    Uso:
        class LaudoCreateView(SecureUploadViewMixin, CreateView):
            UPLOAD_APP = 'ltcat'
            model = LaudoLTCAT
            form_class = LaudoForm
    """

    UPLOAD_APP = 'default'

    def form_valid(self, form):
        obj = form.save(commit=False)

        if hasattr(obj, 'uploaded_by'):
            obj.uploaded_by = self.request.user

        obj.save()
        form.save_m2m()

        logger.info(
            f'[UPLOAD][{self.UPLOAD_APP}] '
            f'Usuário: {self.request.user.username} | '
            f'Arquivo: {getattr(obj, "original_filename", "N/A")} | '
            f'Tamanho: {getattr(obj, "file_size", 0)} bytes'
        )

        messages.success(self.request, '✅ Arquivo enviado com sucesso!')
        return super().form_valid(form)

    def form_invalid(self, form):
        logger.warning(
            f'[UPLOAD FALHOU][{self.UPLOAD_APP}] '
            f'Usuário: {self.request.user.username} | '
            f'Erros: {form.errors.as_text()}'
        )
        messages.error(self.request, '❌ Erro no upload. Verifique o arquivo.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context.get('form')
        if form and hasattr(form, 'get_upload_config_display'):
            context['upload_config'] = form.get_upload_config_display()
        return context


@login_required
def sem_funcionario_view(request):
    """
    Tela amigável exibida quando o usuário autenticado tenta acessar
    um módulo que exige vínculo com Funcionario, mas não possui.
    """
    modulo = request.GET.get('modulo', '')
    return render(request, 'errors/sem_funcionario.html', {'modulo': modulo}, status=403)


class PoliticaPrivacidadeView(TemplateView):
    template_name = "core/politica_privacidade.html"


def _obter_token_valido(token):
    """Retorna o token_obj se existir e estiver válido, senão None."""
    token_obj = TokenAssinaturaRemota.objects.select_related('content_type').filter(token=token).first()
    if token_obj and token_obj.valido:
        return token_obj
    return None


@method_decorator(login_required, name='dispatch')
class GerarLinkAssinaturaView(View):
    """
    Gera (ou reaproveita) um token de assinatura remota para qualquer objeto.
    Uso via URL: /core/assinatura-remota/gerar/<app_label>/<model_name>/<object_id>/
    """

    def post(self, request, app_label, model_name, object_id):
        content_type = get_object_or_404(ContentType, app_label=app_label, model=model_name)
        modelo = content_type.model_class()
        objeto = get_object_or_404(modelo, pk=object_id)

        if hasattr(objeto, 'pode_ser_assinado') and not objeto.pode_ser_assinado():
            return JsonResponse({
                'ok': False,
                'erro': 'Este registro já foi assinado ou não pode ser assinado neste momento.',
            }, status=400)

        # Invalida tokens antigos ainda não usados para o mesmo objeto
        TokenAssinaturaRemota.objects.filter(
            content_type=content_type,
            object_id=object_id,
            usado_em__isnull=True,
        ).update(usado_em=timezone.now())

        token_obj = TokenAssinaturaRemota.objects.create(
            content_type=content_type,
            object_id=object_id,
            criado_por=request.user,
        )

        link = request.build_absolute_uri(
            reverse('core:assinatura_remota', kwargs={'token': str(token_obj.token)})
        )

        logger.info(
            f'[ASSINATURA REMOTA] Token gerado para {app_label}.{model_name} '
            f'(id={object_id}) por {request.user.username}'
        )

        return JsonResponse({
            'ok': True,
            'link': link,
            'expira_em': token_obj.expira_em.isoformat(),
        })


class AssinaturaRemotaView(View):
    """
    Tela pública (sem login) para exibir o form de assinatura ou processar o POST.
    """

    def get(self, request, token):
        token_obj = _obter_token_valido(token)
        if not token_obj:
            return render(request, 'core/assinatura_remota_erro.html')

        contexto = {
            'token': token,
            'objeto': token_obj.conteudo,
            'tipo_objeto': token_obj.content_type.model,
        }
        return render(request, 'core/assinatura_remota_form.html', contexto)

    def post(self, request, token):
        token_obj = _obter_token_valido(token)
        if not token_obj:
            return render(request, 'core/assinatura_remota_erro.html')

        objeto = token_obj.conteudo
        ip = request.META.get('REMOTE_ADDR')

        # ── Consentimento LGPD é obrigatório (defesa server-side) ──
        if request.POST.get('consentimento_lgpd') != 'on':
            contexto = {
                'token': token,
                'objeto': objeto,
                'tipo_objeto': token_obj.content_type.model,
                'erro': 'É necessário concordar com o tratamento dos dados (LGPD) para assinar.',
            }
            return render(request, 'core/assinatura_remota_form.html', contexto)

        # ── Verificação de status de assinatura (agora "objeto" já existe) ──
        if hasattr(objeto, 'pode_ser_assinado') and not objeto.pode_ser_assinado():
                    contexto = {
                        'token': token,
                        'objeto': objeto,
                        'tipo_objeto': token_obj.content_type.model,
                        'erro': 'Este registro já foi assinado anteriormente.',
                    }
                    return render(request, 'core/assinatura_remota_form.html', contexto)
        

        if not hasattr(objeto, 'assinar_remotamente'):
            logger.warning(
                f'[ASSINATURA REMOTA] Objeto {token_obj.content_type.model} '
                f'não possui método assinar_remotamente (token={token})'
            )
            return render(request, 'core/assinatura_remota_erro.html')

        try:
            objeto.assinar_remotamente(
                post_data=request.POST,
                files_data=request.FILES,
                ip=ip,
            )
        except Exception:
            logger.exception(
                f'[ASSINATURA REMOTA] Falha ao assinar objeto '
                f'{token_obj.content_type.model} (id={token_obj.object_id}, token={token})'
            )
            return render(request, 'core/assinatura_remota_erro.html')

        token_obj.marcar_utilizado(ip=ip)

        logger.info(
            f'[ASSINATURA REMOTA] Assinatura concluída para '
            f'{token_obj.content_type.model} (id={token_obj.object_id}), IP={ip}'
        )

        return render(request, 'core/assinatura_remota_sucesso.html')
