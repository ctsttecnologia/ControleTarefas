from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Treinamento, TipoTreinamento
from .forms import TreinamentoForm, TipoTreinamentoForm

# Treinamento Views

def listar_treinamentos(request):
    treinamentos = Treinamento.objects.all().order_by('data_inicio')
    return render(request, 'treinamentos/listar_treinamentos.html', {'treinamentos': treinamentos})

def detalhes_treinamento(request, pk):
    treinamento = get_object_or_404(Treinamento, pk=pk)
    return render(request, 'treinamentos/detalhes_treinamento.html', {'treinamento': treinamento})

def cadastrar_treinamento(request):
    if request.method == 'POST':
        form = TreinamentoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Treinamento cadastrado com sucesso!')
            return redirect('treinamentos:listar_treinamentos')
    else:
        form = TreinamentoForm()
    
    return render(request, 'treinamentos/cadastrar_treinamento.html', {'form': form})

def editar_treinamento(request, pk):
    treinamento = get_object_or_404(Treinamento, pk=pk)
    if request.method == 'POST':
        form = TreinamentoForm(request.POST, instance=treinamento)
        if form.is_valid():
            form.save()
            messages.success(request, 'Treinamento atualizado com sucesso!')
            return redirect('treinamentos:listar_treinamentos')
    else:
        form = TreinamentoForm(instance=treinamento)
    
    return render(request, 'treinamentos/editar_treinamento.html', {'form': form})

def excluir_treinamento(request, pk):
    treinamento = get_object_or_404(Treinamento, pk=pk)
    if request.method == 'POST':
        treinamento.delete()
        messages.success(request, 'Treinamento excluído com sucesso!')
        return redirect('treinamentos:listar_treinamentos')
    
    return render(request, 'treinamentos/confirmar_exclusao.html', {'treinamento': treinamento})

def listar_tipos_treinamento(request):
    tipos = TipoTreinamento.objects.all()
    return render(request, 'treinamentos/listar_tipos_treinamento.html', {'tipos_treinamento': tipos})

def buscar_treinamentos(request):
    query = request.GET.get('q')
    resultados = Treinamento.objects.filter(nome_treinamento__icontains=query) if query else None
    return render(request, 'treinamentos/listar_treinamentos.html', {'resultados': resultados, 'query': query})

def treinamentos_disponiveis(request):
    treinamentos = Treinamento.objects.all()
    return render(request, 'treinamentos/treinamentos_disponiveis.html', {'treinamentos': treinamentos})

def treinamentos_colaborador(request, colaborador_id):
    colaborador = get_object_or_404(Colaborador, pk=colaborador_id)
    
    # Filtros
    status = request.GET.get('status')
    tipo = request.GET.get('tipo')
    
    treinamentos = colaborador.treinamentos.all()
    
    if status:
        treinamentos = treinamentos.filter(status=status)
    if tipo:
        treinamentos = treinamentos.filter(treinamento__tipo=tipo)
    
    # Contadores para os cards
    treinamentos_ativos = colaborador.treinamentos.filter(status='ativo').count()
    treinamentos_proximos = colaborador.treinamentos.filter(status='proximo').count()
    treinamentos_expirados = colaborador.treinamentos.filter(status='expirado').count()
    
    context = {
        'aluno': colaborador,
        'treinamentos': treinamentos,
        'treinamentos_ativos': treinamentos_ativos,
        'treinamentos_proximos': treinamentos_proximos,
        'treinamentos_expirados': treinamentos_expirados,
    }
    
    return render(request, 'treinamentos/treinamentos_colaborador.html', context)

def adicionar_treinamento_colaborador(request, colaborador_id):
    colaborador = get_object_or_404(Colaborador, pk=colaborador_id)
    
    if request.method == 'POST':
        form = TreinamentoColaboradorForm(request.POST, request.FILES)
        if form.is_valid():
            treinamento_colab = form.save(commit=False)
            treinamento_colab.colaborador = colaborador
            treinamento_colab.save()
            messages.success(request, 'Treinamento adicionado com sucesso!')
            return redirect('treinamentos_colaborador', colaborador_id=colaborador.id)
    else:
        form = TreinamentoColaboradorForm()
    
    return render(request, 'treinamentos/adicionar_treinamento.html', {
        'form': form,
        'colaborador': colaborador
    })








