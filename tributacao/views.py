
# tributacao/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q

from .models import NCM, CFOP, CST, GrupoTributario, TributacaoFederal, TributacaoEstadual
from .forms import (
    NCMForm, CFOPForm, CSTForm,
    GrupoTributarioForm, TributacaoFederalForm,
    TributacaoEstadualForm, TributacaoEstadualFormSet,
)
from django.http import JsonResponse



# ══════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════
@login_required
def dashboard(request):
    context = {
        "total_ncm": NCM.objects.filter(ativo=True).count(),
        "total_cfop": CFOP.objects.filter(ativo=True).count(),
        "total_cst": CST.objects.count(),
        "total_grupos": GrupoTributario.objects.filter(ativo=True).count(),
        "total_trib_federal": TributacaoFederal.objects.count(),
        "total_trib_estadual": TributacaoEstadual.objects.filter(ativo=True).count(),
    }
    return render(request, "tributacao/dashboard.html", context)


# ══════════════════════════════════════════════════════
# NCM — CRUD
# ══════════════════════════════════════════════════════
@login_required
def ncm_list(request):
    q = request.GET.get("q", "").strip()
    ncms = NCM.objects.all()
    if q:
        ncms = ncms.filter(Q(codigo__icontains=q) | Q(descricao__icontains=q))
    return render(request, "tributacao/ncm_list.html", {"ncms": ncms, "q": q})


@login_required
def ncm_create(request):
    if request.method == "POST":
        form = NCMForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "NCM cadastrado com sucesso!")
            return redirect("tributacao:ncm_list")
    else:
        form = NCMForm()
    return render(request, "tributacao/ncm_form.html", {"form": form, "titulo": "Novo NCM"})


@login_required
def ncm_update(request, pk):
    ncm = get_object_or_404(NCM, pk=pk)
    if request.method == "POST":
        form = NCMForm(request.POST, instance=ncm)
        if form.is_valid():
            form.save()
            messages.success(request, "NCM atualizado com sucesso!")
            return redirect("tributacao:ncm_list")
    else:
        form = NCMForm(instance=ncm)
    return render(request, "tributacao/ncm_form.html", {"form": form, "titulo": "Editar NCM"})


@login_required
def ncm_delete(request, pk):
    ncm = get_object_or_404(NCM, pk=pk)
    if request.method == "POST":
        ncm.delete()
        messages.success(request, "NCM excluído com sucesso!")
        return redirect("tributacao:ncm_list")
    return render(request, "tributacao/confirm_delete.html", {"objeto": ncm, "tipo": "NCM"})


# ══════════════════════════════════════════════════════
# CFOP — CRUD
# ══════════════════════════════════════════════════════
@login_required
def cfop_list(request):
    q = request.GET.get("q", "").strip()
    cfops = CFOP.objects.all()
    if q:
        cfops = cfops.filter(Q(codigo__icontains=q) | Q(descricao__icontains=q))
    return render(request, "tributacao/cfop_list.html", {"cfops": cfops, "q": q})


@login_required
def cfop_create(request):
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
def cfop_update(request, pk):
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
def cfop_delete(request, pk):
    cfop = get_object_or_404(CFOP, pk=pk)
    if request.method == "POST":
        cfop.delete()
        messages.success(request, "CFOP excluído com sucesso!")
        return redirect("tributacao:cfop_list")
    return render(request, "tributacao/confirm_delete.html", {"objeto": cfop, "tipo": "CFOP"})


# ══════════════════════════════════════════════════════
# CST — CRUD
# ══════════════════════════════════════════════════════
@login_required
def cst_list(request):
    q = request.GET.get("q", "").strip()
    tipo_filtro = request.GET.get("tipo", "").strip()
    csts = CST.objects.all()
    if q:
        csts = csts.filter(Q(codigo__icontains=q) | Q(descricao__icontains=q))
    if tipo_filtro:
        csts = csts.filter(tipo=tipo_filtro)
    return render(request, "tributacao/cst_list.html", {
        "csts": csts, "q": q, "tipo_filtro": tipo_filtro,
        "tipos": CST.TIPO_CHOICES,
    })


@login_required
def cst_create(request):
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
def cst_update(request, pk):
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
def cst_delete(request, pk):
    cst = get_object_or_404(CST, pk=pk)
    if request.method == "POST":
        cst.delete()
        messages.success(request, "CST excluído com sucesso!")
        return redirect("tributacao:cst_list")
    return render(request, "tributacao/confirm_delete.html", {"objeto": cst, "tipo": "CST"})


# ══════════════════════════════════════════════════════
# GRUPO TRIBUTÁRIO — CRUD com inlines
# ══════════════════════════════════════════════════════
@login_required
def grupo_list(request):
    q = request.GET.get("q", "").strip()
    grupos = GrupoTributario.objects.select_related("cfop", "ncm", "filial").all()
    if q:
        grupos = grupos.filter(Q(nome__icontains=q) | Q(descricao__icontains=q))
    return render(request, "tributacao/grupo_list.html", {"grupos": grupos, "q": q})


@login_required
def grupo_create(request):
    if request.method == "POST":
        form = GrupoTributarioForm(request.POST)
        federal_form = TributacaoFederalForm(request.POST, prefix="federal")
        estadual_formset = TributacaoEstadualFormSet(request.POST, prefix="estadual")

        if form.is_valid() and federal_form.is_valid() and estadual_formset.is_valid():
            grupo = form.save()

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
        form = GrupoTributarioForm()
        federal_form = TributacaoFederalForm(prefix="federal")
        estadual_formset = TributacaoEstadualFormSet(prefix="estadual")

    return render(request, "tributacao/grupo_form.html", {
        "form": form,
        "federal_form": federal_form,
        "estadual_formset": estadual_formset,
        "titulo": "Novo Grupo Tributário",
    })


@login_required
def grupo_update(request, pk):
    grupo = get_object_or_404(GrupoTributario, pk=pk)

    # Pega ou cria tributação federal
    federal_instance = getattr(grupo, "tributacao_federal", None)

    if request.method == "POST":
        form = GrupoTributarioForm(request.POST, instance=grupo)
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
        form = GrupoTributarioForm(instance=grupo)
        federal_form = TributacaoFederalForm(prefix="federal", instance=federal_instance)
        estadual_formset = TributacaoEstadualFormSet(prefix="estadual", instance=grupo)

    return render(request, "tributacao/grupo_form.html", {
        "form": form,
        "federal_form": federal_form,
        "estadual_formset": estadual_formset,
        "titulo": f"Editar — {grupo.nome}",
    })


@login_required
def grupo_delete(request, pk):
    grupo = get_object_or_404(GrupoTributario, pk=pk)
    if request.method == "POST":
        grupo.delete()
        messages.success(request, "Grupo Tributário excluído com sucesso!")
        return redirect("tributacao:grupo_list")
    return render(request, "tributacao/confirm_delete.html", {
        "objeto": grupo, "tipo": "Grupo Tributário",
    })


@login_required
def grupo_detail(request, pk):
    grupo = get_object_or_404(
        GrupoTributario.objects.select_related("cfop", "ncm", "filial"),
        pk=pk,
    )
    federal = getattr(grupo, "tributacao_federal", None)
    estaduais = grupo.tributacoes_estaduais.filter(ativo=True).order_by("uf_origem", "uf_destino")

    return render(request, "tributacao/grupo_detail.html", {
        "grupo": grupo,
        "federal": federal,
        "estaduais": estaduais,
    })


def grupo_tributario_api(request, pk):
    """Retorna dados do grupo tributário para preview no form de material."""
    grupo = get_object_or_404(GrupoTributario, pk=pk)

    # Tributação Federal (OneToOne via related_name='tributacao_federal')
    federal = getattr(grupo, 'tributacao_federal', None)

    # Tributação Estadual (pega a primeira ativa)
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



def api_grupo_detail(request, pk):
    """API para preview do grupo tributário no formulário de material."""
    grupo = get_object_or_404(GrupoTributario, pk=pk)

    # Calcula com valor exemplo de R$ 1000 para mostrar alíquotas
    calc = grupo.calcular_impostos(valor_produtos=1000, quantidade=1)

    return JsonResponse({
        "nome": grupo.nome,
        "cfop": grupo.cfop.codigo if grupo.cfop else "—",
        "natureza": grupo.get_natureza_display() if hasattr(grupo, 'get_natureza_display') else grupo.natureza,
        "icms": {
            "aliquota": str(calc["icms"]["aliquota"]),
            "recuperavel": calc["icms"]["recuperavel"],
            "reducao_base": str(calc["icms"]["reducao_base"]),
            "uf": calc["icms"]["uf"],
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
