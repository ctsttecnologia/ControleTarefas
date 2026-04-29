# core/decorators.py
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import NoReverseMatch, reverse


def _is_ajax(request):
    """Detecta se eh uma requisicao AJAX/JSON."""
    return (
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or 'application/json' in request.headers.get('accept', '')
        or request.content_type == 'application/json'
    )


# =============================================================================
# == app_permission_required
# =============================================================================

def app_permission_required(app_label):
    """
    Decorator para function-based views que verifica se o usuario
    tem pelo menos uma permissao do app especificado.

    - Responde JSON 403 para requisicoes AJAX
    - Renderiza HTML 403 para requisicoes normais
    - Redireciona para login se nao autenticado

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
                        'error': 'Autenticacao necessaria',
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
                        'error': 'Voce nao possui permissao para acessar este modulo.',
                    }, status=403)
                return render(request, 'core/acesso_negado.html', {
                    'titulo': 'Acesso Negado',
                    'mensagem': 'Voce nao possui permissao para acessar este modulo.',
                }, status=403)

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


# =============================================================================
# == funcionario_required
# =============================================================================

def funcionario_required(view_func):
    """
    Decorator que exige login + vinculo com Funcionario ativo.
    Equivalente ao FuncionarioRequiredMixin para FBVs.

    Comportamento (espelhado do mixin):
      - Nao autenticado          -> redirect_to_login (ou JSON 401 se AJAX)
      - Superuser                -> passa direto (nao precisa de Funcionario)
      - Sem Funcionario vinculado -> redireciona para 'core:sem_funcionario'
                                     (ou JSON 403 se AJAX)
      - Funcionario inativo       -> mesmo tratamento
      - Sucesso                   -> injeta request.funcionario e prossegue

    Uso:
        @funcionario_required
        def minha_view(request):
            funcionario = request.funcionario
            ...
    """
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        user = request.user

        # 1. Nao autenticado
        if not user.is_authenticated:
            if _is_ajax(request):
                return JsonResponse(
                    {"status": "error", "error": "Autenticacao necessaria."},
                    status=401,
                )
            return redirect_to_login(request.get_full_path())

        # 2. Superuser bypass (consistente com o mixin)
        if user.is_superuser:
            request.funcionario = getattr(user, "funcionario", None)
            return view_func(request, *args, **kwargs)

        # 3. Validacao do vinculo Funcionario
        funcionario = getattr(user, "funcionario", None)
        if not funcionario or not getattr(funcionario, "ativo", True):
            if _is_ajax(request):
                return JsonResponse(
                    {
                        "status": "error",
                        "error": "Acesso negado: funcionario nao vinculado ou inativo.",
                    },
                    status=403,
                )
            try:
                return redirect(reverse("core:sem_funcionario"))
            except NoReverseMatch:
                return render(
                    request,
                    "core/acesso_negado.html",
                    {
                        "titulo": "Acesso Negado",
                        "mensagem": "Voce precisa estar vinculado a um Funcionario ativo.",
                    },
                    status=403,
                )

        # 4. Sucesso: injeta funcionario e prossegue
        request.funcionario = funcionario
        return view_func(request, *args, **kwargs)

    return wrapped

