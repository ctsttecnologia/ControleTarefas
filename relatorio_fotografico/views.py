
# relatorio_fotografico/views.py
"""
Views do app Relatório Fotográfico.

Fluxo de imagens:
- No upload (FotoRelatorio.save), a imagem é SANITIZADA (remoção de
  EXIF/metadados) e PADRONIZADA (800x600, JPEG q=80). O arquivo salvo
  no storage já é o definitivo, usado na exibição e na exportação.
- Word/PDF usam diretamente `foto.imagem`, sem cópias temporárias.

Segurança (3 camadas):
1. Login + acesso ao app (LoginRequiredMixin / AppPermissionMixin).
2. Permissão por ação (AdminOrPermissionRequiredMixin).
3. Escopo de objeto (ViewFilialScopedMixin + RelatorioScopeMixin):
   nenhuma view busca objeto fora do queryset escopado.
"""

import json
import logging

import cloudinary.uploader
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Max, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.dateparse import parse_date
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView, View,
)
from django.views.generic.detail import SingleObjectMixin

from core.mixins import (
    AdminOrPermissionRequiredMixin,
    AppPermissionMixin,
    FilialCreateMixin,
    ViewFilialScopedMixin,
)

from .forms import RelatorioFotograficoForm
from .models import FotoRelatorio, RelatorioFotografico
from .services.docx_generator import gerar_docx_relatorio
from .services.pdf_generator import gerar_pdf_relatorio

logger = logging.getLogger(__name__)
User = get_user_model()

APP_LABEL = 'relatorio_fotografico'

PERM_VIEW = f'{APP_LABEL}.view_relatoriofotografico'
PERM_ADD = f'{APP_LABEL}.add_relatoriofotografico'
PERM_CHANGE = f'{APP_LABEL}.change_relatoriofotografico'
PERM_DELETE = f'{APP_LABEL}.delete_relatoriofotografico'
PERM_VIEW_ALL = f'{APP_LABEL}.view_all_relatorios_filial'

PERM_FOTO_ADD = f'{APP_LABEL}.add_fotorelatorio'
PERM_FOTO_CHANGE = f'{APP_LABEL}.change_fotorelatorio'
PERM_FOTO_DELETE = f'{APP_LABEL}.delete_fotorelatorio'


def is_admin(user):
    return user.is_authenticated and (
        user.is_superuser or getattr(user, 'is_administrador', False)
    )


# -----------------------------------------------------------------------
# MIXINS
# -----------------------------------------------------------------------

class RelatorioScopeMixin:
    """
    Escopo vertical:
    - Admin/superuser ou 'view_all_relatorios_filial': todos da filial ativa
      (o filtro de filial é feito pelo ViewFilialScopedMixin).
    - Demais: apenas onde é responsável ou criador.
    """

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if is_admin(user) or user.has_perm(PERM_VIEW_ALL):
            return qs
        return qs.filter(Q(responsavel=user) | Q(criado_por=user)).distinct()


class BaseRelatorioMixin(
    LoginRequiredMixin,
    AppPermissionMixin,
    AdminOrPermissionRequiredMixin,
    ViewFilialScopedMixin,
    RelatorioScopeMixin,
):
    """Base para views que operam sobre um relatório já existente."""
    app_label_required = APP_LABEL
    model = RelatorioFotografico
    raise_exception = True  # 403 em vez de redirect p/ login


class BloqueiaFinalizadoMixin:
    """Impede alterações em relatórios finalizados."""

    def relatorio_bloqueado(self, relatorio):
        return relatorio.status == RelatorioFotografico.STATUS_FINALIZADO


class FotoBaseView(BaseRelatorioMixin, BloqueiaFinalizadoMixin,
                   SingleObjectMixin, View):
    """Base das views AJAX de fotos (sempre via relatório escopado)."""
    http_method_names = ['post']

    def get_relatorio(self, pk, lock=False):
        qs = self.get_queryset()
        if lock:
            qs = qs.select_for_update()
        return get_object_or_404(qs, pk=pk)

    def get_foto(self, foto_pk):
        return get_object_or_404(
            FotoRelatorio.objects.select_related('relatorio'),
            pk=foto_pk,
            relatorio__in=self.get_queryset(),
        )

    @staticmethod
    def erro(msg, status=400):
        return JsonResponse({'ok': False, 'erro': msg}, status=status)


# -----------------------------------------------------------------------
# CRUD DO RELATÓRIO
# -----------------------------------------------------------------------

class RelatorioListView(BaseRelatorioMixin, ListView):
    permission_required = PERM_VIEW
    template_name = 'relatorio_fotografico/relatorio_list.html'
    context_object_name = 'relatorios'
    paginate_by = 20

    def get_scoped_queryset(self):
        return (
            super().get_queryset()
            .select_related('responsavel', 'filial')
            .prefetch_related('fotos')  # evita N+1 em relatorio.fotos.count
        )

    def get_queryset(self):
        qs = self.get_scoped_queryset()
        g = self.request.GET

        busca = g.get('q', '').strip()
        status = g.get('status', '').strip()
        responsavel_id = g.get('responsavel', '').strip()
        data_ini = parse_date(g.get('data_inicio', '').strip() or '') if g.get('data_inicio') else None
        data_fim = parse_date(g.get('data_fim', '').strip() or '') if g.get('data_fim') else None

        if busca:
            qs = qs.filter(Q(titulo__icontains=busca) | Q(obra_contrato__icontains=busca))
        if status in dict(RelatorioFotografico.STATUS_CHOICES):
            qs = qs.filter(status=status)
        if responsavel_id.isdigit():
            qs = qs.filter(responsavel_id=responsavel_id)
        if data_ini:
            qs = qs.filter(data__gte=data_ini)
        if data_fim:
            qs = qs.filter(data__lte=data_fim)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        g = self.request.GET
        ctx.update({
            'status_choices': RelatorioFotografico.STATUS_CHOICES,
            'q': g.get('q', ''),
            'status_filtro': g.get('status', ''),
            'responsavel_filtro': g.get('responsavel', ''),
            'data_inicio': g.get('data_inicio', ''),
            'data_fim': g.get('data_fim', ''),
            # Só responsáveis visíveis no escopo do usuário
            'responsaveis': User.objects.filter(
                pk__in=self.get_scoped_queryset().values('responsavel_id')
            ).order_by('first_name', 'username'),
        })
        return ctx


class RelatorioDetailView(BaseRelatorioMixin, DetailView):
    permission_required = PERM_VIEW
    template_name = 'relatorio_fotografico/relatorio_detail.html'
    context_object_name = 'relatorio'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['paginas'] = self.object.paginas
        ctx['total_folhas'] = self.object.total_folhas
        return ctx


class RelatorioCreateView(
    LoginRequiredMixin, AppPermissionMixin, AdminOrPermissionRequiredMixin,
    FilialCreateMixin, CreateView,
):
    app_label_required = APP_LABEL
    permission_required = PERM_ADD
    raise_exception = True
    model = RelatorioFotografico
    form_class = RelatorioFotograficoForm
    template_name = 'relatorio_fotografico/relatorio_form.html'

    def form_valid(self, form):
        form.instance.criado_por = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Relatório criado. Adicione as fotos.')
        return response

    def get_success_url(self):
        return reverse_lazy('relatorio_fotografico:detail', args=[self.object.pk])


class RelatorioUpdateView(BaseRelatorioMixin, BloqueiaFinalizadoMixin, UpdateView):
    permission_required = PERM_CHANGE
    form_class = RelatorioFotograficoForm
    template_name = 'relatorio_fotografico/relatorio_form.html'

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        return response

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        self._bloqueado = self.relatorio_bloqueado(obj) and not is_admin(self.request.user)
        return obj

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self._bloqueado:
            messages.warning(request, 'Relatório finalizado não pode ser editado.')
            return redirect('relatorio_fotografico:detail', pk=self.object.pk)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self._bloqueado:
            messages.warning(request, 'Relatório finalizado não pode ser editado.')
            return redirect('relatorio_fotografico:detail', pk=self.object.pk)
        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('relatorio_fotografico:detail', args=[self.object.pk])


class RelatorioDeleteView(BaseRelatorioMixin, DeleteView):
    permission_required = PERM_DELETE
    template_name = 'relatorio_fotografico/relatorio_confirm_delete.html'
    success_url = reverse_lazy('relatorio_fotografico:list')

    def form_valid(self, form):
        public_ids = [
            f.imagem.public_id for f in self.object.fotos.all()
            if getattr(f.imagem, 'public_id', None)
        ]
        response = super().form_valid(form)
        for pid in public_ids:
            _destruir_cloudinary(pid)
        messages.success(self.request, 'Relatório excluído com sucesso.')
        return response


class RelatorioFinalizarView(BaseRelatorioMixin, SingleObjectMixin, View):
    permission_required = PERM_CHANGE
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        relatorio = self.get_object()

        if relatorio.status == RelatorioFotografico.STATUS_FINALIZADO:
            messages.info(request, 'Este relatório já está finalizado.')
        else:
            relatorio.status = RelatorioFotografico.STATUS_FINALIZADO
            relatorio.save(update_fields=['status', 'updated_at'])
            messages.success(request, f'Relatório "{relatorio.titulo}" finalizado.')

        next_url = request.POST.get('next')
        if next_url and url_has_allowed_host_and_scheme(
            next_url, {request.get_host()}, require_https=request.is_secure()
        ):
            return redirect(next_url)
        return redirect('relatorio_fotografico:detail', pk=relatorio.pk)


# -----------------------------------------------------------------------
# FOTOS (AJAX)
# -----------------------------------------------------------------------

def _destruir_cloudinary(public_id):
    try:
        cloudinary.uploader.destroy(public_id, resource_type='image')
    except Exception:  # não bloqueia a operação por falha externa
        logger.exception('Falha ao remover imagem %s do Cloudinary', public_id)


class FotoUploadView(FotoBaseView):
    permission_required = PERM_FOTO_ADD

    def post(self, request, pk):
        arquivos = request.FILES.getlist('imagens')
        if not arquivos:
            return self.erro('Nenhuma imagem enviada.')

        legendas = request.POST.getlist('legendas')
        latitudes = request.POST.getlist('latitudes')
        longitudes = request.POST.getlist('longitudes')

        with transaction.atomic():
            relatorio = self.get_relatorio(pk, lock=True)
            if self.relatorio_bloqueado(relatorio):
                return self.erro('Relatório finalizado não aceita novas fotos.', 403)

            self._atualizar_dados_relatorio(request, relatorio)

            ultima_ordem = relatorio.fotos.aggregate(m=Max('ordem'))['m'] or 0
            criadas = []
            for i, arquivo in enumerate(arquivos):
                foto = FotoRelatorio.objects.create(
                    relatorio=relatorio,
                    imagem=arquivo,
                    legenda=legendas[i] if i < len(legendas) else '',
                    ordem=ultima_ordem + i + 1,
                    latitude=(latitudes[i] if i < len(latitudes) else None) or None,
                    longitude=(longitudes[i] if i < len(longitudes) else None) or None,
                )
                criadas.append({
                    'id': foto.id,
                    'url': foto.imagem.url,
                    'legenda': foto.legenda,
                    'ordem': foto.ordem,
                    'coordenadas': foto.coordenadas_formatadas,
                })

        return JsonResponse({'ok': True, 'fotos': criadas})

    def _atualizar_dados_relatorio(self, request, relatorio):
        user = request.user
        if not (is_admin(user) or user.has_perm(PERM_CHANGE)):
            return  # quem só adiciona fotos não altera o cabeçalho

        campos = []
        obra = request.POST.get('obra')
        if obra:
            relatorio.obra_contrato = obra
            campos.append('obra_contrato')

        data_convertida = parse_date(request.POST.get('data') or '')
        if data_convertida:
            relatorio.data = data_convertida
            campos.append('data')

        assunto = request.POST.get('assunto')
        if assunto is not None:
            relatorio.assunto = assunto
            campos.append('assunto')

        responsavel_id = request.POST.get('responsavel')
        if responsavel_id and responsavel_id.isdigit():
            # Responsável precisa estar ativo (ajuste o filtro de filial ao seu modelo)
            usuario = User.objects.filter(pk=responsavel_id, is_active=True).first()
            if usuario:
                relatorio.responsavel = usuario
                campos.append('responsavel')

        if campos:
            relatorio.save(update_fields=campos + ['updated_at'])


class FotoUpdateView(FotoBaseView):
    permission_required = PERM_FOTO_CHANGE

    def post(self, request, pk):
        foto = self.get_foto(pk)
        if self.relatorio_bloqueado(foto.relatorio):
            return self.erro('Relatório finalizado não pode ser alterado.', 403)

        foto.legenda = request.POST.get('legenda', '')
        try:
            foto.ordem = int(request.POST['ordem'])
        except (KeyError, TypeError, ValueError):
            pass
        foto.save(update_fields=['legenda', 'ordem'])
        return JsonResponse({'ok': True})


class FotoDeleteView(FotoBaseView):
    permission_required = PERM_FOTO_DELETE

    def post(self, request, pk):
        foto = self.get_foto(pk)
        if self.relatorio_bloqueado(foto.relatorio):
            return self.erro('Relatório finalizado não pode ser alterado.', 403)

        relatorio_pk = foto.relatorio_id
        public_id = getattr(foto.imagem, 'public_id', None)
        foto.delete()
        if public_id:
            transaction.on_commit(lambda: _destruir_cloudinary(public_id))
        return JsonResponse({'ok': True, 'relatorio': relatorio_pk})


class FotoReorderView(FotoBaseView):
    """Recebe {'ordem': [3, 1, 2, ...]}."""
    permission_required = PERM_FOTO_CHANGE

    def post(self, request, pk):
        relatorio = self.get_relatorio(pk)
        if self.relatorio_bloqueado(relatorio):
            return self.erro('Relatório finalizado não pode ser alterado.', 403)

        try:
            ids = json.loads(request.body).get('ordem', [])
            ids = [int(x) for x in ids]
        except (ValueError, TypeError, AttributeError):
            return self.erro('Payload inválido.')

        with transaction.atomic():
            for i, foto_id in enumerate(ids, start=1):
                FotoRelatorio.objects.filter(
                    pk=foto_id, relatorio=relatorio
                ).update(ordem=i)
        return JsonResponse({'ok': True})


# -----------------------------------------------------------------------
# EXPORTAÇÃO — WORD e PDF
# -----------------------------------------------------------------------

class RelatorioExportDocxView(BaseRelatorioMixin, SingleObjectMixin, View):
    permission_required = PERM_VIEW

    def get(self, request, *args, **kwargs):
        relatorio = self.get_object()
        buffer = gerar_docx_relatorio(relatorio)
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
        response['Content-Disposition'] = (
            f'attachment; filename="relatorio_fotografico_{relatorio.pk}.docx"'
        )
        return response


class RelatorioExportPdfView(BaseRelatorioMixin, SingleObjectMixin, View):
    permission_required = PERM_VIEW

    def get(self, request, *args, **kwargs):
        relatorio = self.get_object()
        pdf_bytes = gerar_pdf_relatorio(relatorio, request=request)
        disposition = 'inline' if request.GET.get('inline') == '1' else 'attachment'
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'{disposition}; filename="relatorio_fotografico_{relatorio.pk}.pdf"'
        )
        return response
