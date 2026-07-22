
# relatorio_fotografico/api_views.py
from django.db import transaction
from django.http import HttpResponse
from django.db.models import Q
from rest_framework import viewsets, permissions, status, parsers
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import RelatorioFotografico, FotoRelatorio
from .serializers import (
    RelatorioFotograficoSerializer,
    RelatorioFotograficoListSerializer,
    FotoRelatorioSerializer,
)
from .services.docx_generator import gerar_docx_relatorio
from .services.pdf_generator import gerar_pdf_relatorio

APP_LABEL = 'relatorio_fotografico'


class RelatorioFotograficoViewSet(viewsets.ModelViewSet):
    """
    CRUD completo + ações de exportação e upload de fotos,
    reaproveitando as mesmas regras de escopo das views web.
    """
    serializer_class = RelatorioFotograficoSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    def get_serializer_class(self):
        if self.action == 'list':
            return RelatorioFotograficoListSerializer
        return RelatorioFotograficoSerializer

    def get_queryset(self):
        user = self.request.user
        filial_ativa = getattr(self.request, 'filial_ativa', None) or getattr(user, 'filial_ativa', None)

        qs = RelatorioFotografico.objects.all()
        if filial_ativa is not None:
            qs = qs.filter(filial=filial_ativa)

        if not (
            user.is_superuser
            or user.has_perm(f'{APP_LABEL}.view_all_relatorios_filial')
        ):
            qs = qs.filter(Q(responsavel=user) | Q(criado_por=user)).distinct()

        busca = self.request.query_params.get('q')
        status_ = self.request.query_params.get('status')
        if busca:
            qs = qs.filter(Q(titulo__icontains=busca) | Q(obra_contrato__icontains=busca))
        if status_:
            qs = qs.filter(status=status_)

        return qs.order_by('-data', '-created_at')

    def perform_create(self, serializer):
        user = self.request.user
        filial_ativa = getattr(self.request, 'filial_ativa', None) or getattr(user, 'filial_ativa', None)

        if filial_ativa is None:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'filial': 'Usuário sem filial ativa definida.'})

        serializer.save(
            responsavel=user,
            filial=filial_ativa,
        )

    # --- Upload de fotos (multipart, múltiplos arquivos) ---
    @action(detail=True, methods=['post'], url_path='fotos/upload')
    def upload_fotos(self, request, pk=None):
        relatorio = self.get_object()
        arquivos = request.FILES.getlist('imagens')

        if not arquivos:
            return Response(
                {'ok': False, 'erro': 'Nenhuma imagem enviada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        criadas = []
        with transaction.atomic():
            relatorio_locked = (
                RelatorioFotografico.objects.select_for_update().get(pk=relatorio.pk)
            )
            ultima_ordem = relatorio_locked.fotos.count()
            for i, arquivo in enumerate(arquivos):
                foto = FotoRelatorio.objects.create(
                    relatorio=relatorio_locked,
                    imagem=arquivo,
                    ordem=ultima_ordem + i + 1,
                )
                criadas.append(
                    FotoRelatorioSerializer(foto, context={'request': request}).data
                )

        return Response({'ok': True, 'fotos': criadas}, status=status.HTTP_201_CREATED)

    # --- Reordenar fotos ---
    @action(detail=True, methods=['post'], url_path='fotos/reordenar')
    def reordenar_fotos(self, request, pk=None):
        ids_ordenados = request.data.get('ordem', [])
        with transaction.atomic():
            for i, foto_id in enumerate(ids_ordenados):
                FotoRelatorio.objects.filter(pk=foto_id, relatorio_id=pk).update(ordem=i + 1)
        return Response({'ok': True})

    # --- Exportar PDF ---
    @action(detail=True, methods=['get'], url_path='exportar/pdf')
    def exportar_pdf(self, request, pk=None):
        relatorio = self.get_object()
        pdf_bytes = gerar_pdf_relatorio(relatorio, request=request)

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="relatorio_{relatorio.pk}.pdf"'
        )
        return response

    # --- Exportar DOCX ---
    @action(detail=True, methods=['get'], url_path='exportar/docx')
    def exportar_docx(self, request, pk=None):
        relatorio = self.get_object()
        buffer = gerar_docx_relatorio(relatorio)

        response = HttpResponse(
            buffer.getvalue(),
            content_type=(
                'application/vnd.openxmlformats-officedocument'
                '.wordprocessingml.document'
            ),
        )
        response['Content-Disposition'] = f'attachment; filename="relatorio_{relatorio.pk}.docx"'
        return response


class FotoRelatorioViewSet(viewsets.ModelViewSet):
    """
    CRUD de fotos isoladas via API (usado por telas de edição de
    legenda/ordem). Escopado para as fotos dos relatórios que o
    usuário pode acessar — evita que qualquer usuário autenticado
    edite/exclua fotos de relatórios de terceiros só sabendo o ID.
    """
    serializer_class = FotoRelatorioSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def get_queryset(self):
        user = self.request.user
        qs = FotoRelatorio.objects.select_related('relatorio')

        if user.is_superuser or user.has_perm(
            f'{APP_LABEL}.view_all_relatorios_filial'
        ):
            return qs

        return qs.filter(
            Q(relatorio__responsavel=user) | Q(relatorio__criado_por=user)
        ).distinct()

