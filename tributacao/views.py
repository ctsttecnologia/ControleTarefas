
# tributacao/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import JsonResponse

from .models import NCM, CFOP, CST, GrupoTributario, TributacaoFederal, TributacaoEstadual
from .forms import (
    NCMForm, CFOPForm, CSTForm,
    GrupoTributarioForm, TributacaoFederalForm,
    TributacaoEstadualForm, TributacaoEstadualFormSet,
)


# ══════════════════════════════════════════════════════
# HELPERS DE PERMISSÃO
# ══════════════════════════════════════════════════════
def _pode_gerenciar_tabelas(user):
    """Verifica se o usuário pode mexer em NCM/CFOP/CST (dados sensíveis)."""
    return (
        user.is_superuser
        or user.has_perm('tributacao.pode_gerenciar_tabelas_fiscais')
    )


def _pode_ver_todas_filiais(user):
    """Verifica bypass de filial para grupos tributários."""
    return (
        user.is_superuser
        or user.has_perm('tributacao.pode_gerenciar_todas_filiais')
    )


def _filtrar_grupos_por_filial(qs, user):
    """Aplica filtro de filial baseado nas permissões do usuário."""
    if _pode_ver_todas_filiais(user):
        return qs

    # Filtra apenas pela filial ativa do usuário
    filial_ativa = getattr(user, 'filial_ativa', None)
    if filial_ativa:
        return qs.filter(filial=filial_ativa)

    # Sem filial ativa: filiais permitidas
    filiais_permitidas = getattr(user, 'filiais_permitidas', None)
    if filiais_permitidas is not None:
        return qs.filter(filial__in=filiais_permitidas.all())

    return qs.none()


# ══════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════
@login_required
@permission_required('tributacao.view_grupotributario', raise_exception=True)
def dashboard(request):
    # Filtra grupos pela filial do usuário
    grupos_qs = _filtrar_grupos_por_filial(GrupoTributario.objects.all(), request.user)

    context = {
        "total_ncm": NCM.objects.filter(ativo=True).count(),
        "total_cfop": CFOP.objects.filter(ativo=True).count(),
        "total_cst": CST.objects.count(),
        "total_grupos": grupos_qs.filter(ativo=True).count(),
        "total_trib_federal": TributacaoFederal.objects.filter(
            grupo__in=grupos_qs
        ).count(),
        "total_trib_estadual": TributacaoEstadual.objects.filter(
            grupo__in=grupos_qs, ativo=True
        ).count(),
        "pode_gerenciar_tabelas": _pode_gerenciar_tabelas(request.user),
        "pode_ver_todas_filiais": _pode_ver_todas_filiais(request.user),
    }
    return render(request, "tributacao/dashboard.html", context)


# ══════════════════════════════════════════════════════
# NCM — CRUD (dados globais, sensíveis)
# ══════════════════════════════════════════════════════
@login_required
@permission_required('tributacao.view_ncm', raise_exception=True)
def ncm_list(request):
    q = request.GET.get("q", "").strip()
    ncms = NCM.objects.all()
    if q:
        ncms = ncms.filter(Q(codigo__icontains=q) | Q(descricao__icontains=q))

    context = {
        "ncms": ncms,
        "q": q,
        "pode_gerenciar": _pode_gerenciar_tabelas(request.user),
    }
    return render(request, "tributacao/ncm_list.html", context)


@login_required
@permission_required('tributacao.add_ncm', raise_exception=True)
def ncm_create(request):
    if not _pode_gerenciar_tabelas(request.user):
        raise PermissionDenied("Você não tem permissão para cadastrar NCMs.")

    if request.method == "POST":
        form = NCMForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "NCM cadastrado com sucesso!")
            return redirect("tributacao:ncm_list")
    else:
        form = NCMForm()
    return render(request, "tributacao/ncm_form.html", {"form": form, "titulo": "Novo NCM"})


@login_required
@permission_required('tributacao.change_ncm', raise_exception=True)
def ncm_update(request, pk):
    if not _pode_gerenciar_tabelas(request.user):
        raise PermissionDenied("Você não tem permissão para editar NCMs.")

    ncm = get_object_or_404(NCM, pk=pk)
    if request.method == "POST":
        form = NCMForm(request.POST, request.FILES, instance=ncm)
        if form.is_valid():
            form.save()
            messages.success(request, "NCM atualizado com sucesso!")
            return redirect("tributacao:ncm_list")
    else:
        form = NCMForm(instance=ncm)
    return render(request, "tributacao/ncm_form.html", {"form": form, "titulo": "Editar NCM"})


@login_required
@permission_required('tributacao.delete_ncm', raise_exception=True)
def ncm_delete(request, pk):
    if not _pode_gerenciar_tabelas(request.user):
        raise PermissionDenied("Você não tem permissão para excluir NCMs.")

    ncm = get_object_or_404(NCM, pk=pk)
    if request.method == "POST":
        ncm.delete()
        messages.success(request, "NCM excluído com sucesso!")
        return redirect("tributacao:ncm_list")
    return render(request, "tributacao/confirm_delete.html", {"objeto": ncm, "tipo": "NCM"})


# ══════════════════════════════════════════════════════
# CFOP — CRUD (dados globais, sensíveis)
# ══════════════════════════════════════════════════════
@login_required
@permission_required('tributacao.view_cfop', raise_exception=True)
def cfop_list(request):
    q = request.GET.get("q", "").strip()
    cfops = CFOP.objects.all()
    if q:
        cfops = cfops.filter(Q(codigo__icontains=q) | Q(descricao__icontains=q))
    return render(request, "tributacao/cfop_list.html", {
        "cfops": cfops,
        "q": q,
        "pode_gerenciar": _pode_gerenciar_tabelas(request.user),
    })


@login_required
@permission_required('tributacao.add_cfop', raise_exception=True)
def cfop_create(request):
    if not _pode_gerenciar_tabelas(request.user):
        raise PermissionDenied("Você não tem permissão para cadastrar CFOPs.")

    if request.method == "POST":
        form = CFOPForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "CFOP cadastrado com sucesso!")
            return redirect("tributacao:cfop_list")
    else:
        form = CFOPForm()
    return render(request, "tributacao/cfop_form.html", {"form": form, "titulo": "Novo CFOP"})


@login_required
@permission_required('tributacao.change_cfop', raise_exception=True)
def cfop_update(request, pk):
    if not _pode_gerenciar_tabelas(request.user):
        raise PermissionDenied("Você não tem permissão para editar CFOPs.")

    cfop = get_object_or_404(CFOP, pk=pk)
    if request.method == "POST":
        form = CFOPForm(request.POST, instance=cfop)
        if form.is_valid():
            form.save()
            messages.success(request, "CFOP atualizado com sucesso!")
            return redirect("tributacao:cfop_list")
    else:
        form = CFOPForm(instance=cfop)
    return render(request, "tributacao/cfop_form.html", {"form": form, "titulo": "Editar CFOP"})


@login_required
@permission_required('tributacao.delete_cfop', raise_exception=True)
def cfop_delete(request, pk):
    if not _pode_gerenciar_tabelas(request.user):
        raise PermissionDenied("Você não tem permissão para excluir CFOPs.")

    cfop = get_object_or_404(CFOP, pk=pk)
    if request.method == "POST":
        cfop.delete()
        messages.success(request, "CFOP excluído com sucesso!")
        return redirect("tributacao:cfop_list")
    return render(request, "tributacao/confirm_delete.html", {"objeto": cfop, "tipo": "CFOP"})


# ══════════════════════════════════════════════════════
# CST — CRUD (dados globais, sensíveis)
# ══════════════════════════════════════════════════════
@login_required
@permission_required('tributacao.view_cst', raise_exception=True)
def cst_list(request):
    q = request.GET.get("q", "").strip()
    tipo_filtro = request.GET.get("tipo", "").strip()
    csts = CST.objects.all()
    if q:
        csts = csts.filter(Q(codigo__icontains=q) | Q(descricao__icontains=q))
    if tipo_filtro:
        csts = csts.filter(tipo=tipo_filtro)
    return render(request, "tributacao/cst_list.html", {
        "csts": csts,
        "q": q,
        "tipo_filtro": tipo_filtro,
        "tipos": CST.TIPO_CHOICES,
        "pode_gerenciar": _pode_gerenciar_tabelas(request.user),
    })


@login_required
@permission_required('tributacao.add_cst', raise_exception=True)
def cst_create(request):
    if not _pode_gerenciar_tabelas(request.user):
        raise PermissionDenied("Você não tem permissão para cadastrar CSTs.")

    if request.method == "POST":
        form = CSTForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "CST cadastrado com sucesso!")
            return redirect("tributacao:cst_list")
    else:
        form = CSTForm()
    return render(request, "tributacao/cst_form.html", {"form": form, "titulo": "Novo CST"})


@login_required
@permission_required('tributacao.change_cst', raise_exception=True)
def cst_update(request, pk):
    if not _pode_gerenciar_tabelas(request.user):
        raise PermissionDenied("Você não tem permissão para editar CSTs.")

    cst = get_object_or_404(CST, pk=pk)
    if request.method == "POST":
        form = CSTForm(request.POST, instance=cst)
        if form.is_valid():
            form.save()
            messages.success(request, "CST atualizado com sucesso!")
            return redirect("tributacao:cst_list")
    else:
        form = CSTForm(instance=cst)
    return render(request, "tributacao/cst_form.html", {"form": form, "titulo": "Editar CST"})


@login_required
@permission_required('tributacao.delete_cst', raise_exception=True)
def cst_delete(request, pk):
    if not _pode_gerenciar_tabelas(request.user):
        raise PermissionDenied("Você não tem permissão para excluir CSTs.")

    cst = get_object_or_404(CST, pk=pk)
    if request.method == "POST":
        cst.delete()
        messages.success(request, "CST excluído com sucesso!")
        return redirect("tributacao:cst_list")
    return render(request, "tributacao/confirm_delete.html", {"objeto": cst, "tipo": "CST"})


# ══════════════════════════════════════════════════════
# GRUPO TRIBUTÁRIO — CRUD com filtro por filial
# ══════════════════════════════════════════════════════
@login_required
@permission_required('tributacao.view_grupotributario', raise_exception=True)
def grupo_list(request):
    q = request.GET.get("q", "").strip()
    grupos = GrupoTributario.objects.select_related("cfop", "ncm", "filial").all()

    # Filtra por filial
    grupos = _filtrar_grupos_por_filial(grupos, request.user)

    if q:
        grupos = grupos.filter(Q(nome__icontains=q) | Q(descricao__icontains=q))

    return render(request, "tributacao/grupo_list.html", {
        "grupos": grupos,
        "q": q,
        "pode_ver_todas_filiais": _pode_ver_todas_filiais(request.user),
    })


@login_required
@permission_required('tributacao.add_grupotributario', raise_exception=True)
def grupo_create(request):
    if request.method == "POST":
        form = GrupoTributarioForm(request.POST, user=request.user)
        federal_form = TributacaoFederalForm(request.POST, prefix="federal")
        estadual_formset = TributacaoEstadualFormSet(request.POST, prefix="estadual")

        if form.is_valid() and federal_form.is_valid() and estadual_formset.is_valid():
            grupo = form.save(commit=False)

            # Valida filial para não-admins
            if not _pode_ver_todas_filiais(request.user):
                filial_ativa = getattr(request.user, 'filial_ativa', None)
                if filial_ativa and grupo.filial != filial_ativa:
                    raise PermissionDenied(
                        "Você só pode criar grupos para a sua filial ativa."
                    )

            grupo.save()

            # Federal
            federal = federal_form.save(commit=False)
            federal.grupo = grupo
            federal.save()

            # Estadual
            estadual_formset.instance = grupo
            estadual_formset.save()

            messages.success(request, "Grupo Tributário criado com sucesso!")
            return redirect("tributacao:grupo_list")
    else:
        form = GrupoTributarioForm(user=request.user)
        federal_form = TributacaoFederalForm(prefix="federal")
        estadual_formset = TributacaoEstadualFormSet(prefix="estadual")

    return render(request, "tributacao/grupo_form.html", {
        "form": form,
        "federal_form": federal_form,
        "estadual_formset": estadual_formset,
        "titulo": "Novo Grupo Tributário",
    })


@login_required
@permission_required('tributacao.change_grupotributario', raise_exception=True)
def grupo_update(request, pk):
    grupo = get_object_or_404(GrupoTributario, pk=pk)

    # Checa acesso à filial
    if not _pode_ver_todas_filiais(request.user):
        grupos_permitidos = _filtrar_grupos_por_filial(
            GrupoTributario.objects.all(), request.user
        )
        if grupo not in grupos_permitidos:
            raise PermissionDenied(
                "Você não tem permissão para editar grupos desta filial."
            )

    federal_instance = getattr(grupo, "tributacao_federal", None)

    if request.method == "POST":
        form = GrupoTributarioForm(request.POST, instance=grupo, user=request.user)
        federal_form = TributacaoFederalForm(
            request.POST, prefix="federal", instance=federal_instance
        )
        estadual_formset = TributacaoEstadualFormSet(
            request.POST, prefix="estadual", instance=grupo
        )

        if form.is_valid() and federal_form.is_valid() and estadual_formset.is_valid():
            grupo = form.save()

            federal = federal_form.save(commit=False)
            federal.grupo = grupo
            federal.save()

            estadual_formset.save()

            messages.success(request, "Grupo Tributário atualizado com sucesso!")
            return redirect("tributacao:grupo_list")
    else:
        form = GrupoTributarioForm(instance=grupo, user=request.user)
        federal_form = TributacaoFederalForm(prefix="federal", instance=federal_instance)
        estadual_formset = TributacaoEstadualFormSet(prefix="estadual", instance=grupo)

    return render(request, "tributacao/grupo_form.html", {
        "form": form,
        "federal_form": federal_form,
        "estadual_formset": estadual_formset,
        "titulo": f"Editar — {grupo.nome}",
    })


@login_required
@permission_required('tributacao.delete_grupotributario', raise_exception=True)
def grupo_delete(request, pk):
    grupo = get_object_or_404(GrupoTributario, pk=pk)

    # Checa acesso à filial
    if not _pode_ver_todas_filiais(request.user):
        grupos_permitidos = _filtrar_grupos_por_filial(
            GrupoTributario.objects.all(), request.user
        )
        if grupo not in grupos_permitidos:
            raise PermissionDenied(
                "Você não tem permissão para excluir grupos desta filial."
            )

    if request.method == "POST":
        grupo.delete()
        messages.success(request, "Grupo Tributário excluído com sucesso!")
        return redirect("tributacao:grupo_list")
    return render(request, "tributacao/confirm_delete.html", {
        "objeto": grupo, "tipo": "Grupo Tributário",
    })


@login_required
@permission_required('tributacao.view_grupotributario', raise_exception=True)
def grupo_detail(request, pk):
    grupo = get_object_or_404(
        GrupoTributario.objects.select_related("cfop", "ncm", "filial"),
        pk=pk,
    )

    # Checa acesso à filial
    if not _pode_ver_todas_filiais(request.user):
        grupos_permitidos = _filtrar_grupos_por_filial(
            GrupoTributario.objects.all(), request.user
        )
        if grupo not in grupos_permitidos:
            raise PermissionDenied(
                "Você não tem permissão para visualizar grupos desta filial."
            )

    federal = getattr(grupo, "tributacao_federal", None)
    estaduais = grupo.tributacoes_estaduais.filter(ativo=True).order_by("uf_origem", "uf_destino")

    return render(request, "tributacao/grupo_detail.html", {
        "grupo": grupo,
        "federal": federal,
        "estaduais": estaduais,
    })


# ══════════════════════════════════════════════════════
# APIs (usadas por JS em outros módulos)
# ══════════════════════════════════════════════════════
@login_required
@permission_required('tributacao.view_grupotributario', raise_exception=True)
def grupo_tributario_api(request, pk):
    """Retorna dados do grupo tributário para preview no form de material."""
    grupo = get_object_or_404(GrupoTributario, pk=pk)

    # Checa acesso à filial
    if not _pode_ver_todas_filiais(request.user):
        grupos_permitidos = _filtrar_grupos_por_filial(
            GrupoTributario.objects.all(), request.user
        )
        if grupo not in grupos_permitidos:
            return JsonResponse({'error': 'Sem permissão'}, status=403)

    federal = getattr(grupo, 'tributacao_federal', None)
    estadual = grupo.tributacoes_estaduais.filter(ativo=True).first()

    return JsonResponse({
        'nome': grupo.nome,
        'cfop': f"{grupo.cfop.codigo} — {grupo.cfop.descricao[:50]}" if grupo.cfop else '—',
        'icms': {
            'cst': str(estadual.cst_icms) if estadual and estadual.cst_icms else '—',
            'aliquota': str(estadual.aliquota_icms) if estadual else '0',
            'reducao_base': str(estadual.reducao_base_icms) if estadual else '0',
            'permite_credito': estadual.permite_credito if estadual else False,
        },
        'ipi': {
            'cst': str(federal.cst_ipi) if federal and federal.cst_ipi else '—',
            'aliquota': str(federal.aliquota_ipi) if federal else '0',
        },
        'pis': {
            'cst': str(federal.cst_pis) if federal and federal.cst_pis else '—',
            'aliquota': str(federal.aliquota_pis) if federal else '0',
            'gera_credito': federal.gera_credito_pis if federal else False,
        },
        'cofins': {
            'cst': str(federal.cst_cofins) if federal and federal.cst_cofins else '—',
            'aliquota': str(federal.aliquota_cofins) if federal else '0',
            'gera_credito': federal.gera_credito_cofins if federal else False,
        },
        'icms_st': {
            'tem_st': estadual.tem_st if estadual else False,
            'aliquota': str(estadual.aliquota_icms_st) if estadual else '0',
            'mva': str(estadual.mva) if estadual else '0',
            'aliquota_fcp': str(estadual.aliquota_fcp) if estadual else '0',
        },
    })


@login_required
@permission_required('tributacao.view_grupotributario', raise_exception=True)
def api_grupo_detail(request, pk):
    """API para preview do grupo tributário no formulário de material."""
    grupo = get_object_or_404(GrupoTributario, pk=pk)

    # Checa acesso à filial
    if not _pode_ver_todas_filiais(request.user):
        grupos_permitidos = _filtrar_grupos_por_filial(
            GrupoTributario.objects.all(), request.user
        )
        if grupo not in grupos_permitidos:
            return JsonResponse({'error': 'Sem permissão'}, status=403)

    calc = grupo.calcular_impostos(valor_produtos=1000, quantidade=1)

    return JsonResponse({
        "nome": grupo.nome,
        "cfop": grupo.cfop.codigo if grupo.cfop else "—",
        "natureza": grupo.get_natureza_display() if hasattr(grupo, 'get_natureza_display') else grupo.natureza,
        "icms": {
            "aliquota": str(calc["icms"]["aliquota"]),
            "recuperavel": calc["icms"]["recuperavel"],
            "reducao_base": str(calc["icms"]["reducao_base"]),
            "uf": calc["icms"].get("uf", "SP"),
        },
        "ipi": {
            "aliquota": str(calc["ipi"]["aliquota"]),
            "recuperavel": calc["ipi"]["recuperavel"],
        },
        "pis": {
            "aliquota": str(calc["pis"]["aliquota"]),
            "recuperavel": calc["pis"]["recuperavel"],
        },
        "cofins": {
            "aliquota": str(calc["cofins"]["aliquota"]),
            "recuperavel": calc["cofins"]["recuperavel"],
        },
        "icms_st": {
            "tem_st": calc["icms_st"]["tem_st"],
            "mva": str(calc["icms_st"]["mva"]),
        },
    })

