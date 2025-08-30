#controle_de_telefones/forms.py

from django import forms
from .models import Aparelho, Marca, Modelo, Operadora, Plano, LinhaTelefonica, Vinculo, LinhaTelefonica



class AparelhoForm(forms.ModelForm):

    # 1. Declaramos o campo 'imei' manualmente.
    #    Isso diz ao Django para criar um campo de texto no formulário,
    #    mesmo que não haja uma coluna 'imei' no banco de dados.
    imei = forms.CharField(
        label="IMEI",
        required=True, # Defina como False se não for obrigatório
        max_length=15, 
        help_text="O número IMEI será armazenado de forma segura."
    )
    class Meta:
        model = Aparelho
       
        fields = [
            'modelo', 
            'filial',
            'numero_serie', 
            'data_aquisicao', 
            'valor_aquisicao', 
            'status', 
            'observacoes'
        ]
        widgets = {'data_aquisicao': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

     # 3. Populamos o valor inicial do campo 'imei'.
        #    Se o formulário estiver sendo usado para editar um aparelho (`self.instance.pk` existe),
        #    nós pegamos o valor descriptografado usando a property `self.instance.imei`
        #    e o colocamos como valor inicial do campo do formulário.
        if self.instance and self.instance.pk:
            self.fields['imei'].initial = self.instance.imei

        # Aplica a classe 'form-control' a todos os campos
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            
    def save(self, commit=True):
        # 4. Sobrescrevemos o método save() para lidar com a property.
        
        # Primeiro, pegamos o objeto 'Aparelho' sem salvá-lo no banco de dados ainda.
        # Isso nos dá uma instância do modelo preenchida com os dados dos campos da classe Meta.
        aparelho = super().save(commit=False)
        
        # Agora, pegamos o valor limpo do nosso campo customizado 'imei'.
        imei_digitado = self.cleaned_data['imei']
        
        # E o atribuímos à property do modelo. O setter `@imei.setter` será
        # chamado automaticamente, criptografando o valor e armazenando em `encrypted_imei`.
        aparelho.imei = imei_digitado
        
        # Se commit=True, salvamos a instância completa no banco de dados.
        if commit:
            aparelho.save()
            
        return aparelho

class MarcaForm(forms.ModelForm):
    class Meta:
        model = Marca
        fields = ['nome']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nome'].widget.attrs['class'] = 'form-control'

class ModeloForm(forms.ModelForm):
    class Meta:
        model = Modelo
        fields = ['marca', 'nome']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

class OperadoraForm(forms.ModelForm):
    class Meta:
        model = Operadora
        fields = ['nome']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nome'].widget.attrs['class'] = 'form-control'

class PlanoForm(forms.ModelForm):
    class Meta:
        model = Plano
        fields = ['operadora', 'nome', 'valor_mensal', 'franquia_dados_gb']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

class LinhaTelefonicaForm(forms.ModelForm):
    class Meta:
        model = LinhaTelefonica
        # O campo 'filial' foi removido da lista de 'fields'
        fields = ['plano', 'numero', 'data_ativacao', 'status']
        widgets = {'data_ativacao': forms.DateInput(attrs={'type': 'date'})}
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

class VinculoForm(forms.ModelForm):
    class Meta:
        model = Vinculo
        fields = ['funcionario', 'aparelho', 'linha', 'data_entrega', 'data_devolucao', 'termo_responsabilidade']
        widgets = {
            'data_entrega': forms.DateInput(attrs={'type': 'date'}),
            'data_devolucao': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name != 'termo_responsabilidade':
                field.widget.attrs['class'] = 'form-control'
