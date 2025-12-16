
# api/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import authenticate
from django.utils import timezone
from django.core.files.base import ContentFile
import base64
import uuid

from tarefas.models import Tarefas, Comentario
from automovel.models import Carro, Carro_agendamento, Carro_checklist
from seguranca_trabalho.models import FichaEPI, EntregaEPI
from ferramentas.models import TermoDeResponsabilidade

from .serializers import (
    UserSerializer,
    TarefaListSerializer, TarefaDetailSerializer, ComentarioSerializer,
    CarroSerializer, AgendamentoListSerializer, AgendamentoDetailSerializer, ChecklistSerializer,
    FichaEPIListSerializer, FichaEPIDetailSerializer, EntregaEPISerializer,
    TermoListSerializer, TermoDetailSerializer,
    AssinaturaSerializer
)


# ===================== AUTENTICAÇÃO =====================
class LoginView(APIView):
    """
    POST /api/auth/login/
    Body: {"email": "user@example.com", "password": "senha123"}
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response(
                {'error': 'Email e senha são obrigatórios.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(request, username=email, password=password)

        if user is None:
            return Response(
                {'error': 'Credenciais inválidas.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_active:
            return Response(
                {'error': 'Usuário inativo.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        token, created = Token.objects.get_or_create(user=user)
        
        # Configura a filial ativa na sessão
        if hasattr(user, 'filial_ativa') and user.filial_ativa:
            request.session['active_filial_id'] = user.filial_ativa.id

        return Response({
            'token': token.key,
            'user': UserSerializer(user).data
        })


class LogoutView(APIView):
    """POST /api/auth/logout/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            request.user.auth_token.delete()
            return Response({'message': 'Logout realizado com sucesso.'})
        except Exception:
            return Response({'message': 'Logout realizado.'})


class MeView(APIView):
    """GET /api/auth/me/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


# ===================== HELPER PARA FILIAL =====================
def setup_filial_session(request):
    """Configura a sessão com a filial ativa do usuário."""
    user = request.user
    if user.is_authenticated and hasattr(user, 'filial_ativa') and user.filial_ativa:
        request.session['active_filial_id'] = user.filial_ativa.id


# ===================== TAREFAS =====================
class TarefaViewSet(viewsets.ModelViewSet):
    """API para gerenciar Tarefas."""
    queryset = Tarefas.objects.all()  # Queryset base (será filtrado)
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        setup_filial_session(self.request)
        queryset = Tarefas.objects.for_request(self.request).order_by('-data_criacao')
        
        # Filtros opcionais
        status_filter = self.request.query_params.get('status')
        prioridade = self.request.query_params.get('prioridade')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if prioridade:
            queryset = queryset.filter(prioridade=prioridade)
            
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return TarefaListSerializer
        return TarefaDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            usuario=self.request.user,
            filial=self.request.user.filial_ativa
        )

    @action(detail=True, methods=['post'])
    def alterar_status(self, request, pk=None):
        """POST /api/tarefas/{id}/alterar_status/"""
        tarefa = self.get_object()
        novo_status = request.data.get('status')
        
        status_validos = dict(Tarefas.STATUS_CHOICES).keys()
        if novo_status not in status_validos:
            return Response(
                {'error': f'Status inválido. Opções: {list(status_validos)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        tarefa._user = request.user
        tarefa.status = novo_status
        tarefa.save()
        
        return Response({
            'message': f'Status alterado para {novo_status}',
            'tarefa': TarefaDetailSerializer(tarefa).data
        })

    @action(detail=True, methods=['get', 'post'])
    def comentarios(self, request, pk=None):
        """GET/POST /api/tarefas/{id}/comentarios/"""
        tarefa = self.get_object()
        
        if request.method == 'GET':
            comentarios = tarefa.comentarios.all()
            return Response(ComentarioSerializer(comentarios, many=True).data)
        
        elif request.method == 'POST':
            serializer = ComentarioSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(
                    tarefa=tarefa,
                    autor=request.user,
                    filial=request.user.filial_ativa
                )
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ===================== AUTOMÓVEL =====================
class CarroViewSet(viewsets.ReadOnlyModelViewSet):
    """API para listar carros."""
    queryset = Carro.objects.all()
    serializer_class = CarroSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        setup_filial_session(self.request)
        queryset = Carro.objects.for_request(self.request).filter(ativo=True)
        
        disponivel = self.request.query_params.get('disponivel')
        if disponivel is not None:
            queryset = queryset.filter(disponivel=disponivel.lower() == 'true')
            
        return queryset


class AgendamentoViewSet(viewsets.ModelViewSet):
    """API para gerenciar agendamentos de veículos."""
    queryset = Carro_agendamento.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        setup_filial_session(self.request)
        queryset = Carro_agendamento.objects.for_request(self.request)
        queryset = queryset.select_related('carro').order_by('-data_hora_agenda')
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return AgendamentoListSerializer
        return AgendamentoDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            usuario=self.request.user,
            filial=self.request.user.filial_ativa
        )


class ChecklistViewSet(viewsets.ModelViewSet):
    """API para Checklists de veículos."""
    queryset = Carro_checklist.objects.all()
    serializer_class = ChecklistSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        setup_filial_session(self.request)
        return Carro_checklist.objects.for_request(self.request)

    def create(self, request, *args, **kwargs):
        """Processa imagens Base64 antes de salvar."""
        data = request.data.copy()

        foto_fields = [
            'foto_frontal', 'foto_trazeira',
            'foto_lado_motorista', 'foto_lado_passageiro'
        ]

        for field in foto_fields:
            base64_data = data.get(field)
            if base64_data and isinstance(base64_data, str):
                if base64_data.startswith('data:image'):
                    format_part, imgstr = base64_data.split(';base64,')
                    ext = format_part.split('/')[-1]
                    filename = f"{field}_{uuid.uuid4().hex[:8]}.{ext}"
                    data[field] = ContentFile(
                        base64.b64decode(imgstr),
                        name=filename
                    )

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            usuario=self.request.user,
            filial=self.request.user.filial_ativa
        )
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ===================== SEGURANÇA DO TRABALHO =====================
class FichaEPIViewSet(viewsets.ReadOnlyModelViewSet):
    """API para consultar Fichas de EPI."""
    queryset = FichaEPI.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        setup_filial_session(self.request)
        return FichaEPI.objects.for_request(self.request).select_related('funcionario')

    def get_serializer_class(self):
        if self.action == 'list':
            return FichaEPIListSerializer
        return FichaEPIDetailSerializer

    @action(detail=True, methods=['get'])
    def pendentes(self, request, pk=None):
        """GET /api/fichas-epi/{id}/pendentes/"""
        ficha = self.get_object()
        pendentes = ficha.entregas.filter(
            assinatura_recebimento__isnull=True,
            assinatura_imagem__isnull=True
        ).order_by('-criado_em')
        
        return Response(EntregaEPISerializer(pendentes, many=True).data)


class EntregaEPIViewSet(viewsets.ModelViewSet):
    """API para gerenciar entregas de EPI."""
    queryset = EntregaEPI.objects.all()
    serializer_class = EntregaEPISerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        setup_filial_session(self.request)
        return EntregaEPI.objects.for_request(self.request).select_related('equipamento')

    @action(detail=True, methods=['post'])
    def assinar(self, request, pk=None):
        """POST /api/entregas-epi/{id}/assinar/"""
        entrega = self.get_object()

        if entrega.assinatura_recebimento or entrega.assinatura_imagem:
            return Response(
                {'error': 'Esta entrega já foi assinada.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = AssinaturaSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        assinatura_base64 = serializer.validated_data['assinatura_base64']

        if assinatura_base64.startswith('data:image'):
            format_part, imgstr = assinatura_base64.split(';base64,')
            ext = format_part.split('/')[-1]
            filename = f"assinatura_epi_{entrega.pk}_{uuid.uuid4().hex[:8]}.{ext}"
            entrega.assinatura_imagem.save(
                filename,
                ContentFile(base64.b64decode(imgstr))
            )

        entrega.assinatura_recebimento = assinatura_base64
        entrega.data_assinatura = timezone.now()
        entrega.save()

        return Response({
            'message': 'Assinatura registrada com sucesso!',
            'entrega': EntregaEPISerializer(entrega).data
        })


# ===================== TERMOS DE RESPONSABILIDADE =====================
class TermoViewSet(viewsets.ReadOnlyModelViewSet):
    """API para Termos de Responsabilidade."""
    queryset = TermoDeResponsabilidade.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        setup_filial_session(self.request)
        queryset = TermoDeResponsabilidade.objects.for_request(self.request)
        queryset = queryset.select_related('responsavel').prefetch_related('itens')
        return queryset.order_by('-data_emissao')

    def get_serializer_class(self):
        if self.action == 'list':
            return TermoListSerializer
        return TermoDetailSerializer

    @action(detail=True, methods=['post'])
    def assinar(self, request, pk=None):
        """POST /api/termos/{id}/assinar/"""
        termo = self.get_object()

        if termo.is_signed():
            return Response(
                {'error': 'Este termo já foi assinado.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = AssinaturaSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        termo.assinatura_data = serializer.validated_data['assinatura_base64']
        termo.data_recebimento = timezone.now()
        termo.save()

        return Response({
            'message': 'Termo assinado com sucesso!',
            'termo': TermoDetailSerializer(termo).data
        })


