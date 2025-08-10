# seguranca_trabalho/forms.py

from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Equipamento, FichaEPI, EntregaEPI, Fabricante, Fornecedor
from departamento_pessoal.models import Funcionario
import pathlib

class FabricanteForm(forms.ModelForm):
    class Meta:
        model = Fabricante
        fields = ['nome', 'cnpj', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'cnpj': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00.000.000/0000-00'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class FornecedorForm(forms.ModelForm):
    class Meta:
        model = Fornecedor
        fields = ['razao_social', 'nome_fantasia', 'cnpj', 'email', 'telefone', 'ativo']
        widgets = {
            'razao_social': forms.TextInput(attrs={'class': 'form-control'}),
            'nome_fantasia': forms.TextInput(attrs={'class': 'form-control'}),
            'cnpj': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00.000.000/0000-00'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(00) 00000-0000'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class EquipamentoForm(forms.ModelForm):
    class Meta:
        model = Equipamento
        fields = [
            'nome', 'modelo', 'fabricante', 'fornecedor_padrao', 
            'certificado_aprovacao', 'data_validade_ca', 'vida_util_dias',
            'estoque_minimo', 'requer_numero_serie', 'foto', 'observacoes', 'ativo'
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Protetor Auricular Plug'}),
            'modelo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 1100'}),
            'fabricante': forms.Select(attrs={'class': 'form-select'}),
            'fornecedor_padrao': forms.Select(attrs={'class': 'form-select'}),
            'certificado_aprovacao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 5745'}),
            'data_validade_ca': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'vida_util_dias': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'estoque_minimo': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'foto': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'requer_numero_serie': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class FichaEPIForm(forms.ModelForm):
    class Meta:
        model = FichaEPI
        fields = ['funcionario'] # Apenas o funcionário é necessário, o resto é preenchido no model/view
        widgets = {
            'funcionario': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtra para mostrar apenas funcionários ativos que ainda não têm ficha
        funcionarios_com_ficha = FichaEPI.objects.values_list('funcionario_id', flat=True)
        self.fields['funcionario'].queryset = Funcionario.objects.filter(status='ATIVO').exclude(id__in=funcionarios_com_ficha)
        self.fields['funcionario'].label_from_instance = lambda obj: f"{obj.nome_completo} (Mat. {obj.id})"

    def clean_funcionario(self):
        funcionario = self.cleaned_data['funcionario']
        if not hasattr(funcionario, 'cargo') or not funcionario.cargo:
            raise forms.ValidationError(
                _("O funcionário selecionado não possui um cargo definido. Por favor, atualize o cadastro no Departamento Pessoal."),
                code='sem_cargo'
            )
        return funcionario


class EntregaEPIForm(forms.ModelForm):
    class Meta:
        model = EntregaEPI
        fields = ['equipamento', 'quantidade', 'lote', 'numero_serie']
        widgets = {
            'equipamento': forms.Select(attrs={'class': 'form-select'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'lote': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_serie': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        # 1. Remove o argumento 'filial' de kwargs antes de chamar o construtor pai.
        filial = kwargs.pop('filial', None)
        
        # 2. Chama o construtor pai de forma segura.
        super().__init__(*args, **kwargs)
        
        # 3. Usa o argumento 'filial' para filtrar a queryset de equipamentos.
        if filial:
            self.fields['equipamento'].queryset = Equipamento.objects.filter(ativo=True, filial=filial)
        else:
            # Fallback para evitar que o campo fique sem opções caso a filial não seja passada.
            self.fields['equipamento'].queryset = Equipamento.objects.filter(ativo=True)

    @property
    def get_assinatura_imagem_path_for_pdf(self):
        """
        Retorna o caminho da imagem de assinatura em formato de URI (file:///),
        que é o formato correto para o gerador de PDF (WeasyPrint).
        """
        if self.assinatura_imagem and hasattr(self.assinatura_imagem, 'path'):
            try:
                return pathlib.Path(self.assinatura_imagem.path).as_uri()
            except Exception:
                return None
        return None
        
class AssinaturaForm(forms.Form):
    assinatura_base64 = forms.CharField(widget=forms.HiddenInput())
        


