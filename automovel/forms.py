from django import forms
from .models import Carro, Carro_agendamento, Carro_checklist, Carro_foto, Carro_manutencao
from django.utils import timezone


class CarroForm(forms.ModelForm):
    class Meta:
        model = Carro
        # MUDANÇA: Lista explícita de campos. 'filial' e 'ativo' são controlados pelo sistema.
        fields = [
            'placa', 'modelo', 'marca', 'cor', 'ano', 'renavan', 
            'quilometragem', 'data_ultima_manutencao', 'data_proxima_manutencao',
            'disponivel', 'observacoes', 'foto'
        ]
        widgets = {
            'observacoes': forms.Textarea(attrs={'rows': 3}),
            'data_ultima_manutencao': forms.DateInput(attrs={'type': 'date'}),
            'data_proxima_manutencao': forms.DateInput(attrs={'type': 'date'}),
        }

class AgendamentoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['carro'].disabled = True
            self.fields['data_hora_agenda'].disabled = True
            self.fields['data_hora_agenda'].help_text = "A data de agendamento não pode ser alterada."

    class Meta:
        model = Carro_agendamento
        # MUDANÇA: Lista explícita. Campos como 'usuario', 'filial', 'status' são controlados pelo sistema.
        fields = [
            'carro', 'funcionario', 'data_hora_agenda', 'data_hora_devolucao',
            'cm', 'descricao', 'pedagio', 'abastecimento', 'km_inicial', 'km_final',
            'responsavel', 'ocorrencia', 'assinatura'
        ]
        widgets = {
            'data_hora_agenda': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'data_hora_devolucao': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'descricao': forms.Textarea(attrs={'rows': 3}),
            'ocorrencia': forms.Textarea(attrs={'rows': 3}),
            'assinatura': forms.HiddenInput(),
        }

class ChecklistForm(forms.ModelForm):

    # Adicionado campo para coletar o KM inicial na SAÍDA.
    km_inicial = forms.IntegerField(
        label="Quilometragem Inicial do Veículo",
        required=False,
        widget=forms.NumberInput(attrs={'placeholder': 'Ex: 12500'})
    )

    # Adicionado campo para coletar o KM inicial no RETORNO.
    km_final = forms.IntegerField(
        label="Quilometragem Final do Veículo",
        required=False,  # A obrigatoriedade será validada na view.
        widget=forms.NumberInput(attrs={'placeholder': 'Ex: 15000'})
    )

    class Meta:
        model = Carro_checklist

        fields = [
            'tipo', 'data_hora',
            'revisao_frontal_status', 'foto_frontal',
            'revisao_trazeira_status', 'foto_trazeira',
            'revisao_lado_motorista_status', 'foto_lado_motorista',
            'revisao_lado_passageiro_status', 'foto_lado_passageiro',
            'observacoes_gerais', 'assinatura',
        ]
        widgets = {
            'tipo': forms.HiddenInput(),
            'data_hora': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'observacoes_gerais': forms.Textarea(attrs={'rows': 2}),
            'assinatura': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):

        tipo_checklist = kwargs.pop('tipo_checklist', None)

        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            self.fields['data_hora'].initial = timezone.now().strftime('%Y-%m-%dT%H:%M')

        # Lógica para mostrar o campo km_final apenas se for um checklist de retorno.
        if tipo_checklist != 'retorno':
            if 'km_final' in self.fields:
                del self.fields['km_final']
        # Lógica para mostrar o campo correto para cada tipo.
        if tipo_checklist == 'saida':
            # Se for saída, removemos o km_final
            if 'km_final' in self.fields:
                del self.fields['km_final']
        elif tipo_checklist == 'retorno':
            # Se for retorno, removemos o km_inicial
            if 'km_inicial' in self.fields:
                del self.fields['km_inicial']
        else:
            # Se não for nenhum dos dois, removemos ambos
            if 'km_inicial' in self.fields:
                del self.fields['km_inicial']
            if 'km_final' in self.fields:
                del self.fields['km_final']

    def clean(self):
        cleaned_data = super().clean()
        agendamento = self.initial.get('agendamento')
        tipo = cleaned_data.get('tipo')

        # Validação para garantir que um checklist de retorno só seja criado se houver um de saída
        if tipo == 'retorno' and agendamento:
            if not agendamento.checklists.filter(tipo='saida').exists():
                raise forms.ValidationError("Não é possível registrar o retorno sem antes ter registrado a saída.")
        
        return cleaned_data

    def clean_assinatura(self):
        assinatura = self.cleaned_data.get('assinatura')
        if not assinatura:
            raise forms.ValidationError("A assinatura digital do responsável é obrigatória.")
        return assinatura

class FotoForm(forms.ModelForm):
    class Meta:
        model = Carro_foto
        # MUDANÇA: Lista explícita. 'agendamento' e 'filial' são definidos pela view.
        fields = ['imagem', 'observacao']

class ManutencaoForm(forms.ModelForm):
    class Meta:
        model = Carro_manutencao
        fields = ['data_manutencao', 'tipo', 'descricao', 'custo', 'concluida', 'observacoes']
        widgets = {
            'data_manutencao': forms.DateInput(attrs={'type': 'date'}),
            'descricao': forms.Textarea(attrs={'rows': 3}),
            'observacoes': forms.Textarea(attrs={'rows': 2}),
        }
    
    def clean_data_manutencao(self):
        data_manutencao = self.cleaned_data.get('data_manutencao')
        if data_manutencao and data_manutencao < timezone.now().date():
            raise forms.ValidationError("A data da manutenção não pode ser no passado.")
        return data_manutencao

