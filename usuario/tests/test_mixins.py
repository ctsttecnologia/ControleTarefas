# usuario/tests/test_mixins.py
"""
Testes dos mixins de segurança do app usuário.
"""
import pytest
from django.contrib.messages.storage.fallback import FallbackStorage
from django.forms import modelform_factory
from django.http import HttpResponse, HttpResponseRedirect
from django.test import RequestFactory
from django.views.generic import ListView, View

from usuario.mixins import (
    FilialScopedUserMixin,
    HideSuperusersMixin,
    HierarchyProtectionMixin,
    LastSuperuserProtectionMixin,
    PreventPrivilegeEscalationMixin,
    PreventSelfActionMixin,
    RequireActiveFilialMixin,
)
from usuario.models import Usuario


# Marca TODO o módulo como precisando de DB
pytestmark = pytest.mark.django_db


# =============================================================================
# HELPERS
# =============================================================================

def _add_session_and_messages(request):
    from django.contrib.sessions.backends.db import SessionStore
    request.session = SessionStore()
    setattr(request, '_messages', FallbackStorage(request))
    return request


@pytest.fixture
def rf():
    return RequestFactory()


# =============================================================================
# 1. FilialScopedUserMixin
# =============================================================================

class TestFilialScopedUserMixin:

    def _build_view(self, request):
        class DummyView(FilialScopedUserMixin, ListView):
            model = Usuario
        view = DummyView()
        view.request = request
        return view

    def test_superuser_ve_todos_os_usuarios(self, rf, superuser, usuario_comum, filial_b):
        u2 = Usuario.objects.create_user(username="outro", password="x", email="o@t.com")
        u2.filiais_permitidas.add(filial_b)

        request = rf.get("/")
        request.user = superuser

        view = self._build_view(request)
        qs = view.get_queryset()

        assert superuser in qs
        assert usuario_comum in qs
        assert u2 in qs

    def test_usuario_comum_ve_apenas_sua_filial(self, rf, usuario_comum, filial_a, filial_b):
        u_fora = Usuario.objects.create_user(username="fora", password="x", email="f@t.com")
        u_fora.filiais_permitidas.add(filial_b)

        u_dentro = Usuario.objects.create_user(username="dentro", password="x", email="d@t.com")
        u_dentro.filiais_permitidas.add(filial_a)

        request = rf.get("/")
        request.user = usuario_comum

        view = self._build_view(request)
        qs = view.get_queryset()

        assert usuario_comum in qs
        assert u_dentro in qs
        assert u_fora not in qs

    def test_queryset_sem_duplicatas(self, rf, usuario_comum, filial_a, filial_b):
        usuario_comum.filiais_permitidas.add(filial_b)

        u_multi = Usuario.objects.create_user(username="multi", password="x", email="m@t.com")
        u_multi.filiais_permitidas.add(filial_a, filial_b)

        request = rf.get("/")
        request.user = usuario_comum

        view = self._build_view(request)
        qs = view.get_queryset()

        assert list(qs).count(u_multi) == 1


# =============================================================================
# 2. HideSuperusersMixin
# =============================================================================

class TestHideSuperusersMixin:

    def _build_view(self, request):
        class DummyView(FilialScopedUserMixin, HideSuperusersMixin, ListView):
            model = Usuario
        view = DummyView()
        view.request = request
        return view

    def test_nao_superuser_nao_ve_superusers(self, rf, usuario_comum, superuser, filial_a):
        superuser.filiais_permitidas.add(filial_a)

        request = rf.get("/")
        request.user = usuario_comum

        view = self._build_view(request)
        qs = view.get_queryset()

        assert superuser not in qs
        assert usuario_comum in qs

    def test_superuser_ve_outros_superusers(self, rf, superuser):
        outro_super = Usuario.objects.create_superuser(
            username="super2", email="s2@t.com", password="x"
        )

        request = rf.get("/")
        request.user = superuser

        view = self._build_view(request)
        qs = view.get_queryset()

        assert superuser in qs
        assert outro_super in qs


# =============================================================================
# 3. HierarchyProtectionMixin
# =============================================================================

class TestHierarchyProtectionMixin:

    def _build_view(self, request, target_user):
        class DummyView(HierarchyProtectionMixin, View):
            def get_object(self_inner):
                return target_user

            def get(self_inner, *args, **kwargs):
                return HttpResponse("ok")

        view = DummyView()
        view.request = request
        view.kwargs = {}
        return view

    def test_nao_super_bloqueado_ao_editar_super(self, rf, usuario_comum, superuser):
        request = rf.get("/")
        request.user = usuario_comum
        _add_session_and_messages(request)

        view = self._build_view(request, target_user=superuser)
        response = view.dispatch(request)

        assert response.status_code == 302

    def test_super_pode_editar_outro_super(self, rf, superuser):
        outro_super = Usuario.objects.create_superuser(
            username="s2", email="s2@t.com", password="x"
        )

        request = rf.get("/")
        request.user = superuser
        _add_session_and_messages(request)

        view = self._build_view(request, target_user=outro_super)
        response = view.dispatch(request)

        assert response.status_code == 200

    def test_nao_super_pode_editar_user_comum(self, rf, usuario_comum):
        outro_comum = Usuario.objects.create_user(
            username="u2", email="u2@t.com", password="x"
        )

        request = rf.get("/")
        request.user = usuario_comum
        _add_session_and_messages(request)

        view = self._build_view(request, target_user=outro_comum)
        response = view.dispatch(request)

        assert response.status_code == 200


# =============================================================================
# 4. PreventSelfActionMixin
# =============================================================================

class TestPreventSelfActionMixin:

    def _build_view(self, request, target_user=None, pk=None):
        class DummyView(PreventSelfActionMixin, View):
            def get_object(self_inner):
                if target_user is None:
                    raise Exception("no object")
                return target_user

            def get(self_inner, *args, **kwargs):
                return HttpResponse("ok")

        view = DummyView()
        view.request = request
        view.kwargs = {"pk": pk} if pk else {}
        return view

    def test_usuario_nao_pode_agir_sobre_si_mesmo(self, rf, usuario_comum):
        request = rf.get("/")
        request.user = usuario_comum
        _add_session_and_messages(request)

        view = self._build_view(request, target_user=usuario_comum)
        response = view.dispatch(request)

        assert response.status_code == 302

    def test_usuario_pode_agir_sobre_outro(self, rf, usuario_comum):
        outro = Usuario.objects.create_user(username="o", email="o@t.com", password="x")

        request = rf.get("/")
        request.user = usuario_comum
        _add_session_and_messages(request)

        view = self._build_view(request, target_user=outro)
        response = view.dispatch(request)

        assert response.status_code == 200

    def test_fallback_via_pk_em_kwargs(self, rf, usuario_comum):
        request = rf.get("/")
        request.user = usuario_comum
        _add_session_and_messages(request)

        class DummyView(PreventSelfActionMixin, View):
            def get(self_inner, *args, **kwargs):
                return HttpResponse("ok")

        view = DummyView()
        view.request = request
        view.kwargs = {"pk": usuario_comum.pk}

        response = view.dispatch(request)
        assert response.status_code == 302


# =============================================================================
# 5. LastSuperuserProtectionMixin
# =============================================================================

class TestLastSuperuserProtectionMixin:

    def _build_view(self, request, target_user):
        class DummyView(LastSuperuserProtectionMixin, View):
            def get_object(self_inner):
                return target_user

            def get(self_inner, *args, **kwargs):
                return HttpResponse("ok")

        view = DummyView()
        view.request = request
        view.kwargs = {}
        return view

    def test_bloqueia_desativar_ultimo_super(self, rf, superuser):
        request = rf.get("/")
        request.user = superuser
        _add_session_and_messages(request)

        view = self._build_view(request, target_user=superuser)
        response = view.dispatch(request)

        assert response.status_code == 302

    def test_permite_quando_ha_mais_de_um_super(self, rf, superuser):
        Usuario.objects.create_superuser(
            username="s2", email="s2@t.com", password="x"
        )

        request = rf.get("/")
        request.user = superuser
        _add_session_and_messages(request)

        view = self._build_view(request, target_user=superuser)
        response = view.dispatch(request)

        assert response.status_code == 200

    def test_nao_aplica_em_usuario_comum(self, rf, superuser, usuario_comum):
        request = rf.get("/")
        request.user = superuser
        _add_session_and_messages(request)

        view = self._build_view(request, target_user=usuario_comum)
        response = view.dispatch(request)

        assert response.status_code == 200

    def test_nao_aplica_em_super_inativo(self, rf, superuser):
        superuser.is_active = False
        superuser.save()

        request = rf.get("/")
        request.user = superuser
        _add_session_and_messages(request)

        view = self._build_view(request, target_user=superuser)
        response = view.dispatch(request)

        assert response.status_code == 200


# =============================================================================
# 6. PreventPrivilegeEscalationMixin
# =============================================================================

class TestPreventPrivilegeEscalationMixin:
    """
    Testa o form_valid do mixin usando um "pai fake" que apenas salva
    o form (simulando o UpdateView/CreateView sem redirect real).
    """

    def _build_view(self, request, instance=None):
        class FakeParent:
            """Simula UpdateView.form_valid: salva e retorna redirect."""
            def form_valid(self_inner, form):
                form.save()
                return HttpResponseRedirect("/ok/")

        class FinalView(PreventPrivilegeEscalationMixin, FakeParent):
            pass

        view = FinalView()
        view.request = request
        if instance is not None:
            view.object = instance
            view.kwargs = {"pk": instance.pk}
        else:
            view.kwargs = {}
        return view

    def test_gerente_nao_consegue_promover_via_form(self, rf, usuario_comum):
        """Mesmo com POST malicioso, o mixin reverte is_superuser/is_staff."""
        alvo = Usuario.objects.create_user(
            username="alvo", email="a@t.com", password="x",
            is_superuser=False, is_staff=False,
        )

        request = rf.post("/", data={})
        request.user = usuario_comum  # NÃO é superuser

        view = self._build_view(request, instance=alvo)

        Form = modelform_factory(Usuario, fields=["username", "is_superuser", "is_staff"])
        form = Form(
            data={"username": "alvo", "is_superuser": True, "is_staff": True},
            instance=alvo,
        )
        assert form.is_valid(), form.errors

        view.form_valid(form)

        alvo.refresh_from_db()
        assert alvo.is_superuser is False
        assert alvo.is_staff is False

    def test_superuser_pode_promover_via_form(self, rf, superuser):
        """Superuser legítimo consegue promover outro usuário."""
        alvo = Usuario.objects.create_user(
            username="alvo2", email="a2@t.com", password="x",
            is_superuser=False, is_staff=False,
        )

        request = rf.post("/", data={})
        request.user = superuser

        view = self._build_view(request, instance=alvo)

        Form = modelform_factory(Usuario, fields=["username", "is_superuser", "is_staff"])
        form = Form(
            data={"username": "alvo2", "is_superuser": True, "is_staff": True},
            instance=alvo,
        )
        assert form.is_valid(), form.errors

        view.form_valid(form)

        alvo.refresh_from_db()
        assert alvo.is_superuser is True
        assert alvo.is_staff is True


# =============================================================================
# 7. RequireActiveFilialMixin
# =============================================================================

class TestRequireActiveFilialMixin:

    def _build_view(self):
        class DummyView(RequireActiveFilialMixin, View):
            def get(self_inner, *args, **kwargs):
                return HttpResponse("ok")
        return DummyView()

    def test_bloqueia_sem_filial_ativa(self, rf, usuario_comum):
        request = rf.get("/")
        request.user = usuario_comum
        _add_session_and_messages(request)

        view = self._build_view()
        view.request = request
        view.kwargs = {}

        response = view.dispatch(request)
        assert response.status_code == 302

    def test_permite_com_filial_ativa(self, rf, usuario_comum, filial_a):
        request = rf.get("/")
        request.user = usuario_comum
        _add_session_and_messages(request)
        request.session["active_filial_id"] = filial_a.pk

        view = self._build_view()
        view.request = request
        view.kwargs = {}

        response = view.dispatch(request)
        assert response.status_code == 200

    def test_superuser_passa_mesmo_sem_filial_ativa(self, rf, superuser):
        request = rf.get("/")
        request.user = superuser
        _add_session_and_messages(request)

        view = self._build_view()
        view.request = request
        view.kwargs = {}

        response = view.dispatch(request)
        assert response.status_code == 200
