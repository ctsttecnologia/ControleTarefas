
# relatorio_fotografico/views.py
import io

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, View,
)
from weasyprint import HTML

from core.mixins import (
    AppPermissionMixin, ViewFilialScopedMixin, FilialCreateMixin,
)

from .models import RelatorioFotografico, FotoRelatorio
from .forms import RelatorioFotograficoForm
from .services.docx_generator import gerar_docx_relatorio
from .services.pdf_generator import gerar_pdf_relatorio


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
                Q(titulo__icontains=busca) | Q(obra_codigo__icontains=busca)
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

    def gerar_pdf_relatorio(relatorio, request=None):
        html_string = render_to_string(
            'relatorio_fotografico/relatorio_pdf.html',
            {'relatorio': relatorio, 'total_folhas': relatorio.total_folhas},
            request=request,
        )
        base_url = request.build_absolute_uri('/') if request else None
        return HTML(string=html_string, base_url=base_url).write_pdf()


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
    via POST AJAX e cria os registros FotoRelatorio.
    """
    app_label_required = APP_LABEL

    def post(self, request, pk):
        relatorio = get_object_or_404(RelatorioFotografico, pk=pk)
        arquivos = request.FILES.getlist('imagens')

        if not arquivos:
            return JsonResponse(
                {'ok': False, 'erro': 'Nenhuma imagem enviada.'}, status=400
            )

        ultima_ordem = relatorio.fotos.count()
        criadas = []

        with transaction.atomic():
            for i, arquivo in enumerate(arquivos):
                foto = FotoRelatorio.objects.create(
                    relatorio=relatorio,
                    imagem=arquivo,
                    ordem=ultima_ordem + i + 1,
                )
                criadas.append({
                    'id': foto.id,
                    'url': foto.imagem.url,
                    'ordem': foto.ordem,
                })

        return JsonResponse({'ok': True, 'fotos': criadas})


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
        import json
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
        pdf_bytes = gerar_pdf_relatorio(relatorio, request=self.request)
        filename = f'relatorio_fotografico_{relatorio.pk}.pdf'

        inline = request.GET.get('inline') == '1'
        disposition = 'inline' if inline else 'attachment'

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
        return response

