from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Treinamento, TipoTreinamento
from .forms import TreinamentoForm, TipoTreinamentoForm

# Treinamento Views
def listar_treinamentos(request):
    treinamentos = Treinamento.objects.all().order_by('-data_inicio')
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

# TipoTreinamento Views
def listar_tipos_treinamento(request):
    tipos = TipoTreinamento.objects.all()
    return render(request, 'treinamentos/listar_treinamentos.html', {'tipos_treinamento': tipos})

def buscar_treinamentos(request):
    query = request.GET.get('q')
    resultados = Treinamento.objects.filter(nome__icontains=query) if query else None
    return render(request, 'treinamentos/buscar_treinamentos.html', {'resultados': resultados, 'query': query})