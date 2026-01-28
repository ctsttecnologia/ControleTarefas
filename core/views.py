
# core/views.py

from django.shortcuts import redirect, render
from django.views import View
from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from usuario.models import Filial


class SelecionarFilialView(UserPassesTestMixin, View):
    
    def test_func(self):
        """
        Permite que qualquer usuário autenticado acesse a view.
        """
        return self.request.user.is_authenticated

    def post(self, request, *args, **kwargs):
        filial_id = request.POST.get('filial_id')

        if filial_id:
            try:
                if filial_id == '0':
                    if 'active_filial_id' in request.session:
                        del request.session['active_filial_id']
                    messages.success(request, "Visão alterada para Todas as Filiais.")
                else:
                    filial = Filial.objects.get(pk=filial_id)
                    request.session['active_filial_id'] = filial.id
                    messages.success(request, f"Visão alterada para a filial: {filial.nome}.")
            
            except (Filial.DoesNotExist, ValueError):
                messages.error(request, "A filial selecionada é inválida ou ocorreu um erro.")
        else:
            messages.warning(request, "Nenhuma filial foi selecionada.")
        
        return redirect(request.META.get('HTTP_REFERER', 'ferramentas:dashboard'))


class SetFilialView(View):
    def post(self, request, *args, **kwargs):
        filial_id = request.POST.get('filial_id')
        if filial_id:
            request.session['filial_id'] = filial_id
        
        return redirect(request.META.get('HTTP_REFERER', '/'))


# ============================================================
# VIEWS DE ERRO PERSONALIZADAS
# ============================================================

def error_400_view(request, exception=None):
    """
    View personalizada para erro 400 (Bad Request).
    Ocorre quando há dados malformados na requisição.
    """
    if not hasattr(request, 'user'):
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
    
    return render(request, 'errors/400.html', status=400)


def error_403_view(request, exception=None):
    """
    View personalizada para erro 403 (Permissão Negada).
    """
    if not hasattr(request, 'user'):
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
    
    return render(request, 'errors/403.html', status=403)


def error_404_view(request, exception):
    """
    View personalizada para erro 404 (Página Não Encontrada).
    """
    if not hasattr(request, 'user'):
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
    
    return render(request, 'errors/404.html', status=404)


def error_500_view(request):
    """
    View personalizada para erro 500 (Erro Interno do Servidor).
    """
    if not hasattr(request, 'user'):
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
    
    return render(request, 'errors/500.html', status=500)


def error_503_view(request, exception=None):
    """
    View personalizada para erro 503 (Serviço Indisponível).
    Útil para páginas de manutenção.
    """
    if not hasattr(request, 'user'):
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
    
    return render(request, 'errors/503.html', status=503)

