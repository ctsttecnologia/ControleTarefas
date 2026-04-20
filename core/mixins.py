# core/mixins.py
import io
import os
import uuid

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.mixins import AccessMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import models
from django.db.models import Q, QuerySet
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from PIL import Image
from core.magic_utils import get_mime_type
from core.validators import SecureFileValidator
from .forms import ChangeFilialForm


# =============================================================================
# == MIXINS DE PERMISSÃO E ESCOPO (ARQUITETURA DE 3 NÍVEIS)
# =============================================================================

class SSTPermissionMixin(PermissionRequiredMixin):
    """
    NÍVEL 1 (Página):
    Mixin que herda do PermissionRequiredMixin do Django, customizando
    o comportamento em caso de falha de permissão (UX amigável).
    """

    def handle_no_permission(self):
        messages.error(self.request, "Você não tem permissão para acessar esta página.")
        return redirect('usuario:profile')


class AdminFilialScopedMixin:
    """
    NÍVEL 2 (Horizontal/Filial) - Para o Admin:
    Filtra o queryset chamando o método 'for_request(request)' 
    do manager do modelo, SE disponível.
    """

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if hasattr(qs, 'for_request'):
            return qs.for_request(request)
        return qs


class ViewFilialScopedMixin:
    """
    NÍVEL 2 (Horizontal/Filial) - Para Views:
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

    Ex:
        class MinhaView(AppPermissionMixin, TecnicoScopeMixin, ViewFilialScopedMixin, ListView):
            ...
    """

    tecnico_scope_lookup = None
    _TECNICO_CACHE_ATTR = '_tecnico_group_cache'

    def _is_tecnico(self) -> bool:
        user = self.request.user
        if not hasattr(user, self._TECNICO_CACHE_ATTR):
            setattr(
                user,
                self._TECNICO_CACHE_ATTR,
                user.groups.filter(name='TÉCNICO').exists()
            )
        return getattr(user, self._TECNICO_CACHE_ATTR)

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
# == MIXIN DE PERMISSÃO POR APP
# =============================================================================

class AppPermissionMixin(PermissionRequiredMixin):
    """
    Mixin que verifica se o usuário tem pelo menos UMA permissão
    do app especificado. Superusers passam direto.

    ✅ Tolerante à presença (ou ausência) de LoginRequiredMixin na cadeia.
       Se o usuário não estiver autenticado, o handle_no_permission delega
       para o fluxo padrão do Django (redireciona para LOGIN_URL).

    Uso nas views:
        class MinhaView(AppPermissionMixin, ListView):
            app_label_required = 'ata_reuniao'

    Padrão Django (granular) também é suportado:
        class MinhaView(AppPermissionMixin, ListView):
            permission_required = 'ata_reuniao.view_atareuniao'

    Compatibilidade retroativa:
        class MinhaView(LoginRequiredMixin, AppPermissionMixin, ListView):
            ...  # continua funcionando
    """
    app_label_required = None
    permission_required = None
    raise_exception = False  # ✅ False = redireciona pro login; True = 403

    def get_permission_required(self):
        if self.permission_required:
            if isinstance(self.permission_required, str):
                return (self.permission_required,)
            return self.permission_required
        return ()

    def has_permission(self):
        user = self.request.user

        # Guard: anônimo nunca passa
        if not user.is_authenticated:
            return False

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
        # Se NÃO está autenticado → redireciona pro login (comportamento padrão)
        if not self.request.user.is_authenticated:
            return redirect(f"{settings.LOGIN_URL}?next={self.request.path}")

        # Autenticado mas sem permissão → página 403 customizada
        return render(self.request, 'errors/acesso_negado.html', {
            'titulo': 'Acesso Negado',
            'mensagem': (
                'Você não possui permissão para acessar este módulo. '
                'Solicite acesso ao administrador do sistema.'
            ),
        }, status=403)


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
                "Nenhuma filial selecionada. "
                "Por favor, escolha uma filial no menu superior."
            )
            raise PermissionDenied("Nenhuma filial selecionada para criação de objeto.")

        form.instance.filial_id = filial_id
        response = super().form_valid(form)  # ✅ save primeiro

        # Só envia mensagem se a view NÃO estiver usando SuccessMessageMixin
        if not hasattr(self, 'success_message') or not self.success_message:
            messages.success(
                self.request,
                f"{self.model._meta.verbose_name.capitalize()} criado(a) com sucesso."
            )
        return response


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
    Mixin para criar logs de atividade para Ferramentas ou Malas.
    """

    def _log_atividade(self, tipo, descricao, ferramenta=None, mala=None):
        if not ferramenta and not mala:
            raise ValueError("A função _log_atividade requer um objeto 'ferramenta' ou 'mala'.")

        item = ferramenta or mala

        if not hasattr(self, 'request') or not hasattr(self.request, 'user'):
            raise TypeError(
                f"O {self.__class__.__name__} deve ter acesso ao 'request.user' para logar atividades."
            )

        # ✅ Import lazy — evita circular import no carregamento dos models
        from ferramentas.models import Atividade

        Atividade.objects.create(
            ferramenta=ferramenta,
            mala=mala,
            filial=item.filial,
            tipo_atividade=tipo,
            descricao=descricao,
            usuario=self.request.user,
        )

class HTMXModalFormMixin:
    """
    Mixin para adaptar CreateView e UpdateView para funcionar com modais HTMX.
    """

    def get_template_names(self):
        if self.request.htmx:
            templates = super().get_template_names()
            if templates:
                base, ext = templates[0].rsplit('.', 1)
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
# == MIXIN DE UPLOAD SEGURO PARA MODELS
# =============================================================================

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
            'core.mixins.UploadPath',
            (self.app_name,),
            {},
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
    Retorna o arquivo limpo ou o original se não for imagem válida.
    """
    try:
        # 1ª passada: verificar integridade
        img = Image.open(uploaded_file)
        img.verify()

        # verify() invalida o objeto — precisa reabrir
        uploaded_file.seek(0)
        img = Image.open(uploaded_file)

        img_format = img.format or "PNG"

        # JPEG não suporta RGBA/LA/P — converte pra RGB
        if img_format.upper() == "JPEG" and img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")

        # Re-salva SEM metadados
        output = io.BytesIO()
        img.save(output, format=img_format)
        output.seek(0)

        return InMemoryUploadedFile(
            file=output,
            field_name=getattr(uploaded_file, 'field_name', 'file'),
            name=uploaded_file.name,
            content_type=getattr(uploaded_file, 'content_type', f'image/{img_format.lower()}'),
            size=output.getbuffer().nbytes,
            charset=None,
        )
    except Exception:
        # Se não for imagem válida, retorna o original intacto
        try:
            uploaded_file.seek(0)
        except Exception:
            pass
        return uploaded_file


# Alias público
sanitize_image = _sanitize_image

def _sanitize_pdf(uploaded_file):
    """
    Re-escreve o PDF removendo:
    - Metadados (autor, software, histórico)
    - JavaScript embutido
    - Ações automáticas (OpenAction, AA)
    - Arquivos incorporados (EmbeddedFiles)
    - Formulários XFA

    Retorna o arquivo limpo ou o original se não for PDF válido.
    """
    try:
        from pypdf import PdfReader, PdfWriter
        from pypdf.generic import NameObject
    except ImportError:
        # pypdf não instalado — retorna original
        try:
            uploaded_file.seek(0)
        except Exception:
            pass
        return uploaded_file

    try:
        uploaded_file.seek(0)
        reader = PdfReader(uploaded_file, strict=False)

        # PDFs criptografados: tenta abrir com senha vazia
        if reader.is_encrypted:
            try:
                if not reader.decrypt(""):
                    # Não conseguiu descriptografar → retorna original
                    uploaded_file.seek(0)
                    return uploaded_file
            except Exception:
                uploaded_file.seek(0)
                return uploaded_file

        writer = PdfWriter()

        # Copia APENAS as páginas (sem estruturas do documento-raiz suspeitas)
        for page in reader.pages:
            # Remove ações de página (AA = Additional Actions)
            if NameObject("/AA") in page:
                del page[NameObject("/AA")]
            # Remove anotações de JavaScript
            if NameObject("/Annots") in page:
                annots = page[NameObject("/Annots")]
                try:
                    # Filtra anotações que contêm JS
                    safe_annots = []
                    for annot_ref in annots:
                        try:
                            annot = annot_ref.get_object()
                            subtype = annot.get("/Subtype")
                            # Remove anotações de ação/JS
                            if subtype in ("/Link",):
                                action = annot.get("/A", {})
                                if action and action.get("/S") == "/JavaScript":
                                    continue
                            safe_annots.append(annot_ref)
                        except Exception:
                            continue
                    page[NameObject("/Annots")] = safe_annots
                except Exception:
                    # Se der erro processando annotations, remove todas
                    del page[NameObject("/Annots")]

            writer.add_page(page)

        # Remove TODOS os metadados (autor, software, título, etc)
        writer.add_metadata({})

        # Garante que o writer não herde catálogo malicioso
        # (OpenAction, Names/JavaScript, Names/EmbeddedFiles, AcroForm/XFA)
        root = writer._root_object
        for key in ("/OpenAction", "/AA", "/Names", "/AcroForm", "/JavaScript"):
            name = NameObject(key)
            if name in root:
                del root[name]

        output = io.BytesIO()
        writer.write(output)
        output.seek(0)

        return InMemoryUploadedFile(
            file=output,
            field_name=getattr(uploaded_file, 'field_name', 'file'),
            name=uploaded_file.name,
            content_type='application/pdf',
            size=output.getbuffer().nbytes,
            charset=None,
        )
    except Exception:
        # Se algo falhar na sanitização, retorna o original intacto
        # (o validator já validou que é PDF legítimo)
        try:
            uploaded_file.seek(0)
        except Exception:
            pass
        return uploaded_file


# Alias público
sanitize_pdf = _sanitize_pdf


class SecureUploadMixin(models.Model):
    """
    Mixin abstrato para upload seguro com sanitização automática de imagens.

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
                field.upload_to = make_upload_path(app)
                field.validators = [SecureFileValidator(app)]

    def _is_new_upload(self):
        """Detecta se é um upload novo (não um registro já salvo sendo editado)."""
        return (
            self.file
            and hasattr(self.file, 'file')
            and isinstance(self.file.file, InMemoryUploadedFile)
        )

    def save(self, *args, **kwargs):
        if self.file and self._is_new_upload():
            uploaded = self.file.file
            content_type = getattr(uploaded, 'content_type', '') or ''

            # ✅ Sanitização por tipo de arquivo
            try:
                if content_type.startswith('image/'):
                    self.file.file = _sanitize_image(uploaded)
                elif content_type == 'application/pdf':
                    self.file.file = _sanitize_pdf(uploaded)
            except Exception:
                # Se sanitização falhar, deixa passar (validator já checou)
                pass

            # Captura nome original
            if not self.original_filename:
                self.original_filename = os.path.basename(
                    getattr(self.file, 'name', '') or ''
                )

            # Captura tamanho (pode ter mudado após sanitização)
            try:
                self.file_size = self.file.size
            except Exception:
                self.file_size = 0

            # Captura MIME type
            if not self.mime_type:
                try:
                    self.mime_type = get_mime_type(self.file)
                except Exception:
                    self.mime_type = content_type or 'application/octet-stream'

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


# Alias público
sanitize_image = _sanitize_image
