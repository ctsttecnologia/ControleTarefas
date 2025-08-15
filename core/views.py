# core/views.py

from django.shortcuts import redirect, render
from django.views import View
from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin # 1. Importar o Mixin de permissão
from usuario.models import Filial

# 2. Usar o Mixin para verificar a permissão ANTES de executar a view.
#    O Django automaticamente redirecionará usuários não autorizados.
class SelecionarFilialView(UserPassesTestMixin, View):
    
    def test_func(self):
        """
        Esta função é chamada pelo UserPassesTestMixin.
        A view só será executada se a função retornar True.
        """
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def post(self, request, *args, **kwargs):
        # A verificação de superusuário já foi feita pelo mixin,
        # então podemos remover o `if` daqui.
        filial_id = request.POST.get('filial_id')

        if filial_id:
            try:
                # O valor '0' é um caso especial para limpar a sessão e ver todas as filiais.
                if filial_id == '0':
                    if 'active_filial_id' in request.session:
                        del request.session['active_filial_id']
                    messages.success(request, "Visão alterada para Todas as Filiais.")
                else:
                    # 3. Bloco try/except mais robusto, capturando também ValueError.
                    filial = Filial.objects.get(pk=filial_id)
                    request.session['active_filial_id'] = filial.id
                    messages.success(request, f"Visão alterada para a filial: {filial.nome}.")
            
            except (Filial.DoesNotExist, ValueError):
                # Captura tanto IDs que não existem quanto valores que não são números.
                messages.error(request, "A filial selecionada é inválida ou ocorreu um erro.")
        else:
            messages.warning(request, "Nenhuma filial foi selecionada.")
        
        # 4. Redireciona apenas uma vez no final, simplificando o fluxo.
        return redirect(request.META.get('HTTP_REFERER', 'ferramentas:dashboard'))
    
def error_404_view(request, exception):
    """
    View para renderizar a página 404 personalizada.
    """
    return render(request, '404.html', status=404)

