# core/decorators.py
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import NoReverseMatch, reverse


def _is_ajax(request):
    """
    Detecta se a requisicao espera resposta JSON.
    
    Retorna True se:
    - Header X-Requested-With: XMLHttpRequest (jQuery, axios configurado)
    - Content-Type: application/json (POST/PUT com body JSON)
    - Accept: application/json (sem text/html no mesmo header)
    - Path contem /api/ (convencao do projeto)
    """
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return True
    
    if request.content_type == 'application/json':
        return True
    
    accept = request.headers.get('accept', '')
    if 'application/json' in accept and 'text/html' not in accept:
        return True
    
    if '/api/' in request.path:
        return True
    
    return False


# =============================================================================
# == app_permission_required
# =============================================================================

def app_permission_required(app_label):
    """
    Decorator para FBVs: exige login + pelo menos uma permissao do app.
    
    - Responde JSON 401/403 para AJAX
    - Renderiza HTML 403 ou redireciona pro login
    
    Uso:
        @app_permission_required('ata_reuniao')
        def minha_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user

            # 1. Autenticacao + ativo
            if not user.is_authenticated or not user.is_active:
                if _is_ajax(request):
                    return JsonResponse({
                        'status': 'error',
                        'error': 'Autenticacao necessaria',
                    }, status=401)
                return redirect_to_login(request.get_full_path())

            # 2. Superuser bypass
            if user.is_superuser:
                return view_func(request, *args, **kwargs)

            # 3. Permissao do app
            if not user.has_module_perms(app_label):
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
    Decorator: exige login + vinculo com Funcionario ativo.
    Equivalente ao FuncionarioRequiredMixin para FBVs.
    
    Injeta request.funcionario quando bem-sucedido.
    """
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        user = request.user

        # 1. Autenticacao + ativo
        if not user.is_authenticated or not user.is_active:
            if _is_ajax(request):
                return JsonResponse(
                    {"status": "error", "error": "Autenticacao necessaria."},
                    status=401,
                )
            return redirect_to_login(request.get_full_path())

        # 2. Superuser bypass
        if user.is_superuser:
            request.funcionario = getattr(user, "funcionario", None)
            return view_func(request, *args, **kwargs)

        # 3. Vinculo Funcionario (fail-safe: default False)
        funcionario = getattr(user, "funcionario", None)
        if not funcionario or not getattr(funcionario, "ativo", False):
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

        # 4. Sucesso
        request.funcionario = funcionario
        return view_func(request, *args, **kwargs)

    return wrapped
