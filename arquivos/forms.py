from django import forms
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from .models import Arquivo
from documentos.models import Documento

class ArquivoForm(forms.ModelForm):
    # --- Campos que serão salvos no app 'Documentos' ---
    doc_arquivo = forms.FileField(
        label="Arquivo (PDF/Imagem)", 
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    doc_inicio = forms.DateField(
        label="Data de Emissão/Início",
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    doc_vencimento = forms.DateField(
        label="Data de Vencimento", 
        required=False, 
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    doc_responsavel = forms.ModelChoiceField(
        queryset=get_user_model().objects.none(), # Popula no __init__
        label="Responsável",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Arquivo
        fields = ['nome', 'tipo', 'cliente', 'status', 'dias_aviso', 'descricao']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'dias_aviso': forms.NumberInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'cliente': forms.Select(attrs={'class': 'form-select select2'}),
        }

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtra usuários (responsáveis) com base na regra de negócio (ex: apenas ativos)
        self.fields['doc_responsavel'].queryset = get_user_model().objects.filter(is_active=True)

        # Se for edição, popula os campos virtuais com dados do documento existente
        if self.instance.pk:
            doc = self.instance.documento_vigente
            if doc:
                self.initial['doc_inicio'] = doc.data_emissao
                self.initial['doc_vencimento'] = doc.data_vencimento
                self.initial['doc_responsavel'] = doc.responsavel
                # Nota: FileField não pode ter initial value por segurança do navegador
        # Filtra clientes apenas da filial do usuário (Regra de segurança)
        # Assumindo que seu model Cliente também tem vínculo com Filial
        if 'cliente' in self.fields:
             from cliente.models import Cliente # Importe aqui para evitar erro circular
             self.fields['cliente'].queryset = Cliente.objects.filter(filial=user.filial_ativa)

    def save(self, commit=True, user=None):
        # 1. Salva o Arquivo (Metadados)
        arquivo_obj = super().save(commit=False)
        if user and not arquivo_obj.pk:
            arquivo_obj.filial = user.filial_ativa  # Atribui filial se for novo
        
        if commit:
            arquivo_obj.save()

            # 2. Gerencia o Documento Genérico (Arquivo e Datas)
            uploaded_file = self.cleaned_data.get('doc_arquivo')
            
            defaults = {
                'nome': arquivo_obj.nome, # O nome do doc segue o nome do arquivo
                'data_emissao': self.cleaned_data.get('doc_inicio'),
                'data_vencimento': self.cleaned_data.get('doc_vencimento'),
                'responsavel': self.cleaned_data.get('doc_responsavel'),
                'filial': arquivo_obj.filial,
                'status': 'VIGENTE', # Status do documento (validade), não do arquivo (pasta)
            }

            # Verifica se já existe documento
            doc_atual = arquivo_obj.documento_vigente

            if doc_atual:
                # Atualiza o existente
                if uploaded_file: # Só atualiza arquivo se enviou um novo
                    doc_atual.arquivo = uploaded_file
                
                for key, value in defaults.items():
                    setattr(doc_atual, key, value)
                doc_atual.save()
            else:
                # Cria um novo registro no app Documentos
                if uploaded_file:
                    defaults['arquivo'] = uploaded_file
                    defaults['content_type'] = ContentType.objects.get_for_model(Arquivo)
                    defaults['object_id'] = arquivo_obj.pk
                    Documento.objects.create(**defaults)
        
        return arquivo_obj