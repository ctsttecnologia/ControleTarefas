# core/mixins.py
from django.db.models import Q, QuerySet
from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.core.exceptions import PermissionDenied
from .forms import ChangeFilialForm
from django.contrib.auth.mixins import AccessMixin, PermissionRequiredMixin
from ferramentas.models import Atividade
from django.http import HttpResponse
import os
import uuid
from core.magic_utils import get_mime_type
from io import BytesIO
from django.db import models
from django.conf import settings
from django.utils import timezone
from PIL import Image
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.exceptions import ValidationError
from core.validators import SecureFileValidator
import io



# =============================================================================
# == MIXINS DE PERMISSÃO E ESCOPO (A SUA ARQUITETURA DE 3 NÍVEIS)
# =============================================================================

class SSTPermissionMixin(PermissionRequiredMixin):
    """
    NÍVEL 1 (Página):
    Mixin que herda do PermissionRequiredMixin do Django, mas customiza
    o comportamento em caso de falha de permissão (UX amigável).
    """

    def handle_no_permission(self):
        messages.error(self.request, "Você não tem permissão para acessar esta página.")
        return redirect('usuario:profile')


class AdminFilialScopedMixin:
    """
    NÍVEL 2 (Horizontal/Filial) - Para o Admin:
    Mixin para ser usado EXCLUSIVAMENTE no admin.py (ModelAdmin e Inlines).
    Filtra o queryset chamando o método 'for_request(request)' 
    do manager do modelo, SE disponível.

    Seguro para uso em inlines cujo modelo NÃO possui FilialManager.
    """

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        # ✅ Só chama for_request() se o queryset/manager suportar
        if hasattr(qs, 'for_request'):
            return qs.for_request(request)

        return qs


class ViewFilialScopedMixin:
    """
    NÍVEL 2 (Horizontal/Filial) - Para Views:
    Mixin para ser usado EXCLUSIVAMENTE em Class-Based Views (views.py).
    Filtra o queryset chamando o método 'for_request(request)' 
    do manager do modelo.

    IMPORTANTE: O modelo desta View DEVE usar o 'FilialManager'.
    """

    def get_queryset(self):
        qs = super().get_queryset()

        if hasattr(qs, 'for_request'):
            return qs.for_request(self.request)

        return qs


class TecnicoScopeMixin:
    """
    NÍVEL 3 (Vertical/Dados):
    Mixin global para filtrar querysets para usuários do grupo 'TÉCNICO'.
    Deve ser herdado ANTES do ViewFilialScopedMixin.

    Ex: class MinhaView(SSTPermissionMixin, TecnicoScopeMixin, ViewFilialScopedMixin, ListView):
    """

    tecnico_scope_lookup = None

    def _is_tecnico(self) -> bool:
        user = self.request.user
        if not hasattr(user, '_is_tecnico'):
            user._is_tecnico = user.groups.filter(name='TÉCNICO').exists()
        return user._is_tecnico

    def get_queryset(self) -> QuerySet:
        queryset = super().get_queryset()
        return self.scope_tecnico_queryset(queryset)

    def scope_tecnico_queryset(self, queryset: QuerySet) -> QuerySet:
        if not self._is_tecnico():
            return queryset

        if self.tecnico_scope_lookup:
            filter_kwargs = {self.tecnico_scope_lookup: self.request.user}
            return queryset.filter(**filter_kwargs).distinct()

        return queryset.none()


class TarefaPermissionMixin(AccessMixin):
    """
    Mixin de permissão a nível de objeto.
    Garante que o usuário logado seja o criador ou o responsável pela tarefa.
    """

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(
            Q(usuario=self.request.user) | Q(responsavel=self.request.user)
        ).distinct()


# =============================================================================
# == MIXINS UTILITÁRIOS
# =============================================================================

class FilialCreateMixin:
    """
    Mixin para views de criação. Atribui automaticamente a filial da sessão
    ao novo objeto antes de salvá-lo.
    """

    def form_valid(self, form):
        filial_id = self.request.session.get('active_filial_id')
        if not filial_id:
            messages.error(
                self.request,
                "Nenhuma filial selecionada. Por favor, escolha uma filial no menu superior."
            )
            raise PermissionDenied("Nenhuma filial selecionada para criação de objeto.")

        form.instance.filial_id = filial_id
        messages.success(
            self.request,
            f"{self.model._meta.verbose_name.capitalize()} criado(a) com sucesso."
        )
        return super().form_valid(form)


class ChangeFilialAdminMixin:
    """
    Ação de Admin para trocar a filial de objetos em lote.
    """
    actions = ['change_filial_action']

    def change_filial_action(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(
                request,
                "Apenas superusuários podem mover itens entre filiais.",
                level=messages.ERROR
            )
            return None

        form = None
        if 'post' in request.POST:
            form = ChangeFilialForm(request.POST)

            if form.is_valid():
                nova_filial = form.cleaned_data['filial']
                ids_selecionados_str = form.cleaned_data['selected_ids']

                try:
                    ids_selecionados = [int(pk) for pk in ids_selecionados_str.split(',')]
                except (ValueError, TypeError):
                    self.message_user(request, "Erro: IDs de seleção inválidos.", messages.ERROR)
                    return None

                queryset_para_atualizar = self.model.objects.filter(pk__in=ids_selecionados)
                contador = 0
                for obj in queryset_para_atualizar:
                    obj.filial = nova_filial
                    obj.save()
                    contador += 1

                nome_filial = nova_filial.nome if nova_filial else "Global (Sem Filial)"
                self.message_user(
                    request,
                    f"{contador} item(ns) foram movidos com sucesso para a filial: {nome_filial}.",
                    messages.SUCCESS
                )
                return None

        if not form:
            ids_selecionados = ','.join(str(pk) for pk in queryset.values_list('pk', flat=True))
            form = ChangeFilialForm(initial={'selected_ids': ids_selecionados})

        contexto = {
            'opts': self.model._meta,
            'queryset': queryset,
            'form': form,
            'title': "Alterar Filial"
        }
        return render(request, 'admin/actions/change_filial_intermediate.html', contexto)

    change_filial_action.short_description = "Alterar filial dos itens selecionados"


class AtividadeLogMixin:
    """
    Mixin refatorado para criar logs de atividade para Ferramentas ou Malas.
    """

    def _log_atividade(self, tipo, descricao, ferramenta=None, mala=None):
        if not ferramenta and not mala:
            raise ValueError("A função _log_atividade requer um objeto 'ferramenta' ou 'mala'.")

        item = ferramenta or mala

        if not hasattr(self, 'request') or not hasattr(self.request, 'user'):
            raise TypeError(
                f"O {self.__class__.__name__} deve ter acesso ao 'request.user' para logar atividades."
            )

        Atividade.objects.create(
            ferramenta=ferramenta,
            mala=mala,
            filial=item.filial,
            tipo_atividade=tipo,
            descricao=descricao,
            usuario=self.request.user
        )


class HTMXModalFormMixin:
    """
    Mixin para adaptar CreateView e UpdateView para funcionar com modais HTMX.
    """

    def get_template_names(self):
        if self.request.htmx:
            original_template = super().get_template_names()[0]
            base, ext = original_template.rsplit('.', 1)
            return [f"{base}_partial.{ext}"]
        return super().get_template_names()

    def form_valid(self, form):
        response = super().form_valid(form)

        if self.request.htmx:
            htmx_response = HttpResponse(status=204)
            htmx_response['HX-Redirect'] = response.url
            return htmx_response

        return response


# =============================================================================
# == MIXIN DE ACESSO A TAREFAS
# =============================================================================

class TarefaAccessMixin:
    """
    Mixin que garante acesso à tarefa.
    Acesso: criador, responsável, participantes, staff, superuser.
    """

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not self.user_can_access(self.request.user, obj):
            raise PermissionDenied('Você não tem permissão para acessar esta tarefa.')
        return obj

    @staticmethod
    def user_can_access(user, tarefa):
        if user.is_superuser or user.is_staff:
            return True
        if tarefa.usuario_id == user.pk:
            return True
        if tarefa.responsavel_id == user.pk:
            return True
        if tarefa.participantes.filter(pk=user.pk).exists():
            return True
        return False

    @staticmethod
    def user_can_edit(user, tarefa):
        if user.is_superuser or user.is_staff:
            return True
        if tarefa.usuario_id == user.pk:
            return True
        if tarefa.responsavel_id == user.pk:
            return True
        return False


# =============================================================================
# == MIXIN DE PERMISSÃO POR APP (Controle de acesso por módulo)
# =============================================================================

class AppPermissionMixin(PermissionRequiredMixin):
    """
    Mixin que verifica se o usuário tem pelo menos UMA permissão
    do app especificado. Superusers passam direto.

    Uso nas views:
        class MinhaView(LoginRequiredMixin, AppPermissionMixin, ListView):
            app_label_required = 'ata_reuniao'

    Também aceita o padrão do Django:
        class MinhaView(LoginRequiredMixin, AppPermissionMixin, ListView):
            permission_required = 'ata_reuniao.view_atareuniao'
    """
    app_label_required = None
    permission_required = None
    raise_exception = True

    def get_permission_required(self):
        if self.permission_required:
            if isinstance(self.permission_required, str):
                return (self.permission_required,)
            return self.permission_required
        return ()

    def has_permission(self):
        user = self.request.user

        if user.is_superuser:
            return True

        if self.permission_required:
            return super().has_permission()

        if self.app_label_required:
            all_perms = user.get_all_permissions()
            return any(
                perm.startswith(f'{self.app_label_required}.')
                for perm in all_perms
            )

        return False

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return render(self.request, 'errors/acesso_negado.html', {
                'titulo': 'Acesso Negado',
                'mensagem': (
                    'Você não possui permissão para acessar este módulo. '
                    'Solicite acesso ao administrador do sistema.'
                ),
            }, status=403)
        return super().handle_no_permission()

# ============================================================
#  MIXIN DE UPLOAD SEGURO PARA MODELS
# ============================================================

class UploadPath:
    """
    Callable serializável para upload_to.
    O Django consegue serializar classes com deconstruct().
    """
    def __init__(self, app_name):
        self.app_name = app_name

    def __call__(self, instance, filename):
        ext = os.path.splitext(filename)[1].lower()
        safe_name = f"{uuid.uuid4().hex}{ext}"
        return f"{self.app_name}/{safe_name}"

    def deconstruct(self):
        return (
            'core.mixins.UploadPath',  # caminho completo da classe
            (self.app_name,),           # args
            {},                         # kwargs
        )

def make_upload_path(app_name):
    """
    Retorna um callable serializável para upload_to.

    Uso no model:
        arquivo = models.FileField(upload_to=make_upload_path('ltcat_anexos'))
    """
    return UploadPath(app_name)


def _sanitize_image(uploaded_file):
    """
    Re-salva a imagem para remover metadados (EXIF) e payloads maliciosos.
    Retorna o arquivo limpo ou o original se não for imagem.
    """
    try:
        img = Image.open(uploaded_file)
        img.verify()  # verifica integridade
        uploaded_file.seek(0)
        img = Image.open(uploaded_file)  # reabre após verify

        # Remove EXIF/metadados re-salvando
        output = io.BytesIO()
        img_format = img.format or "PNG"
        img.save(output, format=img_format)
        output.seek(0)

        return InMemoryUploadedFile(
            file=output,
            field_name=uploaded_file.field_name if hasattr(uploaded_file, 'field_name') else 'file',
            name=uploaded_file.name,
            content_type=uploaded_file.content_type,
            size=output.getbuffer().nbytes,
            charset=None,
        )
    except Exception:
        # Se não for imagem válida, retorna o original
        uploaded_file.seek(0)
        return uploaded_file

class SecureUploadMixin(models.Model):
    """
    Mixin abstrato para upload seguro.

    Uso para models NOVOS que precisam de upload como funcionalidade principal:
        class MaterialTreinamento(SecureUploadMixin):
            UPLOAD_APP = 'treinamentos'
            titulo = models.CharField(max_length=200)

    ⚠️ NÃO use se o model já herda de BaseModel ou outro abstract.
       Nesses casos, use diretamente nos campos:
        arquivo = models.FileField(
            upload_to=make_upload_path('app_name'),
            validators=[SecureFileValidator('app_name')],
        )
    """

    UPLOAD_APP = 'default'

    original_filename = models.CharField(
        max_length=255,
        verbose_name='Nome original',
        editable=False,
        default='',
    )
    file = models.FileField(
        upload_to='uploads/',
        verbose_name='Arquivo',
    )
    file_size = models.PositiveIntegerField(
        verbose_name='Tamanho (bytes)',
        editable=False,
        default=0,
    )
    mime_type = models.CharField(
        max_length=100,
        verbose_name='Tipo MIME',
        editable=False,
        default='',
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Enviado por',
        related_name='%(app_label)s_%(class)s_uploads',
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data de envio',
    )

    class Meta:
        abstract = True
        ordering = ['-uploaded_at']

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        app = getattr(cls, 'UPLOAD_APP', 'default')

        for field in cls._meta.local_fields:
            if field.name == 'file' and isinstance(field, models.FileField):
                field.upload_to = make_upload_path(app)  # ✅ Usa a mesma função pública
                field.validators = [SecureFileValidator(app)]

    def save(self, *args, **kwargs):
        if self.file:
            if not self.original_filename:
                self.original_filename = os.path.basename(
                    getattr(self.file, 'name', '') or ''
                )
            try:
                self.file_size = self.file.size
            except Exception:
                pass

            # ✅ Usa wrapper
            if not self.mime_type:
                try:
                    self.mime_type = get_mime_type(self.file)
                except Exception:
                    self.mime_type = 'application/octet-stream'

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.original_filename} ({self.get_size_display()})"

    def get_size_display(self):
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        return f"{self.file_size / (1024 * 1024):.1f} MB"

    @property
    def is_image(self):
        return self.mime_type.startswith('image/')

    @property
    def is_pdf(self):
        return self.mime_type == 'application/pdf'

sanitize_image = _sanitize_image