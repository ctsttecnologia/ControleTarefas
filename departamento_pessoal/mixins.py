
# Em: departamento_pessoal/mixins.py

from django.contrib.auth.mixins import AccessMixin

class StaffRequiredMixin(AccessMixin):
    """
    Mixin que verifica se o usuário está autenticado e é um membro da equipe (is_staff=True).
    Se não for, redireciona para a página de login.
    """
    def dispatch(self, request, *args, **kwargs):
        # Verifica primeiro se o usuário está logado.
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        # Depois, verifica se o usuário é da equipe.
        if not request.user.is_staff:
            return self.handle_no_permission()
            
        # Se passar nas duas verificações, permite o acesso à view.
        return super().dispatch(request, *args, **kwargs)

