
# relatorio_fotografico/api_views.py
from django.db import IntegrityError, transaction
from django.db.models import Max, Q
from django.http import HttpResponse
from rest_framework import parsers, permissions, status, viewsets
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from .models import FotoRelatorio, RelatorioFotografico, RelatorioVisao
from .serializers import (
    FotoRelatorioSerializer,
    RelatorioFotograficoListSerializer,
    RelatorioFotograficoSerializer,
)
from .services.docx_generator import gerar_docx_relatorio
from .services.pdf_generator import gerar_pdf_relatorio
from .views import (
    APP_LABEL, PERM_ADD, PERM_CHANGE, PERM_DELETE, PERM_FOTO_ADD,
    PERM_FOTO_CHANGE, PERM_FOTO_DELETE, PERM_VIEW, PERM_VIEW_ALL,
    _coord, _destruir_cloudinary, is_admin,
)

PERM_VISAO_ADD = f'{APP_LABEL}.add_relatoriovisao'
PERM_VISAO_CHANGE = f'{APP_LABEL}.change_relatoriovisao'
PERM_VISAO_DELETE = f'{APP_LABEL}.delete_relatoriovisao'
PERM_VISAO_VIEW = f'{APP_LABEL}.view_relatoriovisao'

PARSERS = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]
AUTH = [TokenAuthentication, SessionAuthentication]  # Token p/ n8n, sessão p/ front


# -----------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------

def _filial_ativa(request):
    return (getattr(request, 'filial_ativa', None)
            or getattr(request.user, 'filial_ativa', None))


def relatorios_escopados(request):
    """Mesmas regras das views web: filial + escopo vertical."""
    user = request.user
    qs = RelatorioFotografico.objects.all()

    filial = _filial_ativa(request)
    if filial is not None:
        qs = qs.filter(filial=filial)
    elif not is_admin(user):
        return qs.none()  # sem filial ativa não vê nada

    if not (is_admin(user) or user.has_perm(PERM_VIEW_ALL)):
        qs = qs.filter(Q(responsavel=user) | Q(criado_por=user))
    return qs


def _finalizado(relatorio):
    return relatorio.status == RelatorioFotografico.STATUS_FINALIZADO


def _checar_editavel(request, relatorio):
    if _finalizado(relatorio) and not is_admin(request.user):
        raise PermissionDenied('Relatório finalizado não pode ser alterado.')


class ActionPermission(permissions.BasePermission):
    """Exige a permissão mapeada em view.action_perms[action][method]."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if is_admin(user):
            return True
        regra = view.action_perms.get(view.action)
        if isinstance(regra, dict):
            regra = regra.get(request.method)
        return bool(regra) and user.has_perm(regra)


# -----------------------------------------------------------------------
# RELATÓRIOS
# -----------------------------------------------------------------------

class RelatorioFotograficoViewSet(viewsets.ModelViewSet):
    authentication_classes = AUTH
    permission_classes = [ActionPermission]
    parser_classes = PARSERS

    action_perms = {
        'list': PERM_VIEW,
        'retrieve': PERM_VIEW,
        'create': PERM_ADD,
        'update': PERM_CHANGE,
        'partial_update': PERM_CHANGE,
        'destroy': PERM_DELETE,
        'upload_fotos': PERM_FOTO_ADD,
        'reordenar_fotos': PERM_FOTO_CHANGE,
        'exportar_pdf': PERM_VIEW,
        'exportar_docx': PERM_VIEW,
        'visao': {'GET': PERM_VISAO_VIEW, 'POST': PERM_VISAO_ADD},
    }

    def get_serializer_class(self):
        if self.action == 'list':
            return RelatorioFotograficoListSerializer
        return RelatorioFotograficoSerializer

    def get_queryset(self):
        qs = relatorios_escopados(self.request)
        p = self.request.query_params

        busca = (p.get('q') or '').strip()
        status_ = (p.get('status') or '').strip()
        if busca:
            qs = qs.filter(
                Q(titulo__icontains=busca)
                | Q(obra_contrato__icontains=busca)
                | Q(empresa__icontains=busca)
            )
        if status_ in dict(RelatorioFotografico.STATUS_CHOICES):
            qs = qs.filter(status=status_)

        if self.action == 'list':
            qs = qs.select_related('responsavel', 'filial').prefetch_related('fotos')
        return qs.order_by('-data', '-created_at')

    def perform_create(self, serializer):
        filial = _filial_ativa(self.request)
        if filial is None:
            raise ValidationError({'filial': 'Usuário sem filial ativa definida.'})
        user = self.request.user
        serializer.save(criado_por=user, responsavel=user, filial=filial)

    def perform_update(self, serializer):
        _checar_editavel(self.request, serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        public_ids = [
            f.imagem.public_id for f in instance.fotos.all()
            if getattr(f.imagem, 'public_id', None)
        ]
        with transaction.atomic():
            instance.delete()
            for pid in public_ids:
                transaction.on_commit(lambda p=pid: _destruir_cloudinary(p))

    # --- Upload de fotos ---
    @action(detail=True, methods=['post'], url_path='fotos/upload')
    def upload_fotos(self, request, pk=None):
        relatorio = self.get_object()  # valida escopo
        arquivos = request.FILES.getlist('imagens')
        if not arquivos:
            return Response({'ok': False, 'erro': 'Nenhuma imagem enviada.'},
                            status=status.HTTP_400_BAD_REQUEST)

        legendas = request.data.getlist('legendas')
        latitudes = request.data.getlist('latitudes')
        longitudes = request.data.getlist('longitudes')

        criadas = []
        with transaction.atomic():
            relatorio = RelatorioFotografico.objects.select_for_update().get(pk=relatorio.pk)
            if _finalizado(relatorio):
                return Response(
                    {'ok': False, 'erro': 'Relatório finalizado não aceita novas fotos.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            ultima = relatorio.fotos.aggregate(m=Max('ordem'))['m'] or 0
            for i, arquivo in enumerate(arquivos):
                foto = FotoRelatorio.objects.create(
                    relatorio=relatorio,
                    imagem=arquivo,
                    legenda=legendas[i] if i < len(legendas) else '',
                    ordem=ultima + i + 1,
                    latitude=_coord(latitudes, i),
                    longitude=_coord(longitudes, i),
                )
                criadas.append(FotoRelatorioSerializer(foto, context={'request': request}).data)

        return Response({'ok': True, 'fotos': criadas}, status=status.HTTP_201_CREATED)

    # --- Reordenar fotos ---
    @action(detail=True, methods=['patch'], url_path='fotos/reordenar')
    def reordenar_fotos(self, request, pk=None):
        relatorio = self.get_object()  # valida escopo
        _checar_editavel(request, relatorio)

        itens = request.data.get('ordem', [])
        if not isinstance(itens, list) or not itens:
            return Response({'ok': False, 'erro': 'Lista de ordem inválida.'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            ids = [int(x.get('id') if isinstance(x, dict) else x) for x in itens]
        except (TypeError, ValueError):
            return Response({'ok': False, 'erro': 'IDs inválidos.'},
                            status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            for i, foto_id in enumerate(ids, start=1):
                FotoRelatorio.objects.filter(pk=foto_id, relatorio=relatorio).update(ordem=i)
        return Response({'ok': True})

    # --- Exportações ---
    @action(detail=True, methods=['get'], url_path='exportar/pdf')
    def exportar_pdf(self, request, pk=None):
        relatorio = self.get_object()
        response = HttpResponse(gerar_pdf_relatorio(relatorio, request=request),
                                content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="relatorio_{relatorio.pk}.pdf"'
        return response

    @action(detail=True, methods=['get'], url_path='exportar/docx')
    def exportar_docx(self, request, pk=None):
        relatorio = self.get_object()
        response = HttpResponse(
            gerar_docx_relatorio(relatorio).getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
        response['Content-Disposition'] = f'attachment; filename="relatorio_{relatorio.pk}.docx"'
        return response

    # --- Visão (n8n) ---
    @action(detail=True, methods=['get', 'post'], url_path='visao')
    def visao(self, request, pk=None):
        relatorio = self.get_object()  # valida escopo

        if request.method == 'GET':
            return Response([self._visao_dict(v) for v in relatorio.visoes.all()])

        resultado = request.data.get('resultado')
        if resultado is None:
            return Response({'ok': False, 'erro': 'Campo "resultado" é obrigatório.'},
                            status=status.HTTP_400_BAD_REQUEST)

        foto = None
        foto_id = request.data.get('foto_id')
        if foto_id not in (None, ''):
            foto = relatorio.fotos.filter(pk=foto_id).first() if str(foto_id).isdigit() else None
            if foto is None:
                return Response({'ok': False, 'erro': 'Foto não pertence ao relatório.'},
                                status=status.HTTP_400_BAD_REQUEST)

        execucao_id = (str(request.data.get('execucao_id') or '').strip()[:100]) or None
        dados = {
            'foto': foto,
            'resultado': resultado,
            'modelo': str(request.data.get('modelo') or '')[:100],
        }

        if execucao_id is None:
            obj, criado = RelatorioVisao.objects.create(relatorio=relatorio, **dados), True
        else:
            try:
                with transaction.atomic():
                    obj, criado = RelatorioVisao.objects.get_or_create(
                        relatorio=relatorio, execucao_id=execucao_id, defaults=dados,
                    )
            except IntegrityError:  # corrida entre retries do n8n
                obj = RelatorioVisao.objects.get(relatorio=relatorio, execucao_id=execucao_id)
                criado = False

        return Response(
            {'ok': True, 'criado': criado, 'visao': self._visao_dict(obj)},
            status=status.HTTP_201_CREATED if criado else status.HTTP_200_OK,
        )

    @staticmethod
    def _visao_dict(v):
        return {
            'id': v.id,
            'relatorio': v.relatorio_id,
            'foto': v.foto_id,
            'execucao_id': v.execucao_id,
            'modelo': v.modelo,
            'resultado': v.resultado,
            'created_at': v.created_at,
        }


# -----------------------------------------------------------------------
# FOTOS
# -----------------------------------------------------------------------

class FotoRelatorioViewSet(viewsets.ModelViewSet):
    serializer_class = FotoRelatorioSerializer
    authentication_classes = AUTH
    permission_classes = [ActionPermission]
    parser_classes = PARSERS

    action_perms = {
        'list': PERM_VIEW,
        'retrieve': PERM_VIEW,
        'create': PERM_FOTO_ADD,
        'update': PERM_FOTO_CHANGE,
        'partial_update': PERM_FOTO_CHANGE,
        'destroy': PERM_FOTO_DELETE,
    }

    def get_queryset(self):
        return (
            FotoRelatorio.objects.select_related('relatorio')
            .filter(relatorio__in=relatorios_escopados(self.request))
            .order_by('relatorio_id', 'ordem')
        )

    def _validar_relatorio(self, relatorio):
        if not relatorios_escopados(self.request).filter(pk=relatorio.pk).exists():
            raise PermissionDenied('Relatório fora do seu escopo.')
        _checar_editavel(self.request, relatorio)

    def perform_create(self, serializer):
        self._validar_relatorio(serializer.validated_data['relatorio'])
        serializer.save()

    def perform_update(self, serializer):
        self._validar_relatorio(serializer.instance.relatorio)
        novo = serializer.validated_data.get('relatorio')
        if novo and novo.pk != serializer.instance.relatorio_id:
            raise ValidationError({'relatorio': 'Não é permitido mover a foto de relatório.'})
        serializer.save()

    def perform_destroy(self, instance):
        _checar_editavel(self.request, instance.relatorio)
        public_id = getattr(instance.imagem, 'public_id', None)
        with transaction.atomic():
            instance.delete()
            if public_id:
                transaction.on_commit(lambda: _destruir_cloudinary(public_id))


