
# core/decorators.py

from functools import wraps
from django.shortcuts import render
from django.contrib.auth.views import redirect_to_login


def app_permission_required(app_label):
    """
    Decorator para function-based views que verifica se o usuário
    tem pelo menos uma permissão do app especificado.

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
                return redirect_to_login(request.get_full_path())

            if user.is_superuser:
                return view_func(request, *args, **kwargs)

            all_perms = user.get_all_permissions()
            has_perm = any(p.startswith(f'{app_label}.') for p in all_perms)

            if not has_perm:
                return render(request, 'core/acesso_negado.html', {
                    'titulo': 'Acesso Negado',
                    'mensagem': 'Você não possui permissão para acessar este módulo.',
                }, status=403)

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

