# ltcat/views.py
import base64
import json

from django.contrib import messages
from django.core.files.base import ContentFile
from django.db.models import Count, Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView,
)

from cliente.models import Cliente
from core.decorators import funcionario_required
from core.mixins import FilialCreateMixin, ViewFilialScopedMixin
from departamento_pessoal.models import Cargo, Funcionario
from seguranca_trabalho.models import Funcao

from .mixins import (
    FilialFormKwargsMixin,
    LTCATAccessMixin,
    LTCATBaseMixin,
    LTCATChildMixin,
)
from .forms import (
    AnexoLTCATForm,
    AvaliacaoPericulosidadeForm,
    ConclusaoFuncaoForm,
    EmpresaLTCATForm,
    FuncaoAnalisadaForm,
    LocalPrestacaoServicoForm,
    LTCATForm,
    ReconhecimentoRiscoForm,
    RecomendacaoTecnicaForm,
    RevisaoLTCATForm,
)
from .models import (
    STATUS_LTCAT_CHOICES,
    TIPO_RESPONSABILIDADE_LTCAT_CHOICES,
    AnexoLTCAT,
    AvaliacaoPericulosidade,
    ConclusaoFuncao,
    DocumentoLocalPrestacao,
    EmpresaLTCAT,
    FuncaoAnalisada,
    LocalPrestacaoServicoLTCAT,
    LTCATDocumento,
    LTCATDocumentoResponsavel,
    ProfissionalResponsavelLTCAT,
    ReconhecimentoRisco,
    RecomendacaoTecnica,
    RevisaoLTCAT,
)


# =============================================================================
# == DASHBOARD
# =============================================================================

class DashboardView(LTCATBaseMixin, ViewFilialScopedMixin, ListView):
    model = LTCATDocumento
    template_name = "ltcat/dashboard.html"
    context_object_name = "ltcats"
    permission_required = "ltcat.view_ltcatdocumento"

    def get_queryset(self):
        return (
            super().get_queryset()
            .select_related("empresa", "filial")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        ctx["total_ltcats"] = qs.count()
        ctx["total_vigentes"] = qs.filter(status="vigente").count()
        ctx["total_rascunhos"] = qs.filter(status="rascunho").count()
        ctx["total_vencidos"] = sum(1 for obj in qs if obj.is_vencido)
        ctx["recentes"] = qs[:5]
        return ctx


# =============================================================================
# == EMPRESA LTCAT (Contratada) - CRUD
# =============================================================================

class EmpresaLTCATListView(LTCATBaseMixin, ViewFilialScopedMixin, ListView):
    model = EmpresaLTCAT
    template_name = "ltcat/empresa_ltcat_list.html"
    context_object_name = "empresas"
    permission_required = "ltcat.view_empresaltcat"
    paginate_by = 20


class EmpresaLTCATCreateView(LTCATBaseMixin, FilialFormKwargsMixin, FilialCreateMixin, CreateView):
    model = EmpresaLTCAT
    form_class = EmpresaLTCATForm
    template_name = "ltcat/empresa_ltcat_form.html"
    permission_required = "ltcat.add_empresaltcat"

    def form_valid(self, form):
        form.instance.criado_por = self.request.user
        messages.success(self.request, "Empresa contratada cadastrada com sucesso!")
        return super().form_valid(form)

    def get_success_url(self):
        next_url = self.request.GET.get("next")
        if next_url:
            return next_url
        return reverse("ltcat:empresa_ltcat_list")


class EmpresaLTCATUpdateView(LTCATBaseMixin, FilialFormKwargsMixin, ViewFilialScopedMixin, UpdateView):
    model = EmpresaLTCAT
    form_class = EmpresaLTCATForm
    template_name = "ltcat/empresa_ltcat_form.html"
    permission_required = "ltcat.change_empresaltcat"

    def form_valid(self, form):
        messages.success(self.request, "Empresa contratada atualizada com sucesso!")
        return super().form_valid(form)

    def get_success_url(self):
        next_url = self.request.GET.get("next")
        if next_url:
            return next_url
        return reverse("ltcat:empresa_ltcat_list")


class EmpresaLTCATDeleteView(LTCATBaseMixin, ViewFilialScopedMixin, DeleteView):
    model = EmpresaLTCAT
    template_name = "ltcat/empresa_ltcat_confirm_delete.html"
    permission_required = "ltcat.delete_empresaltcat"
    success_url = reverse_lazy("ltcat:empresa_ltcat_list")

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Empresa contratada excluida com sucesso!")
        return super().delete(request, *args, **kwargs)


# =============================================================================
# == LTCAT DOCUMENTO - CRUD
# =============================================================================

class LTCATListView(LTCATBaseMixin, ViewFilialScopedMixin, ListView):
    model = LTCATDocumento
    template_name = "ltcat/ltcat_list.html"
    context_object_name = "ltcats"
    paginate_by = 15
    permission_required = "ltcat.view_ltcatdocumento"

    def get_queryset(self):
        qs = (
            super().get_queryset()
            .select_related("empresa", "filial")
            .annotate(
                total_funcoes=Count("funcoes"),
                total_riscos=Count("funcoes__riscos"),
            )
        )

        status = self.request.GET.get("status")
        busca = self.request.GET.get("q")
        if status:
            qs = qs.filter(status=status)
        if busca:
            qs = qs.filter(
                Q(empresa__razao_social__icontains=busca)
                | Q(titulo__icontains=busca)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = STATUS_LTCAT_CHOICES
        ctx["status_atual"] = self.request.GET.get("status", "")
        ctx["busca"] = self.request.GET.get("q", "")
        return ctx


class LTCATCreateView(LTCATBaseMixin, FilialFormKwargsMixin, FilialCreateMixin, CreateView):
    model = LTCATDocumento
    form_class = LTCATForm
    template_name = "ltcat/ltcat_form.html"
    permission_required = "ltcat.add_ltcatdocumento"

    def form_valid(self, form):
        form.instance.criado_por = self.request.user
        messages.success(self.request, "LTCAT criado com sucesso!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.object.pk})


class LTCATUpdateView(LTCATBaseMixin, FilialFormKwargsMixin, LTCATAccessMixin, ViewFilialScopedMixin, UpdateView):
    model = LTCATDocumento
    form_class = LTCATForm
    template_name = "ltcat/ltcat_form.html"
    permission_required = "ltcat.change_ltcatdocumento"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not self.check_ltcat_access(obj):
            raise Http404("LTCAT nao encontrado.")
        return obj

    def form_valid(self, form):
        messages.success(self.request, "LTCAT atualizado com sucesso!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.object.pk})


class LTCATDetailView(LTCATBaseMixin, LTCATAccessMixin, ViewFilialScopedMixin, DetailView):
    model = LTCATDocumento
    template_name = "ltcat/ltcat_detail.html"
    context_object_name = "ltcat"
    permission_required = "ltcat.view_ltcatdocumento"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not self.check_ltcat_access(obj):
            raise Http404("LTCAT nao encontrado.")
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ltcat_doc = self.object
        ctx["revisoes"] = ltcat_doc.revisoes.all()
        ctx["funcoes"] = ltcat_doc.funcoes.prefetch_related("riscos").all()
        ctx["periculosidades"] = ltcat_doc.avaliacoes_periculosidade.all()
        ctx["conclusoes"] = ltcat_doc.conclusoes.select_related("funcao").all()
        ctx["recomendacoes"] = ltcat_doc.recomendacoes.all()
        ctx["anexos"] = ltcat_doc.anexos.all()
        ctx["locais"] = LocalPrestacaoServicoLTCAT.objects.filter(
            empresa=ltcat_doc.empresa
        )

        # Responsaveis vinculados
        ctx["responsaveis_doc"] = LTCATDocumentoResponsavel.objects.filter(
            ltcat_documento=ltcat_doc
        ).select_related("profissional", "profissional__funcionario")

        # Funcionarios para o select (ativos da filial)
        filial_id = self.request.session.get("active_filial_id")
        if filial_id:
            ctx["funcionarios_disponiveis"] = (
                Funcionario.objects
                .filter(filial_id=filial_id, status="ativo")
                .select_related("cargo")
                .order_by("nome_completo")
            )
        else:
            ctx["funcionarios_disponiveis"] = Funcionario.objects.none()

        ctx["tipos_responsabilidade"] = TIPO_RESPONSABILIDADE_LTCAT_CHOICES
        return ctx


class LTCATDeleteView(LTCATBaseMixin, LTCATAccessMixin, ViewFilialScopedMixin, DeleteView):
    model = LTCATDocumento
    template_name = "ltcat/ltcat_confirm_delete.html"
    success_url = reverse_lazy("ltcat:ltcat_list")
    permission_required = "ltcat.delete_ltcatdocumento"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not self.check_ltcat_access(obj):
            raise Http404("LTCAT nao encontrado.")
        return obj

    def delete(self, request, *args, **kwargs):
        messages.success(request, "LTCAT excluido com sucesso!")
        return super().delete(request, *args, **kwargs)


# =============================================================================
# == LOCAIS DE PRESTACAO DE SERVICO - CRUD
# =============================================================================

class LocalPrestacaoListView(LTCATBaseMixin, ViewFilialScopedMixin, ListView):
    model = LocalPrestacaoServicoLTCAT
    template_name = "ltcat/local_list.html"
    context_object_name = "locais"
    paginate_by = 20
    permission_required = "ltcat.view_localprestacaoservicoltcat"

    def get_queryset(self):
        qs = super().get_queryset().select_related("empresa", "logradouro", "filial")
        busca = self.request.GET.get("q")
        empresa_id = self.request.GET.get("empresa")
        if busca:
            qs = qs.filter(
                Q(nome_local__icontains=busca)
                | Q(empresa__razao_social__icontains=busca)
                | Q(cidade__icontains=busca)
            )
        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["busca"] = self.request.GET.get("q", "")
        return ctx


class LocalPrestacaoCreateView(LTCATBaseMixin, FilialFormKwargsMixin, FilialCreateMixin, CreateView):
    model = LocalPrestacaoServicoLTCAT
    form_class = LocalPrestacaoServicoForm
    template_name = "ltcat/local_form.html"
    permission_required = "ltcat.add_localprestacaoservicoltcat"
    success_url = reverse_lazy("ltcat:local_list")

    def form_valid(self, form):
        form.instance.criado_por = self.request.user
        messages.success(self.request, "Local de prestacao cadastrado com sucesso!")
        return super().form_valid(form)


class LocalPrestacaoUpdateView(LTCATBaseMixin, FilialFormKwargsMixin, ViewFilialScopedMixin, UpdateView):
    model = LocalPrestacaoServicoLTCAT
    form_class = LocalPrestacaoServicoForm
    template_name = "ltcat/local_form.html"
    permission_required = "ltcat.change_localprestacaoservicoltcat"
    success_url = reverse_lazy("ltcat:local_list")

    def form_valid(self, form):
        messages.success(self.request, "Local de prestacao atualizado!")
        return super().form_valid(form)


class LocalPrestacaoDeleteView(LTCATBaseMixin, ViewFilialScopedMixin, DeleteView):
    model = LocalPrestacaoServicoLTCAT
    template_name = "ltcat/confirm_delete_generic.html"
    permission_required = "ltcat.delete_localprestacaoservicoltcat"
    success_url = reverse_lazy("ltcat:local_list")

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Local excluido com sucesso!")
        return super().delete(request, *args, **kwargs)


# =============================================================================
# == REVISOES (filho de LTCAT)
# =============================================================================

class RevisaoCreateView(LTCATChildMixin, CreateView):
    model = RevisaoLTCAT
    form_class = RevisaoLTCATForm
    template_name = "ltcat/revisao_form.html"
    permission_required = "ltcat.add_revisaoltcat"

    def form_valid(self, form):
        form.instance.ltcat_documento = self.get_ltcat()
        messages.success(self.request, "Revisao adicionada com sucesso!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


class RevisaoUpdateView(LTCATChildMixin, UpdateView):
    model = RevisaoLTCAT
    form_class = RevisaoLTCATForm
    template_name = "ltcat/revisao_form.html"
    permission_required = "ltcat.change_revisaoltcat"

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


class RevisaoDeleteView(LTCATChildMixin, DeleteView):
    model = RevisaoLTCAT
    template_name = "ltcat/confirm_delete_generic.html"
    permission_required = "ltcat.delete_revisaoltcat"

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


# =============================================================================
# == FUNCOES ANALISADAS (filho de LTCAT)
# =============================================================================

class FuncaoCreateView(LTCATChildMixin, CreateView):
    model = FuncaoAnalisada
    form_class = FuncaoAnalisadaForm
    template_name = "ltcat/funcao_form.html"
    permission_required = "ltcat.add_funcaoanalisada"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["ltcat"] = self.get_ltcat()
        return kwargs

    def form_valid(self, form):
        form.instance.ltcat_documento = self.get_ltcat()
        messages.success(self.request, "Funcao adicionada com sucesso!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


class FuncaoUpdateView(LTCATChildMixin, UpdateView):
    model = FuncaoAnalisada
    form_class = FuncaoAnalisadaForm
    template_name = "ltcat/funcao_form.html"
    permission_required = "ltcat.change_funcaoanalisada"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["ltcat"] = self.get_ltcat()
        return kwargs

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


class FuncaoDeleteView(LTCATChildMixin, DeleteView):
    model = FuncaoAnalisada
    template_name = "ltcat/confirm_delete_generic.html"
    permission_required = "ltcat.delete_funcaoanalisada"

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


# =============================================================================
# == RECONHECIMENTO DE RISCOS (filho de LTCAT)
# =============================================================================

class RiscoCreateView(LTCATChildMixin, CreateView):
    """Cria um risco vinculado a um LTCAT (e opcionalmente a uma funcao)."""
    model = ReconhecimentoRisco
    form_class = ReconhecimentoRiscoForm
    template_name = "ltcat/risco_form.html"
    permission_required = "ltcat.add_reconhecimentorisco"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["ltcat"] = self.get_ltcat()
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        funcao_pk = self.request.GET.get("funcao") or self.kwargs.get("funcao_pk")
        if funcao_pk:
            try:
                ctx["funcao"] = FuncaoAnalisada.objects.get(pk=funcao_pk)
            except FuncaoAnalisada.DoesNotExist:
                ctx["funcao"] = None
        return ctx

    def get_initial(self):
        initial = super().get_initial()
        funcao_pk = self.request.GET.get("funcao") or self.kwargs.get("funcao_pk")
        if funcao_pk:
            initial["funcao"] = funcao_pk
        return initial

    def form_valid(self, form):
        form.instance.ltcat_documento = self.get_ltcat()
        messages.success(self.request, "Risco cadastrado com sucesso!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


class RiscoUpdateView(LTCATChildMixin, UpdateView):
    model = ReconhecimentoRisco
    form_class = ReconhecimentoRiscoForm
    template_name = "ltcat/risco_form.html"
    permission_required = "ltcat.change_reconhecimentorisco"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["ltcat"] = self.get_ltcat()
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Risco atualizado com sucesso!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


class RiscoDeleteView(LTCATChildMixin, DeleteView):
    model = ReconhecimentoRisco
    template_name = "ltcat/confirm_delete_generic.html"
    permission_required = "ltcat.delete_reconhecimentorisco"

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


# =============================================================================
# == AVALIACAO DE PERICULOSIDADE (filho de LTCAT)
# =============================================================================

class PericulosidadeCreateView(LTCATChildMixin, CreateView):
    model = AvaliacaoPericulosidade
    form_class = AvaliacaoPericulosidadeForm
    template_name = "ltcat/periculosidade_form.html"
    permission_required = "ltcat.add_avaliacaopericulosidade"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["ltcat"] = self.get_ltcat()
        return kwargs

    def form_valid(self, form):
        form.instance.ltcat_documento = self.get_ltcat()
        messages.success(self.request, "Avaliacao de periculosidade adicionada!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


class PericulosidadeUpdateView(LTCATChildMixin, UpdateView):
    model = AvaliacaoPericulosidade
    form_class = AvaliacaoPericulosidadeForm
    template_name = "ltcat/periculosidade_form.html"
    permission_required = "ltcat.change_avaliacaopericulosidade"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["ltcat"] = self.get_ltcat()
        return kwargs

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


# =============================================================================
# == CONCLUSOES (filho de LTCAT)
# =============================================================================

class ConclusaoCreateView(LTCATChildMixin, CreateView):
    model = ConclusaoFuncao
    form_class = ConclusaoFuncaoForm
    template_name = "ltcat/conclusao_form.html"
    permission_required = "ltcat.add_conclusaofuncao"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["ltcat"] = self.get_ltcat()
        return kwargs

    def form_valid(self, form):
        form.instance.ltcat_documento = self.get_ltcat()
        messages.success(self.request, "Conclusao adicionada com sucesso!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


class ConclusaoUpdateView(LTCATChildMixin, UpdateView):
    model = ConclusaoFuncao
    form_class = ConclusaoFuncaoForm
    template_name = "ltcat/conclusao_form.html"
    permission_required = "ltcat.change_conclusaofuncao"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["ltcat"] = self.get_ltcat()
        return kwargs

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


# =============================================================================
# == RECOMENDACOES (filho de LTCAT)
# =============================================================================

class RecomendacaoCreateView(LTCATChildMixin, CreateView):
    model = RecomendacaoTecnica
    form_class = RecomendacaoTecnicaForm
    template_name = "ltcat/recomendacao_form.html"
    permission_required = "ltcat.add_recomendacaotecnica"

    def form_valid(self, form):
        form.instance.ltcat_documento = self.get_ltcat()
        messages.success(self.request, "Recomendacao adicionada com sucesso!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


class RecomendacaoUpdateView(LTCATChildMixin, UpdateView):
    model = RecomendacaoTecnica
    form_class = RecomendacaoTecnicaForm
    template_name = "ltcat/recomendacao_form.html"
    permission_required = "ltcat.change_recomendacaotecnica"

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


class RecomendacaoDeleteView(LTCATChildMixin, DeleteView):
    model = RecomendacaoTecnica
    template_name = "ltcat/confirm_delete_generic.html"
    permission_required = "ltcat.delete_recomendacaotecnica"

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


# =============================================================================
# == ANEXOS (filho de LTCAT)
# =============================================================================

class AnexoCreateView(LTCATChildMixin, CreateView):
    model = AnexoLTCAT
    form_class = AnexoLTCATForm
    template_name = "ltcat/anexo_form.html"
    permission_required = "ltcat.add_anexoltcat"

    def form_valid(self, form):
        form.instance.ltcat_documento = self.get_ltcat()
        messages.success(self.request, "Anexo adicionado com sucesso!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


class AnexoDeleteView(LTCATChildMixin, DeleteView):
    model = AnexoLTCAT
    template_name = "ltcat/confirm_delete_generic.html"
    permission_required = "ltcat.delete_anexoltcat"

    def get_success_url(self):
        return reverse("ltcat:ltcat_detail", kwargs={"pk": self.kwargs["ltcat_pk"]})


# =============================================================================
# == HELPERS PRIVADOS (uso interno das FBVs AJAX)
# =============================================================================

def _user_pode_acessar_ltcat(user, ltcat_doc, session_filial_id):
    """Replica logica do LTCATAccessMixin para FBVs."""
    if user.is_superuser or user.is_staff:
        return True
    return bool(session_filial_id) and ltcat_doc.filial_id == int(session_filial_id)


# =============================================================================
# == AJAX - LOCAIS DE PRESTACAO
# =============================================================================

@funcionario_required
def ajax_locais_por_empresa(request):
    """Retorna locais de prestacao filtrados por empresa (Cliente)."""
    empresa_id = request.GET.get("empresa_id")
    if not empresa_id:
        return JsonResponse([], safe=False)

    qs = LocalPrestacaoServicoLTCAT.objects.filter(empresa_id=empresa_id)

    user = request.user
    filial_id = request.session.get("active_filial_id")
    if not (user.is_superuser or user.is_staff) and filial_id:
        qs = qs.filter(filial_id=filial_id)

    locais = [{"id": str(loc.pk), "nome": str(loc)} for loc in qs]
    return JsonResponse(locais, safe=False)


@funcionario_required
def ajax_buscar_logradouros(request):
    """Autocomplete de logradouros com busca por texto."""
    from logradouro.models import Logradouro

    termo = request.GET.get("q", "").strip()
    if len(termo) < 2:
        return JsonResponse([], safe=False)

    filial_id = request.session.get("active_filial_id")
    qs = Logradouro.objects.all()

    user = request.user
    if not (user.is_superuser or user.is_staff) and filial_id:
        qs = qs.filter(filial_id=filial_id)
    elif filial_id:
        qs = qs.filter(filial_id=filial_id)

    qs = qs.filter(
        Q(endereco__icontains=termo)
        | Q(bairro__icontains=termo)
        | Q(cidade__icontains=termo)
        | Q(cep__icontains=termo.replace("-", ""))
    )[:20]

    resultados = [
        {
            "id": log.pk,
            "text": log.get_endereco_completo(),
            "endereco": log.endereco,
            "numero": log.numero,
            "bairro": log.bairro,
            "cidade": log.cidade,
            "estado": log.estado,
            "cep": log.cep_formatado,
        }
        for log in qs
    ]
    return JsonResponse(resultados, safe=False)


@funcionario_required
@require_POST
def ajax_local_create_bulk(request):
    """Cria varios locais de prestacao de uma vez (bulk)."""
    from logradouro.models import Logradouro
    from usuario.models import Filial

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON invalido."}, status=400)

    empresa_id = data.get("empresa_id")
    locais_data = data.get("locais", [])

    if not empresa_id:
        return JsonResponse({"error": "Empresa nao informada."}, status=400)
    if not locais_data:
        return JsonResponse({"error": "Nenhum local informado."}, status=400)

    try:
        empresa = Cliente.objects.get(pk=empresa_id)
    except Cliente.DoesNotExist:
        return JsonResponse({"error": "Empresa nao encontrada."}, status=404)

    filial_id = request.session.get("active_filial_id")
    if not filial_id:
        return JsonResponse({"error": "Filial ativa nao definida."}, status=400)

    try:
        filial = Filial.objects.get(pk=filial_id)
    except Filial.DoesNotExist:
        return JsonResponse({"error": "Filial nao encontrada."}, status=400)

    user = request.user
    if not (user.is_superuser or user.is_staff):
        if empresa.filial_id != int(filial_id):
            return JsonResponse({"error": "Sem permissao para esta empresa."}, status=403)

    logradouro_ids = [
        loc.get("logradouro_id")
        for loc in locais_data
        if loc.get("logradouro_id")
    ]
    logradouros_existentes = set(
        Logradouro.objects.filter(pk__in=logradouro_ids).values_list("pk", flat=True)
    )

    errors = []
    criados = []
    for idx, loc in enumerate(locais_data, start=1):
        nome_local = (loc.get("nome_local") or "").strip()
        if not nome_local:
            errors.append(f"Local #{idx}: Nome eh obrigatorio.")
            continue

        logradouro_id = loc.get("logradouro_id")
        if logradouro_id and int(logradouro_id) not in logradouros_existentes:
            logradouro_id = None

        criados.append(LocalPrestacaoServicoLTCAT(
            empresa=empresa,
            filial=filial,
            criado_por=user,
            nome_local=nome_local,
            razao_social=(loc.get("razao_social") or "").strip(),
            cnpj=(loc.get("cnpj") or "").strip(),
            descricao=(loc.get("descricao") or "").strip(),
            logradouro_id=logradouro_id or None,
            endereco=(loc.get("endereco") or "").strip(),
            numero=(loc.get("numero") or "").strip(),
            complemento=(loc.get("complemento") or "").strip(),
            bairro=(loc.get("bairro") or "").strip(),
            cidade=(loc.get("cidade") or "").strip(),
            estado=(loc.get("estado") or "").strip(),
            cep=(loc.get("cep") or "").strip(),
        ))

    if errors:
        return JsonResponse({"errors": errors}, status=400)

    LocalPrestacaoServicoLTCAT.objects.bulk_create(criados)
    return JsonResponse({
        "success": True,
        "total": len(criados),
        "message": f"{len(criados)} local(is) cadastrado(s) com sucesso!",
    })


# =============================================================================
# == AJAX - DADOS DE CLIENTE
# =============================================================================

@funcionario_required
def ajax_dados_cliente(request):
    """Retorna dados do Cliente para auto-preenchimento do form EmpresaLTCAT."""
    cliente_id = request.GET.get("cliente_id")
    if not cliente_id:
        return JsonResponse({"error": "cliente_id obrigatorio"}, status=400)

    try:
        cliente = Cliente.objects.get(pk=cliente_id)
    except Cliente.DoesNotExist:
        return JsonResponse({"error": "Cliente nao encontrado"}, status=404)

    log = getattr(cliente, "logradouro", None)
    dados = {
        "razao_social": cliente.razao_social or "",
        "cnpj": getattr(cliente, "cnpj", "") or "",
        "telefone": getattr(cliente, "telefone", "") or "",
        "email": getattr(cliente, "email", "") or "",
        "endereco": "",
        "numero": "",
        "complemento": "",
        "bairro": "",
        "cidade": "",
        "estado": "",
        "cep": "",
    }

    if log:
        dados.update({
            "endereco": getattr(log, "endereco", "") or "",
            "numero": getattr(log, "numero", "") or "",
            "complemento": getattr(log, "complemento", "") or "",
            "bairro": getattr(log, "bairro", "") or "",
            "cidade": getattr(log, "cidade", "") or "",
            "estado": getattr(log, "estado", "") or "",
            "cep": getattr(log, "cep", "") or "",
        })

    return JsonResponse(dados)


# =============================================================================
# == AJAX - VINCULOS LOCAIS x DOCUMENTO LTCAT
# =============================================================================

@funcionario_required
@require_POST
def ajax_vincular_locais_documento(request, ltcat_pk):
    """Vincula locais de prestacao ao documento LTCAT."""
    ltcat_doc = get_object_or_404(LTCATDocumento, pk=ltcat_pk)
    filial_id = request.session.get("active_filial_id")

    if not _user_pode_acessar_ltcat(request.user, ltcat_doc, filial_id):
        return JsonResponse({"error": "Sem permissao."}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON invalido."}, status=400)

    local_ids = data.get("local_ids", [])
    if not local_ids:
        return JsonResponse({"error": "Nenhum local informado."}, status=400)

    locais = LocalPrestacaoServicoLTCAT.objects.filter(
        pk__in=local_ids, empresa=ltcat_doc.empresa,
    )

    ja_vinculados = set(
        DocumentoLocalPrestacao.objects.filter(
            ltcat_documento=ltcat_doc, local_prestacao_id__in=local_ids,
        ).values_list("local_prestacao_id", flat=True)
    )

    tem_principal = DocumentoLocalPrestacao.objects.filter(
        ltcat_documento=ltcat_doc, principal=True,
    ).exists()

    novos = []
    for idx, local in enumerate(locais):
        if local.pk not in ja_vinculados:
            novos.append(DocumentoLocalPrestacao(
                ltcat_documento=ltcat_doc,
                local_prestacao=local,
                principal=(not tem_principal and idx == 0 and not novos),
                ordem=DocumentoLocalPrestacao.objects.filter(
                    ltcat_documento=ltcat_doc
                ).count() + len(novos),
            ))

    if novos:
        DocumentoLocalPrestacao.objects.bulk_create(novos)

    total = len(novos)
    return JsonResponse({
        "success": True,
        "vinculados": total,
        "message": f"{total} local(is) vinculado(s) ao documento.",
    })


@funcionario_required
@require_POST
def ajax_desvincular_local_documento(request, ltcat_pk, pk):
    """Remove o vinculo de um local com o documento LTCAT."""
    ltcat_doc = get_object_or_404(LTCATDocumento, pk=ltcat_pk)
    filial_id = request.session.get("active_filial_id")

    if not _user_pode_acessar_ltcat(request.user, ltcat_doc, filial_id):
        return JsonResponse({"error": "Sem permissao."}, status=403)

    vinculo = get_object_or_404(
        DocumentoLocalPrestacao, pk=pk, ltcat_documento=ltcat_doc,
    )
    nome = vinculo.local_prestacao.nome_local
    vinculo.delete()

    return JsonResponse({
        "success": True,
        "message": f"Local '{nome}' desvinculado do documento.",
    })


@funcionario_required
@require_POST
def ajax_toggle_principal_local(request, ltcat_pk, pk):
    """Marca/desmarca um local como principal no documento."""
    ltcat_doc = get_object_or_404(LTCATDocumento, pk=ltcat_pk)
    filial_id = request.session.get("active_filial_id")

    if not _user_pode_acessar_ltcat(request.user, ltcat_doc, filial_id):
        return JsonResponse({"error": "Sem permissao."}, status=403)

    vinculo = get_object_or_404(
        DocumentoLocalPrestacao, pk=pk, ltcat_documento=ltcat_doc,
    )
    vinculo.principal = not vinculo.principal
    vinculo.save()

    return JsonResponse({
        "success": True,
        "principal": vinculo.principal,
        "message": (
            f"Local '{vinculo.local_prestacao.nome_local}' "
            f"{'marcado como' if vinculo.principal else 'desmarcado de'} principal."
        ),
    })


# =============================================================================
# == AJAX - INFO CARGO/FUNCAO
# =============================================================================

@funcionario_required
def ajax_cargo_info(request):
    """Retorna nome e CBO de um Cargo."""
    cargo_id = request.GET.get("cargo_id")
    if not cargo_id:
        return JsonResponse({"error": "cargo_id obrigatorio"}, status=400)
    try:
        cargo = Cargo.objects.get(pk=cargo_id, ativo=True)
        return JsonResponse({
            "nome": cargo.nome,
            "cbo": cargo.cbo or "",
            "descricao": cargo.descricao or "",
        })
    except Cargo.DoesNotExist:
        return JsonResponse({"error": "Cargo nao encontrado"}, status=404)


@funcionario_required
def ajax_funcao_st_info(request):
    """Retorna nome e descricao de uma Funcao (Seguranca do Trabalho)."""
    funcao_id = request.GET.get("funcao_id")
    if not funcao_id:
        return JsonResponse({"error": "funcao_id obrigatorio"}, status=400)
    try:
        funcao = Funcao.objects.get(pk=funcao_id, ativo=True)
        return JsonResponse({
            "nome": funcao.nome,
            "registro": funcao.registro or "",
            "descricao": funcao.descricao or "",
        })
    except Funcao.DoesNotExist:
        return JsonResponse({"error": "Funcao nao encontrada"}, status=404)


# =============================================================================
# == AJAX - RESPONSAVEIS DO DOCUMENTO LTCAT
# =============================================================================

@funcionario_required
@require_POST
def ajax_vincular_responsavel(request, ltcat_pk):
    """
    Vincula um funcionario como responsavel ao documento LTCAT.
    Cria ProfissionalResponsavelLTCAT automaticamente se nao existir.
    """
    ltcat_doc = get_object_or_404(LTCATDocumento, pk=ltcat_pk)
    filial_id = request.session.get("active_filial_id")

    if not _user_pode_acessar_ltcat(request.user, ltcat_doc, filial_id):
        return JsonResponse({"error": "Sem permissao."}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON invalido."}, status=400)

    funcionario_id = data.get("funcionario_id")
    tipo = data.get("tipo_responsabilidade", "elaborador")
    funcao_prof = data.get("funcao_profissional", "").strip()
    registro = data.get("registro_classe", "").strip()
    orgao = data.get("orgao_classe", "").strip()

    if not funcionario_id:
        return JsonResponse({"error": "Funcionario nao informado."}, status=400)
    if not funcao_prof:
        return JsonResponse({"error": "Funcao profissional eh obrigatoria."}, status=400)
    if not registro:
        return JsonResponse({"error": "Registro de classe eh obrigatorio."}, status=400)

    funcionario = get_object_or_404(Funcionario, pk=funcionario_id)

    profissional = ProfissionalResponsavelLTCAT.objects.filter(
        funcionario=funcionario, filial=ltcat_doc.filial,
    ).first()

    if not profissional:
        profissional = ProfissionalResponsavelLTCAT.objects.create(
            funcionario=funcionario,
            filial=ltcat_doc.filial,
            nome_completo=funcionario.nome_completo,
            funcao=funcao_prof,
            registro_classe=registro,
            orgao_classe=orgao or None,
            email=getattr(funcionario, "email_pessoal", None) or None,
            telefone=getattr(funcionario, "telefone", None) or None,
        )
    else:
        atualizar = False
        if funcao_prof and profissional.funcao != funcao_prof:
            profissional.funcao = funcao_prof
            atualizar = True
        if registro and profissional.registro_classe != registro:
            profissional.registro_classe = registro
            atualizar = True
        if orgao and profissional.orgao_classe != orgao:
            profissional.orgao_classe = orgao
            atualizar = True
        if atualizar:
            profissional.save()

    vinculo, created = LTCATDocumentoResponsavel.objects.get_or_create(
        ltcat_documento=ltcat_doc,
        profissional=profissional,
        defaults={"tipo_responsabilidade": tipo},
    )

    if not created:
        return JsonResponse({
            "error": f"{profissional.nome_completo} ja esta vinculado a este documento."
        }, status=400)

    return JsonResponse({
        "success": True,
        "vinculo_id": vinculo.pk,
        "profissional_id": profissional.pk,
        "nome": profissional.nome_completo,
        "funcao": profissional.funcao,
        "registro": profissional.registro_classe,
        "tipo": vinculo.get_tipo_responsabilidade_display(),
        "message": f"{profissional.nome_completo} vinculado com sucesso.",
    })


@funcionario_required
@require_POST
def ajax_desvincular_responsavel(request, ltcat_pk, pk):
    """Desvincula um profissional do documento LTCAT."""
    ltcat_doc = get_object_or_404(LTCATDocumento, pk=ltcat_pk)
    filial_id = request.session.get("active_filial_id")

    if not _user_pode_acessar_ltcat(request.user, ltcat_doc, filial_id):
        return JsonResponse({"error": "Sem permissao."}, status=403)

    vinculo = get_object_or_404(
        LTCATDocumentoResponsavel, pk=pk, ltcat_documento=ltcat_doc
    )
    nome = vinculo.profissional.nome_completo
    vinculo.delete()

    return JsonResponse({
        "success": True,
        "message": f"{nome} desvinculado com sucesso.",
    })


@funcionario_required
@require_POST
def ajax_salvar_assinatura(request, pk):
    """Salva a assinatura digital de um profissional (base64 -> ImageField)."""
    profissional = get_object_or_404(ProfissionalResponsavelLTCAT, pk=pk)
    filial_id = request.session.get("active_filial_id")

    user = request.user
    if not (user.is_superuser or user.is_staff):
        if not filial_id or profissional.filial_id != int(filial_id):
            return JsonResponse({"error": "Sem permissao."}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON invalido."}, status=400)

    assinatura_data = data.get("assinatura", "")
    if not assinatura_data or "base64," not in assinatura_data:
        return JsonResponse({"error": "Dados de assinatura invalidos."}, status=400)

    try:
        fmt, imgstr = assinatura_data.split(";base64,")
        ext = fmt.split("/")[-1]
        if ext not in ("png", "jpeg", "jpg", "webp"):
            ext = "png"

        image_data = base64.b64decode(imgstr)
        nome_limpo = profissional.nome_completo[:20].replace(" ", "_").replace("/", "_")
        filename = f"assinatura_{profissional.pk}_{nome_limpo}.{ext}"

        if profissional.assinatura_imagem:
            try:
                profissional.assinatura_imagem.delete(save=False)
            except Exception:
                pass

        profissional.assinatura_imagem.save(filename, ContentFile(image_data), save=True)
    except Exception as e:
        return JsonResponse({"error": f"Erro ao processar: {str(e)}"}, status=400)

    return JsonResponse({
        "success": True,
        "message": "Assinatura salva com sucesso.",
        "url": profissional.assinatura_imagem.url,
    })


@funcionario_required
@require_POST
def ajax_limpar_assinatura(request, pk):
    """Remove a assinatura digital de um profissional."""
    profissional = get_object_or_404(ProfissionalResponsavelLTCAT, pk=pk)
    filial_id = request.session.get("active_filial_id")

    user = request.user
    if not (user.is_superuser or user.is_staff):
        if not filial_id or profissional.filial_id != int(filial_id):
            return JsonResponse({"error": "Sem permissao."}, status=403)

    if profissional.assinatura_imagem:
        try:
            profissional.assinatura_imagem.delete(save=False)
        except Exception:
            pass
        profissional.assinatura_imagem = None
        profissional.save(update_fields=["assinatura_imagem"])

    return JsonResponse({
        "success": True,
        "message": "Assinatura removida com sucesso.",
    })


@funcionario_required
def ajax_buscar_profissional_por_funcionario(request):
    """
    Retorna dados do ProfissionalResponsavelLTCAT vinculado a um funcionario,
    se existir. Usado para pre-preencher o modal.
    """
    funcionario_id = request.GET.get("funcionario_id")
    if not funcionario_id:
        return JsonResponse({"found": False})

    filial_id = request.session.get("active_filial_id")
    profissional = ProfissionalResponsavelLTCAT.objects.filter(
        funcionario_id=funcionario_id, filial_id=filial_id,
    ).first()

    if profissional:
        return JsonResponse({
            "found": True,
            "funcao_profissional": profissional.funcao,
            "registro_classe": profissional.registro_classe,
            "orgao_classe": profissional.orgao_classe or "",
        })

    return JsonResponse({"found": False})


# =============================================================================
# == GERACAO DE PDF
# =============================================================================

@funcionario_required
def gerar_pdf_ltcat(request, pk):
    """Gera e retorna o PDF completo do LTCAT."""
    from .relatorio_pdf import LTCATRelatorio

    ltcat_doc = get_object_or_404(LTCATDocumento, pk=pk)
    filial_id = request.session.get("active_filial_id")

    if not _user_pode_acessar_ltcat(request.user, ltcat_doc, filial_id):
        raise Http404("LTCAT nao encontrado.")

    relatorio = LTCATRelatorio(ltcat_doc)
    pdf_bytes = relatorio.gerar()

    filename = f"LTCAT_{ltcat_doc.codigo_documento}_{ltcat_doc.versao_atual:02d}.pdf"
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response

