# core/middleware.py
import threading

from django.conf import settings
from django.db import close_old_connections
from django.shortcuts import render, redirect
from django.urls import reverse, resolve, Resolver404


# ════════════════════════════════════════════════════════════════════════════
# THREAD-LOCAL — Filial atual
# ════════════════════════════════════════════════════════════════════════════

_thread_locals = threading.local()


def get_current_filial():
    """
    Retorna a filial ativa do usuário logado na thread atual.
    Retorna None se não houver filial no contexto
    (ex: shell, migrations, comandos de management, requisições anônimas).
    """
    return getattr(_thread_locals, 'filial', None)


def set_current_filial(filial):
    """Define a filial atual na thread (uso interno do middleware)."""
    _thread_locals.filial = filial


def get_current_user():
    """Retorna o usuário atual da thread (utilitário extra)."""
    return getattr(_thread_locals, 'user', None)


# ════════════════════════════════════════════════════════════════════════════
# MIDDLEWARE — Filial atual
# ════════════════════════════════════════════════════════════════════════════

class CurrentFilialMiddleware:
    """
    Captura a filial ativa do usuário logado em cada request
    e a disponibiliza globalmente via get_current_filial().

    Deve ser registrado APÓS o AuthenticationMiddleware no settings.py.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        filial = None
        user = None

        if hasattr(request, 'user') and request.user.is_authenticated:
            user = request.user
            # Ajuste o atributo conforme seu modelo Usuario
            filial = getattr(request.user, 'filial_ativa', None)

        _thread_locals.user = user
        _thread_locals.filial = filial

        try:
            response = self.get_response(request)
        finally:
            # 🔒 Limpa após a resposta — evita vazamento entre requests
            _thread_locals.user = None
            _thread_locals.filial = None

        return response


# ════════════════════════════════════════════════════════════════════════════
# MIDDLEWARE — Modo de manutenção
# ════════════════════════════════════════════════════════════════════════════

class MaintenanceModeMiddleware:
    """
    Middleware para ativar modo de manutenção.
    Configure MAINTENANCE_MODE = True no settings.py para ativar.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(settings, 'MAINTENANCE_MODE', False):
            # Permite que superusuários acessem mesmo em manutenção
            if not (request.user.is_authenticated and request.user.is_superuser):
                if not request.path.startswith('/admin/') and not request.path.startswith('/static/'):
                    return render(request, 'errors/503.html', status=503)

        return self.get_response(request)


# ════════════════════════════════════════════════════════════════════════════
# MIDDLEWARE — Conexões de banco
# ════════════════════════════════════════════════════════════════════════════

class DBConnectionMiddleware:
    """Fecha conexões obsoletas antes de cada request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        close_old_connections()
        return self.get_response(request)


# ════════════════════════════════════════════════════════════════════════════
# MIDDLEWARE — Exige vínculo Funcionário
# ════════════════════════════════════════════════════════════════════════════

class ExigeFuncionarioMiddleware:
    """
    Garante que todo usuário autenticado tenha um Funcionario vinculado
    antes de acessar o sistema.

    Superusuários e usuários com permissão de RH global
    ('departamento_pessoal.view_all_departamento_pessoal') são isentos,
    pois precisam acessar o sistema justamente para fazer esse vínculo.

    Deve ser registrado APÓS AuthenticationMiddleware no settings.py.
    """

    ROTAS_LIVRES = {
        'usuario:login',
        'usuario:logout',
        'usuario:pendente_vinculo',
        'usuario:password_reset',
        'usuario:password_reset_done',
        'usuario:password_reset_confirm',
        'usuario:password_reset_complete',
        'departamento_pessoal:lista_funcionarios',
        'departamento_pessoal:funcionario_create',
        'departamento_pessoal:detalhe_funcionario',
        'departamento_pessoal:editar_funcionario',
    }

    PREFIXOS_LIVRES = (
        '/admin/',
        '/static/',
        '/media/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)

        if (
            user
            and user.is_authenticated
            and not user.is_superuser
            and not user.has_perm('departamento_pessoal.view_all_departamento_pessoal')
            and not hasattr(user, 'funcionario')
        ):
            if not self._rota_liberada(request):
                return redirect('usuario:pendente_vinculo')

        return self.get_response(request)

    def _rota_liberada(self, request):
        path = request.path

        if any(path.startswith(prefixo) for prefixo in self.PREFIXOS_LIVRES):
            return True

        try:
            match = resolve(path)
            view_name = f"{match.namespace}:{match.url_name}" if match.namespace else match.url_name
        except Resolver404:
            return True

        return view_name in self.ROTAS_LIVRES


