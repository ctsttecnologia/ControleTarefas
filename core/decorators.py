# core/decorators.py

from functools import wraps
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth.views import redirect_to_login


def _is_ajax(request):
    """Detecta se é uma requisição AJAX/JSON."""
    return (
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or 'application/json' in request.headers.get('accept', '')
        or request.content_type == 'application/json'
    )


def app_permission_required(app_label):
    """
    Decorator para function-based views que verifica se o usuário
    tem pelo menos uma permissão do app especificado.

    - Responde JSON 403 para requisições AJAX
    - Renderiza HTML 403 para requisições normais
    - Redireciona para login se não autenticado

    Uso:
        @login_required
        @app_permission_required('ata_reuniao')
        def minha_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user

            if not user.is_authenticated:
                if _is_ajax(request):
                    return JsonResponse({
                        'status': 'error',
                        'error': 'Autenticação necessária',
                    }, status=401)
                return redirect_to_login(request.get_full_path())

            if user.is_superuser:
                return view_func(request, *args, **kwargs)

            all_perms = user.get_all_permissions()
            has_perm = any(p.startswith(f'{app_label}.') for p in all_perms)

            if not has_perm:
                if _is_ajax(request):
                    return JsonResponse({
                        'status': 'error',
                        'error': 'Você não possui permissão para acessar este módulo.',
                    }, status=403)
                return render(request, 'core/acesso_negado.html', {
                    'titulo': 'Acesso Negado',
                    'mensagem': 'Você não possui permissão para acessar este módulo.',
                }, status=403)

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

