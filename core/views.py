# core/views.py

from django.shortcuts import redirect
from django.views import View
from django.contrib import messages
from usuario.models import Filial # Importe seu modelo Filial

class SelecionarFilialView(View):
    def post(self, request, *args, **kwargs):
        filial_id = request.POST.get('filial_id')

        # Permite que apenas superusuários troquem de filial
        if not request.user.is_superuser:
            messages.error(request, "Você não tem permissão para realizar esta ação.")
            return redirect(request.META.get('HTTP_REFERER', 'ferramentas:dashboard'))

        if filial_id:
            try:
                # '0' ou um valor vazio significa "Ver todas"
                if filial_id == '0':
                    if 'active_filial_id' in request.session:
                        del request.session['active_filial_id']
                    messages.success(request, "Visão alterada para Todas as Filiais.")
                else:
                    filial = Filial.objects.get(pk=filial_id)
                    request.session['active_filial_id'] = filial.id
                    messages.success(request, f"Visão alterada para a filial: {filial.nome}.")

            except Filial.DoesNotExist:
                messages.error(request, "Filial selecionada é inválida.")
        
        # Redireciona o usuário para a página de onde ele veio
        return redirect(request.META.get('HTTP_REFERER', 'ferramentas:dashboard'))