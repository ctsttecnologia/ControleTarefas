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
import logging
from django.contrib.auth.decorators import login_required


logger = logging.getLogger('uploads')




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
                    import storages.backends.gcloud as gcloud_module
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
