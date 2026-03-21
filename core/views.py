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

from usuario.models import Filial


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
                    from storages.backends.gcloud import GoogleCloudStorage

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
