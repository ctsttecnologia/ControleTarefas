from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.contrib.auth.mixins import AccessMixin

class AuthenticatedUserRedirectMixin(AccessMixin):
    """
    Mixin que redireciona o usuário se ele já estiver autenticado.
    """
    redirect_url = 'usuario:profile' # Rota para onde o usuário logado será enviado

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(self.redirect_url)
        return super().dispatch(request, *args, **kwargs)

class HomeView(TemplateView):
    template_name = 'home/home.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            # Se o usuário já está logado, envia para a página de perfil/menu
            return redirect('usuario:profile')
        # Se não, continua e mostra a home page
        return super().dispatch(request, *args, **kwargs)