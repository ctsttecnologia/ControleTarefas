
"""
Formulários do módulo pgr_gestao.

Regras:
- Todo form aceita `request=` e restringe os FKs pela filial ativa (falha fechado:
  sem request/usuário autenticado o queryset é vazio).
- Documentos e riscos usam `selectors` (filial + escopo de técnico).
- Campos calculados (severidade, classificação, prioridade) NÃO fazem parte do form.
"""
from dal import autocomplete
from django import forms
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.forms import BaseInlineFormSet

from core.mixins import sanitize_image, sanitize_pdf
from core.utils import get_filial_ativa, queryset_da_filial
from core.validators import SecureFileValidator

from .models import (
    AcompanhamentoPlanoAcao,
    AnexoPGR,
    AnexoPlanoAcao,
    AvaliacaoQuantitativa,
    CronogramaAcaoPGR,
    Empresa,
    GESGrupoExposicao,
    LocalPrestacaoServico,
    PGRDocumento,
    PGRDocumentoResponsavel,
    PGRRevisao,
    PlanoAcaoPGR,
    ProfissionalResponsavel,
    RiscoIdentificado,
)
from .selectors import documentos_visiveis, riscos_visiveis

# Unidades sugeridas por tipo. "outro" libera todas.
UNIDADES_POR_TIPO = {
    'ruido':          ['dB', 'dB(A)', '%', 'outro'],
    'calor':          ['IBUTG', 'ºC', 'UR', 'm/s', 'outro'],
    'iluminacao':     ['lux', 'outro'],
    'agente_quimico': ['ppm', 'mg/m³', 'f/cm³', '%', 'outro'],
    'vibracao':       ['m/s²', 'outro'],
    'radiacao':       ['mW/cm²', 'Bq', 'mSv', 'outro'],
}

# ========================================
# HELPERS
# ========================================

def _autenticado(request):
    user = getattr(request, "user", None)
    return bool(user and user.is_authenticated)


def _scoped(model, request):
    """Queryset do model restrito à filial ativa. Sem request => vazio."""
    if not _autenticado(request):
        return model.objects.none()
    manager = model.objects
    if hasattr(manager, "for_request"):
        return manager.for_request(request)
    # Fallback para models sem FilialManager (exige campo `filial`)
    return queryset_da_filial(manager.all(), request.user, request)


def _docs(request):
    if not _autenticado(request):
        return PGRDocumento.objects.none()
    return documentos_visiveis(request)


def _riscos(request):
    if not _autenticado(request):
        return RiscoIdentificado.objects.none()
    return riscos_visiveis(request)


def _date_widget():
    # format ISO é necessário para o <input type="date"> exibir o valor na edição
    return forms.DateInput(format="%Y-%m-%d", attrs={"class": "form-control", "type": "date"})


class RequestFormMixin:
    """Recebe `request`, descarta `user` legado e oferece helpers de escopo."""

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        kwargs.pop("user", None)  # legado
        super().__init__(*args, **kwargs)

    def scope_field(self, name):
        """Restringe o FK `name` à filial ativa usando o model do próprio campo."""
        field = self.fields.get(name)
        if field is None:
            return None
        qs = _scoped(field.queryset.model, self.request)
        field.queryset = qs
        return qs


# --- Arquivos ---------------------------------------------------------------

_IMAGENS = {"jpg", "jpeg", "png"}
EXT_ANEXO_PGR = ["pdf", "doc", "docx", "xls", "xlsx", "jpg", "jpeg", "png"]
EXT_EVIDENCIA = ["pdf", "jpg", "jpeg", "png"]


def _ext(f):
    return f.name.rsplit(".", 1)[-1].lower() if "." in f.name else ""


def validar_arquivo(f, extensoes, max_mb):
    """Valida extensão e tamanho. Ignora arquivos já salvos / campo limpo."""
    if not isinstance(f, UploadedFile):
        return f
    ext = _ext(f)
    if ext not in extensoes:
        raise ValidationError(
            f'Extensão .{ext} não permitida. Extensões válidas: {", ".join(extensoes)}'
        )
    if f.size > max_mb * 1024 * 1024:
        raise ValidationError(f"Arquivo muito grande. Máximo permitido: {max_mb}MB.")
    return f


def sanitizar_arquivo(f):
    """Sanitiza imagem/PDF recém-enviados (não reprocessa arquivo já salvo)."""
    if not isinstance(f, UploadedFile):
        return f
    ext = _ext(f)
    if ext in _IMAGENS:
        return sanitize_image(f)
    if ext == "pdf":
        return sanitize_pdf(f)
    return f


# ========================================
# EMPRESA
# ========================================

class EmpresaForm(RequestFormMixin, forms.ModelForm):
    class Meta:
        model = Empresa
        fields = [
            'cliente', 'cnpj', 'tipo_empresa', 'cnae_especifico', 'descricao_cnae',
            'atividade_principal', 'grau_risco', 'grau_risco_texto',
            'numero_empregados', 'numero_empregados_texto', 'jornada_trabalho',
            'endereco', 'numero', 'complemento', 'bairro', 'cidade', 'estado',
            'cep', 'telefone', 'ativo',
        ]
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'cnpj': forms.TextInput(attrs={'class': 'form-control', 'data-mask': '00.000.000/0000-00'}),
            'tipo_empresa': forms.Select(attrs={'class': 'form-select'}),
            'cnae_especifico': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao_cnae': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'atividade_principal': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'grau_risco': forms.Select(attrs={'class': 'form-select'}),
            'grau_risco_texto': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_empregados': forms.NumberInput(attrs={'class': 'form-control'}),
            'numero_empregados_texto': forms.TextInput(attrs={'class': 'form-control'}),
            'jornada_trabalho': forms.TextInput(attrs={'class': 'form-control'}),
            'endereco': forms.TextInput(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'complemento': forms.TextInput(attrs={'class': 'form-control'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '2'}),
            'cep': forms.TextInput(attrs={'class': 'form-control', 'data-mask': '00000-000'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'data-mask': '(00) 00000-0000'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scope_field('cliente')


# ========================================
# LOCAL DE PRESTAÇÃO
# ========================================

class LocalPrestacaoServicoForm(RequestFormMixin, forms.ModelForm):
    class Meta:
        model = LocalPrestacaoServico
        fields = [
            'empresa', 'razao_social', 'cnpj', 'descricao',
            'endereco', 'numero', 'complemento', 'bairro', 'cidade', 'estado', 'cep', 'ativo',
        ]
        widgets = {
            'empresa': forms.Select(attrs={'class': 'form-select'}),
            'razao_social': forms.TextInput(attrs={'class': 'form-control'}),
            'cnpj': forms.TextInput(attrs={'class': 'form-control', 'data-mask': '00.000.000/0000-00'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'endereco': forms.TextInput(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'complemento': forms.TextInput(attrs={'class': 'form-control'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '2'}),
            'cep': forms.TextInput(attrs={'class': 'form-control', 'data-mask': '00000-000'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scope_field('empresa')


# ========================================
# PROFISSIONAL RESPONSÁVEL
# ========================================

class ProfissionalResponsavelForm(RequestFormMixin, forms.ModelForm):
    class Meta:
        model = ProfissionalResponsavel
        fields = [
            'nome_completo', 'funcao', 'registro_classe', 'orgao_classe',
            'especialidade', 'telefone', 'email', 'ativo',
        ]
        widgets = {
            'nome_completo': forms.TextInput(attrs={'class': 'form-control'}),
            'funcao': forms.TextInput(attrs={'class': 'form-control'}),
            'registro_classe': forms.TextInput(attrs={'class': 'form-control'}),
            'orgao_classe': forms.TextInput(attrs={'class': 'form-control'}),
            'especialidade': forms.TextInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'data-mask': '(00) 00000-0000'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class BaseResponsavelFormSet(BaseInlineFormSet):
    """Uso: ResponsavelFormSet(request.POST or None, instance=doc, request=request)"""
    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)

    def add_fields(self, form, index):
        super().add_fields(form, index)
        form.fields["profissional"].queryset = _scoped(ProfissionalResponsavel, self.request).filter(ativo=True)
        if "profissional" in form.fields:
            form.fields["profissional"].queryset = _scoped(ProfissionalResponsavel, self.request)


ResponsavelFormSet = forms.inlineformset_factory(
    PGRDocumento,
    PGRDocumentoResponsavel,
    formset=BaseResponsavelFormSet,
    fields=('profissional', 'tipo_responsabilidade'),
    extra=1,
    can_delete=True,
    widgets={
        'profissional': forms.Select(attrs={'class': 'form-control'}),
        'tipo_responsabilidade': forms.Select(attrs={'class': 'form-control'}),
    },
)


# ========================================
# DOCUMENTO PGR
# ========================================

class PGRDocumentoForm(RequestFormMixin, forms.ModelForm):
    class Meta:
        model = PGRDocumento
        fields = [
            'codigo_documento', 'empresa', 'local_prestacao',
            'data_elaboracao', 'data_vencimento', 'data_ultima_revisao',
            'versao_atual', 'status', 'observacoes', 'objetivo', 'escopo',
            'metodologia_avaliacao',
        ]
        widgets = {
            'codigo_documento': forms.TextInput(attrs={'class': 'form-control'}),
            'empresa': autocomplete.ModelSelect2(
                url='pgr_gestao:cliente-autocomplete',
                attrs={
                    'data-placeholder': 'Digite o nome da empresa...',
                    'data-minimum-input-length': 1,
                    'class': 'form-select',
                },
            ),
            'local_prestacao': forms.Select(attrs={'class': 'form-select'}),
            'data_elaboracao': _date_widget(),
            'data_vencimento': _date_widget(),
            'data_ultima_revisao': _date_widget(),
            'versao_atual': forms.NumberInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'objetivo': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'escopo': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'metodologia_avaliacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scope_field('empresa')
        self.scope_field('local_prestacao')

        # Controlados pelo signal de revisão (PGRRevisao)
        for nome in ('versao_atual', 'data_ultima_revisao'):
            self.fields[nome].disabled = True
            self.fields[nome].required = False

        if self.instance and self.instance.pk:
            for nome in ('data_elaboracao', 'data_vencimento'):
                self.fields[nome].disabled = True
                self.fields[nome].required = False

    def clean_codigo_documento(self):
        codigo = (self.cleaned_data.get('codigo_documento') or '').strip()
        if self.instance.pk:
            filial_id = self.instance.filial_id
        else:
            filial = get_filial_ativa(self.request.user, self.request) if self.request else None
            filial_id = filial.pk if filial else None
        if codigo and filial_id:
            qs = PGRDocumento.objects.all_filiais().filter(
                filial_id=filial_id, codigo_documento__iexact=codigo
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('Já existe um documento com este código.')
        return codigo

    def clean(self):
        cleaned = super().clean()
        elaboracao = cleaned.get('data_elaboracao')
        vencimento = cleaned.get('data_vencimento')
        if elaboracao and vencimento and vencimento <= elaboracao:
            raise ValidationError('A data de vencimento deve ser posterior à data de elaboração.')

        empresa, local = cleaned.get('empresa'), cleaned.get('local_prestacao')
        # Assume LocalPrestacaoServico.empresa -> Cliente (confirme no models.py)
        if empresa and local and local.empresa_id != empresa.pk:
            self.add_error('local_prestacao', 'O local não pertence à empresa selecionada.')
        return cleaned


# ========================================
# GES
# ========================================

class GESGrupoExposicaoForm(RequestFormMixin, forms.ModelForm):
    """Cria/edita Grupos de Exposição Similar."""

    class Meta:
        model = GESGrupoExposicao
        fields = [
            'pgr_documento', 'codigo', 'nome', 'ambiente_trabalho', 'cargo', 'funcao',
            'numero_trabalhadores', 'jornada_trabalho', 'horario_trabalho',
            'descricao_atividades', 'equipamentos_utilizados', 'produtos_manipulados',
            'ativo',
        ]
        widgets = {
            'pgr_documento': forms.Select(attrs={'class': 'form-select'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: GES-001'}),
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Administração, Produção Linha A'}),
            'ambiente_trabalho': forms.Select(attrs={'class': 'form-select'}),
            'cargo': forms.Select(attrs={'class': 'form-select'}),
            'funcao': forms.Select(attrs={'class': 'form-select'}),
            'numero_trabalhadores': forms.NumberInput(attrs={'class': 'form-control'}),
            'jornada_trabalho': forms.TextInput(attrs={'class': 'form-control'}),
            'horario_trabalho': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 08:00 às 17:00'}),
            'descricao_atividades': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'equipamentos_utilizados': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'produtos_manipulados': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'codigo': 'Código único dentro do PGR. Deixe em branco para gerar automaticamente.',
            'nome': 'Um nome descritivo para o grupo, como o setor ou a equipe.',
            'ambiente_trabalho': 'Selecione o ambiente onde este grupo trabalha.',
            'cargo': 'Selecione o cargo principal dos trabalhadores neste grupo.',
            'ativo': 'Desmarque para inativar este GES (não será incluído no PDF).',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pgr_documento'].queryset = _docs(self.request)
        for nome in ('ambiente_trabalho', 'cargo', 'funcao'):
            self.scope_field(nome)

        self.fields['codigo'].required = False  # gerado automaticamente

        if self.instance and self.instance.pk:
            self.fields['pgr_documento'].disabled = True

    def clean_codigo(self):
        codigo = (self.cleaned_data.get('codigo') or '').strip()
        pgr_documento = self.cleaned_data.get('pgr_documento')
        if codigo and pgr_documento:
            qs = GESGrupoExposicao.objects.filter(
                pgr_documento=pgr_documento, codigo__iexact=codigo
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('Já existe um GES com este código neste Documento PGR.')
        return codigo


# Alias de compatibilidade: o antigo GESForm era redundante e sem filtro de filial.
GESForm = GESGrupoExposicaoForm


# ========================================
# RISCO IDENTIFICADO
# ========================================

class RiscoIdentificadoForm(RequestFormMixin, forms.ModelForm):
    """
    Campos calculados (severidade_s, classificacao_risco, prioridade_acao) saem do
    form: são definidos por services/risco.py no pre_save. Exiba-os no template
    a partir de `object` (somente leitura).
    """

    class Meta:
        model = RiscoIdentificado
        fields = [
            'pgr_documento', 'ges', 'codigo_risco', 'tipo_risco', 'agente',
            'fonte_geradora', 'meio_propagacao', 'perfil_exposicao',
            'possiveis_efeitos_saude', 'ambiente_trabalho', 'cargo',
            'gravidade_g', 'exposicao_e', 'probabilidade_p',
            'metodo_avaliacao', 'status_controle', 'observacoes',
            'data_identificacao',
        ]
        widgets = {
            'pgr_documento': forms.Select(attrs={'class': 'form-select'}),
            'ges': forms.Select(attrs={'class': 'form-select'}),
            'codigo_risco': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_risco': forms.Select(attrs={'class': 'form-select'}),
            'agente': forms.TextInput(attrs={'class': 'form-control'}),
            'fonte_geradora': forms.TextInput(attrs={'class': 'form-control'}),
            'meio_propagacao': forms.TextInput(attrs={'class': 'form-control'}),
            'perfil_exposicao': forms.Select(attrs={'class': 'form-select'}),
            'possiveis_efeitos_saude': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'ambiente_trabalho': forms.Select(attrs={'class': 'form-select'}),
            'cargo': forms.Select(attrs={'class': 'form-select'}),
            'gravidade_g': forms.Select(attrs={'class': 'form-select'}),
            'exposicao_e': forms.Select(attrs={'class': 'form-select'}),
            'probabilidade_p': forms.Select(attrs={'class': 'form-select'}),
            'metodo_avaliacao': forms.Select(attrs={'class': 'form-select'}),
            'status_controle': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'data_identificacao': _date_widget(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        docs = _docs(self.request)
        self.fields['pgr_documento'].queryset = docs

        for nome in ('ambiente_trabalho', 'cargo'):
            self.scope_field(nome)

        # TipoRisco (app gestao_riscos): só ativos, da filial
        tipo_qs = self.scope_field('tipo_risco')
        if tipo_qs is not None:
            self.fields['tipo_risco'].queryset = (
                tipo_qs.filter(ativo=True).order_by('categoria', 'nome')
            )

        # GES: sempre dentro dos documentos visíveis; filtra pelo documento escolhido
        ges_qs = GESGrupoExposicao.objects.filter(pgr_documento__in=docs)
        doc_id = self._documento_id()
        if doc_id:
            ges_qs = ges_qs.filter(pgr_documento_id=doc_id)
        self.fields['ges'].queryset = ges_qs.order_by('nome')

    def _documento_id(self):
        if self.is_bound:
            raw = self.data.get(self.add_prefix('pgr_documento'))
        elif self.instance.pk:
            raw = self.instance.pgr_documento_id
        else:
            raw = self.initial.get('pgr_documento')
        raw = getattr(raw, 'pk', raw)
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    def clean(self):
        cleaned = super().clean()
        doc, ges = cleaned.get('pgr_documento'), cleaned.get('ges')
        if doc and ges and ges.pgr_documento_id != doc.pk:
            self.add_error('ges', 'O GES selecionado pertence a outro documento.')
        return cleaned


# ========================================
# PLANO DE AÇÃO
# ========================================

class PlanoAcaoPGRForm(RequestFormMixin, forms.ModelForm):
    """Formulário único (as duas definições antigas foram consolidadas)."""

    class Meta:
        model = PlanoAcaoPGR
        fields = [
            'risco_identificado', 'tipo_acao', 'descricao_acao', 'justificativa',
            'prioridade', 'responsavel', 'recursos_necessarios', 'custo_estimado',
            'data_prevista', 'data_conclusao', 'status', 'resultado_obtido',
            'eficacia_acao', 'observacoes',
        ]
        widgets = {
            'risco_identificado': forms.Select(attrs={'class': 'form-select'}),
            'tipo_acao': forms.Select(attrs={'class': 'form-select'}),
            'descricao_acao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'justificativa': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'prioridade': forms.Select(attrs={'class': 'form-select'}),
            'responsavel': forms.TextInput(attrs={'class': 'form-control'}),
            'recursos_necessarios': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'custo_estimado': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'data_prevista': _date_widget(),
            'data_conclusao': _date_widget(),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'resultado_obtido': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'eficacia_acao': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        risco_inicial = kwargs.pop('risco_inicial', None)
        super().__init__(*args, **kwargs)

        # Na criação, estes campos não são renderizados
        if not self.instance.pk:
            for nome in ('resultado_obtido', 'eficacia_acao'):
                self.fields.pop(nome, None)

        for nome in ('justificativa', 'recursos_necessarios',
                     'resultado_obtido', 'eficacia_acao'):
            if nome in self.fields:
                self.fields[nome].required = False

        riscos = _riscos(self.request)          # <- chama a função (queryset)
        if risco_inicial:
            riscos = riscos.filter(pk=getattr(risco_inicial, 'pk', risco_inicial))

        campo = self.fields['risco_identificado']
        campo.queryset = riscos.select_related('tipo_risco', 'pgr_documento').order_by(
            'pgr_documento__codigo_documento', 'codigo_risco'
        )
        
        campo.empty_label = 'Selecione um risco...'
        campo.label_from_instance = lambda r: (
            f"{r.pgr_documento.codigo_documento} · {r.codigo_risco or r.pk} — "
            f"{r.agente} ({r.get_classificacao_risco_display()})"
        )
        if self.instance.pk:
            campo.disabled = True

    def clean(self):
        cleaned = super().clean()
        prevista, conclusao = cleaned.get('data_prevista'), cleaned.get('data_conclusao')
        if prevista and conclusao and conclusao < prevista:
            self.add_error('data_conclusao', 'A data de conclusão não pode ser anterior à data prevista.')
        return cleaned


# ========================================
# CRONOGRAMA
# ========================================

class CronogramaAcaoPGRForm(RequestFormMixin, forms.ModelForm):
    class Meta:
        model = CronogramaAcaoPGR
        fields = [
            'pgr_documento', 'numero_item', 'acao_necessaria', 'publico_alvo',
            'periodicidade', 'responsavel', 'data_proxima_avaliacao', 'status',
            'data_realizacao', 'observacoes',
        ]
        widgets = {
            'pgr_documento': forms.Select(attrs={'class': 'form-select'}),
            'numero_item': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'acao_necessaria': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'publico_alvo': forms.TextInput(attrs={'class': 'form-control'}),
            'periodicidade': forms.Select(attrs={'class': 'form-select'}),
            'responsavel': forms.TextInput(attrs={'class': 'form-control'}),
            'data_proxima_avaliacao': _date_widget(),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'data_realizacao': _date_widget(),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        docs = _docs(self.request)
        self.fields['pgr_documento'].queryset = docs

        # Se o usuário só enxerga UM documento, pré-seleciona (somente na criação)
        if not self.instance.pk and not self.is_bound:
            unicos = list(docs[:2])
            if len(unicos) == 1:
                self.fields['pgr_documento'].initial = unicos[0]

    def clean(self):
        cleaned = super().clean()
        pgr, item = cleaned.get('pgr_documento'), cleaned.get('numero_item')
        
        if pgr and item:
            qs = CronogramaAcaoPGR.objects.filter(pgr_documento=pgr, numero_item=item)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(f'Já existe uma ação com o item nº {item} neste documento PGR.')

        if cleaned.get('status') == 'concluido' and not cleaned.get('data_realizacao'):
            self.add_error('numero_item', f'Já existe uma ação com o item nº {item} neste documento PGR.')
        return cleaned


# ========================================
# REVISÃO
# ========================================

class PGRRevisaoForm(RequestFormMixin, forms.ModelForm):
    class Meta:
        model = PGRRevisao
        fields = [
            'pgr_documento', 'numero_revisao', 'descricao_revisao',
            'motivo', 'data_realizacao', 'realizada_por', 'observacoes',
        ]
        widgets = {
            'pgr_documento': forms.Select(attrs={'class': 'form-select'}),
            'numero_revisao': forms.NumberInput(attrs={'class': 'form-control'}),
            'descricao_revisao': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'motivo': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'data_realizacao': _date_widget(),
            'realizada_por': forms.TextInput(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pgr_documento'].queryset = _docs(self.request)

    def clean(self):
        cleaned = super().clean()
        doc, n = cleaned.get('pgr_documento'), cleaned.get('numero_revisao')
        if doc and n is not None:
            qs = PGRRevisao.objects.filter(pgr_documento=doc, numero_revisao=n)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error('numero_revisao', 'Já existe uma revisão com este número neste PGR.')
        return cleaned


# ========================================
# AVALIAÇÃO QUANTITATIVA
# ========================================

class AvaliacaoQuantitativaForm(RequestFormMixin, forms.ModelForm):
    class Meta:
        model = AvaliacaoQuantitativa
        fields = [
            'risco_identificado', 'tipo_avaliacao', 'data_avaliacao',
            'resultado_medido', 'unidade_medida', 'limite_tolerancia_nr',
            'conforme', 'metodologia_utilizada', 'equipamento_utilizado',
            'responsavel_avaliacao', 'laudo_tecnico', 'observacoes',
        ]
        widgets = {
            'risco_identificado': forms.Select(attrs={'class': 'form-select'}),
            'tipo_avaliacao': forms.Select(attrs={'class': 'form-select'}),
            'data_avaliacao': _date_widget(),
            'resultado_medido': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any', 'placeholder': '0.00'}),
            'unidade_medida': forms.Select(attrs={'class': 'form-select'}),
            'limite_tolerancia_nr': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 85 dB(A) - NR-15'}),
            'conforme': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'metodologia_utilizada': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: NHO-01 / NHO-06 / NR-15 Anexo X'}),
            'equipamento_utilizado': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Marca / modelo / nº série'}),
            'responsavel_avaliacao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do responsável técnico'}),
            'laudo_tecnico': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Notas adicionais, condições da medição, etc.'}),
        }
        labels = {
            'risco_identificado': 'Risco Identificado',
            'tipo_avaliacao': 'Tipo de Avaliação',
            'data_avaliacao': 'Data da Avaliação',
            'resultado_medido': 'Resultado Medido',
            'unidade_medida': 'Unidade de Medida',
            'limite_tolerancia_nr': 'Limite de Tolerância (NR)',
            'conforme': 'Está conforme?',
            'metodologia_utilizada': 'Metodologia Utilizada',
            'equipamento_utilizado': 'Equipamento Utilizado',
            'responsavel_avaliacao': 'Responsável pela Avaliação',
            'laudo_tecnico': 'Laudo Técnico (PDF)',
            'observacoes': 'Observações',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['risco_identificado'].queryset = (
            _riscos(self.request)
            .select_related('tipo_risco', 'ges', 'pgr_documento')
            .order_by('pgr_documento__codigo_documento', 'codigo_risco')
        )
        # Risco não pode ser trocado depois de salvo
        if self.instance.pk:
            self.fields['risco_identificado'].disabled = True

        # Rótulo do placeholder do select
        choices = list(self.fields['unidade_medida'].choices)
        if choices and choices[0][0] == '':
            choices[0] = ('', 'Unidade...')
            self.fields['unidade_medida'].choices = choices

    @property
    def mapa_unidades(self):
        """Use no template: {{ form.mapa_unidades|json_script:"mapa-unidades" }}"""
        return UNIDADES_POR_TIPO

    def clean(self):
        cleaned = super().clean()
        tipo, unid = cleaned.get('tipo_avaliacao'), cleaned.get('unidade_medida')
        permitidas = UNIDADES_POR_TIPO.get(tipo)

        if permitidas and unid and unid not in permitidas:
            # Registro legado: só bloqueia se tipo/unidade foram alterados
            mudou = (not self.instance.pk
                     or tipo != self.instance.tipo_avaliacao
                     or unid != self.instance.unidade_medida)
            if mudou:
                self.add_error(
                    'unidade_medida',
                    f'A unidade "{unid}" não é compatível com este tipo de avaliação.'
                )
        return cleaned

    def clean_laudo_tecnico(self):
        f = validar_arquivo(self.cleaned_data.get('laudo_tecnico'), EXT_EVIDENCIA, 20)
        return sanitizar_arquivo(f)


# ========================================
# ACOMPANHAMENTO DO PLANO
# ========================================

class AcompanhamentoPlanoAcaoForm(RequestFormMixin, forms.ModelForm):
    """Uma única entrada de acompanhamento (o plano é definido na view)."""

    class Meta:
        model = AcompanhamentoPlanoAcao
        fields = [
            'data_acompanhamento', 'status_atual', 'descricao',
            'percentual_conclusao', 'responsavel_acompanhamento',
            'dificuldades', 'proximos_passos', 'arquivo_evidencia',
        ]
        widgets = {
            'data_acompanhamento': _date_widget(),
            'status_atual': forms.Select(attrs={'class': 'form-select'}),
            'descricao': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Descreva o progresso...', 'class': 'form-control'}),
            'percentual_conclusao': forms.NumberInput(attrs={'min': 0, 'max': 100, 'class': 'form-control'}),
            'responsavel_acompanhamento': forms.TextInput(attrs={'placeholder': 'Nome do responsável...', 'class': 'form-control'}),
            'dificuldades': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'proximos_passos': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'arquivo_evidencia': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # A view preenche com o status atual do plano quando vier vazio
        self.fields['status_atual'].required = False

    def clean_percentual_conclusao(self):
        v = self.cleaned_data.get('percentual_conclusao')
        if v is not None and not 0 <= v <= 100:
            raise ValidationError('Informe um valor entre 0 e 100.')
        return v    

    def clean_arquivo_evidencia(self):
        f = validar_arquivo(self.cleaned_data.get('arquivo_evidencia'), EXT_EVIDENCIA, 20)
        return sanitizar_arquivo(f)


# ========================================
# ANEXOS
# ========================================

class AnexoPGRForm(RequestFormMixin, forms.ModelForm):

    arquivo = forms.FileField(
        validators=[SecureFileValidator("pgr_anexos")],   # confirme a chave em core.validators
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png',
        }),
    )
    class Meta:
        model = AnexoPGR
        fields = [
            'tipo_anexo', 'numero_romano', 'titulo',
            'descricao', 'arquivo', 'incluir_no_pdf', 'ordem',
        ]
        widgets = {
            'tipo_anexo': forms.Select(attrs={'class': 'form-select', 'id': 'id_tipo_anexo'}),
            'numero_romano': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Auto (I, II, III...)'}),
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: ANÁLISE QUANTITATIVA DE RUÍDO', 'id': 'id_titulo_anexo'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Observações sobre este anexo (opcional)'}),
            'arquivo': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png'}),
            'incluir_no_pdf': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ordem': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'placeholder': 'Auto'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nome in ('numero_romano', 'titulo', 'descricao', 'ordem'):
            self.fields[nome].required = False

    def clean_arquivo(self):
        # Sanitização fica em AnexoPGR.save (evita processar duas vezes)
        return validar_arquivo(self.cleaned_data.get('arquivo'), EXT_ANEXO_PGR, 50)


class AnexoPGRMultipleForm(RequestFormMixin, forms.Form):
    """Upload múltiplo: na view, valide cada arquivo com
    `validar_arquivo(f, EXT_ANEXO_PGR, 50)` antes de salvar."""

    tipo_anexo = forms.ChoiceField(
        choices=AnexoPGR.TIPO_ANEXO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Tipo de Anexo',
    )
    titulo = forms.CharField(
        max_length=300,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Preenchido automaticamente pelo tipo'}),
        label='Título',
    )
    incluir_no_pdf = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Incluir como Anexo no PDF',
    )


class AnexoPlanoAcaoForm(RequestFormMixin, forms.ModelForm):
    arquivo = forms.FileField(
        validators=[SecureFileValidator("pgr_planos")],
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = AnexoPlanoAcao
        fields = ["nome_arquivo", "arquivo"]

    def clean_arquivo(self):
        return sanitizar_arquivo(self.cleaned_data["arquivo"])

