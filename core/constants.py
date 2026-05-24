
"""
Constantes centralizadas do projeto.

Fonte única da verdade para:
- Chaves de sessão
- Nomes de grupos (perfis, setores, features)
- Outros valores compartilhados entre apps
"""
from __future__ import annotations

# ============================================================
# SESSÃO
# ============================================================
SESSION_FILIAL_ATIVA = 'active_filial_id'

# ============================================================
# GRUPOS — PERFIS HIERÁRQUICOS
# ============================================================
GRUPO_ADMINISTRADOR = "ADMINISTRADOR"
GRUPO_GERENTE = "GERENTE"
GRUPO_COORDENADOR = "COORDENADOR"
GRUPO_TECNICO = "TECNICO"
GRUPO_ASSISTENTE = "ASSISTENTE"
GRUPO_USUARIO_COMUM = "USUARIO_COMUM"

GRUPOS_PERFIL: frozenset[str] = frozenset({
    GRUPO_ADMINISTRADOR,
    GRUPO_GERENTE,
    GRUPO_COORDENADOR,
    GRUPO_TECNICO,
    GRUPO_ASSISTENTE,
    GRUPO_USUARIO_COMUM,
})

# ============================================================
# GRUPOS — SETORES / DEPARTAMENTOS
# ============================================================
GRUPO_DEPARTAMENTO_PESSOAL = "DEPARTAMENTO_PESSOAL"
GRUPO_PLANEJAMENTO = "PLANEJAMENTO"
GRUPO_SUPRIMENTOS = "SUPRIMENTOS"
GRUPO_GESTAO_QUALIDADE = "GESTAO_QUALIDADE"
GRUPO_SST_SEGURANCA = "SST_SEGURANCA"

GRUPOS_SETOR: frozenset[str] = frozenset({
    GRUPO_DEPARTAMENTO_PESSOAL,
    GRUPO_PLANEJAMENTO,
    GRUPO_SUPRIMENTOS,
    GRUPO_GESTAO_QUALIDADE,
    GRUPO_SST_SEGURANCA,
})

# ============================================================
# GRUPOS — FEATURE FLAGS
# ============================================================
GRUPO_DASHBOARD_FULL = "DASHBOARD_FULL"

GRUPOS_FEATURE: frozenset[str] = frozenset({
    GRUPO_DASHBOARD_FULL,
})

# ============================================================
# CONJUNTO COMPLETO (útil para validações)
# ============================================================
GRUPOS_TODOS: frozenset[str] = GRUPOS_PERFIL | GRUPOS_SETOR | GRUPOS_FEATURE
