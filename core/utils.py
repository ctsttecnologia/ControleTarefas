
# core/utils.py
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse, NoReverseMatch


def redirect_sem_funcionario(request, modulo: str = ''):
    """
    Redireciona para a tela amigável de 'sem funcionário vinculado'.
    Uso: return redirect_sem_funcionario(request, modulo='Automóvel')
    """
    messages.warning(
        request,
        "Seu usuário ainda não possui funcionário vinculado. "
        "Entre em contato com o Departamento Pessoal."
    )
    try:
        url = reverse('core:sem_funcionario')
        if modulo:
            url += f'?modulo={modulo}'
        return redirect(url)
    except NoReverseMatch:
        try:
            return redirect('core:home')
        except NoReverseMatch:
            return redirect('/')

