#controle_de_telefones/forms.py

from datetime import date
from django import forms
from django.urls import reverse
from cliente import models
from core.managers import FilialManager
from .models import Aparelho, Marca, Modelo, Operadora, Plano, LinhaTelefonica, Vinculo, LinhaTelefonica
from departamento_pessoal.models import Funcionario
from .models import Vinculo
import base64
import uuid
from django.core.files.base import ContentFile



class AparelhoForm(forms.ModelForm):

    imei = forms.CharField(
        label="IMEI",
        required=True, 
        max_length=15, 
        help_text="O número IMEI será armazenado de forma segura."
    )
    class Meta:
        model = Aparelho
       
        fields = [
            'tipo_de_aparelho',
            'modelo', 
            'filial',
            'imei',
            'numero_serie', 
            'data_aquisicao', 
            'valor_aquisicao', 
            'status',
            'acessorios', 
            'observacoes',
            
        ]
        widgets = {'data_aquisicao': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        fields = [
            'funcionario',
            'aparelho', 
            'linha',
            'data_entrega', 
            'data_devolucao', 
            'status',
            'termo_assinado_upload', 
            'foi_assinado', 
        ]
        widgets = {
            'data_entrega': forms.DateInput(attrs={'type': 'date'}),
            'data_devolucao': forms.DateInput(attrs={'type': 'date'}),
            'termo_assinado_upload': forms.ClearableFileInput(),
            'foi_assinado': forms.CheckboxInput(),

        }

    def __init__(self, *args, **kwargs):
        # 1. Capture e remova o 'filial_id' ANTES de chamar o método pai.
        filial_id = kwargs.pop('filial_id', None)

        # 2. Chame o método pai com os argumentos já "limpos".
        super().__init__(*args, **kwargs)
        
        # 3. Use o filial_id para filtrar os campos do formulário.
        if filial_id:
            # Filtra funcionários para mostrar apenas os da filial ativa e que não foram demitidos.
            self.fields['funcionario'].queryset = Funcionario.objects.filter(
                filial_id=filial_id, data_demissao__isnull=True
            )
            
            # Filtra aparelhos e linhas para mostrar apenas os disponíveis na filial ativa.
            # O 'self.instance.pk' garante que, na edição, o item já selecionado continue aparecendo.
            aparelho_atual = self.instance.aparelho
            linha_atual = self.instance.linha

            aparelhos_disponiveis = Aparelho.objects.filter(filial_id=filial_id, status='disponivel')
            if aparelho_atual:
                aparelhos_disponiveis = aparelhos_disponiveis | Aparelho.objects.filter(pk=aparelho_atual.pk)
            self.fields['aparelho'].queryset = aparelhos_disponiveis

            linhas_disponiveis = LinhaTelefonica.objects.filter(filial_id=filial_id, status='disponivel')
            if linha_atual:
                linhas_disponiveis = linhas_disponiveis | LinhaTelefonica.objects.filter(pk=linha_atual.pk)
            self.fields['linha'].queryset = linhas_disponiveis
        # self.instance é o objeto que está sendo editado.
        # Verificamos se a instância existe e se já tem uma data de entrega.
        instance = getattr(self, 'instance', None)
        if instance and instance.pk and instance.data_entrega:
            # Se a data de entrega já foi definida, desabilita o campo de data de entrega
            self.fields['data_entrega'].disabled = True
            self.fields['data_entrega'].help_text = 'A data de entrega não pode ser alterada pois o recebimento já foi registrado.'

    # Garantir a cronologia com validação
    def clean(self):
        cleaned_data = super().clean()
        data_entrega = cleaned_data.get("data_entrega")
        data_recebimento = cleaned_data.get("data_recebimento")

        if data_entrega and data_recebimento:
            # Garante que a data de recebimento não seja anterior à de entrega
            if data_recebimento < data_entrega:
                raise forms.ValidationError(
                    "A data de recebimento não pode ser anterior à data de entrega."
                )
        return cleaned_data    


# Renomeei seu formulário para mais clareza
class VinculoAssinaturaForm(forms.ModelForm):
    # Campo oculto para receber os dados da imagem em base64 do front-end
    assinatura_base64 = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Vinculo
        # Nenhum campo do modelo precisa ser exibido diretamente pelo Django
        fields = []

    def save(self, commit=True):
        vinculo = super().save(commit=False)
        
        # Pega os dados da assinatura do campo com o nome correto
        assinatura_base64_data = self.cleaned_data.get('assinatura_base64')

        if assinatura_base64_data:
            try:
                # O front-end envia um cabeçalho 'data:image/png;base64,' que precisa ser removido.
                format, imgstr = assinatura_base64_data.split(';base64,') 
                ext = format.split('/')[-1]
                
                # Decodifica os dados base64 para binário
                data = ContentFile(base64.b64decode(imgstr))
                
                # Cria um nome de arquivo único
                file_name = f'assinatura_{vinculo.pk}_{uuid.uuid4().hex}.{ext}'
                
                # Associa o arquivo de imagem decodificado ao campo do modelo
                vinculo.assinatura_digital.save(file_name, data, save=False)

            except (ValueError, TypeError) as e:
                # Lida com casos onde a string base64 é inválida
                print(f"Erro ao decodificar a assinatura: {e}")
                pass

        if commit:
            vinculo.save()
            
        return vinculo

           
