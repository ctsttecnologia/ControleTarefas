
# core/utils.py

"""Utilitários compartilhados do core."""
from __future__ import annotations
from typing import Optional, TYPE_CHECKING
from core.constants import SESSION_FILIAL_ATIVA

if TYPE_CHECKING:
    from django.http import HttpRequest
    from models import Filial  

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse, NoReverseMatch
from typing import Optional


"""
core/utils.py
Utilitários globais. A função get_filial_ativa() é a FONTE ÚNICA
de verdade para resolver qual é a filial ativa de um usuário.
"""

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

# core/utils.py  (ou no topo de suprimentos/views.py)

def usuario_ve_todas_filiais(user):
    """
    Define a regra UNIFICADA de bypass do escopo de filial.
    
    Retorna True se o usuário pode ver dados de TODAS as filiais
    (ou seja, NÃO deve ser filtrado pela filial_ativa).
    
    Regra: superuser OU administrador.
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if getattr(user, 'is_administrador', False):
        return True
    return False


def get_filial_ativa(user, request: Optional["HttpRequest"] = None) -> Optional["Filial"]:
    """
    Fonte única para resolver a filial ativa de um usuário.

    Ordem de prioridade:
    1. ID em `request.session[SESSION_FILIAL_ATIVA]` — se válido e pertencer ao usuário
    2. `user.filial_padrao` (fallback)

    Returns:
        Instância de Filial ou None.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return None

    from usuario.models import Filial
    # 1) Tenta sessão
    if request is not None:
        filial_id = request.session.get(SESSION_FILIAL_ATIVA)
        if filial_id:
            filial = (
                Filial.objects.filter(pk=filial_id, usuarios=user).first()
                if hasattr(Filial, "usuarios")
                else Filial.objects.filter(pk=filial_id).first()
            )
            if filial is not None:
                return filial

    # 2) Fallback
    return getattr(user, "filial_ativa", None)


def get_filial_ativa_id(user, request=None) -> Optional[int]:
    """Atalho: retorna apenas o PK da filial ativa, ou None."""
    filial = get_filial_ativa(user, request)
    return filial.pk if filial else None


def queryset_da_filial(queryset, user, request=None, campo_filial='filial'):
    """
    Filtra um queryset pela filial ativa do usuário.
    Superuser e ADMINISTRADOR veem todos.

    Args:
        queryset: QuerySet a filtrar
        user: instância de Usuario
        request: HttpRequest opcional (fallback de sessão)
        campo_filial: nome do campo FK para Filial (default: 'filial')

    Returns:
        QuerySet filtrado
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return queryset.none()

    # Superuser e admin veem tudo
    if user.is_superuser or getattr(user, 'is_administrador', False):
        return queryset

    filial = get_filial_ativa(user, request)
    if filial:
        return queryset.filter(**{campo_filial: filial})

    return queryset.none()