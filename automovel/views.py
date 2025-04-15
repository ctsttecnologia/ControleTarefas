from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import CarroForm, AgendamentoForm
from django.contrib import messages
from automovel.models import Carro, Agendamento

@login_required
def lista_carros(request):
    carros = Carro.objects.all()
    return render(request, 'automovel/lista_carros.html', {'carros': carros})

@login_required
def adicionar_carro(request):
    if request.method == 'POST':
        form = CarroForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Carro adicionado com sucesso!')
            return redirect('automovel:lista_carros')
    else:
        form = CarroForm()
    return render(request, 'automovel/carro_form.html', {'form': form})

@login_required
def editar_carro(request, renavan):
    carro = get_object_or_404(Carro, renavan=renavan)
    if request.method == 'POST':
        form = CarroForm(request.POST, instance=carro)
        if form.is_valid():
            form.save()
            messages.success(request, 'Carro atualizado com sucesso!')
            return redirect('automovel:lista_carros')
    else:
        form = CarroForm(instance=carro)
    return render(request, 'automovel/carro_form.html', {'form': form})

@login_required
def excluir_carro(request, renavan):
    carro = get_object_or_404(Carro, renavan=renavan)
    if request.method == 'POST':
        carro.delete()
        messages.success(request, 'Carro excluído com sucesso!')
        return redirect('automovel:lista_carros')
    return render(request, 'automovel/confirmar_exclusao.html', {'obj': carro})

@login_required
def lista_agendamentos(request):
    agendamentos = Agendamento.objects.all()
    return render(request, 'automovel/lista_agendamentos.html', {'agendamentos': agendamentos})

@login_required
def adicionar_agendamento(request):
    if request.method == 'POST':
        form = AgendamentoForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                agendamento = form.save(commit=False)
                # Adiciona o usuário atual como responsável se não estiver preenchido
                if not agendamento.responsavel:
                    agendamento.responsavel = request.user.get_full_name() or request.user.username
                agendamento.save()
                messages.success(request, 'Agendamento criado com sucesso!')
                return redirect('automovel:lista_agendamentos')
            except Exception as e:
                messages.error(request, f'Erro ao salvar agendamento: {str(e)}')
        else:
            messages.error(request, 'Por favor, corrija os erros abaixo.')
    else:
        form = AgendamentoForm(initial={
            'pedagio': 'N',
            'abastecimento': 'N',
            'cancelar_agenda': 'N',
            'status': 'agendado'
        })
    
    context = {
        'form': form,
        'title': 'Novo Agendamento',
        'current_page': 'agendamento'
    }
    return render(request, 'automovel/agendamento_form.html', context)


@login_required
def editar_agendamento(request, pk):
    agendamento = get_object_or_404(Agendamento, pk=pk)
    if request.method == 'POST':
        form = AgendamentoForm(request.POST, request.FILES, instance=agendamento)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Agendamento atualizado com sucesso!')
                return redirect('automovel:lista_agendamentos')
            except Exception as e:
                messages.error(request, f'Erro ao atualizar agendamento: {str(e)}')
        else:
            messages.error(request, 'Por favor, corrija os erros abaixo.')
    else:
        form = AgendamentoForm(instance=agendamento)
    
    context = {
        'form': form,
        'title': 'Editar Agendamento',
        'current_page': 'agendamento'
    }
    return render(request, 'automovel/agendamento_form.html', context)


@login_required
def excluir_agendamento(request, pk):
    agendamento = get_object_or_404(Agendamento, pk=pk)
    if request.method == 'POST':
        agendamento.delete()
        messages.success(request, 'Agendamento excluído com sucesso!')
        return redirect('automovel:lista_agendamentos')
    return render(request, 'automovel/confirmar_exclusao.html', {'obj': agendamento})

@login_required
def assinar_agendamento(request, pk):
    agendamento = get_object_or_404(Agendamento, pk=pk)
    if request.method == 'POST':
        assinatura = request.POST.get('assinatura')
        if assinatura:
            agendamento.assinatura = assinatura
            agendamento.save()
            messages.success(request, 'Assinatura registrada com sucesso!')
            return redirect('automovel:lista_agendamentos')
    return render(request, 'automovel/assinar.html', {'agendamento': agendamento})



