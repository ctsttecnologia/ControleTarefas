
# ltcat/forms.py

from django import forms

from cliente.models import Cliente
from .models import (
    LTCATDocumento, RevisaoLTCAT, FuncaoAnalisada, ReconhecimentoRisco,
    AvaliacaoPericulosidade, ConclusaoFuncao, RecomendacaoTecnica,
    AnexoLTCAT, EmpresaLTCAT, LocalPrestacaoServicoLTCAT,
    ProfissionalResponsavelLTCAT, DocumentoLocalPrestacao,
)


class BaseFormMixin:
    """Aplica classes Bootstrap 5 em todos os campos do form."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            css_class = "form-control"
            if isinstance(field.widget, forms.CheckboxInput):
                css_class = "form-check-input"
            elif isinstance(field.widget, forms.Select):
                css_class = "form-select"
            elif isinstance(field.widget, forms.FileInput):
                css_class = "form-control"
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.setdefault("rows", 4)

            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} {css_class}".strip()

       
# =============================================================================
# FORM — Cadastro/Edição de Empresa LTCAT (Contratada)
# =============================================================================

class EmpresaLTCATForm(BaseFormMixin, forms.ModelForm):
    """
    Form para cadastrar EmpresaLTCAT a partir de um Cliente existente.
    Puxa razão social e endereço do Cliente, permite complementar campos extras.
    """

    class Meta:
        model = EmpresaLTCAT
        fields = [
            'cliente', 'cnpj', 'cnae', 'descricao_cnae',
            'grau_risco', 'grau_risco_texto',
            'atividade_principal',
            'numero_empregados', 'numero_empregados_texto',
            'jornada_trabalho',
            'endereco', 'numero', 'complemento',
            'bairro', 'cidade', 'estado', 'cep',
            'telefone', 'email',
        ]
        widgets = {
            'descricao_cnae': forms.Textarea(attrs={'rows': 2}),
            'atividade_principal': forms.Textarea(attrs={'rows': 2}),
        }
        exclude = ["filial"]

    def __init__(self, *args, filial=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._filial = filial

        if filial:
            self.fields['cliente'].queryset = Cliente.objects.filter(
                filial=filial, estatus=True
            )
        else:
            self.fields['cliente'].queryset = Cliente.objects.none()

        # Labels mais amigáveis
        self.fields['cliente'].label = 'Empresa (Cliente cadastrado)'
        self.fields['cliente'].help_text = 'Selecione a empresa que elabora o LTCAT (ex: CETEST)'
        self.fields['cnpj'].help_text = 'Será preenchido automaticamente ao selecionar o cliente'
        self.fields['grau_risco'].help_text = 'Ex: 3'
        self.fields['grau_risco_texto'].help_text = 'Ex: 03 (três) estando trabalhando nas instalações do contratante'
        self.fields['numero_empregados_texto'].help_text = 'Ex: 9 (Nove), sendo 8 fixos e 1 coordenador'

    def clean(self):
        cleaned = super().clean()
        cliente = cleaned.get('cliente')

        # Verifica unicidade cliente + filial
        if cliente and self._filial:
            qs = EmpresaLTCAT.objects.filter(
                cliente=cliente, filial=self._filial
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error(
                    'cliente',
                    'Já existe uma Empresa LTCAT cadastrada para este cliente nesta filial.'
                )

        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Preenche filial automaticamente
        if self._filial:
            instance.filial = self._filial

        # Se CNPJ não foi informado, puxa do Cliente
        if not instance.cnpj and instance.cliente:
            instance.cnpj = getattr(instance.cliente, 'cnpj', '') or ''

        if commit:
            instance.save()
            self.save_m2m()

        return instance
        

# No forms.py, DEPOIS de ProfissionalResponsavelForm, ADICIONE:

class LocalPrestacaoServicoForm(BaseFormMixin, forms.ModelForm):
    """Form para cadastro de Local de Prestação de Serviço LTCAT."""

    class Meta:
        model = LocalPrestacaoServicoLTCAT
        fields = [
            "empresa", "nome_local", "razao_social", "cnpj",
            "logradouro", "descricao",
            "endereco", "numero", "complemento",
            "bairro", "cidade", "estado", "cep",
        ]

    def __init__(self, *args, filial=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._filial = filial

        if filial:
            from cliente.models import Cliente
            self.fields["empresa"].queryset = Cliente.objects.filter(
                filial=filial, estatus=True
            )
        else:
            from cliente.models import Cliente
            self.fields["empresa"].queryset = Cliente.objects.none()

        # ═══════════════════════════════════════════════════════
        # LOGRADOURO: NÃO carrega todos — será preenchido via AJAX
        # ═══════════════════════════════════════════════════════
        from logradouro.models import Logradouro

        # Se editando e já tem logradouro vinculado, carrega SÓ ele
        if self.instance and self.instance.pk and self.instance.logradouro_id:
            self.fields["logradouro"].queryset = Logradouro.objects.filter(
                pk=self.instance.logradouro_id
            )
        else:
            self.fields["logradouro"].queryset = Logradouro.objects.none()

        self.fields["logradouro"].required = False
        self.fields["logradouro"].widget.attrs.update({
            "id": "id_logradouro",
            "data-autocomplete-url": "",  # será definido no template via JS
        })

        # Campos opcionais
        for campo in ["endereco", "numero", "complemento", "bairro",
                       "cidade", "estado", "cep",
                       "razao_social", "cnpj", "descricao"]:
            self.fields[campo].required = False


class ProfissionalResponsavelForm(BaseFormMixin, forms.ModelForm):
    class Meta:
        model = ProfissionalResponsavelLTCAT
        exclude = ["filial"]


class LTCATForm(BaseFormMixin, forms.ModelForm):
    """
    Formulário do LTCATDocumento.
    `local_prestacao` é campo extra (não-model) para selecionar o local principal.
    `empresa_contratada` agora aparece no form.
    """

    local_prestacao = forms.ModelChoiceField(
        queryset=LocalPrestacaoServicoLTCAT.objects.none(),
        required=False,
        label="Local de Prestação de Serviço (Principal)",
        help_text="Selecione o local principal. Locais adicionais podem ser gerenciados na tela de detalhe.",
    )

    class Meta:
        model = LTCATDocumento
        fields = [
            "empresa", "empresa_contratada", "titulo",
            "data_elaboracao", "data_ultima_revisao", "data_vencimento",
            "status", "objetivo", "condicoes_preliminares",
            "avaliacao_periculosidade_texto", "referencias_bibliograficas",
        ]
        widgets = {
            "data_elaboracao": forms.DateInput(
                attrs={"type": "date"}, format="%Y-%m-%d"
            ),
            "data_ultima_revisao": forms.DateInput(
                attrs={"type": "date"}, format="%Y-%m-%d"
            ),
            "data_vencimento": forms.DateInput(
                attrs={"type": "date"}, format="%Y-%m-%d"
            ),
        }

    def __init__(self, *args, filial=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._filial = filial

        if filial:
            from cliente.models import Cliente
            self.fields["empresa"].queryset = Cliente.objects.filter(
                filial=filial, estatus=True
            )

            # ══════════════════════════════════════════════
            # EMPRESA CONTRATADA — filtra por filial
            # ══════════════════════════════════════════════
            self.fields["empresa_contratada"].queryset = EmpresaLTCAT.objects.filter(
                filial=filial
            )
            self.fields["empresa_contratada"].required = False
            self.fields["empresa_contratada"].label = "Empresa Contratada (Elaboradora)"
            self.fields["empresa_contratada"].help_text = "Ex: CETEST — empresa que elabora o LTCAT"

            # ══════════════════════════════════════════════
            # LOCAL DE PRESTAÇÃO — FIX: sempre aceitar
            # locais da filial; se tem empresa, filtra por ela
            # ══════════════════════════════════════════════
            if self.instance and self.instance.pk and self.instance.empresa_id:
                # Editando — filtra locais pela empresa do documento
                self.fields["local_prestacao"].queryset = (
                    LocalPrestacaoServicoLTCAT.objects.filter(
                        empresa=self.instance.empresa,
                        filial=filial,
                    )
                )
                # Pré-seleciona o local principal atual
                local_principal = self.instance.local_prestacao_principal
                if local_principal:
                    self.initial["local_prestacao"] = local_principal.pk
            else:
                # Criando — inicia com TODOS os locais da filial
                # (será filtrado via AJAX no frontend, mas o backend
                #  precisa aceitar qualquer local válido da filial)
                self.fields["local_prestacao"].queryset = (
                    LocalPrestacaoServicoLTCAT.objects.filter(filial=filial)
                )
        else:
            from cliente.models import Cliente
            self.fields["empresa"].queryset = Cliente.objects.none()
            self.fields["empresa_contratada"].queryset = EmpresaLTCAT.objects.none()
            self.fields["local_prestacao"].queryset = (
                LocalPrestacaoServicoLTCAT.objects.none()
            )

    def clean(self):
        """Valida que o local pertence à empresa selecionada."""
        cleaned = super().clean()
        empresa = cleaned.get("empresa")
        local = cleaned.get("local_prestacao")

        if local and empresa and local.empresa_id != empresa.pk:
            self.add_error(
                "local_prestacao",
                "Este local não pertence à empresa selecionada."
            )

        return cleaned

    def save(self, commit=True):
        """Salva o documento e cria/atualiza o vínculo M2M do local principal."""
        instance = super().save(commit=commit)
        local = self.cleaned_data.get("local_prestacao")

        if commit:
            self._salvar_local_principal(instance, local)
        else:
            old_save_m2m = self.save_m2m

            def new_save_m2m():
                old_save_m2m()
                self._salvar_local_principal(instance, local)

            self.save_m2m = new_save_m2m

        return instance

    def _salvar_local_principal(self, instance, local):
        """Cria ou atualiza o vínculo DocumentoLocalPrestacao como principal."""
        if local:
            DocumentoLocalPrestacao.objects.filter(
                ltcat_documento=instance, principal=True
            ).update(principal=False)

            vinculo, created = DocumentoLocalPrestacao.objects.get_or_create(
                ltcat_documento=instance,
                local_prestacao=local,
                defaults={"principal": True, "ordem": 0},
            )
            if not created:
                vinculo.principal = True
                vinculo.save(update_fields=["principal"])
        else:
            DocumentoLocalPrestacao.objects.filter(
                ltcat_documento=instance, principal=True
            ).update(principal=False)


# ═══════════════════════════════════════════════════════
# REVISÃO (Seção 1)
# ═══════════════════════════════════════════════════════
class RevisaoLTCATForm(BaseFormMixin, forms.ModelForm):
    class Meta:
        model = RevisaoLTCAT
        fields = [
            'numero_revisao', 'data_realizada', 'realizada_por',
            'descricao', 'observacoes',
        ]
        widgets = {
            'data_realizada': forms.DateInput(
                attrs={'type': 'date'}, format='%Y-%m-%d'
            ),
            'descricao': forms.Textarea(attrs={'rows': 4}),
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'numero_revisao': 'Nº da Revisão',
            'data_realizada': 'Data da Revisão',
            'realizada_por': 'Responsável',
            'descricao': 'Descrição da Revisão',
            'observacoes': 'Observações',
        }


# ═══════════════════════════════════════════════════════
# FUNÇÃO ANALISADA (Seção 6)
# ═══════════════════════════════════════════════════════
class FuncaoAnalisadaForm(BaseFormMixin, forms.ModelForm):
    class Meta:
        model = FuncaoAnalisada
        fields = [
            'cargo', 'funcao_st',
            'nome_funcao', 'cbo', 'ghe', 'departamento',
            'local_prestacao', 'descricao_atividades',
        ]
        widgets = {
            'descricao_atividades': forms.Textarea(attrs={'rows': 5}),
            'nome_funcao': forms.TextInput(attrs={
                'placeholder': 'Preenchido automaticamente ou digite manualmente',
            }),
            'cbo': forms.TextInput(attrs={
                'placeholder': 'Preenchido automaticamente ou digite manualmente',
            }),
        }
        labels = {
            'cargo': 'Cargo (Depto. Pessoal)',
            'funcao_st': 'Função (Seg. Trabalho)',
            'nome_funcao': 'Nome da Função',
            'cbo': 'Código CBO',
            'ghe': 'GHE (Grupo Homogêneo de Exposição)',
            'departamento': 'Departamento / Setor',
            'local_prestacao': 'Local de Prestação',
            'descricao_atividades': 'Descrição das Atividades',
        }

    def __init__(self, *args, ltcat=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ltcat = ltcat

        # ── Cargo: filtra ativos, ordena por nome ──
        if 'cargo' in self.fields:
            self.fields['cargo'].required = False
            self.fields['cargo'].queryset = (
                self.fields['cargo'].queryset
                .filter(ativo=True)
                .order_by('nome')
            )
            self.fields['cargo'].empty_label = '— Selecione um Cargo (opcional) —'

        # ── Função ST: filtra ativas, ordena por nome ──
        if 'funcao_st' in self.fields:
            self.fields['funcao_st'].required = False
            self.fields['funcao_st'].queryset = (
                self.fields['funcao_st'].queryset
                .filter(ativo=True)
                .order_by('nome')
            )
            self.fields['funcao_st'].empty_label = '— Selecione uma Função (opcional) —'

        # ── Local: filtra locais vinculados ao documento ──
        if ltcat and 'local_prestacao' in self.fields:
            locais_ids = ltcat.documento_locais.values_list(
                'local_prestacao_id', flat=True
            )
            self.fields['local_prestacao'].queryset = (
                self.fields['local_prestacao'].queryset.filter(pk__in=locais_ids)
            )


# ═══════════════════════════════════════════════════════
# RECONHECIMENTO DE RISCO (Seção 7)
# ═══════════════════════════════════════════════════════
class ReconhecimentoRiscoForm(BaseFormMixin, forms.ModelForm):
    class Meta:
        model = ReconhecimentoRisco
        fields = [
            'funcao',  # ← ADICIONADO
            'tipo_risco', 'agente', 'fonte_geradora',
            'exposicao', 'tipo_avaliacao',
            'limite_tolerancia', 'resultado_avaliacao', 'unidade_medida',
        ]
        widgets = {
            'fonte_geradora': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'funcao': 'Função / GHE',
            'tipo_risco': 'Tipo de Risco',
            'agente': 'Agente Nocivo',
            'fonte_geradora': 'Fonte Geradora',
            'exposicao': 'Exposição',
            'tipo_avaliacao': 'Tipo de Avaliação',
            'limite_tolerancia': 'Limite de Tolerância',
            'resultado_avaliacao': 'Resultado da Avaliação',
            'unidade_medida': 'Unidade de Medida',
        }

    def __init__(self, *args, ltcat=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ltcat = ltcat

        # Filtra funções do LTCAT
        if ltcat and 'funcao' in self.fields:
            self.fields['funcao'].queryset = FuncaoAnalisada.objects.filter(
                ltcat_documento=ltcat, ativo=True
            ).order_by('nome_funcao')
            self.fields['funcao'].empty_label = '— Selecione a Função/GHE —'
        elif 'funcao' in self.fields:
            self.fields['funcao'].queryset = FuncaoAnalisada.objects.none()


# ═══════════════════════════════════════════════════════
# PERICULOSIDADE (Seção 8)
# ═══════════════════════════════════════════════════════
class AvaliacaoPericulosidadeForm(BaseFormMixin, forms.ModelForm):
    class Meta:
        model = AvaliacaoPericulosidade
        fields = [
            'tipo', 'aplicavel', 'funcoes_expostas', 'descricao',
        ]
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 5}),
            'funcoes_expostas': forms.SelectMultiple(attrs={'size': 5}),
        }
        labels = {
            'tipo': 'Tipo de Periculosidade (NR-16)',
            'aplicavel': 'Aplicável?',
            'funcoes_expostas': 'Funções Expostas',
            'descricao': 'Descrição / Justificativa',
        }

    def __init__(self, *args, ltcat=None, **kwargs):
        super().__init__(*args, **kwargs)
        if ltcat:
            self.fields['funcoes_expostas'].queryset = (
                FuncaoAnalisada.objects.filter(
                    ltcat_documento=ltcat, ativo=True
                ).order_by('nome_funcao')
            )

# ═══════════════════════════════════════════════════════
# CONCLUSÃO POR FUNÇÃO (Seção 9)
# ═══════════════════════════════════════════════════════
class ConclusaoFuncaoForm(BaseFormMixin, forms.ModelForm):
    class Meta:
        model = ConclusaoFuncao
        fields = [
            'funcao', 'tipo_conclusao', 'codigo_gfip',
            'faz_jus_insalubridade', 'faz_jus_periculosidade',
            'faz_jus_aposentadoria_especial', 'justificativa',
        ]
        widgets = {
            'justificativa': forms.Textarea(attrs={'rows': 6}),
        }
        labels = {
            'funcao': 'Função Analisada',
            'tipo_conclusao': 'Tipo de Conclusão',
            'codigo_gfip': 'Código GFIP / SEFIP',
            'faz_jus_insalubridade': 'Insalubridade',
            'faz_jus_periculosidade': 'Periculosidade',
            'faz_jus_aposentadoria_especial': 'Aposentadoria Especial',
            'justificativa': 'Justificativa / Fundamentação',
        }

    def __init__(self, *args, ltcat=None, **kwargs):
        super().__init__(*args, **kwargs)
        if ltcat:
            self.fields['funcao'].queryset = (
                FuncaoAnalisada.objects.filter(
                    ltcat_documento=ltcat, ativo=True
                ).order_by('nome_funcao')
            )


# ═══════════════════════════════════════════════════════
# RECOMENDAÇÃO TÉCNICA (Seção 10)
# ═══════════════════════════════════════════════════════
class RecomendacaoTecnicaForm(BaseFormMixin, forms.ModelForm):
    class Meta:
        model = RecomendacaoTecnica
        fields = [
            'descricao', 'prioridade', 'prazo_implementacao',
            'ordem', 'implementada', 'data_implementacao',
        ]
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 5}),
            'data_implementacao': forms.DateInput(
                attrs={'type': 'date'}, format='%Y-%m-%d'
            ),
            'prazo_implementacao': forms.DateInput(
                attrs={'type': 'date'}, format='%Y-%m-%d'
            ),
        }
        labels = {
            'descricao': 'Descrição da Recomendação',
            'prioridade': 'Prioridade',
            'prazo_implementacao': 'Prazo para Implementação',
            'ordem': 'Ordem de Exibição',
            'implementada': 'Implementada?',
            'data_implementacao': 'Data de Implementação',
        }


# ═══════════════════════════════════════════════════════
# ANEXO
# ═══════════════════════════════════════════════════════
class AnexoLTCATForm(BaseFormMixin, forms.ModelForm):
    class Meta:
        model = AnexoLTCAT
        fields = [
            'tipo', 'titulo', 'ordem', 'arquivo', 'descricao',
        ]
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'tipo': 'Tipo de Anexo',
            'titulo': 'Título (opcional)',
            'ordem': 'Ordem',
            'arquivo': 'Arquivo',
            'descricao': 'Descrição',
        }

