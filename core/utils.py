# core/utils.py
"""
Utilitários globais compartilhados do core.

get_filial_ativa() é a FONTE ÚNICA de verdade para resolver
qual é a filial ativa de um usuário.
"""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse, NoReverseMatch

from core.constants import SESSION_FILIAL_ATIVA

if TYPE_CHECKING:
    from django.http import HttpRequest
    from usuario.models import Filial


_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


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


def usuario_ve_todas_filiais(user) -> bool:
    """
    Regra UNIFICADA de bypass do escopo de filial.

    Retorna True se o usuário pode ver dados de TODAS as filiais
    (ou seja, NÃO deve ser filtrado pela filial ativa).

    Regra: superuser OU administrador.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    return bool(getattr(user, 'is_administrador', False))


def get_filial_ativa(user, request: Optional["HttpRequest"] = None) -> Optional["Filial"]:
    """
    Fonte única para resolver a filial ativa de um usuário.

    Ordem de prioridade:
    1. `request.session[SESSION_FILIAL_ATIVA]` — se existir e o usuário
       tiver acesso (superuser/administrador acessam qualquer filial).
    2. `user.filial_ativa` (fallback) — também validado contra
       `usuarios_permitidos` para quem não vê todas as filiais.

    Returns:
        Instância de Filial ou None.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return None

    from usuario.models import Filial

    ve_todas = usuario_ve_todas_filiais(user)

    # 1) Filial escolhida na sessão
    if request is not None:
        filial_id = request.session.get(SESSION_FILIAL_ATIVA)
        if filial_id:
            qs = Filial.objects.filter(pk=filial_id)
            if not ve_todas:
                qs = qs.filter(usuarios_permitidos=user)
            filial = qs.first()
            if filial is not None:
                return filial

    # 2) Fallback: filial padrão do usuário (validada)
    fallback = getattr(user, "filial_ativa", None)
    if fallback is None:
        return None
    if not ve_todas and not fallback.usuarios_permitidos.filter(pk=user.pk).exists():
        return None
    return fallback


def get_filial_ativa_id(user, request=None) -> Optional[int]:
    """Atalho: retorna apenas o PK da filial ativa, ou None."""
    filial = get_filial_ativa(user, request)
    return filial.pk if filial else None


def queryset_da_filial(queryset, user, request=None, campo_filial='filial'):
    """
    Filtra um queryset pela filial ativa do usuário.
    Superuser e administrador veem todos.

    Args:
        queryset: QuerySet a filtrar
        user: instância de Usuario
        request: HttpRequest opcional (fallback de sessão)
        campo_filial: nome do campo FK para Filial (default: 'filial')
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return queryset.none()

    if usuario_ve_todas_filiais(user):
        return queryset

    filial = get_filial_ativa(user, request)
    if filial:
        return queryset.filter(**{campo_filial: filial})

    return queryset.none()


# ── departamento_pessoal ─────────────────────────────────────────────────────

def mascarar_cpf(cpf: str) -> str:
    digits = ''.join(filter(str.isdigit, cpf or ''))
    if len(digits) != 11:
        return cpf or ''
    return f"***.{digits[3:6]}.***-{digits[9:11]}"


# ── Exportação segura (formula injection) ────────────────────────────────────

def excel_safe(value):
    """Para pandas: prefixa com ' textos que o Excel interpretaria como fórmula."""
    if isinstance(value, str) and value[:1] in _FORMULA_PREFIXES:
        return "'" + value
    return value


def write_cell(ws, row, col, value):
    """Para openpyxl: grava a célula e força tipo texto se parecer fórmula."""
    cell = ws.cell(row=row, column=col, value=value)
    if isinstance(value, str) and value[:1] in _FORMULA_PREFIXES:
        cell.data_type = "s"
    return cell

