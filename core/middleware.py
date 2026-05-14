# core/middleware.py

import threading

from django.conf import settings
from django.db import close_old_connections
from django.shortcuts import render


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

