
# relatorio_fotografico/views.py
"""
Views do app Relatório Fotográfico.

Fluxo de imagens:
- No upload (FotoRelatorio.save), a imagem é SANITIZADA (remoção de
  EXIF/metadados) e PADRONIZADA (tamanho fixo 800x600, JPEG q=80).
  Essa é a única transformação feita — o arquivo salvo no storage já
  é o definitivo, usado tanto na exibição quanto na exportação.
- Word/PDF usam diretamente `foto.imagem` (sem gerar cópias
  temporárias), já que a imagem já está padronizada desde o upload.
"""

import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q, Max
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils.dateparse import parse_date
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, View,
)

from core.mixins import (
    AppPermissionMixin, ViewFilialScopedMixin, FilialCreateMixin,
)

from .models import RelatorioFotografico, FotoRelatorio
from .forms import RelatorioFotograficoForm
from .services.docx_generator import gerar_docx_relatorio
from .services.pdf_generator import gerar_pdf_relatorio

User = get_user_model()

APP_LABEL = 'relatorio_fotografico'


class RelatorioScopeMixin:
    """
    Regras de escopo (Nível 3 - vertical):
    - Superuser ou usuário com permissão 'view_all_relatorios_filial'
      vê todos os relatórios da filial ativa.
    - Demais usuários veem apenas os relatórios em que são
      responsável ou criador.
    """

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if user.is_superuser or user.has_perm(
            f'{APP_LABEL}.view_all_relatorios_filial'
        ):
            return qs

        return qs.filter(
            Q(responsavel=user) | Q(criado_por=user)
        ).distinct()


class RelatorioListView(
    AppPermissionMixin, ViewFilialScopedMixin, RelatorioScopeMixin, ListView
):
    app_label_required = APP_LABEL
    model = RelatorioFotografico
    template_name = 'relatorio_fotografico/relatorio_list.html'
    context_object_name = 'relatorios'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        busca = self.request.GET.get('q', '').strip()
        status = self.request.GET.get('status', '').strip()
        if busca:
            qs = qs.filter(
                Q(titulo__icontains=busca) | Q(obra_contrato__icontains=busca)
            )
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['status_choices'] = RelatorioFotografico.STATUS_CHOICES
        ctx['q'] = self.request.GET.get('q', '')
        ctx['status_filtro'] = self.request.GET.get('status', '')
        return ctx


class RelatorioDetailView(
    AppPermissionMixin, ViewFilialScopedMixin, RelatorioScopeMixin, DetailView
):
    app_label_required = APP_LABEL
    model = RelatorioFotografico
    template_name = 'relatorio_fotografico/relatorio_detail.html'
    context_object_name = 'relatorio'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['paginas'] = self.object.paginas
        ctx['total_folhas'] = self.object.total_folhas
        return ctx


class RelatorioCreateView(
    AppPermissionMixin, FilialCreateMixin, CreateView
):
    app_label_required = APP_LABEL
    model = RelatorioFotografico
    form_class = RelatorioFotograficoForm
    template_name = 'relatorio_fotografico/relatorio_form.html'

    def form_valid(self, form):
        form.instance.criado_por = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Relatório criado. Adicione as fotos.')
        return response

    def get_success_url(self):
        return reverse_lazy(
            'relatorio_fotografico:detail', args=[self.object.pk]
        )


class RelatorioUpdateView(
    AppPermissionMixin, ViewFilialScopedMixin, RelatorioScopeMixin, UpdateView
):
    app_label_required = APP_LABEL
    model = RelatorioFotografico
    form_class = RelatorioFotograficoForm
    template_name = 'relatorio_fotografico/relatorio_form.html'

    def get_success_url(self):
        return reverse_lazy(
            'relatorio_fotografico:detail', args=[self.object.pk]
        )


class RelatorioDeleteView(
    AppPermissionMixin, ViewFilialScopedMixin, RelatorioScopeMixin, DeleteView
):
    app_label_required = APP_LABEL
    model = RelatorioFotografico
    template_name = 'relatorio_fotografico/relatorio_confirm_delete.html'
    success_url = reverse_lazy('relatorio_fotografico:list')

    def form_valid(self, form):
        messages.success(self.request, 'Relatório excluído com sucesso.')
        return super().form_valid(form)


# -----------------------------------------------------------------------
# UPLOAD MÚLTIPLO DE FOTOS (galeria ou câmera)
# -----------------------------------------------------------------------

class FotoUploadView(AppPermissionMixin, LoginRequiredMixin, View):
    """
    Recebe múltiplos arquivos (input multiple, galeria ou câmera)
    via POST AJAX/multipart e cria os registros FotoRelatorio.

    Além das imagens, aceita opcionalmente:
      - 'legendas': lista paralela às imagens (mesma ordem/índice).
      - 'obra', 'data', 'assunto', 'responsavel': campos do
        RelatorioFotografico, atualizados se enviados (útil para o
        app mobile, que envia tudo em uma única chamada).

    Cada imagem é sanitizada e padronizada automaticamente no
    `FotoRelatorio.save()` (ver models.py) — nada a fazer aqui além
    de criar o registro.
    """
    app_label_required = APP_LABEL

    def post(self, request, pk):
        relatorio = get_object_or_404(RelatorioFotografico, pk=pk)
        arquivos = request.FILES.getlist('imagens')
        legendas = request.POST.getlist('legendas')

        if not arquivos:
            return JsonResponse(
                {'ok': False, 'erro': 'Nenhuma imagem enviada.'}, status=400
            )

        with transaction.atomic():
            relatorio_locked = (
                RelatorioFotografico.objects.select_for_update().get(pk=pk)
            )

            self._atualizar_dados_relatorio(request, relatorio_locked)

            ultima_ordem = (
                relatorio_locked.fotos.aggregate(m=Max('ordem'))['m'] or 0
            )
            criadas = []
            for i, arquivo in enumerate(arquivos):
                legenda = legendas[i] if i < len(legendas) else ''
                foto = FotoRelatorio.objects.create(
                    relatorio=relatorio_locked,
                    imagem=arquivo,
                    legenda=legenda,
                    ordem=ultima_ordem + i + 1,
                )
                criadas.append({
                    'id': foto.id,
                    'url': foto.imagem.url,
                    'legenda': foto.legenda,
                    'ordem': foto.ordem,
                })

        return JsonResponse({'ok': True, 'fotos': criadas})

    def _atualizar_dados_relatorio(self, request, relatorio):
        """
        Atualiza campos do relatório se enviados no POST.
        Todos são opcionais — se ausentes, o relatório permanece
        inalterado nesses campos.
        """
        campos_atualizados = []

        obra = request.POST.get('obra')
        if obra:
            relatorio.obra_contrato = obra
            campos_atualizados.append('obra_contrato')

        data_str = request.POST.get('data')
        if data_str:
            data_convertida = parse_date(data_str)
            if data_convertida:
                relatorio.data = data_convertida
                campos_atualizados.append('data')

        assunto = request.POST.get('assunto')
        if assunto is not None:
            relatorio.assunto = assunto
            campos_atualizados.append('assunto')

        responsavel_id = request.POST.get('responsavel')
        if responsavel_id:
            usuario = User.objects.filter(pk=responsavel_id).first()
            if usuario:
                relatorio.responsavel = usuario
                campos_atualizados.append('responsavel')

        if campos_atualizados:
            relatorio.save(update_fields=campos_atualizados)


class FotoUpdateView(AppPermissionMixin, LoginRequiredMixin, View):
    app_label_required = APP_LABEL

    def post(self, request, pk):
        foto = get_object_or_404(FotoRelatorio, pk=pk)
        legenda = request.POST.get('legenda', '')
        ordem = request.POST.get('ordem')

        foto.legenda = legenda
        if ordem is not None:
            try:
                foto.ordem = int(ordem)
            except (TypeError, ValueError):
                pass
        foto.save(update_fields=['legenda', 'ordem'])
        return JsonResponse({'ok': True})


class FotoDeleteView(AppPermissionMixin, LoginRequiredMixin, View):
    app_label_required = APP_LABEL

    def post(self, request, pk):
        foto = get_object_or_404(FotoRelatorio, pk=pk)
        relatorio_pk = foto.relatorio_id
        foto.imagem.delete(save=False)
        foto.delete()
        return JsonResponse({'ok': True, 'relatorio': relatorio_pk})


class FotoReorderView(AppPermissionMixin, LoginRequiredMixin, View):
    """Recebe lista de IDs na nova ordem: {'ordem': [3,1,2,...]}"""
    app_label_required = APP_LABEL

    def post(self, request, pk):
        try:
            data = json.loads(request.body)
            ids_ordenados = data.get('ordem', [])
        except Exception:
            return JsonResponse({'ok': False}, status=400)

        with transaction.atomic():
            for i, foto_id in enumerate(ids_ordenados):
                FotoRelatorio.objects.filter(
                    pk=foto_id, relatorio_id=pk
                ).update(ordem=i + 1)

        return JsonResponse({'ok': True})


# -----------------------------------------------------------------------
# EXPORTAÇÃO — WORD e PDF
#
# As imagens já estão padronizadas (tamanho fixo, JPEG) desde o
# upload (FotoRelatorio.save), então os services usam `foto.imagem`
# diretamente — sem gerar cópias temporárias.
# -----------------------------------------------------------------------

class RelatorioExportDocxView(
    AppPermissionMixin, ViewFilialScopedMixin, RelatorioScopeMixin, DetailView
):
    app_label_required = APP_LABEL
    model = RelatorioFotografico

    def get(self, request, *args, **kwargs):
        relatorio = self.get_object()
        buffer = gerar_docx_relatorio(relatorio)

        filename = f'relatorio_fotografico_{relatorio.pk}.docx'
        response = HttpResponse(
            buffer.getvalue(),
            content_type=(
                'application/vnd.openxmlformats-officedocument'
                '.wordprocessingml.document'
            ),
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class RelatorioExportPdfView(
    AppPermissionMixin, ViewFilialScopedMixin, RelatorioScopeMixin, DetailView
):
    app_label_required = APP_LABEL
    model = RelatorioFotografico

    def get(self, request, *args, **kwargs):
        relatorio = self.get_object()
        pdf_bytes = gerar_pdf_relatorio(relatorio, request=request)

        filename = f'relatorio_fotografico_{relatorio.pk}.pdf'
        inline = request.GET.get('inline') == '1'
        disposition = 'inline' if inline else 'attachment'

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
        return response
