# usuario/tests/conftest.py
"""
Fixtures compartilhadas entre os testes do app usuário.
"""
from datetime import date

import pytest
from django.contrib.auth.models import Group

from departamento_pessoal.models import Cargo, Departamento, Funcionario
from usuario.models import Filial, Usuario


# =============================================================================
# FILIAIS
# =============================================================================

@pytest.fixture
def filial_a(db):
    return Filial.objects.create(nome="Filial A")


@pytest.fixture
def filial_b(db):
    return Filial.objects.create(nome="Filial B")


# =============================================================================
# GRUPOS
# =============================================================================

@pytest.fixture
def grupo_gerente(db):
    group, _ = Group.objects.get_or_create(name="Gerente")
    return group


@pytest.fixture
def grupo_operador(db):
    group, _ = Group.objects.get_or_create(name="Operador")
    return group


@pytest.fixture
def grupo_admin(db):
    group, _ = Group.objects.get_or_create(name="Administrador")
    return group


# =============================================================================
# DEPARTAMENTO + CARGO (dependem de Filial)
# =============================================================================

@pytest.fixture
def departamento_padrao(db, filial_a):
    """Departamento mínimo para criar Funcionarios nos testes."""
    return Departamento.objects.create(
        nome="TI",
        filial=filial_a,
    )


@pytest.fixture
def cargo_padrao(db, filial_a):
    """Cargo mínimo para criar Funcionarios nos testes."""
    return Cargo.objects.create(
        nome="Analista",
        filial=filial_a,
    )


# =============================================================================
# USUÁRIOS
# =============================================================================

@pytest.fixture
def superuser(db, filial_a):
    user = Usuario.objects.create_superuser(
        username="super",
        email="super@test.com",
        password="Test@123456",
        first_name="Super",
        last_name="User",
    )
    user.filiais_permitidas.add(filial_a)
    user.filial_ativa = filial_a
    user.save()
    return user


@pytest.fixture
def gerente(db, filial_a, grupo_gerente):
    """Gerente da Filial A (via grupo 'Gerente')."""
    user = Usuario.objects.create_user(
        username="gerente_a",
        email="gerente@test.com",
        password="Test@123456",
        first_name="Gerente",
        last_name="A",
        is_staff=False,
        is_superuser=False,
    )
    user.filiais_permitidas.add(filial_a)
    user.filial_ativa = filial_a
    user.groups.add(grupo_gerente)
    user.save()
    return user


@pytest.fixture
def usuario_comum(db, filial_a):
    user = Usuario.objects.create_user(
        username="comum",
        email="comum@test.com",
        password="Test@123456",
        first_name="Usuário",
        last_name="Comum",
    )
    user.filiais_permitidas.add(filial_a)
    user.filial_ativa = filial_a
    user.save()
    return user


# =============================================================================
# FUNCIONÁRIOS
# =============================================================================

@pytest.fixture
def funcionario_disponivel(db, cargo_padrao, departamento_padrao):
    """Funcionário sem usuário vinculado."""
    return Funcionario.objects.create(
        nome_completo="João Disponível",
        matricula="F0001",
        data_admissao=date(2020, 1, 1),
        cargo=cargo_padrao,
        departamento=departamento_padrao,
    )


@pytest.fixture
def funcionario_vinculado(db, usuario_comum, cargo_padrao, departamento_padrao):
    """Funcionário já vinculado ao `usuario_comum`."""
    return Funcionario.objects.create(
        nome_completo="Maria Vinculada",
        matricula="F0002",
        data_admissao=date(2020, 1, 1),
        cargo=cargo_padrao,
        departamento=departamento_padrao,
        usuario=usuario_comum,
    )

# Para rodar os testes: pytest usuario/tests/ --cov=usuario --cov-report=html
# pytest usuario/tests/ --cov=usuario --cov-report=html

# Relatório de cobertura: htmlcov/index.html
# start htmlcov/index.html